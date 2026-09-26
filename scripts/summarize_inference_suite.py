"""Read-only independent reconstruction of formal G5 evidence and portable export.

This does not fit imputation models or change the registered criteria. A failed
statistical criterion is a valid retained result, not an audit execution failure.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import re
import zipfile
from pathlib import Path

import numpy as np
from scipy import stats
from validate_inference import ROOT, simulate_input


def mean_interval(values, level):
    values = np.asarray(values, float)
    mean = float(np.mean(values))
    mcse = float(np.std(values, ddof=1) / np.sqrt(len(values)))
    half = stats.t.ppf((1 + level) / 2, len(values) - 1) * mcse
    return {"mean": mean, "mcse": mcse, "interval": [float(mean - half), float(mean + half)]}


def reconstruct_scenario(rows, reference, gates):
    """Recompute from m raw regression coefficients/variances, not stored pooling."""
    estimates, errors, widths, covered = [], [], [], []
    for row in rows:
        q = np.array([item["estimate"] for item in row["regression"]], float)
        u = np.array([item["variance"] for item in row["regression"]], float)
        if not np.isfinite(q).all() or not np.isfinite(u).all() or np.any(u < 0):
            raise ValueError("Nonfinite or negative raw regression evidence")
        within, between, estimate = u.mean(), q.var(ddof=1), q.mean()
        extra = (1 + 1 / len(q)) * between
        total = within + extra
        df = math.inf if extra == 0 else (len(q) - 1) * (1 + within / extra) ** 2
        half = stats.t.ppf(.975, df) * math.sqrt(total)
        value = {"estimate": float(estimate), "standard_error": math.sqrt(total),
                 "interval_lower": float(estimate - half), "interval_upper": float(estimate + half),
                 "interval_width": float(half * 2), "total_variance": float(total),
                 "between_variance": float(between), "within_variance": float(within)}
        if any(not np.isclose(value[key], row["pooled"][key], rtol=1e-11, atol=1e-13) for key in value):
            raise ValueError("Saved pooling disagrees with raw-regression reconstruction")
        coverage = bool(value["interval_lower"] <= 1 <= value["interval_upper"])
        if coverage != row["covered"]:
            raise ValueError("Saved coverage disagrees with reconstructed interval")
        estimates.append(estimate)
        errors.append(math.sqrt(total))
        widths.append(2 * half)
        covered.append(coverage)
    level = gates["confidence_level"]
    count = len(rows)
    coverage = float(np.mean(covered))
    ci = stats.binomtest(sum(covered), count).proportion_ci(level, method="exact")
    bias = mean_interval(np.asarray(estimates) - 1, level)
    summary = {"datasets": count, "covered": int(sum(covered)), "bias": bias,
               "coverage": {"mean": coverage, "mcse": math.sqrt(coverage * (1 - coverage) / count),
                            "interval": [ci.low, ci.high]},
               "pooled_se": mean_interval(errors, level),
               "interval_width": mean_interval(widths, level), "checks": {}}
    def contains(interval, bounds):
        return bool(interval[0] >= bounds[0] and interval[1] <= bounds[1])
    checks = summary["checks"]
    checks["absolute_bias"] = contains(bias["interval"], gates["absolute_bias_interval"])
    checks["absolute_coverage"] = contains([ci.low, ci.high], gates["absolute_coverage_interval"])
    if reference is not None:
        qdiff = np.asarray(estimates) - [row["pooled"]["estimate"] for row in reference]
        estimated = mean_interval(qdiff, level)
        delta = np.asarray(covered, int) - [int(row["covered"]) for row in reference]
        cp_level = 1 - (1 - level) / 2
        plus = stats.binomtest(int(np.sum(delta == 1)), count).proportion_ci(cp_level, method="exact")
        minus = stats.binomtest(int(np.sum(delta == -1)), count).proportion_ci(cp_level, method="exact")
        cov_interval = [plus.low - minus.high, plus.high - minus.low]
        paired = {"estimate_difference": estimated,
                  "coverage_difference": {"mean": float(np.mean(delta)),
                                          "mcse": float(np.std(delta, ddof=1) / np.sqrt(count)),
                                          "interval": cov_interval,
                                          "positive_discordances": int(np.sum(delta == 1)),
                                          "negative_discordances": int(np.sum(delta == -1))}}
        checks["paired_estimate_difference"] = contains(estimated["interval"], gates["paired_estimate_difference_interval"])
        checks["paired_coverage_difference"] = contains(cov_interval, gates["paired_coverage_difference_interval"])
        for values, key, field in ((errors, "se", "standard_error"), (widths, "width", "interval_width")):
            log_value = mean_interval(np.log(np.asarray(values) / [r["pooled"][field] for r in reference]), level)
            ratio_ci = list(np.exp(log_value["interval"]))
            paired[f"geometric_{key}_ratio"] = {"mean": math.exp(log_value["mean"]),
                                               "log_mcse": log_value["mcse"], "interval": ratio_ci}
            checks[f"paired_{key}_ratio"] = contains(ratio_ci, gates[f"paired_geometric_{key}_ratio_interval"])
        summary["paired_vs_reference"] = paired
    summary["status"] = "passed" if all(checks.values()) else "outside_prespecified_bounds"
    return summary


def fit_evidence_valid(row, route):
    """Check actual per-fit metadata/history rather than the producer's flags alone."""
    if not route.startswith("native-"):
        histories = row.get("iter_histories")
        if not isinstance(histories, list) or len(histories) != 5:
            return False
        if not all(h is None or (isinstance(h, list) and h and isinstance(h[-1], list)
                                 and h[-1] and h[-1][0] == 0) for h in histories):
            return False
        if row.get("code") != 1 or row.get("input_md5_verified") is not True:
            return False
    if route == "r-reference":
        return True
    mode = route.split("-", 1)[1]
    device, dtype = mode[:-2], "float" + mode[-2:]
    backend = row.get("backend") or {}
    if (backend.get("device") != device or backend.get("dtype") != dtype
            or backend.get("reference_version") != "1.8.3" or backend.get("converged") is not True):
        return False
    if route.startswith("hybrid-"):
        if (backend.get("engine") != "r-amelia-torch-em"
                or backend.get("call_engine") != "r-amelia-torch-em"
                or backend.get("current_call_torch_used") is not True
                or backend.get("current_call_gpu_used") != (device != "cpu")):
            return False
        fits = backend.get("fits", [])
    else:
        if backend.get("engine") != "torch-native-continuous" or backend.get("seed") != row["imputation_seed"]:
            return False
        fits = backend.get("replicates", [])
    return len(fits) == 5 and all(fit.get("converged") is True
                                  and fit.get("device") == device and fit.get("dtype") == dtype
                                  for fit in fits)


