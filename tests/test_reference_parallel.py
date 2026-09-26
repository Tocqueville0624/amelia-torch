"""Small actual PSOCK checks of the Python-to-official-R product path."""

import shutil
import subprocess

import numpy as np
import pytest

from amelia_torch.reference import (
    AmeliaReferenceError,
    _runtime_environment,
    amelia_reference,
)

pytestmark = pytest.mark.skipif(shutil.which("Rscript") is None, reason="Optional R runtime")


def data():
    values = np.random.default_rng(9126).normal(size=(96, 3))
    values[:, 2] += 0.3 * values[:, 0]
    values[::7, 0] = np.nan
    values[::11, 1] = np.nan
    return values


def test_python_reference_snow_repeats_and_workers_inherit_selected_library(monkeypatch):
    executable, environment = _runtime_environment(None, None)
    library = subprocess.run(
        [executable, "--vanilla", "-e", 'cat(dirname(find.package("Amelia")))'],
        env=environment, capture_output=True, text=True, check=True, timeout=30,
    ).stdout.strip()
    options = {"m": 3, "seed": 9127, "r_rng_kind": "L'Ecuyer-CMRG", "p2s": 0,
               "parallel": "snow", "ncpus": 2, "tolerance": 1e-6, "autopri": 0,
               "timeout": 45}
    values = data()
    explicit = amelia_reference(values, r_library=library, **options)
    default = amelia_reference(values, **options)
    # An empty explicit list disables source-checkout convenience. Resolve
    # through R's ordinary R_LIBS_USER environment mechanism, inherited by its
    # workers, without relocating or reinstalling dependencies for this test.
    monkeypatch.setenv("R_LIBS_USER", library)
    inherited = amelia_reference(values, r_library=[], **options)
    for result in (explicit, default, inherited):
        assert result.metadata["reference_version"] == "1.8.3"
        assert result.metadata["call_rng_kind"][0] == "L'Ecuyer-CMRG"
        assert all(result.metadata["converged_by_tolerance"])
        assert result.metadata["call_torch_used"] is False
        assert result.metadata["call_gpu_used"] is False
        for draw in result.imputations:
            assert np.isfinite(draw).all()
            np.testing.assert_array_equal(draw[~np.isnan(values)], values[~np.isnan(values)])
    for left, right in zip(explicit.imputations, default.imputations, strict=True):
        np.testing.assert_array_equal(left, right)
    for left, right in zip(explicit.imputations, inherited.imputations, strict=True):
        np.testing.assert_array_equal(left, right)
    assert not np.array_equal(explicit.imputations[0], explicit.imputations[1])


def test_python_reference_propagates_an_actual_snow_worker_error():
    # Deliberately bypass input checking with the documented incheck option.
    # The invalid length-two choice then raises an R condition inside worker
    # bootx, not in the parent preprocessor or a mocked subprocess.
    with pytest.raises(AmeliaReferenceError, match="nodes produced errors") as caught:
        amelia_reference(data(), m=2, seed=9128, r_rng_kind="L'Ecuyer-CMRG",
                         p2s=0, parallel="snow", ncpus=2, incheck=False,
                         autopri=0, timeout=45, **{"boot.type": ["ordinary", "none"]})
    assert caught.value.partial_rds is None
    assert caught.value.code is None
