"""A process exit code cannot replace checks of recorded scientific output."""

import importlib.util
from pathlib import Path

PATH = Path(__file__).parents[1] / "scripts/summarize_benchmarks.py"
SPEC = importlib.util.spec_from_file_location("benchmark_summary", PATH)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def r_run():
    return {
        "error": None,
        "code": 1,
        "converged_by_tolerance": [True, True],
        "quality_status": "computed",
        "observed_values_unchanged": [True, True],
        "remaining_missing_cells": [0, 0],
        "nonfinite_cells": [0, 0],
        "normalized_heldout_rmse": [0.2, 0.3],
    }


def test_r_nonconvergence_invalidates_normal_return_code():
    run = r_run()
    assert module.check_run(run, "r_serial", 2)[0]
    run["converged_by_tolerance"][0] = False
    assert not module.check_run(run, "r_serial", 2)[0]


def test_r_unscored_or_missing_imputation_invalidates_summary():
    run = r_run()
    run["normalized_heldout_rmse"][0] = None
    assert not module.check_run(run, "r_snow4", 2)[0]
    run = r_run()
    run["normalized_heldout_rmse"] = [0.2]
    assert not module.check_run(run, "r_snow4", 2)[0]
