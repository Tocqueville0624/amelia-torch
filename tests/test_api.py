import numpy as np
import pytest

from amelia_torch import AmeliaInputError, amelia


def example():
    x = np.random.default_rng(72).normal(size=(120, 4))
    x[:, 2] += 0.7 * x[:, 0]
    x[::3, 0] = np.nan
    x[::7, 3] = np.nan
    return x


def test_multiple_imputation_preserves_observed_and_seed_without_mutating_input():
    x = example()
    before = x.copy()
    one = amelia(x, m=3, seed=41)
    two = amelia(x, m=3, seed=41)
    for left, right in zip(one["imputations"], two["imputations"]):
        assert np.isfinite(left).all()
        np.testing.assert_array_equal(left[~np.isnan(x)], x[~np.isnan(x)])
        np.testing.assert_array_equal(left, right)
    assert not np.array_equal(one["imputations"][0], one["imputations"][1])
    np.testing.assert_array_equal(x, before)


def test_public_complete_input_rejected_but_wholly_missing_rows_retained():
    with pytest.raises(AmeliaInputError) as caught:
        amelia(np.ones((20, 3)))
    assert caught.value.code == 39
    x = np.vstack([example(), np.full(4, np.nan)])
    result = amelia(x, m=1, seed=1)["imputations"][0]
    assert np.isnan(result[-1]).all()
    assert np.isfinite(result[:-1]).all()


def test_unsupported_options_are_not_ignored():
    with pytest.raises(NotImplementedError, match="noms"):
        amelia(example(), noms=[0])


def test_scale_equivariance_and_column_order_restoration():
    x = example()
    scale = np.array([2.0, 5.0, 10.0, 0.5])
    shift = np.array([10.0, -4.0, 3.0, 2.0])
    a = amelia(x, m=1, seed=18)["imputations"][0]
    b = amelia(x * scale + shift, m=1, seed=18)["imputations"][0]
    np.testing.assert_allclose(b, a * scale + shift, atol=1e-10, rtol=1e-9)
