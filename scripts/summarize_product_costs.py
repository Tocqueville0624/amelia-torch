"""Audit the saved G7 plan/result grid without running an imputation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path


def audit(plan, result):
    errors = []

    def check(value, message):
        if not value:
            errors.append(message)

    check(result["plan"] == plan, "Embedded plan differs")
    check(len(result["runs"]) == len(plan["jobs"]), "Incomplete request grid")
    check(result.get("source_unchanged") is True, "Source guard failed")
    check(result.get("inputs_unchanged") == {name: True for name in plan["inputs"]},
          "Input guard failed or incomplete")
    m = plan["settings"]["m"]
    rows = []
    for index, (job, run) in enumerate(zip(plan["jobs"], result["runs"], strict=False)):
        prefix = f"run {index}: "
        check(all(run[k] == v for k, v in job.items()), prefix + "job mismatch")
        check(math.isfinite(run["wall_seconds"]) and run["wall_seconds"] > 0,
              prefix + "invalid duration")
        check(run["source_unchanged"] is True, prefix + "source changed")
        check(run["peak_ram_bytes"] is None and run["peak_gpu_memory_bytes"] is None,
              prefix + "unmeasured memory must be null")
        metadata = run.get("metadata", {})
        expected_unscored = plan["inputs"][job["case"]]["heldout_cells_in_wholly_missing_rows"]
        expected_status = "heldout_incomplete" if expected_unscored else "ok"
        check(run["status"] == expected_status, prefix + "unexpected outcome")
        check(metadata.get("code") == 1 and metadata.get("m") == m, prefix + "bad result code/count")
        check(metadata.get("reference_version") == "1.8.3", prefix + "reference version changed")
        check(metadata.get("call_rng_kind", [None])[0] == plan["settings"]["r_rng_kind"],
              prefix + "R RNG differs")
        convergence = metadata.get("converged_by_tolerance", [])
        check(len(convergence) == m and all(v is True for v in convergence), prefix + "nonconvergence")
        quality = run.get("quality", {})
        check(quality.get("semantic_output_checks_passed") is True, prefix + "semantic failure")
        check(quality.get("complete_heldout_scoring") == (expected_unscored == 0),
              prefix + "full scoring flag misleading")
        check(quality.get("output_quality_passed") == (expected_unscored == 0),
              prefix + "output quality flag misleading")
        imputations = quality.get("imputations", [])
        check(len(imputations) == m, prefix + "missing imputation scores")
        for q in imputations:
            check(q["observed_preserved"] and q["blank_rows_preserved"] and
                  q["unexpected_nonfinite_cells"] == 0, prefix + "invalid output values")
            check(q["heldout_cells"] == plan["inputs"][job["case"]]["heldout_cells"] and
                  q["unscored_heldout_cells"] == expected_unscored and
                  q["unscored_heldout_in_blank_rows"] == expected_unscored,
                  prefix + "heldout count mismatch")
            rmse = q["normalized_rmse_all_heldout"]
            check(rmse is None if expected_unscored else
                  isinstance(rmse, (int, float)) and math.isfinite(rmse),
                  prefix + "invalid/full RMSE despite omitted heldout")
        if job["method"] != "reference":
            device = "mps" if job["method"] == "hybrid_mps32" else "cpu"
            dtype = "float32" if device == "mps" else "float64"
            fits = metadata.get("hybrid_backend", {}).get("fits", [])
            check(len(fits) == m and all(f["device"] == device and f["dtype"] == dtype and
                                         f["converged"] for f in fits), prefix + "backend mismatch")
        rows.append({"case": job["case"], "method": job["method"], "phase": job["phase"],
                     "repetition": job["repetition"], "seconds": run["wall_seconds"],
                     "status": run["status"], "iterations": metadata.get("iterations"),
                     "unscored_per_imputation": expected_unscored})
    front = {}
    for method in ("reference", "hybrid_cpu64"):
        runs = [r for r in result["runs"] if r["case"] == "front_door" and r["method"] == method]
        check(len(runs) == 3, method + ": first and two later calls required")
        if len(runs) == 3:
            front[method] = {
                "first_call_seconds": runs[0]["wall_seconds"],
                "subsequent_call_seconds": [r["wall_seconds"] for r in runs[1:]],
                "subsequent_median_seconds": statistics.median(r["wall_seconds"] for r in runs[1:]),
                "same_returned_rds_digest_across_three_calls": len({r["returned_rds_sha256"] for r in runs}) == 1,
            }
    check(result.get("all_requests_returned_results") is True, "Not every call returned results")
    check(result.get("all_benchmark_quality_passed") is False,
          "Expected incomplete heldout stress case was labeled a quality success")
    return {"schema_version": 1, "audit_passed": not errors, "audit_errors": errors,
            "scope": "Audit of nine specified calls and honestly retained stress scoring failures",
            "all_runs_valid_for_speed_comparison": False,
            "front_door": front, "runs": rows,
            "interpretation": "First/later calls each include a fresh R process; no subtraction from old R-memory timings. Independent-MCAR results with unscored heldout cells are diagnostic outcomes, not successful benchmark scores."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("result", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    result = json.loads(args.result.read_text())
    summary = audit(plan, result)
    summary["plan_sha256"] = hashlib.sha256(args.plan.read_bytes()).hexdigest()
    summary["result_sha256"] = hashlib.sha256(args.result.read_bytes()).hexdigest()
    if result["plan_sha256"] != summary["plan_sha256"]:
        summary["audit_passed"] = False
        summary["audit_errors"].append("Saved plan file digest mismatch")
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"audit_passed": summary["audit_passed"], "errors": summary["audit_errors"]}))
    return 0 if summary["audit_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
