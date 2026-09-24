import pytest
import torch

from amelia_torch.backends import resolve_backend
from amelia_torch.diagnostics import probe_backend


def test_reference_backend_preserves_double_precision():
    device, dtype = resolve_backend()
    assert device.type == "cpu"
    assert dtype is torch.float64
    assert all(op["ok"] for op in probe_backend("cpu", "float64")["operations"].values())


def test_mps_double_precision_is_never_silently_downcast():
    with pytest.raises(ValueError, match="does not support float64"):
        resolve_backend("mps", "float64")


@pytest.mark.parametrize("device", ["cuda", "mps"])
def test_unavailable_accelerator_does_not_silently_use_cpu(monkeypatch, device):
    backend = torch.cuda if device == "cuda" else torch.backends.mps
    monkeypatch.setattr(backend, "is_available", lambda: False)
    with pytest.raises(RuntimeError, match="not available"):
        resolve_backend(device, "float32")
