"""Small operator checks, explicitly not an imputation speed benchmark."""

import argparse
import json
import os
import platform
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import torch

from .backends import resolve_backend, synchronize


def probe_backend(device: str, dtype: str) -> dict:
    dev, precision = resolve_backend(device, dtype)
    a64 = torch.tensor([[4.0, 1.0], [1.0, 3.0]], dtype=torch.float64)
    b64 = torch.tensor([[1.0], [2.0]], dtype=torch.float64)
    a, b = a64.to(dev, precision), b64.to(dev, precision)
    operations = {
        "matmul": (lambda: a @ b, a64 @ b64),
        "cholesky": (lambda: torch.linalg.cholesky(a), torch.linalg.cholesky(a64)),
        "solve": (lambda: torch.linalg.solve(a, b), torch.linalg.solve(a64, b64)),
        "sum": (lambda: a.sum(dim=0), a64.sum(dim=0)),
        "index_select": (
            lambda: a.index_select(0, torch.tensor([1, 0], device=dev)),
            a64.flip(0),
        ),
    }
    results = {}
    with torch.inference_mode():
        for name, (operation, expected) in operations.items():
            try:
                output = operation()
                synchronize(dev)
                actual = output.cpu().double()
                close = torch.allclose(actual, expected, atol=2e-6, rtol=2e-6)
                results[name] = {
                    "ok": close,
                    "output_device": str(output.device),
                    "max_abs_error_vs_cpu_float64": (actual - expected).abs().max().item(),
                }
            except (RuntimeError, NotImplementedError) as error:
                results[name] = {"ok": False, "error": str(error)}
        try:
            samples = torch.randn((128, 2), device=dev, dtype=precision)
            synchronize(dev)
            results["normal_draws"] = {
                "ok": bool(torch.isfinite(samples).all().item()),
                "output_device": str(samples.device),
            }
        except (RuntimeError, NotImplementedError) as error:
            results["normal_draws"] = {"ok": False, "error": str(error)}
    return {"device": device, "dtype": dtype, "operations": results}


def environment_report() -> dict:
    """No serial numbers, usernames, or local interpreter paths in the report."""
    report = {
        "kind": "environment_and_operator_smoke_only",
        "utc_time": datetime.now(UTC).isoformat(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "torch": str(torch.__version__),
        "numpy": np.__version__,
        "cpu_threads": torch.get_num_threads(),
        "mps_available": torch.backends.mps.is_available(),
        "mps_built": torch.backends.mps.is_built(),
        "mps_cpu_fallback_env": os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK", "unset"),
        "cuda_available": torch.cuda.is_available(),
        "cuda_runtime": torch.version.cuda,
        "probes": [probe_backend("cpu", "float64"), probe_backend("cpu", "float32")],
    }
    if report["mps_available"]:
        report["probes"].append(probe_backend("mps", "float32"))
    if report["cuda_available"]:
        props = torch.cuda.get_device_properties(0)
        report["cuda_device"] = {
            "name": props.name,
            "memory_bytes": props.total_memory,
            "compute_capability": list(torch.cuda.get_device_capability(0)),
            "compiled_architectures": torch.cuda.get_arch_list(),
            "matmul_allow_tf32": torch.backends.cuda.matmul.allow_tf32,
        }
        report["probes"].extend(
            [probe_backend("cuda", "float64"), probe_backend("cuda", "float32")]
        )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-device", choices=["cpu", "mps", "cuda"])
    args = parser.parse_args()
    report = environment_report()
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    available = {probe["device"] for probe in report["probes"]}
    if args.require_device and args.require_device not in available:
        parser.exit(1, f"Required device is unavailable: {args.require_device}\n")
    if not all(op["ok"] for probe in report["probes"] for op in probe["operations"].values()):
        parser.exit(1, "One or more operator probes failed; inspect the report.\n")


if __name__ == "__main__":
    main()