def audit(report):
    errors = []
    protocol = report["protocol"]
    settings, gates = protocol["design"], protocol["gates"]
    if report["mode"] != "formal" or report["source_unchanged"] is not True:
        errors.append("Not a formal unchanged-source execution")
    if settings["replicates_per_primary_scenario"] != 200 or settings["n"] != 300 or settings["m"] != 5:
        errors.append("Unexpected formal design")
    expected = [(s, i) for i in range(200) for s in ("mcar", "mar_y_observed")]
    expected.extend(("stress_mcar", i) for i in range(20))
    manifest = report["manifest"]
    if [(row["scenario"], row["replicate"]) for row in manifest] != expected:
        errors.append("Manifest does not contain the complete prespecified design")
    # Reuse only the original input generator, not producer summaries or gate helpers.
    for row in manifest:
        if row["scenario"] == "stress_mcar":
            children = np.random.SeedSequence([settings["seed"], 2, row["replicate"]]).spawn(3)
            ds, ms, seed = [int(child.generate_state(1)[0]) for child in children]
            rng = np.random.default_rng(ds)
            x = rng.multivariate_normal([0, 0], [[1, .95], [.95, 1]], size=300)
            y = 1 + x[:, 0] + .5 * x[:, 1] + rng.normal(size=300)
            data = np.column_stack([y, x])
            mask = np.random.default_rng(ms).random((300, 2)) < .5
            data[:, 1:][mask] = np.nan
            metadata = {"data_seed": ds, "mask_seed": ms}
        else:
            data, seed, metadata = simulate_input(300, row["scenario"], settings["seed"], row["replicate"])
        actual = hashlib.sha256(np.asarray(data, dtype="<f8", order="C").tobytes()).hexdigest()
        if (actual != row["input_sha256"] or seed != row["imputation_seed"]
                or seed % (2**31 - 1) != row["r_imputation_seed"]
                or any(row[key] != metadata[key] for key in ("data_seed", "mask_seed"))):
            errors.append(f"Input/seed reconstruction mismatch: {row['id']}")
    results = report["route_results"]
    if list(results) != report["routes_requested"] or "r-reference" not in results:
        errors.append("Missing, reordered, or unexpected route")
    summary = {"schema_version": 1, "kind": "Independent G5 evidence reconstruction",
               "producer_mode": report["mode"], "protocol_sha256": report["protocol_sha256"],
               "routes": {}, "audit_errors": errors}
    for name, result in results.items():
        rows = result["records"]
        valid = (result["completed"] is True and result["process_exit_status"] == 0
                 and len(rows) == len(manifest))
        if [r["id"] for r in rows] != [r["id"] for r in manifest]:
            valid = False
        for row, generated in zip(rows, manifest):
            if any(row.get(key) != generated[key] for key in
                   ("id", "scenario", "replicate", "input_sha256", "data_seed", "mask_seed",
                    "imputation_seed", "r_imputation_seed")):
                errors.append(f"Route record input/seed mismatch: {name}/{row.get('id')}")
        route_summary = {"records": len(rows), "all_planned_records_and_process_complete": valid,
                         "status_counts": {state: sum(r["status"] == state for r in rows)
                                           for state in sorted({r["status"] for r in rows})},
                         "scenarios": {}}
        route_summary["fit_diagnostics"] = {
            "returned": sum(row.get("imputation_fits_returned", 0) for row in rows),
            "converged": sum(row.get("imputation_fits_converged", 0) for row in rows),
            "maximum_em_iterations": max((value for row in rows for value in row.get("em_iterations", [])), default=None),
            "datasets_with_warnings": sum(bool(row.get("warnings")) for row in rows),
            "datasets_missing_internal_diagnostics": sum(row.get("pseudoinverse_uses") is None for row in rows),
            "pseudoinverse_uses": None if name == "r-reference" else sum(row.get("pseudoinverse_uses") or 0 for row in rows),
            "datasets_with_positive_final_empri": None if name == "r-reference" else sum(
                any(value > 0 for value in (row.get("empri_final") or [])) for row in rows),
        }
        summary["routes"][name] = route_summary
        for scenario in ("mcar", "mar_y_observed", "stress_mcar"):
            selected = [row for row in rows if row["scenario"] == scenario]
            usable = valid and all(
                row["status"] == "success" and row.get("observed_preserved") is True
                and row.get("all_completed_values_finite") is True
                and row.get("quality_passed") is True and row.get("backend_contract_passed") is True
                and row.get("imputation_fits_returned") == row.get("imputation_fits_converged") == 5
                and row.get("imputation_fits_nonconverged") == 0
                and len(row.get("regression", [])) == 5 and fit_evidence_valid(row, name) for row in selected)
            if scenario == "stress_mcar":
                route_summary["stress"] = {"attempted": len(selected), "all_valid": usable,
                                           "coverage_gate_applied": False}
                continue
            reference = [row for row in results["r-reference"]["records"] if row["scenario"] == scenario]
            baseline_valid = (
                results["r-reference"]["completed"] is True
                and results["r-reference"]["process_exit_status"] == 0
                and all(row["status"] == "success" and row.get("quality_passed") is True
                        and row.get("imputation_fits_converged") == 5
                        and fit_evidence_valid(row, "r-reference") for row in reference)
                and len(reference) == 200
            )
            if not usable or not baseline_valid:
                route_summary["scenarios"][scenario] = {"status": "insufficient_evidence"}
                if result["inference"][scenario]["status"] != "insufficient_evidence":
                    errors.append(f"Producer accepted unavailable/invalid per-fit evidence: {name}/{scenario}")
                continue
            try:
                recalculated = reconstruct_scenario(selected, None if name == "r-reference" else reference, gates)
                recorded = result["inference"][scenario]
                if recalculated["checks"] != recorded["checks"] or recalculated["status"] != recorded["status"]:
                    errors.append(f"Gate reconstruction disagreement: {name}/{scenario}")
                route_summary["scenarios"][scenario] = recalculated
            except (ValueError, KeyError, TypeError) as error:
                errors.append(f"Reconstruction failed: {name}/{scenario}: {error}")
    summary["all_primary_criteria_passed"] = all(
        entry["status"] == "passed" for result in summary["routes"].values()
        for entry in result["scenarios"].values()
    )
    summary["stress_requires_review"] = any(
        not result["stress"]["all_valid"] for result in summary["routes"].values()
    )
    summary["producer_formal_acceptance_passed"] = report["formal_acceptance_passed"]
    reconstructed_full = summary["all_primary_criteria_passed"] and not summary["stress_requires_review"]
    if (summary["all_primary_criteria_passed"] != report["formal_primary_acceptance_passed"]
            or reconstructed_full != report["formal_acceptance_passed"]
            or summary["stress_requires_review"] != report["stress_requires_review"]):
        errors.append("Overall acceptance flags disagree with independent reconstruction")
    summary["audit_passed"] = not errors
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new export directory")
    data = args.report.read_bytes()
    report = json.loads(data)
    if re.search(rb"/Users/|/private/var/|/content/|[\w.+-]+@[\w.-]+\.[A-Za-z]+", data):
        raise ValueError("Potential private path/email in producer report; inspect before export")
    protocol_path = ROOT / "docs/validation/g5-prespecified/protocol.json"
    protocol_bytes = protocol_path.read_bytes()
    if (hashlib.sha256(protocol_bytes).hexdigest() != report["protocol_sha256"]
            or json.loads(protocol_bytes) != report["protocol"]):
        raise ValueError("Protocol contents/hash disagree with frozen file")
    summary = audit(report)
    summary["raw_report_sha256"] = hashlib.sha256(data).hexdigest()
    summary["raw_report_bytes"] = len(data)
    summary["audit_script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    source = []
    for name, expected in report["source_sha256"].items():
        path = ROOT / name
        if not path.resolve().is_relative_to(ROOT) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Measured source changed or unsafe: {name}")
        source.append((name, path.read_bytes()))
    if not summary["audit_passed"]:
        raise ValueError(summary["audit_errors"])
    args.output.mkdir(parents=True)
    (args.output / "inference-suite.json.gz").write_bytes(gzip.compress(data, mtime=0))
    with zipfile.ZipFile(args.output / "measured-source.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in source:
            archive.writestr(name, content)
        for name in ("LICENSE", "THIRD_PARTY.md"):
            archive.writestr(name, (ROOT / name).read_bytes())
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    hashes = {path.name: {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
              for path in sorted(args.output.iterdir()) if path.is_file()}
    (args.output / "sha256.json").write_text(json.dumps(hashes, indent=2) + "\n")
    print(json.dumps({"audit_passed": summary["audit_passed"],
                      "all_primary_criteria_passed": summary["all_primary_criteria_passed"],
                      "raw_report_sha256": summary["raw_report_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
