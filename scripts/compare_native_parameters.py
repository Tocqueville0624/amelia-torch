"""Offline differences in saved native CPU/GPU parameters and first-1000-row samples.

No fitting or torch import. Re-audit the entire native/R benchmark suite first.
CUDA expects 18 tasks and 12 parameter NPZs; --gpu mps --r-workers 4 expects the
15-task Mac suite and 9 NPZs. Only same-dtype native CPU/GPU pairs are compared.

Example:
  python scripts/compare_native_parameters.py --input-dir results/local/cloud/native \
    --prepared-dir data/prepared --output results/local/cloud/paired/native-parameters.json
Optional --parameter-hashes accepts a JSON object mapping every parameter NPZ
basename to its archived SHA256, without rewriting the archive or binary files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from summarize_benchmarks import (
    COLUMNS,
    DATASETS,
    audit_suite,
    is_count,
    is_number,
    portable_bytes,
    report_path,
    sha256,
    valid_hashes,
)

RNG = "NumPy PCG64; same seed does not reproduce R draws"
CONFIG_FIELDS = ("m", "seed", "repeats", "warmups", "threads", "tolerance", "max_iterations",
                 "empri", "autopri", "dtype")
ENVIRONMENT_FIELDS = ("python", "numpy", "torch", "platform", "cpu_threads", "cuda_runtime",
                      "mps_cpu_fallback")
SCALE_FIELDS = ("column_order_zero_based", "scale_mean_original_order", "scale_sd_original_order")


class EvidenceError(ValueError):
    """A controlled artifact-validation reason, safe to include in portable output."""


def require(condition, reason):
    if not condition:
        raise EvidenceError(reason)


def local_file(directory: Path, name: str, suffix: str) -> Path:
    require(isinstance(name, str) and Path(name).name == name and "/" not in name
            and "\\" not in name and name.endswith(suffix), "unsafe_artifact_filename")
    path = directory / name
    require(not path.is_symlink() and path.resolve().parent == directory.resolve(),
            "artifact_outside_input_directory")
    require(path.is_file(), f"missing_artifact:{name}")
    return path


def load_native_suite(directory, gpu, workers):
    suite_path = directory / "suite.json"
    suite = json.loads(portable_bytes(suite_path))
    require(isinstance(suite, dict), "suite_not_an_object")
    require(isinstance(suite.get("execution", []), list), "execution_not_a_list")
    reports, fingerprints = {}, {}
    for item in suite.get("execution", []):
        require(isinstance(item, dict), "execution_member_not_an_object")
        key = (item.get("dataset"), item.get("method"))
        require(key not in reports, "duplicate_suite_task")
        path = report_path(directory, item.get("result"))
        reports[key] = json.loads(portable_bytes(path))
        fingerprints[path.name] = sha256(path)
    methods = ["cpu64", "cpu32", f"{gpu}32", "r_serial", f"r_snow{workers}"]
    if gpu == "cuda":
        methods.append("cuda64")
    expected = [(dataset, method) for dataset in DATASETS for method in methods]
    audit = audit_suite(suite, reports, expected, expected_rows=100000)
    require(audit["all_passed"], "independent_complete_suite_audit_failed")
    return suite, reports, fingerprints, audit


def load_input(path, expected_hash, expected_shape):
    require(sha256(path) == expected_hash, "prepared_input_sha256_mismatch")
    with np.load(path, allow_pickle=False) as archive:
        data = archive["data"].copy()
        truth = archive["truth"]
        mask = archive["artificial_missing_mask"].copy()
        columns = archive["column_names"].tolist()
        require(data.shape == truth.shape == mask.shape == tuple(expected_shape),
                "prepared_input_shape_mismatch")
        require(data.dtype.kind == truth.dtype.kind == "f" and mask.dtype.kind == "b",
                "prepared_input_array_type_mismatch")
        require(np.isfinite(truth).all() and not np.isinf(data).any(), "nonfinite_complete_truth")
        require(np.array_equal(np.isnan(data), mask) and not mask.all(axis=1).any(),
                "input_not_complete_truth_artificial_mask_task")
        require(np.array_equal(data[~mask], truth[~mask]), "observed_input_differs_from_truth")
        require(len(columns) == data.shape[1] and len(set(columns)) == len(columns)
                and all(isinstance(name, str) for name in columns), "invalid_input_column_names")
        # Same complete-truth scale as benchmark.metrics, using all prepared rows,
        # not the saved prefix or the observed-only EM standardization scale.
        truth_sd = np.nanstd(truth, axis=0, ddof=1)
        require(np.isfinite(truth_sd).all() and (truth_sd > 0).all(), "invalid_full_truth_sd")
    return data, mask, columns, truth_sd


def load_parameters(path, p, m, n):
    with np.load(path, allow_pickle=False) as archive:
        require(set(archive.files) == {"theta", "sample_imputations"}, "unexpected_parameter_arrays")
        arrays = {name: archive[name].copy() for name in archive.files}
    require(arrays["theta"].shape == (p + 1, p + 1, m), "theta_shape_mismatch")
    require(arrays["sample_imputations"].shape == (m, min(n, 1000), p), "sample_shape_mismatch")
    for name, array in arrays.items():
        require(array.dtype.kind == "f" and np.isfinite(array).all(), f"nonfinite_or_nonnumeric:{name}")
    return arrays


def first_measured(report):
    runs = [run for run in report.get("runs", []) if run.get("warmup") is False]
    config = report.get("configuration", {})
    require(is_count(config.get("repeats"), 1) and is_count(config.get("seed")),
            "missing_measured_seed_schedule")
    expected = list(range(config["seed"], config["seed"] + config["repeats"]))
    require([run.get("seed") for run in runs] == expected, "measured_seed_schedule_mismatch")
    run = runs[0]
    require(run.get("seed") == report.get("configuration", {}).get("seed"),
            "first_measured_seed_mismatch")
    return run


def pairing_contract(cpu, gpu, expected_gpu, p, m):
    """Validate recorded metadata, not unrecorded normal draws or embedded NPZ seeds."""
    left, right = cpu.get("configuration", {}), gpu.get("configuration", {})
    for field in CONFIG_FIELDS:
        require(field in left and field in right and left[field] == right[field],
                f"configuration_mismatch_or_missing:{field}")
    require(left.get("device") == "cpu" and right.get("device") == expected_gpu,
            "requested_device_mismatch")
    require(left.get("dtype") in {"float32", "float64"}, "unknown_computation_dtype")
    require(left.get("m") == m, "imputation_count_mismatch")
    require(cpu.get("input_sha256") == gpu.get("input_sha256"), "paired_input_hash_mismatch")
    require(cpu.get("shape") == gpu.get("shape"), "paired_input_shape_mismatch")
    for field in ENVIRONMENT_FIELDS:
        a, b = cpu.get("environment", {}), gpu.get("environment", {})
        require(field in a and field in b and a[field] == b[field],
                f"runtime_mismatch_or_missing:{field}")
    a, b = first_measured(cpu), first_measured(gpu)
    require(a["seed"] == b["seed"] and is_count(a["seed"]), "paired_seed_mismatch")
    x, y = a.get("diagnostics", {}), b.get("diagnostics", {})
    for report, diagnostics in ((cpu, x), (gpu, y)):
        configuration = report["configuration"]
        require(diagnostics.get("rng") == RNG, "missing_or_different_PCG64_contract")
        require(diagnostics.get("seed") == a["seed"], "diagnostic_seed_mismatch")
        require(diagnostics.get("engine") == "torch-native-continuous", "not_native_engine")
        require(diagnostics.get("reference_version") == "1.8.3", "reference_version_mismatch")
        require(diagnostics.get("device") == configuration["device"]
                and diagnostics.get("dtype") == configuration["dtype"], "diagnostic_backend_mismatch")
        require(diagnostics.get("wholly_missing_rows_retained") == 0, "unexpected_wholly_missing_rows")
        order = diagnostics.get("column_order_zero_based")
        require(isinstance(order, list) and len(order) == p
                and all(is_count(value) for value in order) and sorted(order) == list(range(p)),
                "missing_or_invalid_column_order")
        for field in SCALE_FIELDS[1:]:
            values = diagnostics.get(field)
            require(isinstance(values, list) and len(values) == p
                    and all(is_number(value) for value in values), f"missing_or_invalid:{field}")
        require(all(value > 0 for value in diagnostics["scale_sd_original_order"]),
                "nonpositive_standardization_scale")
        fits = diagnostics.get("replicates")
        require(isinstance(fits, list) and len(fits) == m, "missing_replicate_diagnostics")
        for fit in fits:
            require(fit.get("device") == configuration["device"]
                    and fit.get("dtype") == configuration["dtype"], "replicate_backend_mismatch")
            require(is_count(fit.get("bootstrap_attempts"), 1), "missing_or_invalid_bootstrap_attempts")
    for field in SCALE_FIELDS:
        require(x[field] == y[field], f"preprocessing_metadata_mismatch:{field}")
    attempts = [[fit["bootstrap_attempts"] for fit in diagnostics["replicates"]]
                for diagnostics in (x, y)]
    require(attempts[0] == attempts[1], "bootstrap_attempt_counts_differ")
    return {
        "phase": "first_measured", "seed": a["seed"], "m": m,
        "computation_dtype": left["dtype"], "rng": RNG,
        "bootstrap_attempts_per_imputation": attempts[0],
        "standardization_and_column_order_recorded_equal": True,
        "preprocessing_metadata": {field: x[field] for field in SCALE_FIELDS},
        "runtime": {field: cpu["environment"][field] for field in ENVIRONMENT_FIELDS},
        "iterations": {"cpu": [fit.get("iterations") for fit in x["replicates"]],
                       "gpu": [fit.get("iterations") for fit in y["replicates"]]},
        "bootstrap_indices_or_normals_archived": False,
        "NPZ_embeds_seed_or_input_hash": False,
    }


def differences(left, right, relative_floor=1e-12):
    """Descriptive elementwise differences; the floor is not an equivalence tolerance."""
    left, right = np.asarray(left, dtype=np.float64), np.asarray(right, dtype=np.float64)
    require(left.shape == right.shape, "difference_shape_mismatch")
    require(np.isfinite(left).all() and np.isfinite(right).all(), "nonfinite_difference_input")
    if not left.size:
        return {"elements": 0, "exact_numeric_equal_elements": 0, "maximum_absolute": None,
                "maximum_relative_where_reference_exceeds_floor": None,
                "near_zero_reference_elements": 0, "maximum_absolute_near_zero_reference": None,
                "root_mean_squared_pair_difference": None}
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        delta = np.abs(right - left)
        away = np.abs(left) > relative_floor
        relative = delta[away] / np.abs(left[away])
    require(np.isfinite(delta).all() and np.isfinite(relative).all(), "difference_overflow")
    largest = float(delta.max())
    # Scaling keeps the descriptive RMS from overflowing for finite differences.
    rms = largest * float(np.sqrt(np.mean((delta / largest) ** 2))) if largest else 0.0
    return {"elements": int(left.size), "exact_numeric_equal_elements": int((left == right).sum()),
            "maximum_absolute": largest,
            "maximum_relative_where_reference_exceeds_floor": float(relative.max()) if away.any() else None,
            "near_zero_reference_elements": int((~away).sum()),
            "maximum_absolute_near_zero_reference": float(delta[~away].max()) if (~away).any() else None,
            "root_mean_squared_pair_difference": rms}


def absolute_summary(delta):
    """Max/RMS of signed differences, without inventing an acceptance threshold."""
    delta = np.asarray(delta, dtype=np.float64)
    require(np.isfinite(delta).all(), "nonfinite_standardized_difference")
    maximum = float(np.max(np.abs(delta))) if delta.size else None
    rms = (maximum * float(np.sqrt(np.mean((delta / maximum) ** 2)))
           if maximum else 0.0 if delta.size else None)
    return {"elements": int(delta.size), "maximum_absolute": maximum,
            "root_mean_squared_pair_difference": rms}


def compare_arrays(cpu_arrays, gpu_arrays, data, mask, m, relative_floor, truth_sd, columns):
    rows = min(len(data), 1000)
    sample_input, missing = data[:rows], mask[:rows]
    observed = ~missing
    truth_sd = np.asarray(truth_sd, dtype=np.float64)
    require(truth_sd.shape == (data.shape[1],) and np.isfinite(truth_sd).all()
            and (truth_sd > 0).all(), "invalid_full_truth_sd")
    require(len(columns) == data.shape[1], "column_label_count_mismatch")
    results = []
    for replicate in range(m):
        a, b = cpu_arrays["sample_imputations"][replicate], gpu_arrays["sample_imputations"][replicate]
        require(np.array_equal(a[observed], sample_input[observed]), "cpu_sample_changed_observed_cells")
        require(np.array_equal(b[observed], sample_input[observed]), "gpu_sample_changed_observed_cells")
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            raw_delta = np.asarray(b, dtype=np.float64) - np.asarray(a, dtype=np.float64)
            standardized_delta = raw_delta / truth_sd
        per_column = []
        for column in range(data.shape[1]):
            values = raw_delta[missing[:, column], column]
            summary = absolute_summary(values)
            maximum = summary["maximum_absolute"]
            per_column.append({
                "column_zero_based": column, "column": columns[column],
                "missing_elements": summary["elements"], "full_truth_sd_ddof1": float(truth_sd[column]),
                "maximum_absolute_original_units": maximum,
                "maximum_absolute_divided_by_full_truth_sd":
                    maximum / float(truth_sd[column]) if maximum is not None else None,
            })
        results.append({
            "imputation": replicate + 1,
            "theta_standardized_reordered": differences(cpu_arrays["theta"][:, :, replicate],
                                                         gpu_arrays["theta"][:, :, replicate], relative_floor),
            "sample_observed_cells": differences(a[observed], b[observed], relative_floor),
            "sample_artificially_missing_cells": differences(a[missing], b[missing], relative_floor),
            "sample_missing_differences_in_full_truth_sd_units": absolute_summary(
                standardized_delta[missing]),
            "sample_missing_differences_per_column": per_column,
            "both_samples_preserve_original_observed_values_exactly": True,
        })
    return results


def analyze(directory, prepared_dir, gpu, workers, relative_floor, parameter_hashes=None,
            evidence=None):
    evidence = {} if evidence is None else evidence
    if (directory / "suite.json").is_file():
        evidence["suite_sha256"] = sha256(directory / "suite.json")
    suite, reports, report_hashes, audit = load_native_suite(directory, gpu, workers)
    evidence["report_sha256"] = report_hashes
    native_methods = ["cpu64", "cpu32", f"{gpu}32"] + (["cuda64"] if gpu == "cuda" else [])
    expected_files = {f"{dataset}-{method}.parameters.npz" for dataset in DATASETS for method in native_methods}
    observed_files = {path.name for path in directory.glob("*.npz")}
    evidence["observed_parameter_filenames"] = sorted(observed_files)
    require(observed_files == expected_files,
            "parameter_file_set_not_exactly_expected")
    if parameter_hashes is not None:
        require(valid_hashes(parameter_hashes) and set(parameter_hashes) == expected_files,
                "archive_hash_manifest_missing_extra_or_invalid")
    parameters, parameter_provenance = {}, {}
    evidence["parameter_files"] = parameter_provenance
    for dataset in DATASETS:
        for method in native_methods:
            name = f"{dataset}-{method}.parameters.npz"
            report = reports[(dataset, method)]
            require(report.get("parameter_file") == name, "report_parameter_filename_mismatch")
            path = local_file(directory, name, ".parameters.npz")
            digest = sha256(path)
            parameter_provenance[name] = {"sha256": digest, "bytes": path.stat().st_size,
                                          "archived_sha256_verified": False}
            if parameter_hashes is not None:
                require(digest == parameter_hashes[name], f"archived_parameter_sha256_mismatch:{name}")
                parameter_provenance[name]["archived_sha256_verified"] = True
            n, p = report["shape"]
            arrays = load_parameters(path, p, report["configuration"]["m"], n)
            parameters[(dataset, method)] = arrays
            parameter_provenance[name] = {
                "sha256": digest, "bytes": path.stat().st_size,
                "archived_sha256_verified": parameter_hashes is not None,
                "arrays": {key: {"shape": list(value.shape), "storage_dtype": str(value.dtype)}
                           for key, value in arrays.items()},
            }
    pairs, inputs = [], {}
    evidence["inputs"] = inputs
    for dataset in DATASETS:
        reference = reports[(dataset, "cpu64")]
        name = reference.get("input_filename")
        source = local_file(prepared_dir, name, ".npz")
        digest = reference.get("input_sha256")
        data, mask, columns, truth_sd = load_input(source, digest, (100000, COLUMNS[dataset]))
        for item in suite["execution"]:
            if item["dataset"] == dataset:
                require(item.get("input_sha256") == digest, "cross_method_prepared_input_hash_mismatch")
        for method in native_methods:
            report = reports[(dataset, method)]
            require(report.get("input_sha256") == digest and report.get("input_filename") == name,
                    "native_input_provenance_mismatch")
        inputs[dataset] = {"file": name, "sha256": digest, "shape": list(data.shape), "columns": columns,
                           "sample_rows_compared": min(len(data), 1000),
                           "sample_missing_cells_per_imputation": int(mask[:1000].sum()),
                           "sample_observed_cells_per_imputation": int((~mask[:1000]).sum()),
                           "missing_difference_normalization": {
                               "definition": "(GPU sample - CPU sample) / full prepared truth column sample SD",
                               "truth_rows_used": len(data), "ddof": 1,
                               "scale_sd_original_column_order": truth_sd.tolist(),
                               "scale_matches_benchmark_heldout_RMSE_contract": True,
                           }}
        for precision in ([64, 32] if gpu == "cuda" else [32]):
            left, right = f"cpu{precision}", f"{gpu}{precision}"
            cpu_report, gpu_report = reports[(dataset, left)], reports[(dataset, right)]
            m = cpu_report["configuration"]["m"]
            metadata = pairing_contract(cpu_report, gpu_report, gpu, data.shape[1], m)
            records = compare_arrays(parameters[(dataset, left)], parameters[(dataset, right)],
                                     data, mask, m, relative_floor, truth_sd, columns)
            pairs.append({"dataset": dataset, "cpu_method": left, "gpu_method": right,
                          "pairing_contract_verified": True, "metadata": metadata,
                          "cpu_parameter_file": cpu_report["parameter_file"],
                          "gpu_parameter_file": gpu_report["parameter_file"], "imputations": records})
    return {
        "all_pairing_contracts_verified": True,
        "independent_complete_suite_audit_passed": audit["all_passed"],
        "audited_task_count": len(audit["measurements"]), "parameter_files": parameter_provenance,
        "inputs": inputs, "comparisons": pairs,
        "source_provenance": {"suite_sha256": sha256(directory / "suite.json"),
                              "report_sha256": report_hashes,
                              "recorded_benchmark_source_sha256": suite["source_sha256"]},
    }


def write_new_report(output, report):
    checksum_path = output.with_name(output.name + ".sha256.json")
    require(not any(path.exists() or path.is_symlink() for path in (output, checksum_path)),
            "output_already_exists")
    raw = (json.dumps(report, indent=2, allow_nan=False) + "\n").encode()
    checksum = {"file": output.name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(raw)
    with checksum_path.open("x") as stream:
        stream.write(json.dumps(checksum, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--prepared-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--gpu", choices=["cuda", "mps"], default="cuda")
    parser.add_argument("--r-workers", choices=[2, 4], type=int, default=2)
    parser.add_argument("--relative-floor", type=float, default=1e-12,
                        help="Exclude near-zero denominators from relative descriptions; not an equivalence gate")
    parser.add_argument("--parameter-hashes", type=Path,
                        help="Optional JSON object mapping all parameter basenames to archived raw SHA256")
    args = parser.parse_args()
    if not is_number(args.relative_floor) or args.relative_floor <= 0:
        parser.error("relative-floor must be finite and positive")
    checksum_path = args.output.with_name(args.output.name + ".sha256.json")
    if any(path.exists() or path.is_symlink() for path in (args.output, checksum_path)):
        parser.error("Use a fresh output and checksum path; prior evidence is never overwritten")
    report = {
        "schema_version": 1, "kind": "offline_native_first_measured_parameter_and_sample_differences",
        "created_utc": datetime.now(UTC).isoformat(), "fitting_performed": False,
        "performance_timing_includes_this_analysis": False, "relative_floor": args.relative_floor,
        "equivalence_threshold_applied": False,
        "source_code_sha256": {path.name: sha256(path) for path in
                               (Path(__file__), Path(__file__).with_name("summarize_benchmarks.py"))},
        "limitations": [
            "Parameter NPZs contain no seed, input hash, or run-time hash in the measured JSON. Association uses the report filename and audited runner convention: save the first measured call. Current raw hashes, and optional archive hash checks, establish file integrity, not an independent cryptographic link to that run.",
            "Only the first measured call's m parameter matrices and input-order first 1000 rows were saved. No claim covers the remaining rows, other repeats or warmups; this prefix is not a new random evaluation sample.",
            "Recorded PCG64/version/seed, equal standardization and column order, and equal bootstrap attempt counts support the intended native random-stream pairing. Actual bootstrap indices and standard normal arrays were not saved; their elementwise identity is not independently proven here. R RNG is never paired with NumPy by integer seed.",
            "Computation dtype comes from requested configuration and per-fit diagnostics. NPZ storage can be float64 even when Torch calculated in float32; stored dtype is reported separately.",
            "Theta is in standardized, reordered coordinates; sample imputations are restored to original input row/column order and units. Observed and artificially missing sample cells are compared separately.",
            "Missing-cell differences retain their original units and are additionally divided by each complete prepared truth column's sample SD (ddof=1, all rows), matching the benchmark heldout RMSE scale. This is not the first-1000-row or observed-only EM scale; max/RMS and per-column maxima describe differences without attributing their cause.",
            "No allclose or statistical-equivalence gate is introduced. Exact numeric-equality counts and absolute/relative differences describe only saved elements, not bitwise equality or universal statistical validity. Similar RMSE or pooled statistics cannot establish elementwise equality.",
            "The shared suite and runtime metadata describe a same-host experiment; this offline reader cannot independently authenticate hardware identity or unrecorded per-process source immutability. All reading/comparison is outside recorded benchmark timing.",
        ],
    }
    evidence = {}
    try:
        hashes = json.loads(args.parameter_hashes.read_text()) if args.parameter_hashes else None
        if args.parameter_hashes:
            report["parameter_hash_manifest"] = {"file": args.parameter_hashes.name,
                                                 "sha256": sha256(args.parameter_hashes)}
        report.update(analyze(args.input_dir, args.prepared_dir, args.gpu, args.r_workers,
                              args.relative_floor, hashes, evidence))
    except Exception as error:  # noqa: BLE001 - retain corrupt/unsupported artifact failures safely
        # The saved failure type is enough to identify unexpected IO/schema errors
        # without leaking private paths from exception messages.
        report.update(all_pairing_contracts_verified=False, comparisons=[],
                      error_type=type(error).__name__, available_input_evidence=evidence)
        report["error"] = str(error) if isinstance(error, EvidenceError) else "input_read_or_schema_failure"
    write_new_report(args.output, report)
    print(json.dumps({"all_pairing_contracts_verified": report["all_pairing_contracts_verified"],
                      "pairs": len(report.get("comparisons", [])), "output": args.output.name}))
    return 0 if report["all_pairing_contracts_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
