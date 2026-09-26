"""Prespecified, bounded Python front-door costs and independent-MCAR stress.

Write a plan before --execute. Input decoding/scoring/report writes are outside
timing; the complete public call, including its new R process and full typed
transport/RDS return, is inside. No core implementation is modified or injected.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THREAD_VARIABLES = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                    "VECLIB_MAXIMUM_THREADS")
INPUTS = {
    "front_door": "data/prepared/covertype-n100000-block_mcar-rate30-seed20260923.npz",
    "pattern_stress": "data/prepared/household_power-n5000-mcar-rate30-seed20260923.npz",
}


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(part)
    return value.hexdigest()


def sources():
    paths = [*sorted((ROOT / "src/amelia_torch").glob("*.py")),
             *sorted((ROOT / "src/amelia_torch/_r").glob("*.R")),
             *sorted((ROOT / "r-package/R").glob("*.R")),
             *sorted((ROOT / "r-package/src").glob("*.c")),
             ROOT / "r-package/DESCRIPTION", ROOT / "r-package/NAMESPACE",
             Path(__file__).resolve()]
    return {str(path.relative_to(ROOT)): digest(path) for path in paths}


def save_new(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, allow_nan=False)
        stream.write("\n")


def inspect_input(relative):
    import numpy as np

    path = ROOT / relative
    metadata = json.loads(path.with_suffix(".json").read_text())
    value = digest(path)
    if metadata["npz_sha256"] != value:
        raise ValueError("Prepared input differs from its preparation metadata")
    with np.load(path, allow_pickle=False) as prepared:
        data, truth, mask = (prepared[key] for key in
                             ("data", "truth", "artificial_missing_mask"))
        blank = np.isnan(data).all(axis=1)
        if not (data.shape == truth.shape == mask.shape):
            raise ValueError("Prepared dimensions differ")
        if not np.isfinite(truth[mask]).all() or not np.isnan(data[mask]).all():
            raise ValueError("Invalid heldout mask/truth")
        return {"path": relative, "sha256": value, "metadata_sha256": digest(path.with_suffix(".json")),
                "shape": list(data.shape), "mechanism": metadata["mechanism"],
                "missing_patterns": len(np.unique(np.isnan(data), axis=0)),
                "missing_rate": float(np.isnan(data).mean()), "heldout_cells": int(mask.sum()),
                "wholly_missing_rows": int(blank.sum()),
                "heldout_cells_in_wholly_missing_rows": int(mask[blank].sum())}


def make_plan():
    cases = {name: inspect_input(path) for name, path in INPUTS.items()}
    jobs = []
    for repetition in range(3):
        for method in ("reference", "hybrid_cpu64"):
            jobs.append({"case": "front_door", "method": method,
                         "phase": "first_call" if repetition == 0 else "subsequent_call",
                         "repetition": repetition, "seed": 20260926})
    for method in ("reference", "hybrid_cpu64", "hybrid_mps32"):
        jobs.append({"case": "pattern_stress", "method": method,
                     "phase": "single_stress_call", "repetition": 0, "seed": 20260926})
    return {
        "schema_version": 1, "created_utc": datetime.now(UTC).isoformat(),
        "purpose": "Bounded G7 product-call overhead and independent-MCAR behavior",
        "settings": {"m": 5, "threads_requested": 4, "r_rng_kind": "L'Ecuyer-CMRG",
                     "tolerance": 1e-4, "emburn": [0, 300], "empri": None, "autopri": .05,
                     "startvals": 0, "boot.type": "ordinary", "parallel": "no", "ncpus": 1,
                     "timeout_per_r_call_seconds": 180},
        "inputs": cases, "jobs": jobs, "source_sha256": sources(),
        "timing_contract": {
            "included": "Public Python invocation, new Rscript startup, package/Python initialization in R, typed input/output files, full original R workflow and requested EM, materialized NumPy imputations and complete RDS bytes, subprocess exit and temporary-file cleanup",
            "excluded": "Input NPZ reading, Python module import before calls, output scoring, digest/report creation, explicit final save_rds to user storage",
            "first_subsequent": "First vs subsequent calls in this benchmark Python process; each call starts a NEW R process. Neither phase claims a cold OS cache or a persistent warmed R interpreter.",
            "gpu_completion": "The R process must return CPU theta/draws, serialize results and exit before the Python API returns; the timer covers completed work rather than asynchronous GPU submission.",
            "no_subtraction": "Historical R in-memory measurements are unpaired, different-version and different-time measurements; do not subtract them to estimate pure bridge overhead.",
        },
        "quality_contract": {
            "strict": "All requested imputations converged; observed cells unchanged; nonblank rows finite; blank rows remain NA; ALL heldout cells scored. Any unscored heldout makes full RMSE null and benchmark quality false.",
            "stress": "Keep the supplied independent mask unchanged, including the 2 blank rows and 14 heldout cells expected to remain NA. Report semantic preservation separately from failed complete-heldout scoring.",
            "memory": "Peak RAM/VRAM not measured and reported null. Returned array/RDS sizes are not peak memory.",
        },
        "stopping": "Retain every exception, timeout, unscored cell and nonconvergence. Continue bounded remaining jobs; source/input changes abort the plan. No precision or algorithm retry, missingness-pattern changes, or selective success averaging.",
    }


def score(outputs, data, truth, mask):
    import numpy as np

    blank = np.isnan(data).all(axis=1)
    observed = ~np.isnan(data)
    scale = np.std(truth, axis=0, ddof=1)
    records = []
    for completed in outputs:
        if completed.shape != data.shape:
            raise ValueError("Imputation shape differs from input")
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            residual = (completed - truth) / scale
        unscored = int((mask & ~np.isfinite(residual)).sum())
        records.append({
            "observed_preserved": bool(np.array_equal(completed[observed], data[observed])),
            "blank_rows_preserved": bool(np.isnan(completed[blank]).all()),
            "unexpected_nonfinite_cells": int((~np.isfinite(completed[~blank])).sum()),
            "remaining_missing_cells": int(np.isnan(completed).sum()),
            "heldout_cells": int(mask.sum()), "unscored_heldout_cells": unscored,
            "unscored_heldout_in_blank_rows": int((mask[blank] & ~np.isfinite(residual[blank])).sum()),
            "normalized_rmse_all_heldout": None if unscored else
                float(np.sqrt(np.mean(residual[mask] ** 2))),
        })
    semantic = bool(records) and all(
        r["observed_preserved"] and r["blank_rows_preserved"] and
        r["unexpected_nonfinite_cells"] == 0 for r in records)
    complete = bool(records) and all(r["unscored_heldout_cells"] == 0 for r in records)
    return {"semantic_output_checks_passed": semantic,
            "complete_heldout_scoring": complete,
            "output_quality_passed": semantic and complete, "imputations": records}


def status_for(result, quality, requested_m):
    fits_complete = result.m == requested_m
    convergence = result.metadata.get("converged_by_tolerance", [])
    converged = len(convergence) == requested_m and all(convergence)
    if not fits_complete or not quality["semantic_output_checks_passed"]:
        return "invalid_output"
    if not converged:
        return "nonconverged"
    return "ok" if quality["complete_heldout_scoring"] else "heldout_incomplete"


def execute(plan_path, output):
    import numpy as np

    from amelia_torch.reference import AmeliaReferenceError, amelia_reference, amelia_torch_compat

    plan = json.loads(plan_path.read_text())
    if sources() != plan["source_sha256"]:
        raise ValueError("Source differs from the saved plan; do not change a running experiment")
    if output.exists():
        raise FileExistsError("Choose a fresh report path")
    arrays = {}
    for name, info in plan["inputs"].items():
        if inspect_input(info["path"]) != info:
            raise ValueError("Input differs from the saved plan")
        with np.load(ROOT / info["path"], allow_pickle=False) as prepared:
            arrays[name] = tuple(prepared[key] for key in
                                 ("data", "truth", "artificial_missing_mask"))
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=False)
    report = {
        "schema_version": 1, "started_utc": datetime.now(UTC).isoformat(),
        "plan_sha256": digest(plan_path), "plan": plan,
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "torch_distribution": importlib.metadata.version("torch"),
                        "os": platform.system(), "architecture": platform.machine(),
                        "revision": revision.stdout.strip(), "workspace_source_hashes_authoritative": True,
                        "thread_environment": {k: os.environ.get(k) for k in THREAD_VARIABLES},
                        "thread_note": "Requested environment controls, not a measurement of every BLAS thread pool",
                        "mps_fallback": os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK"),
                        "peak_ram_bytes": None, "peak_gpu_memory_bytes": None},
        "runs": [],
    }
    output.parent.mkdir(parents=True, exist_ok=True)

    def checkpoint():
        temporary = output.with_suffix(".tmp")
        temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        os.replace(temporary, output)

    checkpoint()
    for job in plan["jobs"]:
        if sources() != plan["source_sha256"]:
            report["source_changed"] = True
            checkpoint()
            raise ValueError("Source changed during execution; retained partial report")
        data, truth, mask = arrays[job["case"]]
        settings = plan["settings"]
        options = {k: settings[k] for k in
                   ("m", "r_rng_kind", "tolerance", "emburn", "empri", "autopri",
                    "startvals", "boot.type", "parallel", "ncpus")}
        options.update(seed=job["seed"], p2s=0, return_type="numpy",
                       timeout=settings["timeout_per_r_call_seconds"])
        implementation = amelia_reference
        if job["method"] != "reference":
            implementation = amelia_torch_compat
            options.update(device="mps" if job["method"] == "hybrid_mps32" else "cpu",
                           dtype="float32" if job["method"] == "hybrid_mps32" else "float64")
        record = {**job, "peak_ram_bytes": None, "peak_gpu_memory_bytes": None}
        gc.collect()
        started = time.perf_counter()
        result = None
        stage = "public_api_call"
        try:
            result = implementation(data, **options)
            record["wall_seconds"] = time.perf_counter() - started
            stage = "untimed_output_validation"
            if job["method"] != "reference":
                backend = result.metadata["hybrid_backend"]
                expected = (options["device"], options["dtype"])
                fits = backend["fits"]
                if len(fits) != settings["m"] or any(
                    (fit["device"], fit["dtype"]) != expected for fit in fits
                ):
                    raise ValueError("Returned EM diagnostics differ from the requested backend")
            quality = score(result.imputations, data, truth, mask)
            record.update(status=status_for(result, quality, settings["m"]), quality=quality,
                          metadata=result.metadata, warnings=list(result.warnings),
                          returned_rds_bytes=len(result._rds),
                          returned_rds_sha256=hashlib.sha256(result._rds).hexdigest(),
                          returned_numpy_bytes=sum(x.nbytes for x in result.imputations))
        except Exception as error:  # noqa: BLE001 -- retain every failed experimental call
            record.setdefault("wall_seconds", time.perf_counter() - started)
            record.update(status="error", failure_stage=stage,
                          exception_type=type(error).__name__,
                          error=str(error).replace(str(ROOT), "<PROJECT_ROOT>")
                          .replace(str(Path.home()), "<USER_HOME>"))
            if isinstance(error, AmeliaReferenceError):
                record.update(code=error.code, details=error.details,
                              partial_rds_bytes=len(error.partial_rds) if error.partial_rds else None)
        finally:
            del result
        record["source_unchanged"] = sources() == plan["source_sha256"]
        report["runs"].append(record)
        checkpoint()
        print(json.dumps({k: record[k] for k in
                          ("case", "method", "phase", "status", "wall_seconds")}), flush=True)
    report["completed_utc"] = datetime.now(UTC).isoformat()
    report["all_requests_returned_results"] = all(r["status"] != "error" for r in report["runs"])
    report["source_unchanged"] = sources() == plan["source_sha256"]
    report["inputs_unchanged"] = {
        name: digest(ROOT / info["path"]) == info["sha256"]
        for name, info in plan["inputs"].items()
    }
    report["all_benchmark_quality_passed"] = (
        all(r["status"] == "ok" and r["source_unchanged"] for r in report["runs"])
        and report["source_unchanged"] and all(report["inputs_unchanged"].values())
    )
    checkpoint()
    return 0 if report["all_benchmark_quality_passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write-plan", type=Path)
    group.add_argument("--execute", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    for name in THREAD_VARIABLES:
        os.environ[name] = "4"
    os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "0"
    if args.write_plan:
        save_new(args.write_plan, make_plan())
        print("Prespecified plan saved; no imputation has run.")
        return 0
    if args.output is None:
        parser.error("--execute requires --output")
    return execute(args.execute, args.output)


if __name__ == "__main__":
    sys.exit(main())
