"""Independent G5 reconstruction must detect corrupted or misleading summaries."""
import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("inference_summary", SCRIPTS / "summarize_inference_suite.py")
summary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(summary)
from validate_inference import pool_scalar

sys.path.remove(str(SCRIPTS))
GATES = json.loads((SCRIPTS.parent / "docs/validation/g5-prespecified/protocol.json").read_text())["gates"]


def make_rows():
    rows = []
    for i in range(200):
        center = 1 + (.2 if i < 10 else (.05 if i % 2 else -.05))
        q = [center - .01, center - .005, center, center + .005, center + .01]
        u = [.004] * 5
        pooled = pool_scalar(q, u)
        rows.append({"regression": [{"estimate": a, "variance": b} for a, b in zip(q, u)],
                     "pooled": pooled, "covered": pooled["interval_lower"] <= 1 <= pooled["interval_upper"]})
    return rows


def test_raw_regression_reconstruction_matches_valid_producer_pooling():
    rows = make_rows()
    result = summary.reconstruct_scenario(rows, rows, GATES)
    assert result["covered"] == 190
    assert result["coverage"]["mean"] == .95
    assert result["paired_vs_reference"]["estimate_difference"]["mean"] == 0
    assert result["paired_vs_reference"]["geometric_se_ratio"]["mean"] == 1


@pytest.mark.parametrize("field", ["estimate", "standard_error", "interval_width", "total_variance"])
def test_stored_pooling_cannot_override_raw_regression_evidence(field):
    rows = make_rows()
    rows[0]["pooled"][field] += .1
    with pytest.raises(ValueError, match="Saved pooling disagrees"):
        summary.reconstruct_scenario(rows, None, GATES)


def test_saved_coverage_must_match_reconstructed_interval():
    rows = make_rows()
    rows[0]["covered"] = not rows[0]["covered"]
    with pytest.raises(ValueError, match="Saved coverage disagrees"):
        summary.reconstruct_scenario(rows, None, GATES)


def test_nonfinite_raw_variance_rejected():
    rows = make_rows()
    rows[0]["regression"][0]["variance"] = float("nan")
    with pytest.raises(ValueError, match="Nonfinite"):
        summary.reconstruct_scenario(rows, None, GATES)


def test_reconstruction_detects_width_ratio_exceeding_frozen_bound():
    reference = make_rows()
    actual = copy.deepcopy(reference)
    for row in actual:
        q = [item["estimate"] for item in row["regression"]]
        u = [item["variance"] * 1.5 for item in row["regression"]]
        row["regression"] = [{"estimate": a, "variance": b} for a, b in zip(q, u)]
        row["pooled"] = pool_scalar(q, u)
        row["covered"] = row["pooled"]["interval_lower"] <= 1 <= row["pooled"]["interval_upper"]
    result = summary.reconstruct_scenario(actual, reference, GATES)
    assert not result["checks"]["paired_width_ratio"]
    assert not result["checks"]["paired_se_ratio"]
    assert result["status"] == "outside_prespecified_bounds"


def test_real_smoke_metadata_is_checked_per_fit_and_history():
    report = json.loads((SCRIPTS.parent / "docs/validation/g5-prespecified/smoke-cpu-report.json").read_text())
    for route, result in report["route_results"].items():
        row = copy.deepcopy(result["records"][0])
        assert summary.fit_evidence_valid(row, route)
        if route == "r-reference":
            row["iter_histories"][0][-1][0] = 1
        else:
            key = "fits" if route.startswith("hybrid") else "replicates"
            row["backend"][key][0]["converged"] = False
        assert not summary.fit_evidence_valid(row, route)
