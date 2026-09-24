"""Small end-to-end checks for Python -> R -> PyTorch compatibility execution."""

import shutil
import subprocess
import sys

import numpy as np
import pytest

from amelia_torch import amelia_reference, amelia_torch_compat, read_reference_rds
from amelia_torch.reference import AmeliaReferenceError

requires_r = pytest.mark.skipif(shutil.which("Rscript") is None, reason="Hybrid requires Rscript")


def test_importing_both_r_interfaces_does_not_import_torch():
    subprocess.run([
        sys.executable, "-c",
        ("import sys; from amelia_torch import amelia_reference, amelia_torch_compat; "
         "assert 'torch' not in sys.modules"),
    ], check=True)


def test_mps_precision_is_explicit_before_any_runtime_starts():
    with pytest.raises(ValueError, match="float64"):
        amelia_torch_compat(np.zeros((2, 2)), device="mps")


@requires_r
def test_numeric_hybrid_matches_reference_and_preserves_engine_when_appending(tmp_path, monkeypatch):
    rng = np.random.default_rng(192)
    data = rng.normal(size=(120, 4))
    data[:, 2] += 0.3 * data[:, 1]
    data[::7, 0] = np.nan
    data[::11, 2] = np.nan
    # The child R process must use this running interpreter, not a stale user setting.
    monkeypatch.setenv("RETICULATE_PYTHON", "intentionally-nonexistent-python")
    options = {"m": 2, "seed": 192, "p2s": 0, "autopri": 0}
    reference = amelia_reference(data, **options)
    hybrid = amelia_torch_compat(data, **options)
    assert hybrid.engine == "r-amelia-torch-em"
    assert hybrid.metadata["compute_backend"] == "mixed-r-cpu-and-torch"
    assert hybrid.metadata["call_device"] == "cpu"
    assert hybrid.metadata["call_dtype"] == "float64"
    assert hybrid.metadata["torch_used"] is True
    assert hybrid.metadata["gpu_used"] is False
    assert len(hybrid.metadata["hybrid_backend"]["fits"]) == 2
    assert hybrid.metadata["iterations"] == reference.metadata["iterations"]
    for expected, actual in zip(reference.imputations, hybrid.imputations):
        np.testing.assert_allclose(actual, expected, atol=1e-10, rtol=1e-9)
        np.testing.assert_array_equal(actual[np.isfinite(data)], data[np.isfinite(data)])
    extended = hybrid.extend(m=1, seed=193, p2s=0)
    assert extended.m == 3
    assert extended.metadata["call_engine"] == "r-amelia-torch-em"
    assert extended.metadata["call_torch_used"] is True
    assert extended.metadata["call_device"] == "cpu"
    assert extended.metadata["call_dtype"] == "float64"
    assert extended.metadata["provenance"]["historical_m"] == 2
    np.testing.assert_array_equal(extended.imputations[0], hybrid.imputations[0])
    saved = hybrid.save_rds(tmp_path / "hybrid.rds")
    reloaded = read_reference_rds(saved, return_type="numpy")
    assert reloaded.engine == "r-amelia-torch-em"
    assert reloaded.metadata["torch_used"] is True
    assert reloaded.metadata["gpu_used"] is False
    np.testing.assert_array_equal(reloaded.imputations[0], hybrid.imputations[0])
    cpu_append = amelia_reference(input_rds=saved, m=1, seed=194, p2s=0)
    assert cpu_append.metadata["torch_used"] is True
    assert cpu_append.metadata["call_torch_used"] is False


@requires_r
def test_no_bootstrap_replicates_preserve_r_random_stream():
    rng = np.random.default_rng(192)
    data = rng.normal(size=(120, 4))
    data[:, 2] += 0.3 * data[:, 1]
    data[::7, 0] = np.nan
    data[::11, 2] = np.nan
    options = {"m": 2, "seed": 192, "p2s": 0, "autopri": 0, "boot.type": "none"}
    reference = amelia_reference(data, **options)
    hybrid = amelia_torch_compat(data, **options)
    # R's original C++ draws advance C-level RNG state without updating the R
    # .Random.seed vector. Entering reticulate between replicates must not reload
    # that stale vector and repeat the previous imputation's Gaussian draws.
    assert not np.allclose(hybrid.imputations[0], hybrid.imputations[1])
    for expected, actual in zip(reference.imputations, hybrid.imputations):
        np.testing.assert_allclose(actual, expected, atol=1e-10, rtol=1e-9)


@requires_r
def test_typed_transforms_priors_and_bounds_match_original_pipeline():
    pd = pytest.importorskip("pandas")
    rng = np.random.default_rng(947)
    data = pd.DataFrame({
        "id": [f"p-{i}" for i in range(150)],
        "income": np.exp(rng.normal(2, 0.3, 150)),
        "score": rng.normal(0.5, 0.1, 150),
        "group": pd.Categorical(rng.choice(["a", "b", "c"], 150)),
        "rank": pd.Categorical(rng.choice(["low", "high"], 150),
                               categories=["low", "high"], ordered=True),
        "flag": np.tile([True, False], 75),
    })
    data.loc[::7, "income"] = np.nan
    data.loc[::9, "score"] = np.nan
    data.loc[::11, "group"] = np.nan
    data.loc[::13, "rank"] = np.nan
    options = dict(m=1, seed=947, p2s=0, autopri=0, idvars=["id"],
                   logs=["income"], noms=["group"], ords=["rank"],
                   priors=[[1, 3, 0.5, 0.05], [10, 3, 0.5, 0.05]],
                   bounds=[[3, 0, 1]], **{"boot.type": "none"})
    original = amelia_reference(data, **options)
    hybrid = amelia_torch_compat(data, **options)
    assert hybrid.metadata["iterations"] == original.metadata["iterations"]
    for expected, actual in zip(original.imputations, hybrid.imputations):
        pd.testing.assert_frame_equal(actual, expected, check_exact=False, atol=1e-10, rtol=1e-9)


@requires_r
def test_hybrid_serial_scheduling_constraint_is_explicit():
    with pytest.raises(AmeliaReferenceError, match="serial") as failure:
        amelia_torch_compat(np.array([[1, 2], [3, np.nan], [2, 4]]),
                            m=1, p2s=0, parallel="snow", ncpus=2)
    assert failure.value.details["engine"] == "r-amelia-torch-em"


@requires_r
def test_self_contained_molist_rds_uses_the_original_multiple_overimputation_flow(tmp_path):
    from amelia_torch.reference import _runtime_environment

    source = tmp_path / "create-molist.R"
    target = tmp_path / "prepared.rds"
    source.write_text(
        'args <- commandArgs(trailingOnly=TRUE)\n'
        'set.seed(83)\n'
        'data <- data.frame(a=rnorm(100), b=rnorm(100), c=rnorm(100))\n'
        'data$c[seq(2,100,9)] <- NA_real_\n'
        'prepared <- Amelia::moPrep(data, b ~ b, error.sd=.1)\n'
        'prepared$data <- data\n'
        'saveRDS(prepared, args[[1]])\n'
    )
    executable, environment = _runtime_environment(None, None)
    subprocess.run([executable, "--vanilla", str(source), str(target)],
                   env=environment, check=True, capture_output=True)
    original = amelia_reference(input_rds=target, m=1, seed=84, p2s=0, return_type="numpy")
    hybrid = amelia_torch_compat(input_rds=target, m=1, seed=84, p2s=0, return_type="numpy")
    np.testing.assert_allclose(hybrid.imputations[0], original.imputations[0], atol=1e-9, rtol=1e-8)
