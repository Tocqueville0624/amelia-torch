"""Fixtures are produced by the unmodified, pinned R Amelia implementation."""

import json
from pathlib import Path

import numpy as np
import pytest

from amelia_torch.em import em_fit, initial_theta
from amelia_torch.imputation import impute_prepared

FIXTURES = Path(__file__).parent / "fixtures" / "reference_amelia"


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


@pytest.mark.parametrize("name", ["no_prior", "empirical_prior", "cell_prior"])
def test_em_matches_r_reference_step_and_convergence(name):
    case = fixture(name)
    kwargs = {
        "thetaold": case["initial_theta"],
        "empri": case["empri"],
        "priors": case["priors"],
        "autopri": case["autopri"],
        "tolerance": case["tolerance"],
    }
    with pytest.warns(RuntimeWarning, match="before convergence"):
        step = em_fit(case["x"], emburn=(0, 1), **kwargs)
    np.testing.assert_allclose(
        step["theta"], case["expected_one_step_theta"], atol=1e-12, rtol=1e-11
    )
    np.testing.assert_array_equal(step["iter_hist"], case["expected_one_step_history"])
    fit = em_fit(case["x"], emburn=case["emburn"], **kwargs)
    np.testing.assert_allclose(fit["theta"], case["expected_theta"], atol=1e-10, rtol=1e-9)
    np.testing.assert_array_equal(fit["iter_hist"], case["expected_history"])
    assert fit["diagnostics"]["converged"]


@pytest.mark.parametrize("name", ["no_prior", "empirical_prior", "cell_prior"])
def test_conditional_draws_replay_r_with_explicit_random_input(name):
    case = fixture(name)
    result = impute_prepared(
        case["x"],
        case["expected_theta"],
        priors=case["priors"],
        standard_normals=case["standard_normals"],
    )
    np.testing.assert_allclose(result, case["expected_imputation"], atol=1e-11, rtol=1e-10)
    original = np.asarray(case["x"], dtype=float)
    observed = ~np.isnan(original)
    np.testing.assert_array_equal(result[observed], original[observed])


def test_complete_bootstrap_sample_uses_sample_covariance_and_ignores_empri():
    case = fixture("complete_internal")
    result = em_fit(case["x"], empri=case["empri"])
    np.testing.assert_allclose(result["theta"], case["expected_theta"], atol=1e-12, rtol=1e-11)
    assert result["diagnostics"]["iterations"] == 0


def test_startvals_contract():
    case = fixture("preprocessing")
    for start in (0, 1):
        result = initial_theta(np.asarray(case["stacked_x"], dtype=float), start)
        np.testing.assert_allclose(
            result, case[f"expected_startvals_{start}"], atol=1e-12, rtol=1e-11
        )


@pytest.mark.parametrize("name", ["no_complete_rows", "minimum_iterations", "maximum_iterations"])
def test_initialization_and_iteration_limits_match_r(name):
    case = fixture(name)
    kwargs = {key: case[key] for key in ("empri", "priors", "autopri", "tolerance", "emburn")}
    kwargs["thetaold"] = case["initial_theta"]
    if name == "maximum_iterations":
        with pytest.warns(RuntimeWarning, match="before convergence"):
            result = em_fit(case["x"], **kwargs)
        assert not result["diagnostics"]["converged"]
    else:
        result = em_fit(case["x"], **kwargs)
    np.testing.assert_allclose(result["theta"], case["expected_theta"], atol=1e-10, rtol=1e-9)
    np.testing.assert_array_equal(result["iter_hist"], case["expected_history"])


def test_reference_inputs_not_modified():
    case = fixture("no_prior")
    x = np.asarray(case["x"], dtype=float)
    theta = np.asarray(case["initial_theta"], dtype=float)
    before_x, before_theta = x.copy(), theta.copy()
    em_fit(x, thetaold=theta)
    np.testing.assert_array_equal(x, before_x)
    np.testing.assert_array_equal(theta, before_theta)
