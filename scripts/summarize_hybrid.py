"""Audit and export complete R/PyTorch hybrid experiments without trusting status alone.

Copies only portable raw measurement JSON and the original suite JSON. Local
configuration files, logs, inputs and mutable measurement artifacts are not copied
or rewritten. Failed complete suites remain explicit failures with no success timing.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from summarize_benchmarks import (
    COLUMNS,
    ROOT,
    as_list,
    audit_report,
    export_files,
    is_count,
    portable_bytes,
    report_path,
    sha256,
    truths,
    valid_hashes,
    zeros,
)

BACKENDS = {
    "cpu64": ("cpu", "float64"),
    "cpu32": ("cpu", "float32"),
    "mps32": ("mps", "float32"),
    "cuda32": ("cuda", "float32"),
    "cuda64": ("cuda", "float64"),
}
ENGINE = "R-Amelia-pipeline-with-PyTorch-EM"
CALL_ENGINE = "r-amelia-torch-em"


def audit_backend(backend, device, dtype, m):
    """Validate the API attribute, whose engine ID differs from the report title."""
    if not isinstance(backend, dict):
        return ["missing_backend_metadata"]
    reasons = []
    fits = backend.get("fits")
    if (
        backend.get("engine") != CALL_ENGINE
        or backend.get("call_engine") != CALL_ENGINE
        or backend.get("reference_version") != "1.8.3"
        or backend.get("device") != device
        or backend.get("dtype") != dtype
        or backend.get("converged") is not True
        or not isinstance(fits, list)
        or len(fits) != m
    ):
        reasons.append("backend_contract_metadata_mismatch")
    if isinstance(fits, list) and any(
        not isinstance(fit, dict)
        or fit.get("converged") is not True
        or fit.get("device") != device
        or fit.get("dtype") != dtype
        or not is_count(fit.get("iterations"))
        for fit in fits
    ):
        reasons.append("individual_fit_not_converged_or_wrong_backend")
    return reasons


def digest_valid(value):
    return valid_hashes({"value": value})


def audit_hybrid_suite(suite, reports, report_hashes, expected_rows=100000):
    errors = []
    settings = suite.get("settings", {})
    plan = suite.get("planned_order", [])
    execution = suite.get("execution", [])
    if not suite.get("completed_utc") or suite.get("aborted_reason"):
        errors.append("suite_incomplete_or_aborted")
    if not plan or not isinstance(plan, list):
        errors.append("missing_nonempty_plan")
        plan = []
    planned_keys = [(item.get("dataset"), item.get("method")) for item in plan]
    actual_keys = [(item.get("dataset"), item.get("method")) for item in execution]
    if len(set(planned_keys)) != len(planned_keys):
        errors.append("duplicate_planned_task")
    if Counter(actual_keys) != Counter(planned_keys) or actual_keys != planned_keys:
        errors.append("missing_extra_duplicate_or_reordered_task")
    if settings.get("rows") != expected_rows:
        errors.append("unexpected_planned_row_count")
    for field, minimum in (("m", 1), ("warmups", 0), ("repeats", 1), ("threads", 1)):
        if not is_count(settings.get(field), minimum):
            errors.append(f"invalid_planned_{field}")
    if settings.get("parallel") != "no" or settings.get("ncpus") != 1:
        errors.append("unexpected_replicate_scheduling")
    if not valid_hashes(suite.get("source_sha256")):
        errors.append("invalid_source_fingerprints")
    seeds, warmup_seeds = suite.get("seeds", []), suite.get("warmup_seeds", [])
    if (
        not isinstance(seeds, list)
        or not isinstance(warmup_seeds, list)
        or len(seeds) != settings.get("repeats")
        or len(warmup_seeds) != settings.get("warmups")
    ):
        errors.append("planned_seed_count_mismatch")
        seeds, warmup_seeds = [], []
    planned = {key: item for key, item in zip(planned_keys, plan)}
    rows = []
    for item in execution:
        dataset, method = item.get("dataset"), item.get("method")
        key = (dataset, method)
        report = reports.get(key)
        reasons = []
        if method not in BACKENDS or dataset not in COLUMNS or key not in planned:
            reasons.append("unrecognized_or_unplanned_task")
        device, dtype = BACKENDS.get(method, (None, None))
        expected_task = planned.get(key, {})
        if (expected_task.get("device"), expected_task.get("dtype")) != (device, dtype):
            reasons.append("plan_backend_mismatch")
        if (item.get("device"), item.get("dtype")) != (device, dtype):
            reasons.append("execution_backend_mismatch")
        if (
            item.get("status") != "completed"
            or item.get("exit_status") != 0
            or isinstance(item.get("exit_status"), bool)
        ):
            reasons.append("process_not_successful")
        if item.get("source_unchanged_during_process") is not True:
            reasons.append("source_unchanged_not_verified")
        if (
            item.get("report_exists") is not True
            or not digest_valid(item.get("report_sha256"))
            or report_hashes.get(key) != item.get("report_sha256")
        ):
            reasons.append("missing_or_changed_report")
        input_evidence = suite.get("inputs", {}).get(dataset, {})
        if (
            input_evidence.get("shape") != [expected_rows, COLUMNS.get(dataset)]
            or not digest_valid(input_evidence.get("npz_sha256"))
            or not digest_valid(input_evidence.get("source_archive_sha256"))
        ):
            reasons.append("input_shape_or_source_fingerprint_missing")
        for field in ("input", "truth", "mask"):
            csv = input_evidence.get("csv", {}).get(field, {})
            if (
                not digest_valid(csv.get("sha256"))
                or csv.get("rows") != expected_rows
                or csv.get("columns") != COLUMNS.get(dataset)
            ):
                reasons.append("csv_input_evidence_missing")
        if not isinstance(report, dict):
            row = {
                "audit_errors": ["missing_report"],
                "median_seconds": None,
                "iqr_seconds": None,
                "mean_normalized_heldout_rmse": None,
            }
        else:
            row = audit_report(report, "r_hybrid", seeds, expected_rows, COLUMNS.get(dataset))
            config = report.get("config", {})
            if (
                report.get("engine") != ENGINE
                or report.get("reference_version") != "1.8.3"
                or report.get("requested_em_backend") != {"device": device, "dtype": dtype}
            ):
                reasons.append("report_engine_or_backend_mismatch")
            for field in (
                "m",
                "warmups",
                "parallel",
                "ncpus",
                "empri",
                "autopri",
                "tolerance",
                "emburn",
                "startvals",
                "boot.type",
            ):
                if field not in config or config[field] != settings.get(field):
                    reasons.append(f"recorded_{field}_differs_from_plan")
            if (
                config.get("device") != device
                or config.get("em_dtype") != dtype
                or config.get("torch_threads") != settings.get("threads")
            ):
                reasons.append("recorded_backend_or_thread_count_differs_from_plan")
            if as_list(config.get("warmup_seeds")) != warmup_seeds:
                reasons.append("warmup_seeds_differ_from_plan")
            if (
                not is_count(config.get("heldout_cells"), 1)
                or config.get("heldout_cells") != config.get("missing_cells")
                or config.get("completely_missing_input_rows") != 0
            ):
                reasons.append("not_the_complete_truth_scoring_contract")
            provenance = report.get("provenance", {})
            if (
                provenance.get("source_sha256") != suite.get("source_sha256")
                or provenance.get("input") != input_evidence
            ):
                reasons.append("report_provenance_differs_from_suite")
            environment = report.get("environment", {})
            if (
                environment.get("requested_python_matches_active") is not True
                or environment.get("torch_threads") != settings.get("threads")
                or not as_list(environment.get("RNGkind"))
                or as_list(environment.get("RNGkind"))[0] != "L'Ecuyer-CMRG"
            ):
                reasons.append("runtime_python_threads_or_rng_not_verified")
            if device == "mps" and environment.get("mps_cpu_fallback") != "0":
                reasons.append("mps_fallback_not_explicitly_disabled")
            if device == "cuda" and environment.get("cuda_tf32_allowed") is not False:
                reasons.append("cuda_tf32_not_explicitly_disabled")
            m = settings.get("m")
            for run in report.get("runs", []):
                if not is_count(m, 1):
                    break
                backend = run.get("backend", {})
                if (
                    run.get("status") != "ok"
                    or run.get("quality_passed") is not True
                    or run.get("backend_contract_passed") is not True
                ):
                    reasons.append("per_run_backend_or_quality_gate_failed")
                reasons.extend(audit_backend(backend, device, dtype, m))
                if (
                    not zeros(run.get("unscored_heldout_cells_per_imputation"), m)
                    or not zeros(run.get("unexpected_nonfinite_cells"), m)
                    or not truths(run.get("observed_values_unchanged"), m)
                    or not truths(run.get("wholly_missing_rows_preserved"), m)
                ):
                    reasons.append("individual_output_quality_invariant_failed")
        reasons.extend(row.pop("audit_errors", []))
        valid = not reasons
        row.update(
            {
                "independent_quality_audit_passed": valid,
                "audit_errors": sorted(set(reasons)),
                "dataset": dataset,
                "method": method,
                "device": device,
                "dtype": dtype,
                "result": item.get("result"),
                "result_sha256": report_hashes.get(key),
                "exit_status": item.get("exit_status"),
                "source_unchanged_during_process": item.get("source_unchanged_during_process"),
            }
        )
        if not valid:
            row.update(
                {"median_seconds": None, "iqr_seconds": None, "mean_normalized_heldout_rmse": None}
            )
        rows.append(row)
    return {
        "all_passed": not errors
        and bool(rows)
        and all(row["independent_quality_audit_passed"] for row in rows),
        "audit_errors": sorted(set(errors)),
        "measurements": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=ROOT / "results/local/benchmarks/hybrid")
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "docs/validation/2026-09-23-development"
    )
    parser.add_argument("--rows", type=int, default=100000)
    args = parser.parse_args()
    suite_path = args.input_dir / "suite.json"
    suite = json.loads(suite_path.read_text())
    if not suite.get("completed_utc"):
        raise ValueError("Suite is still running; no artifacts exported")
    reports, hashes, files = {}, {}, []
    artifact_dir = args.output_dir / "hybrid-reports"
    for item in suite.get("execution", []):
        key = (item.get("dataset"), item.get("method"))
        path = report_path(args.input_dir, item.get("result"))
        if path.exists():
            reports[key] = json.loads(path.read_text())
            hashes[key] = sha256(path)
            files.append((artifact_dir / path.name, portable_bytes(path)))
    audited = audit_hybrid_suite(suite, reports, hashes, args.rows)
    summary = {
        "schema_version": 1,
        "kind": "independent_R_pipeline_PyTorch_EM_audit",
        "scope": {
            "rows_per_dataset": args.rows,
            "planned_order": suite.get("planned_order"),
            "settings": suite.get("settings"),
        },
        "quality_gate": "Complete planned task/order; process exit 0; unchanged source; original report hash; exact requested phases/seeds and counts; finite positive times; all m fits converged on requested backend; every output preserves observations and scores every heldout cell without nonfinite values.",
        **audited,
        "source_sha256": suite.get("source_sha256"),
        "suite_sha256": sha256(suite_path),
        "auditor_source_sha256": {
            "summarize_hybrid.py": sha256(Path(__file__)),
            "summarize_benchmarks.py": sha256(Path(__file__).with_name("summarize_benchmarks.py")),
        },
        "limitations": [
            "Audit checks the recorded scientific invariants independently of success labels; it does not rerun fits or recreate unsaved full imputation matrices.",
            "R CPU preprocessing/bootstrap/draws/postprocessing and bridge/transfers are included; only initial import/binding and post-run scoring are outside timing.",
            "Hybrid and native suites run at different wall-clock times; this is a same-machine comparison, with potential load/thermal variation.",
            "Only the recorded complete-truth, low-pattern block-MCAR tasks are covered. CPU float64 remains the numerical reference; no CUDA result is implied by MPS results.",
        ],
    }
    files.append((artifact_dir / "suite.json", portable_bytes(suite_path)))
    files.append(
        (
            args.output_dir / "hybrid-summary.json",
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
