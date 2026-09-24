"""Reproducible end-to-end native EMB benchmark; failures are retained.

Data generation, input decoding, scoring and file writes are outside timing.
Preprocessing, bootstrap, EM, conditional draws and output materialization are
inside timing. Use benchmark_reference.R separately for the same data/config.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import torch

from amelia_torch import amelia
from amelia_torch.backends import resolve_backend, synchronize

ROOT = Path(__file__).resolve().parents[1]


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_revision():
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return {
        "commit": revision.stdout.strip() if revision.returncode == 0 else None,
        "dirty": bool(status.stdout.strip()),
    }


def metrics(outputs, original, truth, mask):
    observed = ~np.isnan(original)
    expected_finite = ~np.isnan(original).all(axis=1)
    scale = np.nanstd(truth, axis=0, ddof=1)
    errors, unscored = [], []
    unexpected_nonfinite = []
    for completed in outputs:
        with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
            residual = (completed - truth) / scale
        valid = mask & np.isfinite(residual)
        missing_score_count = int(mask.sum() - valid.sum())
        errors.append(
            float(np.sqrt(np.mean(residual[valid] ** 2)))
            if mask.any() and missing_score_count == 0 else None
        )
        unscored.append(missing_score_count)
        unexpected_nonfinite.append(int((~np.isfinite(completed[expected_finite])).sum()))
    observed_preserved = bool(outputs) and all(
        np.array_equal(out[observed], original[observed]) for out in outputs
    )
    whole_rows_preserved = bool(outputs) and all(
        np.isnan(out[~expected_finite]).all() for out in outputs
    )
    quality_passed = (
        observed_preserved and whole_rows_preserved
        and not any(unexpected_nonfinite) and not any(unscored)
        and all(score is not None and np.isfinite(score) for score in errors)
    )
    return {
        "quality_passed": bool(quality_passed),
        "observed_values_preserved": observed_preserved,
        "wholly_missing_rows_preserved": whole_rows_preserved,
        "remaining_missing_cells": [int(np.isnan(out).sum()) for out in outputs],
        "unexpected_nonfinite_cells": unexpected_nonfinite,
        "normalized_rmse_per_imputation": errors,
        "unscored_heldout_cells_per_imputation": unscored,
        "pooled_column_means": np.mean(
            [np.nanmean(out, axis=0) for out in outputs], axis=0
        ).tolist(),
        "note": "Held-out prediction scores are not tests of Rubin pooling or interval coverage.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--device", choices=["cpu", "mps", "cuda"], default="cpu")
    parser.add_argument("--dtype", choices=["float64", "float32"], default="float64")
    parser.add_argument("--m", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20260923)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--tolerance", type=float, default=1e-4)
    parser.add_argument("--max-iterations", type=int, default=300)
    parser.add_argument("--empri", type=float)
    parser.add_argument("--autopri", type=float, default=0.05)
    args = parser.parse_args()
    if args.repeats < 1 or args.warmups < 0 or args.threads < 1:
        parser.error("Invalid repeat/warmup/thread count")
    if args.device == "mps" and os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK") != "0":
        parser.error("Set PYTORCH_ENABLE_MPS_FALLBACK=0 before launching GPU benchmarks")
    torch.set_num_threads(args.threads)
    # Float32 comparisons must not silently use reduced precision TF32 kernels.
    if args.device == "cuda":
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
    dev, _ = resolve_backend(args.device, args.dtype)
    with np.load(args.input, allow_pickle=False) as prepared:
        data, truth = prepared["data"], prepared["truth"]
        mask = prepared["artificial_missing_mask"]
    input_digest = file_hash(args.input)
    report = {
        "schema_version": 1,
        "kind": "native_emb_end_to_end_benchmark",
        "created_utc": datetime.now(UTC).isoformat(),
        "input_filename": args.input.name,
        "input_sha256": input_digest,
        "shape": list(data.shape),
        "missing_patterns": len(np.unique(np.isnan(data), axis=0)),
        "configuration": {
            key: value for key, value in vars(args).items() if key not in {"input", "output"}
        },
        "environment": {
            "python": platform.python_version(),
            "torch": str(torch.__version__),
            "numpy": np.__version__,
            "platform": platform.platform(),
            "cpu_threads": torch.get_num_threads(),
            "cuda_runtime": torch.version.cuda,
            "mps_cpu_fallback": os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK"),
            "peak_ram_bytes": None,
            "git": git_revision(),
        },
        "timing_scope": "in-memory input to all CPU NumPy completed datasets; preprocessing/bootstrap/EM/draws/transfers included; process startup excluded",
        "runs": [],
    }
    if dev.type == "cuda":
        properties = torch.cuda.get_device_properties(dev)
        report["environment"]["gpu"] = {
            "name": properties.name,
            "vram_bytes": properties.total_memory,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for run in range(args.warmups + args.repeats):
        warmup = run < args.warmups
        seed = args.seed + (100000 + run if warmup else run - args.warmups)
        if dev.type == "cuda":
            torch.cuda.reset_peak_memory_stats(dev)
        synchronize(dev)
        started = time.perf_counter()
        try:
            result = amelia(
                data,
                m=args.m,
                seed=seed,
                device=args.device,
                dtype=args.dtype,
                tolerance=args.tolerance,
                empri=args.empri,
                autopri=args.autopri,
                emburn=(0, args.max_iterations),
            )
            synchronize(dev)
            elapsed = time.perf_counter() - started
            record = {
                "warmup": warmup,
                "seed": seed,
                "status": "ok",
                "wall_seconds": elapsed,
                "diagnostics": result["diagnostics"],
                "quality": metrics(result["imputations"], data, truth, mask),
            }
            if not result["diagnostics"]["converged"]:
                record["status"] = "not_converged"
            elif not record["quality"]["quality_passed"]:
                record["status"] = "quality_failed"
            # Parameters suffice for matched-seed CPU/GPU comparisons; save first measured call.
            if not warmup and run == args.warmups:
                parameter_path = args.output.with_suffix(".parameters.npz")
                np.savez_compressed(
                    parameter_path,
                    theta=result["theta"],
                    sample_imputations=np.stack([out[:1000] for out in result["imputations"]]),
                )
                report["parameter_file"] = parameter_path.name
        except Exception as error:  # noqa: BLE001 - preserve failed benchmark runs in the artifact
            record = {
                "warmup": warmup,
                "seed": seed,
                "status": "error",
                "wall_seconds": time.perf_counter() - started,
                "error_type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc().replace(str(ROOT), "<project>"),
            }
        record["peak_cuda_allocated_bytes"] = (
            torch.cuda.max_memory_allocated(dev) if dev.type == "cuda" else None
        )
        report["runs"].append(record)
        report["completed_utc"] = datetime.now(UTC).isoformat()
        args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        print(
            json.dumps(
                {
                    "device": args.device,
                    "dtype": args.dtype,
                    "run": run,
                    "warmup": warmup,
                    "status": record["status"],
                    "seconds": record["wall_seconds"],
                }
            ),
            flush=True,
        )
        if record["status"] == "error":
            break
    measured = [
        run["wall_seconds"] for run in report["runs"] if not run["warmup"] and run["status"] == "ok"
    ]
    report["summary"] = {
        "successful_measured_runs": len(measured),
        "median_seconds": float(np.median(measured)) if len(measured) == args.repeats else None,
        "iqr_seconds": [float(v) for v in np.quantile(measured, [0.25, 0.75])]
        if len(measured) == args.repeats
        else None,
        "all_requested_runs_succeeded": len(measured) == args.repeats,
    }
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return 0 if report["summary"]["all_requested_runs_succeeded"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
