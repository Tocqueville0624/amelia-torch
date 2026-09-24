"""Explicit device and precision selection for future numerical kernels."""

import torch


def resolve_backend(device: str = "cpu", dtype: str = "float64"):
    """Never silently change precision or fall back from a requested accelerator."""
    if device not in {"cpu", "mps", "cuda"}:
        raise ValueError("device must be cpu, mps, or cuda")
    if dtype not in {"float32", "float64"}:
        raise ValueError("dtype must be float32 or float64")
    if device == "mps" and dtype == "float64":
        raise ValueError("MPS does not support float64; use CPU or explicitly choose float32")
    if device == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("MPS is not available in this process")
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available in this process")
    return torch.device(device), getattr(torch, dtype)


def synchronize(device: torch.device):
    """Finish asynchronous GPU work before inspecting results or measuring time."""
    if device.type == "mps":
        torch.mps.synchronize()
    elif device.type == "cuda":
        torch.cuda.synchronize(device)
