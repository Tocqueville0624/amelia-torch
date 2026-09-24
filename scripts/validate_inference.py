"""Monte Carlo checks of one scalar regression estimand after native EMB.

This is a synthetic-model check, not a proof of general imputation validity.
Both scenarios retain y and mask x1/x2 with 20% marginal probability per
covariate (about 13.33% of all three data columns). MAR depends only on y.

Rubin pooling: qbar=mean(q), Ubar=mean(U), B=sum((q-qbar)^2)/(m-1),
T=Ubar+(1+1/m)*B, nu=(m-1)*(1+Ubar/((1+1/m)*B))^2. For B=0,
nu=infinity and normal quantiles apply. We intentionally do not apply the
Barnard-Rubin finite-complete-sample degrees-of-freedom correction here.

References:
https://amices.org/mice/reference/pool.scalar.html
https://stefvanbuuren.name/publications/2014_MI_sample_population.pdf
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import time
import warnings
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import scipy
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
TRUE_X1 = 1.0
SCENARIOS = ("mcar", "mar_y_observed")


def pool_scalar(estimates, variances, confidence=0.95) -> dict:
    """Pool scalar estimates and their complete-data sampling variances."""
    q, u = np.asarray(estimates, dtype=float), np.asarray(variances, dtype=float)
    if q.ndim != 1 or u.shape != q.shape or len(q) < 2:
        raise ValueError(
            "Pooling requires matching 1D estimates/variances for at least 2 imputations"
        )
    if not np.isfinite(q).all() or not np.isfinite(u).all() or np.any(u < 0):
        raise ValueError("Estimates/variances must be finite and variances nonnegative")
    if not 0 < confidence < 1:
        raise ValueError("Confidence must lie strictly between zero and one")
    m = len(q)
    qbar, ubar, between = float(q.mean()), float(u.mean()), float(q.var(ddof=1))
    extra = (1 + 1 / m) * between
    total = ubar + extra
    if total <= 0:
        raise ValueError("A positive total variance is required for inference")
    degrees = math.inf if extra == 0 else (m - 1) * (1 + ubar / extra) ** 2
    quantile = float(stats.t.ppf((1 + confidence) / 2, degrees))
    halfwidth = quantile * math.sqrt(total)
    return {
        "m": m,
        "estimate": qbar,
        "within_variance": ubar,
        "between_variance": between,
        "total_variance": total,
        "standard_error": math.sqrt(total),
        "df": degrees,
        "interval_lower": qbar - halfwidth,
        "interval_upper": qbar + halfwidth,
        "interval_width": 2 * halfwidth,
    }


def fit_regression(data: np.ndarray) -> tuple[float, float]:
    """OLS y ~ 1 + x1 + x2; return x1 coefficient and homoscedastic variance."""
    if data.ndim != 2 or data.shape[1] != 3 or len(data) <= 3 or not np.isfinite(data).all():
        raise ValueError("Regression needs a finite n-by-3 matrix with n > 3")
    design = np.column_stack([np.ones(len(data)), data[:, 1:]])
    coefficients, _, rank, _ = np.linalg.lstsq(design, data[:, 0], rcond=None)
    if rank != 3:
        raise ValueError("Regression design is rank deficient")
    residual = data[:, 0] - design @ coefficients
    residual_variance = float(residual @ residual / (len(data) - 3))
    _, upper = np.linalg.qr(design, mode="reduced")
    inverse_upper = np.linalg.solve(upper, np.eye(3))
    coefficient_variance = residual_variance * (inverse_upper @ inverse_upper.T)[1, 1]
    return float(coefficients[1]), float(coefficient_variance)


def simulate_input(
    n: int, scenario: str, seed: int, replicate: int, missing_rate: float = 0.2
) -> tuple[np.ndarray, int, dict]:
    """Independent simulation seeds remain stable when the replicate budget changes."""
    if scenario not in SCENARIOS:
        raise ValueError("Unknown missingness scenario")
    children = np.random.SeedSequence([seed, SCENARIOS.index(scenario), replicate]).spawn(3)
    data_seed, mask_seed, imputation_seed = [int(child.generate_state(1)[0]) for child in children]
    rng = np.random.default_rng(data_seed)
    covariates = rng.multivariate_normal([0, 0], [[1, 0.3], [0.3, 1]], size=n)
    y = 1 + covariates[:, 0] + 0.5 * covariates[:, 1] + rng.normal(size=n)
    data = np.column_stack([y, covariates])
    intercept = None
    if scenario == "mcar":
        probabilities = np.full(n, missing_rate)
    else:
        # y population variance is 1 + .25 + 2*.5*.3 + 1 = 2.55.
        observed_anchor = (y - 1) / math.sqrt(2.55)
        low, high = -40.0, 40.0
        for _ in range(80):
            intercept = (low + high) / 2
            probabilities = 1 / (1 + np.exp(-np.clip(intercept + observed_anchor, -40, 40)))
            if probabilities.mean() < missing_rate:
                low = intercept
            else:
                high = intercept
    missing = np.random.default_rng(mask_seed).random((n, 2)) < probabilities[:, None]
    data[:, 1:][missing] = np.nan
    return (
        data,
        imputation_seed,
        {
            "data_seed": data_seed,
            "mask_seed": mask_seed,
            "imputation_seed": imputation_seed,
            "actual_covariate_missing_rate": float(missing.mean()),
            "actual_whole_matrix_missing_rate": float(missing.sum() / data.size),
            "mar_logistic_intercept": intercept,
        },
    )


def run_replicate(n: int, m: int, seed: int, index: int, scenario: str) -> dict:
    from amelia_torch import amelia

    data, imputation_seed, generation = simulate_input(n, scenario, seed, index)
    record = {"replicate": index, "scenario": scenario, **generation}
    started = time.perf_counter()
    try:
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            result = amelia(
                data,
                m=m,
                seed=imputation_seed,
                device="cpu",
                dtype="float64",
                tolerance=1e-4,
                autopri=0.05,
                emburn=(0, 500),
            )
        fits = result["diagnostics"]["replicates"]
        record.update(
            {
                "warnings": [str(warning.message) for warning in captured],
                "imputation_fits_returned": len(fits),
                "imputation_fits_converged": sum(bool(fit["converged"]) for fit in fits),
                "imputation_fits_nonconverged": sum(not fit["converged"] for fit in fits),
                "em_iterations": [fit["iterations"] for fit in fits],
                "empri_final": [fit["empri_final"] for fit in fits],
                "pseudoinverse_uses": sum(fit["pseudoinverse_uses"] for fit in fits),
            }
        )
        if not result["diagnostics"]["converged"]:
            record["status"] = "nonconverged"
        else:
            model_fits = [fit_regression(completed) for completed in result["imputations"]]
            pooled = pool_scalar(*zip(*model_fits))
            record.update(
                {
                    "status": "success",
                    "pooled": pooled,
                    "covered": pooled["interval_lower"] <= TRUE_X1 <= pooled["interval_upper"],
                }
            )
    except (ValueError, RuntimeError, np.linalg.LinAlgError) as error:
        record.update({"status": "failed", "error_type": type(error).__name__, "error": str(error)})
    record["elapsed_seconds"] = time.perf_counter() - started
    return record


def summarize(records: list[dict]) -> dict:
    successful = [record for record in records if record["status"] == "success"]
    summary = {
        "datasets_attempted": len(records),
        "datasets_successful": len(successful),
        "datasets_nonconverged": sum(record["status"] == "nonconverged" for record in records),
        "datasets_failed": sum(record["status"] == "failed" for record in records),
        "imputation_fits_returned": sum(
            record.get("imputation_fits_returned", 0) for record in records
        ),
        "imputation_fits_converged": sum(
            record.get("imputation_fits_converged", 0) for record in records
        ),
        "imputation_fits_nonconverged": sum(
            record.get("imputation_fits_nonconverged", 0) for record in records
        ),
        "datasets_with_unavailable_fit_status": sum(
            "imputation_fits_returned" not in record for record in records
        ),
        "coverage_denominator": "successful, fully converged datasets only; failures listed separately",
    }
    if not successful:
        return summary
    estimates = np.array([record["pooled"]["estimate"] for record in successful])
    widths = np.array([record["pooled"]["interval_width"] for record in successful])
    covered = sum(record["covered"] for record in successful)
    count = len(successful)
    coverage = covered / count
    confidence = stats.binomtest(covered, count).proportion_ci(
        confidence_level=0.95, method="exact"
    )
    summary.update(
        {
            "true_x1_coefficient": TRUE_X1,
            "mean_estimate": float(estimates.mean()),
            "bias": float(estimates.mean() - TRUE_X1),
            "bias_mcse": float(estimates.std(ddof=1) / math.sqrt(count)) if count > 1 else None,
            "empirical_estimate_sd": float(estimates.std(ddof=1)) if count > 1 else None,
            "coverage": coverage,
            "coverage_mcse": math.sqrt(coverage * (1 - coverage) / count),
            "coverage_exact_binomial_95_interval": [confidence.low, confidence.high],
            "average_interval_width": float(widths.mean()),
            "average_interval_width_mcse": float(widths.std(ddof=1) / math.sqrt(count))
            if count > 1
            else None,
            "average_pooled_standard_error": float(
                np.mean([record["pooled"]["standard_error"] for record in successful])
            ),
            "coverage_if_every_unsuccessful_dataset_counted_as_miss": covered / len(records),
            "average_covariate_missing_rate": float(
                np.mean([record["actual_covariate_missing_rate"] for record in records])
            ),
        }
    )
    return summary


def json_safe(value):
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return "Infinity" if value > 0 else "-Infinity" if value < 0 else "NaN"
    return value


def write_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    if path.is_symlink() or temporary.is_symlink():
        raise ValueError("Refusing symbolic-link report destination")
    temporary.write_text(json.dumps(json_safe(report), indent=2, allow_nan=False) + "\n")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--replicates", type=int, default=200, help="Independent datasets per scenario"
    )
    parser.add_argument("--n", type=int, default=300)
    parser.add_argument("--m", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260923)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--time-budget-seconds", type=float, default=300)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "results/local/inference_validation.json"
    )
    args = parser.parse_args()
    if (
        args.replicates < 2
        or args.n < 10
        or args.m < 2
        or args.threads < 1
        or args.time_budget_seconds <= 0
    ):
        parser.error("Need replicates >=2, n >=10, m >=2, threads >=1, positive time budget")
    if args.output.exists():
        parser.error(
            "Output already exists; choose another filename to preserve the previous result"
        )
    import torch

    torch.set_num_threads(args.threads)
    started = time.perf_counter()
    report = {
        "validation": "native EMB synthetic linear-regression inference check",
        "started_utc": datetime.now(UTC).isoformat(),
        "settings": {
            "replicates_per_scenario": args.replicates,
            "n": args.n,
            "m": args.m,
            "seed": args.seed,
            "torch_threads": args.threads,
            "device": "cpu",
            "dtype": "float64",
            "tolerance": 1e-4,
            "autopri": 0.05,
            "empri": None,
            "maximum_em_iterations": 500,
            "time_budget_seconds": args.time_budget_seconds,
        },
        "data_generating_process": "(x1,x2)~N(0,[[1,.3],[.3,1]]); noise~N(0,1) independent; y=1+x1+.5*x2+noise",
        "missingness": "y is always observed; each x1/x2 cell has 20% marginal expected missingness; about 13.33% across all columns. MAR probabilities depend only on observed y; slope=1, intercept calibrated per observed sample.",
        "pooling": {
            "total_variance": "T=Ubar+(1+1/m)*B",
            "between_variance": "B=sample variance of m coefficient estimates (ddof=1)",
            "degrees_of_freedom": "nu=(m-1)*(1+Ubar/((1+1/m)*B))^2; Infinity when B=0",
            "interval": "qbar +/- t(nu,.975)*sqrt(T)",
            "small_sample_correction": "Barnard-Rubin finite-complete-sample df correction NOT applied",
            "regression_variance": "homoscedastic OLS, residual variance SSE/(n-3)",
        },
        "monte_carlo_uncertainty": "bias MCSE=sd(estimates)/sqrt(successes); coverage MCSE=sqrt(p*(1-p)/successes); exact binomial 95% interval also shown",
        "limitations": [
            "Only the stated correctly specified joint-normal model and covariate-missing scenarios are checked.",
            "Not an R-versus-Python comparison, equivalence test, or proof of validity on all real datasets.",
            "No Barnard-Rubin finite-n correction; m=5 and 200 replicates leave Monte Carlo uncertainty.",
            "Coverage excludes failed/nonconverged runs in its main denominator; a failure-as-miss rate is also reported.",
        ],
        "references": [
            "https://amices.org/mice/reference/pool.scalar.html",
            "https://stefvanbuuren.name/publications/2014_MI_sample_population.pdf",
        ],
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "torch": torch.__version__,
            "os": platform.system(),
            "machine_architecture": platform.machine(),
            "blas_thread_environment": {
                key: os.environ.get(key)
                for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")
            },
        },
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [
                *sorted((ROOT / "src/amelia_torch").glob("*.py")),
                Path(__file__).resolve(),
            ]
        },
        "records": [],
        "completed_requested_replicates": False,
    }
    for index in range(args.replicates):
        for scenario in SCENARIOS:
            report["records"].append(run_replicate(args.n, args.m, args.seed, index, scenario))
        report["summary"] = {
            scenario: summarize(
                [item for item in report["records"] if item["scenario"] == scenario]
            )
            for scenario in SCENARIOS
        }
        report["elapsed_seconds"] = time.perf_counter() - started
        report["completed_requested_replicates"] = index + 1 == args.replicates
        if (index + 1) % 25 == 0 or report["completed_requested_replicates"]:
            print(
                json.dumps(
                    {
                        "completed_per_scenario": index + 1,
                        "elapsed_seconds": report["elapsed_seconds"],
                    }
                ),
                flush=True,
            )
            write_report(args.output, report)
        if report["elapsed_seconds"] >= args.time_budget_seconds:
            report["stopping_reason"] = "time_budget_reached_between_paired_simulations"
            break
    else:
        report["stopping_reason"] = "completed"
    report["finished_utc"] = datetime.now(UTC).isoformat()
    write_report(args.output, report)
    print(json.dumps(json_safe(report["summary"]), indent=2))
    return 0 if report["completed_requested_replicates"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
