"""Cross-language oracle checks for the supported public continuous workflow."""

import json
from pathlib import Path

import numpy as np

from amelia_torch import amelia
from amelia_torch.api import _stack

FIXTURE = Path(__file__).parent / "fixtures/reference_amelia/public_continuous.json"


def test_public_continuous_pipeline_matches_official_r_parameters_and_history():
    reference = json.loads(FIXTURE.read_text())
    raw = np.asarray(reference["raw_x"], dtype=np.float64)
    result = amelia(
        raw,
        m=reference["m"],
        seed=71,  # Only parameters/history are compared; R's seed is irrelevant.
        boot_type=reference["boot_type"],
        startvals=np.asarray(reference["initial_theta"], dtype=np.float64),
        tolerance=reference["tolerance"],
        empri=reference["empri"],
        autopri=reference["autopri"],
        emburn=reference["emburn"],
        device="cpu",
        dtype="float64",
    )
    np.testing.assert_allclose(
        result["theta"][:, :, 0], reference["expected_theta"], atol=1e-10, rtol=1e-9
    )
    np.testing.assert_array_equal(result["iterHist"][0], reference["expected_history"])
    diagnostics = result["diagnostics"]
    assert diagnostics["converged"]
    assert diagnostics["replicates"][0]["iterations"] == reference["expected_iterations"]
    np.testing.assert_allclose(
        diagnostics["scale_mean_original_order"], reference["expected_scale_mean"],
        atol=1e-14, rtol=1e-13,
    )
    np.testing.assert_allclose(
        diagnostics["scale_sd_original_order"], reference["expected_scale_sd"],
        atol=1e-14, rtol=1e-13,
    )
    np.testing.assert_array_equal(
        diagnostics["column_order_zero_based"],
        np.asarray(reference["expected_p_order"], dtype=int) - 1,
    )
    expected_blank_rows = np.atleast_1d(reference["expected_blank_rows"]).astype(int) - 1
    assert diagnostics["wholly_missing_rows_retained"] == len(expected_blank_rows)
    assert np.isnan(result["imputations"][0][expected_blank_rows]).all()
    observed = np.isfinite(raw)
    np.testing.assert_array_equal(result["imputations"][0][observed], raw[observed])


def test_prepared_values_and_row_column_order_match_public_r_pipeline():
    reference = json.loads(FIXTURE.read_text())
    raw = np.asarray(reference["raw_x"], dtype=np.float64)
    retained = raw[~np.isnan(raw).all(axis=1)]
    standardized = (
        retained - np.asarray(reference["expected_scale_mean"])
    ) / np.asarray(reference["expected_scale_sd"])
    prepared, rows, columns = _stack(standardized, reorder_columns=True)
    np.testing.assert_array_equal(rows, np.asarray(reference["expected_n_order"]) - 1)
    np.testing.assert_array_equal(columns, np.asarray(reference["expected_p_order"]) - 1)
    np.testing.assert_allclose(
        prepared, np.asarray(reference["expected_prepared_x"], dtype=np.float64),
        atol=1e-14, rtol=1e-13,
    )
