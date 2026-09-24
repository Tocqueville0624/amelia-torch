"""Overflow must fail explicitly rather than return apparently converged results."""

import numpy as np
import pytest

from amelia_torch import amelia, em_fit
from amelia_torch.em import NumericalError
from amelia_torch.imputation import impute_prepared


def test_complete_sample_rejects_input_overflow_on_dtype_conversion():
    x = np.array([[1e40, 2.0], [2e40, 3.0], [3e40, 4.0]])
    with pytest.raises(NumericalError, match="dtype range"):
        em_fit(x, dtype="float32")


def test_complete_sample_rejects_covariance_overflow_after_computation():
    x = np.array([[1e20, 2e20], [2e20, 4e20], [3e20, 1e20]])
    with pytest.raises(NumericalError, match="non-finite"):
        em_fit(x, dtype="float32")


def test_draw_rejects_parameter_overflow_on_dtype_conversion():
    theta = np.diag([-1.0, 1e80, 1.0])
    with pytest.raises(NumericalError, match="dtype range"):
        impute_prepared([[np.nan, 0.0]], theta, seed=1, dtype="float32")


def test_draw_rejects_nonfinite_result_even_with_finite_parameters():
    theta = np.diag([-1.0, 1e20, 1.0])
    with pytest.raises(NumericalError, match="non-finite"):
        impute_prepared(
            [[np.nan, 0.0]], theta, standard_normals=[[1e38, 0.0]], dtype="float32"
        )


def test_public_standardization_overflow_is_not_treated_as_missingness():
    x = np.random.default_rng(5).normal(size=(30, 2)) * 1e200
    x[0, 0] = np.nan
    with np.errstate(over="ignore"), pytest.raises(NumericalError, match="standardization"):
        amelia(x, m=1)


def test_iteration_limits_follow_original_numeric_counter_comparisons():
    x = np.random.default_rng(23).normal(size=(40, 3))
    x[::3, 1] = np.nan
    # C++ counter 0,1 < 1.5; truncating to one iteration would change Amelia.
    with pytest.warns(RuntimeWarning, match="before convergence"):
        fractional = em_fit(x, tolerance=1e-20, emburn=(0, 1.5))
    assert fractional["diagnostics"]["iterations"] == 2
    # A cap below one is unlimited, including negative caps in the original.
    minimum = em_fit(x, tolerance=1e3, emburn=(2.2, -1))
    assert minimum["diagnostics"]["iterations"] == 3
    # Upstream's maximum takes precedence over a larger requested minimum.
    capped = em_fit(x, tolerance=1e3, emburn=(5, 2))
    assert capped["diagnostics"]["iterations"] == 2
