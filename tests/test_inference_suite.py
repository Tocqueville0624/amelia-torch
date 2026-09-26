"""Prespecified G5 audit must not accept missing/failed evidence or seed drift."""
import copy
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("inference_suite", SCRIPTS / "validate_inference_suite.py")
suite = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(suite)
sys.path.remove(str(SCRIPTS))


def protocol():
    return json.loads(suite.PROTOCOL.read_text())


def records():
    return [{"id": f"mcar-{i:03d}", "scenario": "mcar", "status": "success",
             "quality_passed": True, "observed_preserved": True,
             "all_completed_values_finite": True, "backend_contract_passed": True,
             "imputation_fits_returned": 5, "imputation_fits_converged": 5,
             "imputation_fits_nonconverged": 0, "regression": [{}] * 5,
             "pooled": {"estimate": 1 + .06 * (-1 if i % 2 else 1),
                        "standard_error": .07, "interval_width": .3},
             "covered": i >= 10, "input_sha256": f"input-{i}",
             "r_imputation_seed": i, "imputation_seed": i,
             "actual_covariate_missing_rate": .2} for i in range(200)]


def audit(values, reference=None, **kwargs):
    return suite.audit_scenario(values, reference, records(), protocol(), formal=True, **kwargs)


@pytest.mark.parametrize("seed, expected", [(0, 0), (2**31 - 2, 2**31 - 2),
                                             (2**31 - 1, 0), (2**32 - 1, 1)])
def test_uint32_to_r_seed_mapping_is_explicit_and_bounded(seed, expected):
    assert suite.map_r_seed(seed) == expected


@pytest.mark.parametrize("seed", [-1, 2**32, 3.5, True])
def test_r_mapping_rejects_invalid_or_ambiguous_seeds(seed):
    with pytest.raises(ValueError):
        suite.map_r_seed(seed)


def test_prepare_retains_original_base_generation_and_separates_stress_seeds(tmp_path):
    manifest = suite.prepare_inputs(tmp_path / "inputs", protocol(), smoke=True)
    assert len(manifest) == 8
    used = set()
    for item in manifest:
        actual = np.fromfile(item["input_file"], dtype="<f8").reshape(300, 3)
        if item["scenario"] != "stress_mcar":
            expected, seed, generation = suite.simulate_input(300, item["scenario"], 20260923,
                                                             item["replicate"])
            np.testing.assert_array_equal(actual, expected)
            assert item["imputation_seed"] == seed
            assert item["data_seed"] == generation["data_seed"]
            assert item["mask_seed"] == generation["mask_seed"]
        assert item["r_imputation_seed"] == item["imputation_seed"] % (2**31 - 1)
        assert np.isfinite(actual[:, 0]).all()
        assert item["data_seed"] not in used
        used.add(item["data_seed"])


def test_zero_coverage_discordance_still_has_nonzero_exact_uncertainty():
    result = suite.paired_coverage([True] * 200, [True] * 200)
    assert result["mean"] == 0 and result["mcse"] == 0
    assert result["interval"][0] < 0 < result["interval"][1]
    assert result["interval"][1] == pytest.approx(1 - .025 ** (1 / 200))


def test_paired_coverage_sign_and_mcse_use_within_dataset_differences():
    result = suite.paired_coverage([1, 1, 0, 0], [0, 1, 1, 0])
    assert result["positive_discordances"] == result["negative_discordances"] == 1
    assert result["mcse"] == pytest.approx(np.std([1, 0, -1, 0], ddof=1) / 2)


def test_complete_calibrated_reference_and_matching_route_pass():
    expected = records()
    assert audit(expected)["status"] == "passed"
    result = audit(copy.deepcopy(expected), expected)
    assert result["status"] == "passed"
    assert len(result["checks"]) == 6


@pytest.mark.parametrize("change", ["missing", "duplicate", "failed", "unobserved", "nonfinite",
                                     "nonconverged", "m", "backend"])
def test_gate_refuses_successful_subset_and_forged_success(change):
    values = records()
    if change == "missing":
        values.pop()
    elif change == "duplicate":
        values[-1] = values[0]
    elif change == "failed":
        values[0]["status"] = "failed"
    elif change == "unobserved":
        values[0]["observed_preserved"] = False
    elif change == "nonfinite":
        values[0]["all_completed_values_finite"] = False
    elif change == "nonconverged":
        values[0]["imputation_fits_converged"] = 4
    elif change == "m":
        values[0]["imputation_fits_returned"] = 4
    elif change == "backend":
        values[0]["backend_contract_passed"] = False
    assert audit(values)["status"] == "insufficient_evidence"


def test_failed_process_cannot_pass_even_when_all_saved_records_look_good():
    assert audit(records(), process_ok=False)["status"] == "insufficient_evidence"


def test_smoke_is_never_a_formal_pass_even_if_records_match_formal_design():
    values = records()
    result = suite.audit_scenario(values, values, values, protocol(), formal=False)
    assert result["status"] == "insufficient_evidence"


@pytest.mark.parametrize("field", ["input_sha256", "imputation_seed", "r_imputation_seed"])
def test_paired_comparison_requires_same_inputs_and_recorded_seeds(field):
    expected, actual = records(), records()
    actual[0][field] = "different"
    assert audit(actual, expected)["status"] == "insufficient_evidence"


def test_reference_itself_is_subject_to_absolute_quality_gate():
    values = records()
    for value in values:
        value["pooled"]["estimate"] += .2
    result = audit(values)
    assert result["status"] == "outside_prespecified_bounds"
    assert not result["checks"]["absolute_bias"]


def test_nonsignificant_but_imprecise_bias_is_not_equivalence():
    values = records()
    for i, value in enumerate(values):
        value["pooled"]["estimate"] = 1 + (-1 if i % 2 else 1)
    result = audit(values)
    assert result["absolute"]["bias"]["mean"] == pytest.approx(0)
    assert result["status"] == "outside_prespecified_bounds"


def test_excessive_width_ratio_fails_without_adjusting_gate():
    expected, actual = records(), records()
    for value in actual:
        value["pooled"]["interval_width"] *= 1.1
    result = audit(actual, expected)
    assert not result["checks"]["paired_width_ratio"]
    assert result["status"] == "outside_prespecified_bounds"


def test_pooling_failure_is_retained_as_failure():
    record = {"status": "success", "regression": [{"estimate": 1, "variance": -1}] * 5}
    assert suite.add_pooling(record)["status"] == "pooling_failed"
