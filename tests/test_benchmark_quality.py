"""Failed held-out cells and altered observations cannot become speed successes."""

import importlib.util
from pathlib import Path

import numpy as np

PATH = Path(__file__).parents[1] / "scripts/benchmark.py"
SPEC = importlib.util.spec_from_file_location("benchmark", PATH)
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


def inputs():
    truth = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    data = truth.copy()
    data[:2, 0] = np.nan
    return data, truth, np.isnan(data)


def test_one_unscored_heldout_cell_invalidates_entire_score():
    data, truth, mask = inputs()
    output = truth.copy()
    output[0, 0] = np.nan
    result = benchmark.metrics([output], data, truth, mask)
    assert result["normalized_rmse_per_imputation"] == [None]
    assert result["unscored_heldout_cells_per_imputation"] == [1]
    assert not result["quality_passed"]


def test_changed_observed_value_invalidates_otherwise_good_imputation():
    data, truth, mask = inputs()
    output = truth.copy()
    output[2, 1] += 1
    result = benchmark.metrics([output], data, truth, mask)
    assert result["normalized_rmse_per_imputation"] == [0.0]
    assert not result["quality_passed"]


def test_natural_wholly_missing_rows_must_be_preserved_not_scored():
    data, truth, mask = inputs()
    data = np.vstack([data, [np.nan, np.nan]])
    truth = np.vstack([truth, [np.nan, np.nan]])
    mask = np.vstack([mask, [False, False]])
    result = benchmark.metrics([truth.copy()], data, truth, mask)
    assert result["quality_passed"]
    assert result["remaining_missing_cells"] == [2]
    output = truth.copy()
    output[-1] = 0
    assert not benchmark.metrics([output], data, truth, mask)["quality_passed"]
