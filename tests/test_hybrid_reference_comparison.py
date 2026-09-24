"""Paired summary comparisons must not silently compare different R experiments."""

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


load("summarize_benchmarks")
load("summarize_hybrid")
compare = load("compare_hybrid_reference")


def reports():
    config = {
        "n": 100000,
        "p": 2,
        "m": 2,
        "warmups": 1,
        "ncpus": 1,
        "parallel": "no",
        "empri": None,
        "autopri": 0.05,
        "tolerance": 1e-4,
        "emburn": [0, 300],
        "startvals": 0,
        "boot.type": "ordinary",
        "missing_cells": 40000,
        "heldout_cells": 40000,
        "completely_missing_input_rows": 0,
        "seeds": [10, 11],
        "warmup_seeds": [20],
    }
    reference = {
        "version": "1.8.3",
        "config": config,
        "environment": {
            "R": "4.5.3",
            "RNGkind": ["L'Ecuyer-CMRG", "Inversion", "Rejection"],
            "platform": "same-platform",
            "os": {"sysname": "Darwin"},
            "BLAS": "same",
            "LAPACK": None,
            "thread_environment": {"OMP_NUM_THREADS": "4"},
            "packages": {"Amelia": "1.8.3", "Rcpp": "1.1.1", "RcppArmadillo": "15.2.4.1"},
        },
        "runs": [],
    }
    for phase, seed in (("warmup", 20), ("measured", 10), ("measured", 11)):
        reference["runs"].append(
            {
                "phase": phase,
                "seed": seed,
                "code": 1,
                "error": None,
                "converged_by_tolerance": [True, True],
                "quality_status": "computed",
                "observed_values_unchanged": [True, True],
                "remaining_missing_cells": [0, 0],
                "nonfinite_cells": [0, 0],
                "iterations": [4, 5],
                "normalized_heldout_rmse": [0.1, 0.2],
                "pooled_column_means": [0.0, 1.0],
                "mean_covariance": [[1, 0.2], [0.2, 2]],
                "pooled_mean_within_variance": [0.01, 0.02],
                "pooled_mean_between_variance": [0.003, 0.004],
                "pooled_mean_variance": [0.0145, 0.026],
            }
        )
    candidate = copy.deepcopy(reference)
    candidate["reference_version"] = "1.8.3"
    return reference, candidate


def test_identical_summaries_include_warmups_without_claiming_full_output_equality():
    a, b = reports()
    result = compare.compare_reports(a, b)
    assert result["comparison_contract_verified"]
    assert [(item["phase"], item["seed"]) for item in result["paired_runs"]] == [
        ("warmup", 20),
        ("measured", 10),
        ("measured", 11),
    ]
    assert all(value["max_absolute"] == 0 for value in result["maximum_discrepancies"].values())
    assert "equivalent" not in result and "all_passed" not in result


def test_pairs_by_seed_and_phase_not_array_position_and_retains_discrepancies():
    a, b = reports()
    b["runs"][2]["iterations"][1] = 9
    b["runs"][2]["pooled_column_means"][1] += 0.25
    b["runs"] = list(reversed(b["runs"]))
    result = compare.compare_reports(a, b)
    assert result["comparison_contract_verified"]
    assert result["maximum_discrepancies"]["iterations"]["max_absolute"] == 4
    assert result["maximum_discrepancies"]["pooled_column_means"]["max_absolute"] == 0.25
    assert result["maximum_discrepancies"]["iterations"]["max_absolute_at"] == {
        "phase": "measured",
        "seed": 11,
    }


@pytest.mark.parametrize(
    "change", ["rng", "tolerance", "version", "missing", "duplicate", "seed", "parallel"]
)
def test_different_experiments_do_not_receive_paired_discrepancies(change):
    a, b = reports()
    if change == "rng":
        b["environment"]["RNGkind"][0] = "Mersenne-Twister"
    elif change == "tolerance":
        b["config"]["tolerance"] = 0.001
    elif change == "version":
        b["environment"]["packages"]["Amelia"] = "1.8.2"
    elif change == "missing":
        b["runs"].pop()
    elif change == "duplicate":
        b["runs"].append(copy.deepcopy(b["runs"][0]))
    elif change == "seed":
        b["runs"][0]["seed"] = 200
    else:
        b["config"]["parallel"] = "snow"
    result = compare.compare_reports(a, b)
    assert not result["comparison_contract_verified"]
    assert result["paired_runs"] == []


@pytest.mark.parametrize("change", ["nan", "infinity", "shape", "failed_fit"])
def test_nonfinite_missing_or_failed_summary_cannot_pass_contract(change):
    a, b = reports()
    if change == "nan":
        b["runs"][1]["mean_covariance"][0][0] = float("nan")
    elif change == "infinity":
        b["runs"][1]["pooled_column_means"][0] = float("inf")
    elif change == "shape":
        b["runs"][1]["iterations"] = [4]
    else:
        b["runs"][1]["converged_by_tolerance"][0] = False
    result = compare.compare_reports(a, b)
    assert not result["comparison_contract_verified"]
    assert result["maximum_discrepancies"] == {}


def test_relative_error_excludes_zero_denominators_but_retains_absolute_error():
    result = compare.discrepancy([0.0, 1.0], [2.0, 1.1], (2,))
    assert result["max_absolute"] == 2
    assert result["max_relative_on_nonzero_reference"] == pytest.approx(0.1)
    assert result["near_zero_reference_elements"] == 1
    assert result["max_absolute_on_near_zero_reference"] == 2


def test_input_contract_requires_matching_prepared_hash_and_recorded_csv_reuse():
    reference = {"input_sha256": "a" * 64}
    hybrid = {
        "input_policy": compare.REUSED_INPUT_POLICY,
        "inputs": {
            "covertype": {
                "npz_sha256": "a" * 64,
                "csv": {field: {"sha256": "b" * 64} for field in ("input", "truth", "mask")},
            }
        },
    }
    assert compare.input_contract(reference, hybrid, "covertype") == []
    hybrid["inputs"]["covertype"]["npz_sha256"] = "c" * 64
    assert "prepared_NPZ_fingerprint_mismatch" in compare.input_contract(
        reference, hybrid, "covertype"
    )
    hybrid["input_policy"] = "newly generated"
    assert "original_CSV_reuse_not_recorded" in compare.input_contract(
        reference, hybrid, "covertype"
    )


def test_unfinished_suite_is_never_compared_or_exported(tmp_path):
    (tmp_path / "suite.json").write_text(json.dumps({"execution": []}))
    with pytest.raises(ValueError, match="still running"):
        compare.load_suite(tmp_path)
    assert list(tmp_path.iterdir()) == [tmp_path / "suite.json"]
