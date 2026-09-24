"""Compare recorded R Amelia and R/PyTorch summaries for matched R RNG runs.

This is a descriptive, paired summary comparison, not a full-output equivalence
test. It imports no torch module, runs no fit, and refuses unfinished suites.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from summarize_benchmarks import (
    COLUMNS,
    DATASETS,
    DEFAULT_METHODS,
    ROOT,
    as_list,
    audit_suite,
    check_run,
    export_files,
    is_count,
    is_number,
    portable_bytes,
    report_path,
    sha256,
    valid_hashes,
)
from summarize_hybrid import audit_hybrid_suite

CONFIG_FIELDS = (
    "n",
    "p",
    "m",
    "warmups",
    "ncpus",
    "parallel",
    "empri",
    "autopri",
    "tolerance",
    "emburn",
    "startvals",
    "boot.type",
    "missing_cells",
    "heldout_cells",
    "completely_missing_input_rows",
)
VECTOR_CONFIG_FIELDS = ("seeds", "warmup_seeds")
METRICS = (
    "iterations",
    "normalized_heldout_rmse",
    "pooled_column_means",
    "mean_covariance",
    "pooled_mean_within_variance",
    "pooled_mean_between_variance",
    "pooled_mean_variance",
)
REUSED_INPUT_POLICY = "Exact existing main-suite CSV files reused read-only"


def discrepancy(reference, candidate, shape, relative_floor=1e-12):
    """Absolute differences everywhere; relative differences away from zero only."""
    if not is_number(relative_floor) or relative_floor <= 0:
        raise ValueError("relative_floor must be finite and positive")
    left, right = np.asarray(reference), np.asarray(candidate)
    if len(shape) == 1:
        left, right = np.atleast_1d(left), np.atleast_1d(right)
    if left.shape != shape or right.shape != shape:
        raise ValueError("summary_shape_mismatch")
    if any(array.dtype.kind not in "iuf" for array in (left, right)):
        raise ValueError("summary_not_numeric")
    left, right = left.astype(np.float64), right.astype(np.float64)
    if not np.isfinite(left).all() or not np.isfinite(right).all():
        raise ValueError("nonfinite_summary")
    delta = np.abs(right - left)
    away = np.abs(left) > relative_floor
    return {
        "elements": int(left.size),
        "max_absolute": float(delta.max()),
        "max_relative_on_nonzero_reference": float((delta[away] / np.abs(left[away])).max())
        if away.any()
        else None,
        "near_zero_reference_elements": int((~away).sum()),
        "max_absolute_on_near_zero_reference": float(delta[~away].max()) if (~away).any() else None,
        "identical_recorded_elements": int((delta == 0).sum()),
    }


def run_map(report):
    result = {}
    for run in report.get("runs", []):
        key = (run.get("phase"), run.get("seed"))
        if key[0] not in ("warmup", "measured") or not is_count(key[1]) or key in result:
            raise ValueError("invalid_or_duplicate_phase_seed")
        result[key] = run
    return result


def summarize_differences(pairs):
    result = {}
    for metric in METRICS:
        values = [
            (pair, pair["metrics"][metric])
            for pair in pairs
            if pair["metrics"][metric].get("applicable", True)
        ]
        if not values:
            result[metric] = {"applicable": False}
            continue
        largest = max(values, key=lambda item: item[1]["max_absolute"])
        relative = [
            value["max_relative_on_nonzero_reference"]
            for _, value in values
            if value["max_relative_on_nonzero_reference"] is not None
        ]
        result[metric] = {
            "max_absolute": largest[1]["max_absolute"],
            "max_absolute_at": {"phase": largest[0]["phase"], "seed": largest[0]["seed"]},
            "max_relative_on_nonzero_reference": max(relative) if relative else None,
            "compared_elements": sum(value["elements"] for _, value in values),
            "identical_recorded_elements": sum(
                value["identical_recorded_elements"] for _, value in values
            ),
            "near_zero_reference_elements": sum(
                value["near_zero_reference_elements"] for _, value in values
            ),
        }
    return result


def compare_reports(reference, candidate, relative_floor=1e-12):
    """Validate pairing independently of row order before calculating differences."""
    errors = []
    left, right = reference.get("config", {}), candidate.get("config", {})
    for field in CONFIG_FIELDS:
        if field not in left or field not in right or left[field] != right[field]:
            errors.append(f"configuration_mismatch:{field}")
    for field in VECTOR_CONFIG_FIELDS:
        if field not in left or field not in right or as_list(left[field]) != as_list(right[field]):
            errors.append(f"configuration_mismatch:{field}")
    left_env, right_env = reference.get("environment", {}), candidate.get("environment", {})
    for field in ("R", "RNGkind", "platform", "os", "BLAS", "LAPACK", "thread_environment"):
        if field not in left_env or field not in right_env or left_env[field] != right_env[field]:
            errors.append(f"runtime_mismatch:{field}")
    if as_list(left_env.get("RNGkind")) != ["L'Ecuyer-CMRG", "Inversion", "Rejection"]:
        errors.append("unexpected_R_rng_contract")
    for package in ("Amelia", "Rcpp", "RcppArmadillo"):
        a, b = left_env.get("packages", {}).get(package), right_env.get("packages", {}).get(package)
        if not a or a != b:
            errors.append(f"package_version_mismatch:{package}")
    if (
        reference.get("version") != "1.8.3"
        or candidate.get("reference_version") != "1.8.3"
        or left_env.get("packages", {}).get("Amelia") != "1.8.3"
    ):
        errors.append("reference_version_mismatch")
    m, p = left.get("m"), left.get("p")
    if not is_count(m, 1) or not is_count(p, 1):
        errors.append("invalid_shape_or_m")
    try:
        left_runs, right_runs = run_map(reference), run_map(candidate)
        expected = [("warmup", seed) for seed in as_list(left.get("warmup_seeds"))] + [
            ("measured", seed) for seed in as_list(left.get("seeds"))
        ]
        if (
            not expected
            or len(expected) != len(set(expected))
            or set(left_runs) != set(expected)
            or set(right_runs) != set(expected)
        ):
            errors.append("phase_seed_set_mismatch")
    except ValueError as error:
        errors.append(str(error))
        expected, left_runs, right_runs = [], {}, {}
    result = {
        "comparison_contract_verified": not errors,
        "contract_errors": sorted(set(errors)),
        "paired_runs": [],
        "maximum_discrepancies": {},
    }
    if errors:
        return result
    for phase, seed in expected:
        a, b = left_runs[(phase, seed)], right_runs[(phase, seed)]
        if not check_run(a, "r_serial", m)[0] or not check_run(b, "r_hybrid", m)[0]:
            errors.append(f"run_quality_failed:{phase}:{seed}")
            continue
        values = {}
        for metric in METRICS:
            if (
                m == 1
                and metric in ("pooled_mean_between_variance", "pooled_mean_variance")
                and as_list(a.get(metric)) == as_list(b.get(metric)) == [None] * p
            ):
                values[metric] = {
                    "applicable": False,
                    "reason": "m1_between_variance_undefined",
                }
                continue
            shape = (
                (m,)
                if metric in ("iterations", "normalized_heldout_rmse")
                else ((p, p) if metric == "mean_covariance" else (p,))
            )
            try:
                values[metric] = discrepancy(a.get(metric), b.get(metric), shape, relative_floor)
            except ValueError as error:
                errors.append(f"{metric}:{phase}:{seed}:{error}")
        if len(values) == len(METRICS):
            result["paired_runs"].append({"phase": phase, "seed": seed, "metrics": values})
    result["comparison_contract_verified"] = not errors
    result["contract_errors"] = sorted(set(errors))
    if not errors:
        result["maximum_discrepancies"] = summarize_differences(result["paired_runs"])
        result["by_phase"] = {
            phase: summarize_differences(
                [pair for pair in result["paired_runs"] if pair["phase"] == phase]
            )
            for phase in ("warmup", "measured")
        }
    return result


def input_contract(reference_item, hybrid_suite, dataset):
    evidence = hybrid_suite.get("inputs", {}).get(dataset, {})
    errors = []
    if not valid_hashes({"npz": reference_item.get("input_sha256")}) or reference_item.get(
        "input_sha256"
    ) != evidence.get("npz_sha256"):
        errors.append("prepared_NPZ_fingerprint_mismatch")
    if hybrid_suite.get("input_policy") != REUSED_INPUT_POLICY:
        errors.append("original_CSV_reuse_not_recorded")
    for field in ("input", "truth", "mask"):
        if not valid_hashes({field: evidence.get("csv", {}).get(field, {}).get("sha256")}):
            errors.append(f"missing_CSV_fingerprint:{field}")
    return errors


def load_suite(directory):
    path = directory / "suite.json"
    suite = json.loads(portable_bytes(path))
    if not suite.get("completed_utc"):
        raise ValueError("Suite is still running; no comparison or output is permitted")
    reports, hashes = {}, {}
    for item in suite.get("execution", []):
        key = (item.get("dataset"), item.get("method"))
        if key in reports:
            raise ValueError("Duplicate suite task")
        report = report_path(directory, item.get("result"))
        reports[key] = json.loads(portable_bytes(report))
        hashes[key] = sha256(report)
    return suite, reports, hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reference-dir", type=Path, default=ROOT / "results/local/benchmarks/main"
    )
    parser.add_argument("--hybrid-dir", type=Path, default=ROOT / "results/local/benchmarks/hybrid")
    parser.add_argument("--reference-methods", nargs="+", default=list(DEFAULT_METHODS))
    parser.add_argument("--datasets", nargs="+", choices=DATASETS, default=list(DATASETS))
    parser.add_argument("--relative-floor", type=float, default=1e-12)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs/validation/2026-09-23-development/hybrid-reference-comparison.json",
    )
    args = parser.parse_args()
    if not is_number(args.relative_floor) or args.relative_floor <= 0:
        parser.error("relative-floor must be finite and positive")
    reference, reference_reports, reference_hashes = load_suite(args.reference_dir)
    hybrid, hybrid_reports, hybrid_hashes = load_suite(args.hybrid_dir)
    reference_plan = [
        (dataset, method) for dataset in args.datasets for method in args.reference_methods
    ]
    ref_audit = audit_suite(reference, reference_reports, reference_plan)
    hyb_audit = audit_hybrid_suite(hybrid, hybrid_reports, hybrid_hashes)
    if not ref_audit["all_passed"] or not hyb_audit["all_passed"]:
        raise ValueError(
            "Both complete suites must pass independent quality audits before comparison"
        )
    comparisons = []
    reference_items = {(item["dataset"], item["method"]): item for item in reference["execution"]}
    for task in hybrid["planned_order"]:
        dataset, method = task["dataset"], task["method"]
        ref_key, hyb_key = (dataset, "r_serial"), (dataset, method)
        if ref_key not in reference_reports or dataset not in COLUMNS:
            raise ValueError("No matching serial R reference task")
        errors = input_contract(reference_items[ref_key], hybrid, dataset)
        pair = compare_reports(
            reference_reports[ref_key], hybrid_reports[hyb_key], args.relative_floor
        )
        pair["contract_errors"] += errors
        pair["comparison_contract_verified"] = pair["comparison_contract_verified"] and not errors
        comparisons.append(
            {
                "dataset": dataset,
                "hybrid_method": method,
                "reference_method": "r_serial",
                "reference_report_sha256": reference_hashes[ref_key],
                "hybrid_report_sha256": hybrid_hashes[hyb_key],
                "input_provenance": hybrid["inputs"][dataset],
                **pair,
            }
        )
    old_source, new_source = reference["source_sha256"], hybrid["source_sha256"]
    shared = sorted(set(old_source) & set(new_source))
    report = {
        "schema_version": 1,
        "kind": "paired_R_rng_summary_discrepancies_only",
        "all_pairing_contracts_verified": bool(comparisons)
        and all(item["comparison_contract_verified"] for item in comparisons),
        "relative_difference_definition": "abs(hybrid - reference) / abs(reference), only where abs(reference) exceeds relative_floor; absolute discrepancies always include near-zero reference elements.",
        "relative_floor": args.relative_floor,
        "comparison_scope": "All recorded warmup and measured runs paired by phase and R seed. Same R RNGkind/version, preprocessing/task settings and prepared NPZ fingerprints are required.",
        "interpretation": "No numerical equivalence threshold is applied. Verified pairing means that descriptive comparison is possible, not that the methods or their full outputs are equal.",
        "metrics": {
            "iterations": "Recorded EM iteration counts per imputation",
            "normalized_heldout_rmse": "Heldout normalized RMSE per imputation",
            "pooled_column_means": "Column means averaged across m completed datasets",
            "mean_covariance": "Sample covariance matrices averaged across m completed datasets",
            "pooled_mean_within_variance": "Within-imputation variance of estimated column means",
            "pooled_mean_between_variance": "Between-imputation variance of estimated column means",
            "pooled_mean_variance": "Rubin total variance of estimated column means",
        },
        "comparisons": comparisons,
        "source_provenance": {
            "reference_source_sha256": old_source,
            "hybrid_source_sha256": new_source,
            "changed_shared_files": [
                name for name in shared if old_source[name] != new_source[name]
            ],
            "unchanged_shared_files": [
                name for name in shared if old_source[name] == new_source[name]
            ],
            "reference_suite_sha256": sha256(args.reference_dir / "suite.json"),
            "hybrid_suite_sha256": sha256(args.hybrid_dir / "suite.json"),
            "comparison_and_auditor_sha256": {
                path.name: sha256(path)
                for path in (
                    Path(__file__),
                    Path(__file__).with_name("summarize_benchmarks.py"),
                    Path(__file__).with_name("summarize_hybrid.py"),
                )
            },
        },
        "limitations": [
            "Full completed matrices were not saved. Matching or close means, covariance and RMSE cannot establish elementwise or bitwise equality; reported JSON values also have serialization precision limits.",
            "Matching R RNGkind and seeds pairs the intended random streams. These reports do not save every random draw or RNG state and therefore do not by themselves prove identical draw consumption.",
            "The original main suite retained NPZ fingerprints but not contemporaneous per-CSV hashes. The hybrid suite records reuse of the main CSV files and their hashes; this limitation in historical evidence is retained.",
            "The suites ran in separate wall-clock batches and source revisions. Initial interpreter/package imports and cold process startup were excluded. These summary discrepancies are not a controlled timing ratio.",
            "Native Python uses NumPy PCG64 and is excluded from this paired R RNG comparison; equal integer seeds do not pair R and NumPy draws.",
            "Only these complete-truth, block-MCAR development datasets and recorded backends are covered; no real-data universal validity or untested CUDA behavior is established.",
        ],
    }
    export_files([(args.output, (json.dumps(report, indent=2, allow_nan=False) + "\n").encode())])
    for item in comparisons:
        print(
            item["dataset"],
            item["hybrid_method"],
            "PAIRED" if item["comparison_contract_verified"] else "CONTRACT FAILED",
        )
    return int(not report["all_pairing_contracts_verified"])


if __name__ == "__main__":
    raise SystemExit(main())
