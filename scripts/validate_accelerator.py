"""Check an explicitly selected accelerator against three fixed R Amelia cases.

This is a small deterministic numerical check, not a performance benchmark or a
test of statistical equivalence, interval coverage, or full Amelia compatibility.
Float32 EM uses tolerance=1e-5 on both the accelerator and CPU float64 reference.
Float64 retains each R fixture's EM tolerance and the existing reference-test
comparison thresholds. Conditional draws replay the exported R standard normals
with the R fixture's theta, isolating the imputation kernel from stopping error.

Example (run only when other timed experiments have finished):
    PYTORCH_ENABLE_MPS_FALLBACK=0 .venv/bin/python scripts/validate_accelerator.py \
        --device mps --dtype float32 --output results/local/mps-validation.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import warnings
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import torch

from amelia_torch.backends import resolve_backend, synchronize
from amelia_torch.em import em_fit
from amelia_torch.imputation import impute_prepared

ROOT = Path(__file__).resolve().parents[1]
CASES = ("no_prior", "empirical_prior", "cell_prior")
FLOAT32_GATE = {"atol": 1e-5, "rtol": 1e-4}
FLOAT64_EM_GATE = {"atol": 1e-10, "rtol": 1e-9}
FLOAT64_DRAW_GATE = {"atol": 1e-11, "rtol": 1e-10}


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def comparison(actual, expected, gate):
    """Keep failed/non-finite comparisons JSON-safe and visible in the report."""
    actual = np.asarray(actual, dtype=np.float64)
    expected = np.asarray(expected, dtype=np.float64)
    same_shape = actual.shape == expected.shape
    finite = bool(np.isfinite(actual).all() and np.isfinite(expected).all())
    valid = same_shape and finite
    return {
        **gate,
        "passed": bool(valid and np.allclose(actual, expected, **gate)),
        "actual_shape": list(actual.shape),
        "expected_shape": list(expected.shape),
        "all_finite": finite,
        "max_absolute_error": float(np.max(np.abs(actual - expected))) if valid else None,
    }


def save_report(output, report):
    output.parent.mkdir(parents=True, exist_ok=True)
    report["updated_utc"] = datetime.now(UTC).isoformat()
    temporary = output.with_name(output.name + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(output)


def safe_message(error, fixture_directory):
    return (
        str(error)
        .replace(str(fixture_directory), "<fixtures>")
        .replace(str(ROOT), "<project>")
        .replace(str(Path.home()), "<home>")
    )


def check_case(name, args, device):
    """Run both backends with identical EM inputs and explicit random variates."""
    record = {"case": name, "status": "error", "phase": "read_fixture", "checks": {}}
    captured = []
    try:
        fixture_path = args.fixtures / f"{name}.json"
        case = json.loads(fixture_path.read_text(encoding="utf-8"))
        if case["provenance"]["version"] != "1.8.3" or case["case"] != name:
            raise ValueError("Expected the named unmodified Amelia 1.8.3 reference fixture")
        x = np.asarray(case["x"], dtype=np.float64)
        original = x.copy()
        reference_theta = np.asarray(case["expected_theta"], dtype=np.float64)
        reference_draw = np.asarray(case["expected_imputation"], dtype=np.float64)
        normals = np.asarray(case["standard_normals"], dtype=np.float64)
        tolerance = 1e-5 if args.dtype == "float32" else case["tolerance"]
        em_gate = FLOAT32_GATE if args.dtype == "float32" else FLOAT64_EM_GATE
        draw_gate = FLOAT32_GATE if args.dtype == "float32" else FLOAT64_DRAW_GATE
        record.update(
            fixture_filename=fixture_path.name,
            fixture_sha256=file_hash(fixture_path),
            reference_provenance=case["provenance"],
            shape=list(x.shape),
            missing_cells=int(np.isnan(x).sum()),
            em_tolerance=tolerance,
            original_r_em_tolerance=case["tolerance"],
            expected_r_iterations=case["expected_iterations"],
            iteration_policy="Both fits must converge; iteration counts need not be identical.",
        )
        options = {
            "thetaold": case["initial_theta"],
            "empri": case["empri"],
            "priors": case["priors"],
            "autopri": case["autopri"],
            "tolerance": tolerance,
            "emburn": case["emburn"],
        }
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            record["phase"] = "cpu_float64_em"
            cpu = em_fit(x, device="cpu", dtype="float64", **options)
            record["cpu_em_diagnostics"] = cpu["diagnostics"]
            record["phase"] = "accelerator_em"
            accelerated = em_fit(x, device=args.device, dtype=args.dtype, **options)
            synchronize(device)
            record["accelerator_em_diagnostics"] = accelerated["diagnostics"]
            checks = record["checks"]
            checks["both_em_fits_converged"] = {
                "passed": bool(cpu["diagnostics"]["converged"])
                and bool(accelerated["diagnostics"]["converged"]),
                "cpu_iterations": cpu["diagnostics"]["iterations"],
                "accelerator_iterations": accelerated["diagnostics"]["iterations"],
            }
            checks["theta_accelerator_vs_cpu_at_same_tolerance"] = comparison(
                accelerated["theta"], cpu["theta"], em_gate
            )
            if args.dtype == "float64":
                checks["theta_cpu_vs_r"] = comparison(
                    cpu["theta"], reference_theta, FLOAT64_EM_GATE
                )
                checks["theta_accelerator_vs_r"] = comparison(
                    accelerated["theta"], reference_theta, FLOAT64_EM_GATE
                )
            else:
                # R used a tighter EM stopping tolerance. Record this gap but
                # do not conflate it with the matched-tolerance acceptance gate.
                record["theta_gap_to_tighter_r_fit_not_an_acceptance_gate"] = {
                    "cpu_max_absolute_error": comparison(
                        cpu["theta"], reference_theta, FLOAT32_GATE
                    )["max_absolute_error"],
                    "accelerator_max_absolute_error": comparison(
                        accelerated["theta"], reference_theta, FLOAT32_GATE
                    )["max_absolute_error"],
                }
            draw_options = {
                "priors": case["priors"],
                "standard_normals": normals,
            }
            record["phase"] = "cpu_explicit_r_normal_draws"
            cpu_draw = impute_prepared(
                x, reference_theta, device="cpu", dtype="float64", **draw_options
            )
            record["phase"] = "accelerator_explicit_r_normal_draws"
            accelerated_draw = impute_prepared(
                x, reference_theta, device=args.device, dtype=args.dtype, **draw_options
            )
            synchronize(device)
            checks["draw_cpu_vs_r"] = comparison(cpu_draw, reference_draw, FLOAT64_DRAW_GATE)
            checks["draw_accelerator_vs_r"] = comparison(
                accelerated_draw, reference_draw, draw_gate
            )
            checks["draw_accelerator_vs_cpu"] = comparison(
                accelerated_draw, cpu_draw, draw_gate
            )
            observed = ~np.isnan(original)
            checks["observed_values_preserved_exactly"] = {
                "passed": bool(np.array_equal(cpu_draw[observed], original[observed]))
                and bool(np.array_equal(accelerated_draw[observed], original[observed])),
            }
            checks["input_unchanged"] = {
                "passed": bool(np.array_equal(x, original, equal_nan=True)),
            }
            record["cpu_work"] = {
                "accelerator_em_reported": accelerated["diagnostics"].get(
                    "explicit_cpu_work", []
                ),
                "imputation_source_declared": [
                    "input_and_prior_validation",
                    "missingness_grouping",
                    "prior_row_lookup_if_present",
                    "numpy_output_materialization_and_observed_value_restoration",
                ],
                "random_inputs": "Exported R standard normals loaded on CPU; no GPU RNG test.",
            }
            record["status"] = "passed" if all(v["passed"] for v in checks.values()) else "failed"
            record["phase"] = "complete"
    except Exception as error:  # noqa: BLE001 - retain failed device/fixture evidence
        record["error_type"] = type(error).__name__
        record["message"] = safe_message(error, args.fixtures)
    record["warnings"] = [
        {"category": item.category.__name__, "message": safe_message(item.message, args.fixtures)}
        for item in captured
    ]
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", required=True, choices=["mps", "cuda"])
    parser.add_argument("--dtype", required=True, choices=["float32", "float64"])
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fixtures", type=Path, default=ROOT / "tests/fixtures/reference_amelia")
    parser.add_argument("--threads", type=int, default=1)
    args = parser.parse_args()
    report = {
        "schema_version": 1,
        "kind": "three_fixed_accelerator_numerical_cases",
        "created_utc": datetime.now(UTC).isoformat(),
        "scope": "Prepared continuous low-level EM and conditional draws only.",
        "limitations": [
            "Not a statistical-equivalence or inference-coverage result.",
            "Not full Amelia API, public preprocessing, bootstrap, or R-wrapper validation.",
            "Not a speed benchmark; explicit CPU work remains part of accelerator execution.",
        ],
        "configuration": {"device": args.device, "dtype": args.dtype, "threads": args.threads},
        "acceptance_policy": {
            "float32_em_tolerance_both_backends": 1e-5,
            "float32_array_gate": FLOAT32_GATE,
            "float64_em_tolerance": "Original R fixture tolerance, identical on both backends.",
            "float64_theta_gate": FLOAT64_EM_GATE,
            "float64_conditional_draw_gate": FLOAT64_DRAW_GATE,
            "gate_definition": "Every element must satisfy abs(actual-reference) <= atol + rtol*abs(reference).",
            "rationale": "Float32 allows rounding and accumulation error with a matched stopping rule; float64 retains tests/test_em_reference.py gates.",
            "convergence": "Both EM fits must converge. Iteration counts are recorded, not forced equal.",
        },
        "environment": {
            "python": platform.python_version(),
            "torch": str(torch.__version__),
            "numpy": np.__version__,
            "platform": platform.platform(),
            "architecture": platform.machine(),
            "cuda_runtime": torch.version.cuda,
            "mps_available": torch.backends.mps.is_available(),
            "cuda_available": torch.cuda.is_available(),
            "mps_cpu_fallback_env": os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK", "unset"),
        },
        "source_sha256": {
            name: file_hash(ROOT / name)
            for name in (
                "scripts/validate_accelerator.py",
                "src/amelia_torch/em.py",
                "src/amelia_torch/imputation.py",
                "src/amelia_torch/backends.py",
            )
        },
        "harness_cpu_work": ["fixture_loading", "cpu_float64_reference", "comparisons", "report_writes"],
        "cases": [],
    }
    try:
        if args.threads < 1:
            raise ValueError("--threads must be positive")
        if args.device == "mps" and args.dtype == "float64":
            raise ValueError("MPS does not support float64; explicitly select float32 or CUDA")
        if args.device == "mps" and os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK") != "0":
            raise ValueError("Set PYTORCH_ENABLE_MPS_FALLBACK=0 before launching this process")
        torch.set_num_threads(args.threads)
        if args.device == "cuda":
            torch.backends.cuda.matmul.allow_tf32 = False
            torch.backends.cudnn.allow_tf32 = False
        device, _ = resolve_backend(args.device, args.dtype)
        report["environment"]["cpu_threads"] = torch.get_num_threads()
        report["environment"]["selected_device"] = str(device)
        if args.device == "cuda":
            properties = torch.cuda.get_device_properties(device)
            report["environment"]["gpu"] = {
                "name": properties.name,
                "memory_bytes": properties.total_memory,
                "compute_capability": list(torch.cuda.get_device_capability(device)),
                "matmul_allow_tf32": torch.backends.cuda.matmul.allow_tf32,
                "cudnn_allow_tf32": torch.backends.cudnn.allow_tf32,
            }
        for name in CASES:
            result = check_case(name, args, device)
            report["cases"].append(result)
            save_report(args.output, report)
            print(json.dumps({"case": name, "status": result["status"]}), flush=True)
    except Exception as error:  # noqa: BLE001 - record unavailable/invalid required device
        report["setup_error"] = {
            "error_type": type(error).__name__,
            "message": safe_message(error, args.fixtures),
        }
    passed = sum(case["status"] == "passed" for case in report["cases"])
    report["summary"] = {
        "expected_cases": len(CASES),
        "completed_cases": len(report["cases"]),
        "passed_cases": passed,
        "all_passed": passed == len(CASES) and "setup_error" not in report,
    }
    save_report(args.output, report)
    print(json.dumps(report["summary"]), flush=True)
    return 0 if report["summary"]["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
