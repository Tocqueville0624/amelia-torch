"""Independently audit the planned native/R benchmark grid and export portable JSON.

Reports are never modified. Settings and seeds come from each recorded request;
for the legacy suite without a stored plan, --datasets/--methods define the
expected grid explicitly. This audit is for the complete-truth public-data tasks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATASETS = ("covertype", "household_power", "year_prediction_msd")
DEFAULT_METHODS = ("cpu64", "cpu32", "mps32", "r_serial", "r_snow4")
METHODS = (*DEFAULT_METHODS, "r_snow2", "cuda32", "cuda64")
COLUMNS = {"covertype": 10, "household_power": 7, "year_prediction_msd": 90}


def as_list(value):
    return value if isinstance(value, list) else [] if value is None else [value]


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def is_count(value, minimum=0):
    return is_number(value) and int(value) == value and value >= minimum


def zeros(value, m):
    values = as_list(value)
    return len(values) == m and all(is_number(item) and item == 0 for item in values)


def truths(value, m):
    values = as_list(value)
    return len(values) == m and all(item is True for item in values)


def score_values(value, m):
    values = as_list(value)
    return len(values) == m and all(is_number(item) and item >= 0 for item in values)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valid_hashes(mapping):
    return (
        bool(mapping)
        and isinstance(mapping, dict)
        and all(
            isinstance(name, str)
            and isinstance(value, str)
            and re.fullmatch(r"[0-9a-f]{64}", value)
            for name, value in mapping.items()
        )
    )


def portable_bytes(path):
    """Preserve exact raw JSON bytes, refusing private paths instead of redacting."""
    raw = path.read_bytes()
    value = json.loads(raw)
    private = re.compile(
        r"(?:/(?:Users|home)/|/private/(?:var|tmp)/|/var/folders/|[A-Za-z]:[\\/](?:Users|Documents and Settings)[\\/])",
        re.IGNORECASE,
    )

    def walk(item):
        if isinstance(item, str) and (private.search(item) or str(ROOT) in item):
            raise ValueError(f"Private path in {path.name}; keep this artifact local")
        if isinstance(item, dict):
            for key, child in item.items():
                walk(key)
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)

    walk(value)
    return raw


def report_path(directory, name):
    if (
        not isinstance(name, str)
        or Path(name).name != name
        or "/" in name
        or "\\" in name
        or not name.endswith(".json")
        or name.endswith(".config.json")
    ):
        raise ValueError("Expected a report JSON basename, not a path or configuration")
    path = directory / name
    if path.resolve().parent != directory.resolve():
        raise ValueError("Report must stay inside its input directory")
    return path


def export_files(files):
    """Preflight every destination; existing measured evidence is never overwritten."""
    for destination, raw in files:
        if destination.is_symlink():
            raise ValueError(f"Refusing symbolic-link destination: {destination.name}")
        if destination.exists() and destination.read_bytes() != raw:
            raise FileExistsError(
                f"Refusing to replace {destination.name}; select a fresh output directory"
            )
    for destination, raw in files:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            with destination.open("xb") as stream:
                stream.write(raw)


def check_run(run, method, m):
    """Check recorded scientific invariants; timing/schedule are checked separately."""
    if not isinstance(run, dict) or not is_count(m, 1):
        return False, []
    if method.startswith("r_"):
        scores = as_list(run.get("normalized_heldout_rmse"))
        good = (
            run.get("error") is None
            and is_count(run.get("code"), 1)
            and run.get("code") == 1
            and truths(run.get("converged_by_tolerance"), m)
            and run.get("quality_status") == "computed"
            and truths(run.get("observed_values_unchanged"), m)
            and zeros(run.get("remaining_missing_cells"), m)
            and zeros(run.get("nonfinite_cells"), m)
        )
        # Legacy records predate these explicit fields. Their all-matrix zero
        # nonfinite count implies no nonfinite heldout cell on complete truth.
        for field in ("unexpected_nonfinite_cells", "unscored_heldout_cells_per_imputation"):
            if field in run:
                good = good and zeros(run[field], m)
        if "quality_passed" in run:
            good = good and run["quality_passed"] is True
        if "status" in run:
            good = good and run["status"] == "ok"
    else:
        quality, diagnostics = run.get("quality", {}), run.get("diagnostics", {})
        if not isinstance(quality, dict) or not isinstance(diagnostics, dict):
            return False, []
        scores = as_list(quality.get("normalized_rmse_per_imputation"))
        fits = diagnostics.get("replicates")
        good = (
            run.get("status") == "ok"
            and diagnostics.get("converged") is True
            and isinstance(fits, list)
            and len(fits) == m
            and all(isinstance(fit, dict) and fit.get("converged") is True for fit in fits)
            and quality.get("observed_values_preserved") is True
            and zeros(quality.get("remaining_missing_cells"), m)
            and zeros(quality.get("unscored_heldout_cells_per_imputation"), m)
        )
        if "unexpected_nonfinite_cells" in quality:
            good = good and zeros(quality["unexpected_nonfinite_cells"], m)
        if "quality_passed" in quality:
            good = good and quality["quality_passed"] is True
    return bool(good and score_values(scores, m)), scores


def check_schedule(runs, measured_seeds, warmup_seeds, *, r_style):
    reasons = []
    if not isinstance(runs, list):
        return ["runs_not_list"], []
    if not measured_seeds or any(not is_count(seed) for seed in measured_seeds + warmup_seeds):
        reasons.append("invalid_requested_seeds")
    if len(set(measured_seeds + warmup_seeds)) != len(measured_seeds + warmup_seeds):
        reasons.append("duplicate_requested_seed")
    expected = [("warmup", seed) for seed in warmup_seeds] + [
        ("measured", seed) for seed in measured_seeds
    ]
    actual = []
    measured = []
    for run in runs:
        if not isinstance(run, dict):
            reasons.append("invalid_run_record")
            continue
        if r_style:
            phase = run.get("phase")
        else:
            phase = (
                "warmup"
                if run.get("warmup") is True
                else "measured"
                if run.get("warmup") is False
                else None
            )
        actual.append((phase, run.get("seed")))
        if not is_count(run.get("seed")):
            reasons.append("invalid_run_seed")
        if phase == "measured":
            measured.append(run)
        elapsed = run.get("wall_seconds")
        if not is_number(elapsed) or elapsed <= 0:
            reasons.append("nonpositive_or_nonfinite_elapsed")
    if actual != expected:
        reasons.append("run_phase_seed_sequence_or_count_mismatch")
    return reasons, measured


def audit_report(report, method, suite_seeds, expected_rows=100000, expected_columns=None):
    reasons = []
    r_style = method.startswith("r_")
    config = report.get("config" if r_style else "configuration", {})
    config = config if isinstance(config, dict) else {}
    m, warmups = config.get("m"), config.get("warmups")
    if not is_count(m, 1) or not is_count(warmups):
        return {
            "independent_quality_audit_passed": False,
            "audit_errors": ["missing_or_invalid_m_warmups"],
            "median_seconds": None,
            "iqr_seconds": None,
            "mean_normalized_heldout_rmse": None,
        }
    m, warmups = int(m), int(warmups)
    if r_style:
        measured_seeds = as_list(config.get("seeds"))
        warmup_seeds = as_list(config.get("warmup_seeds"))
        if config.get("completely_missing_input_rows") != 0:
            reasons.append("not_complete_truth_nonblank_task")
        if not is_count(config.get("heldout_cells"), 1) or config.get(
            "heldout_cells"
        ) != config.get("missing_cells"):
            reasons.append("heldout_missing_cell_contract_mismatch")
        shape = [config.get("n"), config.get("p")]
    else:
        seed = config.get("seed")
        repeats = config.get("repeats")
        if not is_count(seed) or not is_count(repeats, 1):
            reasons.append("invalid_seed_or_repeats")
            measured_seeds, warmup_seeds = [], []
        else:
            seed, repeats = int(seed), int(repeats)
            measured_seeds = list(range(seed, seed + repeats))
            warmup_seeds = list(range(seed + 100000, seed + 100000 + warmups))
        shape = report.get("shape")
    if measured_seeds != suite_seeds or len(warmup_seeds) != warmups:
        reasons.append("requested_seed_or_warmup_count_mismatch")
    if not isinstance(shape, list) or len(shape) != 2 or shape[0] != expected_rows:
        reasons.append("task_row_count_mismatch")
    elif expected_columns is not None and shape[1] != expected_columns:
        reasons.append("task_column_count_mismatch")
    runs = report.get("runs")
    schedule_errors, measured = check_schedule(runs, measured_seeds, warmup_seeds, r_style=r_style)
    reasons.extend(schedule_errors)
    runs = runs if isinstance(runs, list) else []
    checked = [check_run(run, method, m) for run in runs]
    if not all(good for good, _ in checked):
        reasons.append("scientific_invariant_failed")
    if not r_style:
        device = (
            "cpu" if method.startswith("cpu") else "mps" if method.startswith("mps") else "cuda"
        )
        dtype = "float64" if method.endswith("64") else "float32"
        if config.get("device") != device or config.get("dtype") != dtype:
            reasons.append("configuration_backend_mismatch")
        for run in runs:
            if not isinstance(run, dict):
                continue
            diag = run.get("diagnostics", {})
            if not isinstance(diag, dict):
                reasons.append("malformed_per_fit_diagnostics")
                continue
            fits = diag.get("replicates", [])
            if (
                diag.get("device") != device
                or diag.get("dtype") != dtype
                or diag.get("wholly_missing_rows_retained") != 0
                or not isinstance(fits, list)
                or any(
                    not isinstance(fit, dict)
                    or fit.get("device") != device
                    or fit.get("dtype") != dtype
                    for fit in fits
                )
            ):
                reasons.append("per_fit_backend_or_blank_row_mismatch")
    valid = not reasons
    elapsed = [run["wall_seconds"] for run in measured] if valid else []
    scores = [value for run in measured for value in check_run(run, method, m)[1]] if valid else []
    return {
        "independent_quality_audit_passed": valid,
        "audit_errors": sorted(set(reasons)),
        "m": m,
        "requested_warmups": warmups,
        "requested_measured_runs": len(measured_seeds),
        "warmup_and_measured_runs_audited": len(runs),
        "measured_runs": len(measured),
        "median_seconds": float(np.median(elapsed)) if valid else None,
        "iqr_seconds": np.quantile(elapsed, [0.25, 0.75]).tolist() if valid else None,
        "mean_normalized_heldout_rmse": float(np.mean(scores)) if valid else None,
    }


def audit_suite(suite, reports, expected_tasks, expected_rows=100000):
    errors = []
    execution = suite.get("execution", [])
    if not suite.get("completed_utc") or suite.get("aborted_reason"):
        errors.append("suite_not_completed")
    if not expected_tasks or len(set(expected_tasks)) != len(expected_tasks):
        errors.append("invalid_expected_plan")
    actual = [(item.get("dataset"), item.get("method")) for item in execution]
    if Counter(actual) != Counter(expected_tasks):
        errors.append("missing_extra_or_duplicate_task")
    if not valid_hashes(suite.get("source_sha256")):
        errors.append("invalid_source_fingerprints")
    seeds = suite.get("seeds", [])
    if not isinstance(seeds, list) or not seeds:
        errors.append("missing_suite_seeds")
        seeds = []
    rows = []
    contracts = set()
    for item in execution:
        dataset, method = item.get("dataset"), item.get("method")
        key = (dataset, method)
        report = reports.get(key)
        if not isinstance(report, dict):
            row = {
                "independent_quality_audit_passed": False,
                "audit_errors": ["missing_report"],
                "median_seconds": None,
                "iqr_seconds": None,
                "mean_normalized_heldout_rmse": None,
            }
        else:
            row = audit_report(report, method or "", seeds, expected_rows, COLUMNS.get(dataset))
            config = report.get("config" if str(method).startswith("r_") else "configuration", {})
            config = config if isinstance(config, dict) else {}
            contracts.add(
                json.dumps(
                    {
                        "m": config.get("m"),
                        "warmups": config.get("warmups"),
                        "tolerance": config.get("tolerance"),
                        "autopri": config.get("autopri"),
                        "empri": config.get("empri"),
                        "emburn": config.get("emburn", [0, config.get("max_iterations")]),
                    },
                    sort_keys=True,
                )
            )
            if not str(method).startswith("r_") and report.get("input_sha256") != item.get(
                "input_sha256"
            ):
                row["audit_errors"].append("input_hash_mismatch")
        if dataset not in DATASETS or method not in METHODS:
            row["audit_errors"].append("unrecognized_task")
        if not valid_hashes({"input": item.get("input_sha256")}):
            row["audit_errors"].append("missing_or_invalid_input_hash")
        if (
            "source_unchanged_during_process" in item
            and item["source_unchanged_during_process"] is not True
        ):
            row["audit_errors"].append("source_changed_during_process")
        if item.get("exit_status") != 0 or isinstance(item.get("exit_status"), bool):
            row["audit_errors"].append("process_exit_nonzero_or_missing")
        if row["audit_errors"]:
            row.update(
                {
                    "independent_quality_audit_passed": False,
                    "median_seconds": None,
                    "iqr_seconds": None,
                    "mean_normalized_heldout_rmse": None,
                }
            )
        rows.append({**item, **row})
    if len(contracts) > 1:
        errors.append("inconsistent_cross_method_task_settings")
    return {
        "all_passed": not errors
        and bool(rows)
        and all(row["independent_quality_audit_passed"] for row in rows),
        "audit_errors": errors,
        "measurements": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=ROOT / "results/local/benchmarks/main")
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "docs/validation/2026-09-23-development"
    )
    parser.add_argument("--datasets", nargs="+", choices=DATASETS, default=list(DATASETS))
    parser.add_argument(
        "--methods",
        nargs="+",
        choices=METHODS,
        default=list(DEFAULT_METHODS),
        help="Explicit expected legacy-suite grid; list CPU-only/CUDA methods as appropriate",
    )
    parser.add_argument("--rows", type=int, default=100000)
    args = parser.parse_args()
    suite_path = args.input_dir / "suite.json"
    suite = json.loads(suite_path.read_text())
    if not suite.get("completed_utc"):
        raise ValueError("Suite is still running; no artifacts exported")
    reports, paths = {}, {}
    for item in suite.get("execution", []):
        key = (item.get("dataset"), item.get("method"))
        path = report_path(args.input_dir, item.get("result"))
        paths[key] = path
        if path.exists():
            reports[key] = json.loads(path.read_text())
    plan = [(dataset, method) for dataset in args.datasets for method in args.methods]
    audited = audit_suite(suite, reports, plan, args.rows)
    artifacts = args.output_dir / "benchmark-reports"
    files = [(artifacts / "suite.json", portable_bytes(suite_path))]
    for row in audited["measurements"]:
        path = paths.get((row["dataset"], row["method"]))
        if path is not None and path.exists():
            row["result_sha256"] = sha256(path)
            files.append((artifacts / path.name, portable_bytes(path)))
    summary = {
        "schema_version": 2,
        "scope": {"rows_per_dataset": args.rows, "expected_tasks": [list(key) for key in plan]},
        "quality_gate": "Complete expected task grid; process success; exact requested warmup/measured phase+seed sequence; positive finite timing; m individual fits converged; observed cells preserved and all heldout cells scored on complete-truth tasks.",
        **audited,
        "source_sha256": suite.get("source_sha256"),
        "suite_sha256": sha256(suite_path),
        "auditor_sha256": sha256(Path(__file__)),
        "legacy_evidence_note": "Original measured reports are immutable. Where explicit quality_passed/unexpected_nonfinite fields were not recorded, the audit uses all-matrix nonfinite counts (R), or preserved observations + zero missing/heldout-unscored counts (native) under the complete-truth input contract.",
        "limitations": [
            "Legacy suite did not persist a planned grid or per-process source-unchanged flag; expected tasks are supplied explicitly and source fingerprints are retained without inventing missing telemetry.",
            "R and NumPy use different RNGs; equal seeds do not pair their draws.",
            "Native timings omit the R/Python bridge; hybrid timings need a separate audited suite.",
            "Low-pattern block MCAR only; RAM/VRAM peaks and broader missingness scenarios remain separate.",
        ],
    }
    files.append(
        (
            args.output_dir / "benchmark-summary.json",
            (json.dumps(summary, indent=2, allow_nan=False) + "\n").encode(),
        )
    )
    export_files(files)
    for row in audited["measurements"]:
        print(
            row["dataset"],
            row["method"],
            row["median_seconds"],
            "PASS" if row["independent_quality_audit_passed"] else "FAIL",
        )
    if audited["audit_errors"]:
        print("Suite audit failures:", ", ".join(audited["audit_errors"]))
    return int(not audited["all_passed"])


if __name__ == "__main__":
    raise SystemExit(main())
