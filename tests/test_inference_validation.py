"""Analytical checks for the benchmark's scalar inference evaluation."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest
from scipy import stats

SPEC = importlib.util.spec_from_file_location(
    "validate_inference", Path(__file__).resolve().parents[1] / "scripts/validate_inference.py"
)
validation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validation)


def test_rubin_pooling_matches_hand_computed_three_estimate_example():
    result = validation.pool_scalar([1, 2, 3], [1, 1, 1])
    assert result["estimate"] == pytest.approx(2)
    assert result["within_variance"] == pytest.approx(1)
    assert result["between_variance"] == pytest.approx(1)
    assert result["total_variance"] == pytest.approx(7 / 3)
    assert result["df"] == pytest.approx(6.125)
    halfwidth = stats.t.ppf(0.975, 6.125) * np.sqrt(7 / 3)
    assert result["interval_lower"] == pytest.approx(2 - halfwidth)
    assert result["interval_upper"] == pytest.approx(2 + halfwidth)


def test_identical_estimates_have_zero_between_variance_and_normal_limit():
    result = validation.pool_scalar([2, 2, 2], [1, 4, 4])
    assert result["between_variance"] == 0
    assert result["total_variance"] == 3
    assert np.isinf(result["df"])
    assert result["interval_width"] == pytest.approx(2 * stats.norm.ppf(0.975) * np.sqrt(3))


@pytest.mark.parametrize(
    "q,u", [([1], [1]), ([1, 2], [1]), ([1, 2], [-1, 1]), ([np.nan, 2], [1, 1]), ([1, 1], [0, 0])]
)
def test_pooling_rejects_invalid_inputs(q, u):
    with pytest.raises(ValueError):
        validation.pool_scalar(q, u)


def test_ols_coefficient_and_variance_match_orthogonal_design():
    x1, x2 = np.array([-1, -1, 1, 1]), np.array([-1, 1, -1, 1])
    error = np.array([1, -1, -1, 1])
    data = np.column_stack([1 + x1 + 0.5 * x2 + error, x1, x2])
    estimate, variance = validation.fit_regression(data)
    assert estimate == pytest.approx(1)
    assert variance == pytest.approx(1)


@pytest.mark.parametrize("scenario", validation.SCENARIOS)
def test_masked_simulation_keeps_response_observed_and_is_repeatable(scenario):
    first, first_seed, metadata = validation.simulate_input(300, scenario, 123, 4)
    second, second_seed, _ = validation.simulate_input(300, scenario, 123, 4)
    np.testing.assert_array_equal(first, second)
    assert first_seed == second_seed
    assert np.isfinite(first[:, 0]).all()
    assert 0 < metadata["actual_covariate_missing_rate"] < 1


def test_coverage_summary_keeps_failures_visible():
    success = {
        "status": "success",
        "covered": True,
        "imputation_fits_returned": 5,
        "imputation_fits_converged": 5,
        "actual_covariate_missing_rate": 0.2,
        "pooled": {"estimate": 1.1, "interval_width": 0.4, "standard_error": 0.1},
    }
    failed = {"status": "failed", "actual_covariate_missing_rate": 0.2}
    result = validation.summarize([success, failed])
    assert result["datasets_failed"] == 1
    assert result["coverage"] == 1
    assert result["coverage_if_every_unsuccessful_dataset_counted_as_miss"] == 0.5
