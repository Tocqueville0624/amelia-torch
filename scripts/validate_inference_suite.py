"""Bounded G5 synthetic inference comparison with prespecified marginal gates.

One persistent R process per R route avoids 400 R/Python cold starts. No timing
comparison is made. Formal runs use the frozen protocol; smoke runs cannot pass
formal inference gates. All failed and partial records remain in the report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import subprocess
import sys
import time
import warnings
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from scipy import stats
from validate_inference import (
    ROOT,
    SCENARIOS,
    TRUE_X1,
    fit_regression,
    pool_scalar,
    simulate_input,
    summarize,
    write_report,
)

PROTOCOL = ROOT / "docs/validation/g5-prespecified/protocol.json"
ROUTES = {
    "r-reference": ("reference", "cpu", "float64"),
    **{f"{engine}-{device}{bits}": (engine, device, f"float{bits}")
       for engine in ("hybrid", "native")
       for device, bits in (("cpu", 64), ("cuda", 64), ("cuda", 32), ("mps", 32))},
}


def map_r_seed(seed: int) -> int:
    """Mapping is fixed before any formal result; it never changes native RNG."""
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)) or not 0 <= seed < 2**32:
        raise ValueError("Expected original uint32 imputation seed")
    return int(seed) % (2**31 - 1)


def stress_input(n: int, seed: int, replicate: int) -> tuple[np.ndarray, int, dict]:
    """Independent seed namespace 2; high-correlation MCAR stress, not a new method."""
    children = np.random.SeedSequence([seed, 2, replicate]).spawn(3)
    data_seed, mask_seed, imp_seed = [int(child.generate_state(1)[0]) for child in children]
    rng = np.random.default_rng(data_seed)
    x = rng.multivariate_normal([0, 0], [[1, .95], [.95, 1]], size=n)
    y = 1 + x[:, 0] + .5 * x[:, 1] + rng.normal(size=n)
    data = np.column_stack([y, x])
    missing = np.random.default_rng(mask_seed).random((n, 2)) < .5
    data[:, 1:][missing] = np.nan
    return data, imp_seed, {
        "data_seed": data_seed, "mask_seed": mask_seed, "imputation_seed": imp_seed,
        "actual_covariate_missing_rate": float(missing.mean()),
        "actual_whole_matrix_missing_rate": float(missing.sum() / data.size),
        "mar_logistic_intercept": None,
    }


def prepare_inputs(directory: Path, protocol: dict, smoke: bool) -> list[dict]:
    settings = protocol["design"]
    count = 3 if smoke else settings["replicates_per_primary_scenario"]
    stress_count = 2 if smoke else settings["stress_replicates"]
    directory.mkdir()
    manifest = []
    keys = [(scenario, index) for index in range(count) for scenario in SCENARIOS]
    keys.extend(("stress_mcar", index) for index in range(stress_count))
    for scenario, index in keys:
        if scenario == "stress_mcar":
            data, seed, generated = stress_input(settings["n"], settings["seed"], index)
        else:
            data, seed, generated = simulate_input(
                settings["n"], scenario, settings["seed"], index
            )
        name = f"{scenario}-{index:03d}"
        path = directory / f"{name}.bin"
        content = np.asarray(data, dtype="<f8", order="C").tobytes()
        path.write_bytes(content)
        manifest.append({
            "id": name, "scenario": scenario, "replicate": index, **generated,
            "r_imputation_seed": map_r_seed(seed), "input_sha256": hashlib.sha256(content).hexdigest(),
            "input_md5": hashlib.md5(content).hexdigest(),  # R tools::md5sum transport check.
            "input_file": str(path),
        })
    return manifest


def interval_mean(values, confidence=.9) -> dict:
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("Need >=2 finite independent dataset-level values")
    mean = float(values.mean())
    mcse = float(values.std(ddof=1) / math.sqrt(len(values)))
    half = float(stats.t.ppf((1 + confidence) / 2, len(values) - 1)) * mcse
    return {"mean": mean, "mcse": mcse, "interval": [mean - half, mean + half]}


def paired_coverage(actual, reference, confidence=.9) -> dict:
    """Conservative exact interval via two discordance probabilities + union bound.

    Each Clopper-Pearson interval has 1-alpha/2 confidence. Thus their difference
    has at least 1-alpha coverage, without treating all-zero differences as certain.
    """
    actual, reference = np.asarray(actual, bool), np.asarray(reference, bool)
    if actual.ndim != 1 or actual.shape != reference.shape or len(actual) < 2:
        raise ValueError("Need >=2 matched coverage outcomes")
    difference = actual.astype(float) - reference.astype(float)
    positive, negative = int(np.sum(difference == 1)), int(np.sum(difference == -1))
    level = 1 - (1 - confidence) / 2
    pos = stats.binomtest(positive, len(actual)).proportion_ci(level, method="exact")
    neg = stats.binomtest(negative, len(actual)).proportion_ci(level, method="exact")
    return {
        "mean": float(difference.mean()),
        "mcse": float(difference.std(ddof=1) / math.sqrt(len(actual))),
        "interval": [pos.low - neg.high, pos.high - neg.low],
        "positive_discordances": positive, "negative_discordances": negative,
        "interval_method": "Difference of two Clopper-Pearson intervals, Bonferroni union bound",
    }


def inside(interval, bounds):
    return bool(len(interval) == 2 and np.isfinite(interval).all()
                and interval[0] >= bounds[0] and interval[1] <= bounds[1])


def record_valid(record: dict, m: int) -> bool:
    """Recheck evidence; a success label alone is never enough."""
    pooled = record.get("pooled", {})
    return bool(
        record.get("status") == "success"
        and record.get("quality_passed") is True
        and record.get("observed_preserved") is True
        and record.get("all_completed_values_finite") is True
        and record.get("backend_contract_passed") is True
        and record.get("imputation_fits_returned") == m
        and record.get("imputation_fits_converged") == m
        and record.get("imputation_fits_nonconverged") == 0
        and len(record.get("regression", [])) == m
        and all(isinstance(pooled.get(key), (int, float)) and np.isfinite(pooled[key])
                for key in ("estimate", "standard_error", "interval_width"))
        and pooled["standard_error"] > 0 and pooled["interval_width"] > 0
    )


def audit_scenario(records, reference, planned, protocol, *, formal, process_ok=True):
    gates, settings = protocol["gates"], protocol["design"]
    ids = [record["id"] for record in records]
    expected = [item["id"] for item in planned]
    complete = (len(ids) == len(set(ids)) and ids == expected
                and all(record_valid(record, settings["m"]) for record in records)
                and process_ok)
    inference = {"complete_valid_primary_records": complete,
                 "status": "insufficient_evidence", "checks": {},
                 "descriptive": summarize(records),
                 "status_counts": {state: sum(r["status"] == state for r in records)
                                   for state in sorted({r["status"] for r in records})}}
    valid = [record for record in records if record_valid(record, settings["m"])]
    if len(valid) > 1:
        inference["descriptive_pooled_se"] = interval_mean(
            [record["pooled"]["standard_error"] for record in valid], gates["confidence_level"]
        )
        inference["descriptive_interval_width"] = interval_mean(
            [record["pooled"]["interval_width"] for record in valid], gates["confidence_level"]
        )
    # All diagnostics remain descriptive when failure or a truncated run is present.
    if not complete or not formal or len(records) != settings["replicates_per_primary_scenario"]:
        inference["reason"] = "Incomplete/invalid/process-failed or smoke-only; no successful-subset gate"
        return inference
    level = gates["confidence_level"]
    estimates = np.array([record["pooled"]["estimate"] for record in records])
    bias = interval_mean(estimates - TRUE_X1, level)
    covers = [record["covered"] for record in records]
    interval = stats.binomtest(sum(covers), len(covers)).proportion_ci(level, method="exact")
    inference["absolute"] = {
        "bias": bias,
        "coverage": {"estimate": float(np.mean(covers)), "interval": [interval.low, interval.high],
                     "mcse": math.sqrt(np.mean(covers) * (1 - np.mean(covers)) / len(covers))},
    }
    checks = inference["checks"]
    checks["absolute_bias"] = inside(bias["interval"], gates["absolute_bias_interval"])
    checks["absolute_coverage"] = inside([interval.low, interval.high], gates["absolute_coverage_interval"])
    if reference is not None:
        reference_by_id = {record["id"]: record for record in reference}
        valid_reference = (len(reference_by_id) == len(reference) == len(records)
                           and all(key in reference_by_id for key in ids)
                           and all(record_valid(record, settings["m"]) for record in reference))
        if not valid_reference:
            inference["reason"] = "Reference incomplete or invalid; paired inference unavailable"
            return inference
        paired = [reference_by_id[key] for key in ids]
        if any(a["input_sha256"] != b["input_sha256"] or
               a["r_imputation_seed"] != b["r_imputation_seed"] or
               a["imputation_seed"] != b["imputation_seed"] for a, b in zip(records, paired)):
            inference["reason"] = "Input or seed mismatch; paired inference unavailable"
            return inference
        difference = interval_mean(estimates - [r["pooled"]["estimate"] for r in paired], level)
        coverage_difference = paired_coverage(covers, [r["covered"] for r in paired], level)
        inference["paired_vs_reference"] = {
            "estimate_difference": difference, "coverage_difference": coverage_difference,
        }
        checks["paired_estimate_difference"] = inside(
            difference["interval"], gates["paired_estimate_difference_interval"]
        )
        checks["paired_coverage_difference"] = inside(
            coverage_difference["interval"], gates["paired_coverage_difference_interval"]
        )
        for field, label in (("standard_error", "se"), ("interval_width", "width")):
            log_ratios = [math.log(a["pooled"][field] / b["pooled"][field])
                          for a, b in zip(records, paired)]
            log_summary = interval_mean(log_ratios, level)
            ratio = {"geometric_mean": math.exp(log_summary["mean"]),
                     "log_mcse": log_summary["mcse"],
                     "interval": [math.exp(value) for value in log_summary["interval"]]}
            inference["paired_vs_reference"][f"geometric_{label}_ratio"] = ratio
            checks[f"paired_{label}_ratio"] = inside(
                ratio["interval"], gates[f"paired_geometric_{label}_ratio_interval"]
            )
    inference["status"] = "passed" if all(checks.values()) else "outside_prespecified_bounds"
    return inference


def add_pooling(record: dict) -> dict:
    if record.get("status") != "success":
        return record
    try:
        model = record["regression"]
        pooled = pool_scalar([item["estimate"] for item in model], [item["variance"] for item in model])
        record.update(pooled=pooled, covered=pooled["interval_lower"] <= TRUE_X1 <= pooled["interval_upper"])
    except (KeyError, ValueError, TypeError) as error:
        record.update(status="pooling_failed", error_type=type(error).__name__, error=str(error))
    return record


def run_native(item: dict, settings: dict, route: str) -> dict:
    import torch

    from amelia_torch import amelia
    from amelia_torch.backends import synchronize

    _, device, dtype = ROUTES[route]
    record = {key: value for key, value in item.items() if key != "input_file"}
    record.update(status="failed", quality_passed=False)
    captured = []
    try:
        content = Path(item["input_file"]).read_bytes()
        if hashlib.sha256(content).hexdigest() != item["input_sha256"]:
            raise ValueError("Input digest mismatch")
        x = np.frombuffer(content, dtype="<f8").copy().reshape(settings["n"], 3)
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            fit = amelia(x, m=settings["m"], seed=item["imputation_seed"], device=device,
                         dtype=dtype, tolerance=1e-4, autopri=.05, emburn=(0, 500))
            synchronize(torch.device(device))
        records = fit["diagnostics"]["replicates"]
        imps = fit["imputations"]
        observed = np.isfinite(x)
        kept = all(np.array_equal(value[observed], x[observed]) for value in imps)
        finite = all(np.isfinite(value).all() for value in imps)
        shapes = len(imps) == settings["m"] and all(value.shape == x.shape for value in imps)
        backend_ok = len(records) == settings["m"] and all(
            value["device"] == device and value["dtype"] == dtype for value in records
        )
        record.update(
            warnings=[str(value.message) for value in captured], backend=fit["diagnostics"],
            backend_contract_passed=backend_ok, quality_passed=kept and finite and shapes,
            observed_preserved=kept, all_completed_values_finite=finite,
            imputation_fits_returned=len(records),
            imputation_fits_converged=sum(bool(value["converged"]) for value in records),
            imputation_fits_nonconverged=sum(not value["converged"] for value in records),
            em_iterations=[value["iterations"] for value in records],
            empri_final=[value["empri_final"] for value in records],
            pseudoinverse_uses=sum(value["pseudoinverse_uses"] for value in records),
        )
        if not fit["diagnostics"]["converged"]:
            record["status"] = "nonconverged"
        elif not backend_ok:
            record["status"] = "backend_failed"
        elif not record["quality_passed"]:
            record["status"] = "quality_failed"
        else:
            record["regression"] = [dict(zip(("estimate", "variance"), fit_regression(value)))
                                    for value in imps]
            record["status"] = "success"
    except (ValueError, RuntimeError, np.linalg.LinAlgError) as error:
        record.update(status="oom" if "out of memory" in str(error).lower() else "failed",
                      error_type=type(error).__name__, error=str(error))
    record.setdefault("warnings", [str(value.message) for value in captured])
    return add_pooling(record)


def sanitize(value):
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        value = value.replace(str(ROOT), "<project>").replace(str(Path.home()), "<home>")
        return re.sub(r"(?:/private)?/tmp/[^\s'\"]+", "<temporary>", value)
    return value


def source_hashes():
    paths = [PROTOCOL, Path(__file__), ROOT / "scripts/validate_inference.py",
             ROOT / "scripts/validate_inference_batch.R",
             *sorted((ROOT / "src/amelia_torch").rglob("*.py")),
             *sorted((ROOT / "r-package/R").glob("*.R")),
             *sorted((ROOT / "r-package/src").glob("*.c"))]
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "formal"), default="smoke")
    parser.add_argument("--routes", nargs="+", choices=ROUTES,
                        default=["r-reference", "hybrid-cpu64", "native-cpu64"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--time-budget-seconds", type=float, default=1800)
    args = parser.parse_args()
    if "r-reference" not in args.routes or len(set(args.routes)) != len(args.routes):
        parser.error("Include r-reference exactly once and do not duplicate routes")
    if args.time_budget_seconds <= 0 or not math.isfinite(args.time_budget_seconds):
        parser.error("Need positive finite wall-clock budget")
    if args.output.exists():
        parser.error("Output directory exists; use a fresh path to retain every previous result")
    args.output = args.output.absolute()
    args.output.mkdir(parents=True)
    protocol = json.loads(PROTOCOL.read_text())
    (args.output / "protocol.json").write_bytes(PROTOCOL.read_bytes())
    manifest = prepare_inputs(args.output / "inputs", protocol, args.mode == "smoke")
    settings = protocol["design"]
    source_before = source_hashes()
    report = {"schema_version": 1, "kind": "G5 prespecified synthetic inference comparison",
              "mode": args.mode, "started_utc": datetime.now(UTC).isoformat(),
              "wall_clock_budget_seconds": args.time_budget_seconds,
              "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
              "protocol": protocol, "routes_requested": args.routes,
              "source_sha256": source_before,
              "manifest": [{k: v for k, v in row.items() if k != "input_file"} for row in manifest],
              "environment": {"python": platform.python_version(), "numpy": np.__version__,
                              "os": platform.system(), "architecture": platform.machine()},
              "route_results": {}, "formal_acceptance_passed": False,
              "limitations": ["Only the prespecified Gaussian regression/missingness model.",
                              "Native and R use different random generators and seeds.",
                              "Marginal interval criteria; no familywise equivalence claim.",
                              "Stress has only 20 datasets and no inference acceptance gate.",
                              "No timing/performance claim; no Barnard-Rubin correction."]}
    os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "0"
    environment = os.environ.copy()
    environment.update(RETICULATE_PYTHON=sys.executable, PYTORCH_ENABLE_MPS_FALLBACK="0",
                       OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                       VECLIB_MAXIMUM_THREADS="1")
    # BLAS variables must be set before Python starts; R children receive fixed values.
    report["environment"]["blas_threads_at_python_start"] = {
        key: os.environ.get(key) for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                                            "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")}
    started = time.monotonic()
    for route in args.routes:
        remaining = args.time_budget_seconds - (time.monotonic() - started)
        engine, device, dtype = ROUTES[route]
        result = {"route": route, "records": [], "completed": False, "process_exit_status": None}
        if remaining > 0 and engine in ("reference", "hybrid"):
            destination = args.output / f"{route}.json"
            config = {"route": route, "device": device, "dtype": dtype, "threads": 1,
                      "n": settings["n"], "m": settings["m"], "datasets": manifest,
                      "output_json": str(destination), "time_budget_seconds": remaining}
            config_path = args.output / f"{route}.local-config.json"
            config_path.write_text(json.dumps(config))
            with (args.output / f"{route}.local.log").open("w") as log:
                try:
                    completed = subprocess.run(
                        ["Rscript", "--vanilla", str(ROOT / "scripts/validate_inference_batch.R"),
                         str(config_path)], cwd=ROOT, env=environment, stdout=log,
                        stderr=subprocess.STDOUT, timeout=remaining, check=False,
                    )
                    code = completed.returncode
                except subprocess.TimeoutExpired:
                    code = "timeout"
            if destination.exists():
                result.update(json.loads(destination.read_text()))
            result["process_exit_status"] = code
            if code != 0:
                result["process_log_tail"] = sanitize(
                    (args.output / f"{route}.local.log").read_text(errors="replace")[-4000:]
                )
            generated = {row["id"]: row for row in report["manifest"]}
            result["records"] = [add_pooling({**generated[row["id"]], **row}) for row in result["records"]]
        elif remaining > 0:
            import torch
            torch.set_num_threads(1)
            torch.backends.cuda.matmul.allow_tf32 = False
            torch.backends.cudnn.allow_tf32 = False
            report["environment"]["torch"] = str(torch.__version__)
            report["environment"]["cuda_runtime"] = torch.version.cuda
            report["environment"]["cuda_tf32_allowed"] = torch.backends.cuda.matmul.allow_tf32
            report["environment"]["mps_cpu_fallback"] = os.environ["PYTORCH_ENABLE_MPS_FALLBACK"]
            if device == "cuda" and torch.cuda.is_available():
                report["environment"]["cuda_gpu"] = torch.cuda.get_device_name(0)
                report["environment"]["cuda_total_memory_bytes"] = torch.cuda.get_device_properties(0).total_memory
            for row in manifest:
                if time.monotonic() - started >= args.time_budget_seconds:
                    break
                result["records"].append(run_native(row, settings, route))
                write_report(args.output / f"{route}.json", sanitize(result))
            result["completed"] = len(result["records"]) == len(manifest)
            result["process_exit_status"] = 0 if result["completed"] else "timeout"
        report["route_results"][route] = result
        write_report(args.output / "inference-suite.json", sanitize(report))
        print(json.dumps({"route": route, "retained_datasets": len(result["records"]),
                          "process_exit_status": result["process_exit_status"]}), flush=True)
    report["source_unchanged"] = source_before == source_hashes()
    reference = report["route_results"]["r-reference"]
    for route, result in report["route_results"].items():
        process_ok = (result["completed"] and result["process_exit_status"] == 0
                      and report["source_unchanged"])
        reference_ok = reference["completed"] and reference["process_exit_status"] == 0
        result["inference"] = {}
        for scenario in SCENARIOS:
            rows = [r for r in result["records"] if r["scenario"] == scenario]
            baseline = [r for r in reference["records"] if r["scenario"] == scenario]
            planned = [r for r in manifest if r["scenario"] == scenario]
            result["inference"][scenario] = audit_scenario(
                rows, None if route == "r-reference" else baseline, planned, protocol,
                formal=args.mode == "formal", process_ok=process_ok and reference_ok,
            )
        stress = [r for r in result["records"] if r["scenario"] == "stress_mcar"]
        result["stress"] = {"planned": 2 if args.mode == "smoke" else settings["stress_replicates"],
                            "attempted": len(stress), "valid": sum(record_valid(r, settings["m"]) for r in stress),
                            "status_counts": {state: sum(r["status"] == state for r in stress)
                                              for state in sorted({r["status"] for r in stress})},
                            "inference_gate": "not_applied", "descriptive": summarize(stress)}
    report["formal_primary_acceptance_passed"] = args.mode == "formal" and all(
        item["status"] == "passed" for result in report["route_results"].values()
        for item in result["inference"].values()
    )
    report["stress_requires_review"] = any(
        result["stress"]["attempted"] != result["stress"]["planned"]
        or result["stress"]["valid"] != result["stress"]["planned"]
        for result in report["route_results"].values()
    )
    report["formal_acceptance_passed"] = (
        report["formal_primary_acceptance_passed"] and not report["stress_requires_review"]
    )
    report["finished_utc"] = datetime.now(UTC).isoformat()
    report["validation_elapsed_seconds_not_a_benchmark"] = time.monotonic() - started
    write_report(args.output / "inference-suite.json", sanitize(report))
    if args.mode == "smoke":
        return 0 if report["source_unchanged"] and all(
            result["completed"] and result["process_exit_status"] == 0
            and all(record_valid(row, settings["m"]) for row in result["records"])
            for result in report["route_results"].values()
        ) else 1
    return 0 if report["formal_acceptance_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
