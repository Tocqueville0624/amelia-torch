"""Quality gates of the bounded G7 experiment; no fitting or GPU use."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

SPEC = importlib.util.spec_from_file_location(
    "product_costs", Path(__file__).parents[1] / "scripts/validate_product_costs.py")
product_costs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(product_costs)


def test_blank_heldout_cells_remain_visible_and_invalidate_full_rmse():
    truth = np.array([[1., 2.], [3., 4.], [5., 6.]])
    data = truth.copy()
    data[0, :] = np.nan
    data[1, 0] = np.nan
    completed = truth.copy()
    completed[0, :] = np.nan
    quality = product_costs.score([completed], data, truth, np.isnan(data))
    assert quality["semantic_output_checks_passed"]
    assert not quality["output_quality_passed"]
    assert quality["imputations"][0]["normalized_rmse_all_heldout"] is None
    assert quality["imputations"][0]["unscored_heldout_cells"] == 2
    assert quality["imputations"][0]["unscored_heldout_in_blank_rows"] == 2
    result = SimpleNamespace(m=1, metadata={"converged_by_tolerance": [True]})
    assert product_costs.status_for(result, quality, 1) == "heldout_incomplete"
    result.metadata["converged_by_tolerance"] = [False]
    assert product_costs.status_for(result, quality, 1) == "nonconverged"


def test_altered_observation_or_missing_replicate_cannot_pass():
    truth = np.array([[1., 2.], [3., 4.], [5., 6.]])
    data = truth.copy()
    data[0, 0] = np.nan
    completed = truth.copy()
    completed[2, 1] += 1
    quality = product_costs.score([completed], data, truth, np.isnan(data))
    assert not quality["semantic_output_checks_passed"]
    result = SimpleNamespace(m=1, metadata={"converged_by_tolerance": [True]})
    assert product_costs.status_for(result, quality, 1) == "invalid_output"
    quality = product_costs.score([truth], data, truth, np.isnan(data))
    assert product_costs.status_for(result, quality, 2) == "invalid_output"


def test_saved_audit_rejects_missing_guards_and_hidden_unscored_values():
    root = Path(__file__).parents[1]
    spec = importlib.util.spec_from_file_location(
        "product_audit", root / "scripts/summarize_product_costs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    folder = root / "docs/validation/2026-09-26-g7"
    plan = json.loads((folder / "plan.json").read_text())
    result = json.loads((folder / "results.json").read_text())
    assert module.audit(plan, result)["audit_passed"]
    result["inputs_unchanged"] = {}
    assert not module.audit(plan, result)["audit_passed"]
    result["inputs_unchanged"] = {name: True for name in plan["inputs"]}
    stress = next(r for r in result["runs"] if r["case"] == "pattern_stress")
    stress["quality"]["imputations"][0]["normalized_rmse_all_heldout"] = .1
    stress["quality"]["output_quality_passed"] = True
    audit = module.audit(plan, result)
    assert not audit["audit_passed"]
    assert any("full RMSE" in error for error in audit["audit_errors"])
    assert any("quality flag" in error for error in audit["audit_errors"])
