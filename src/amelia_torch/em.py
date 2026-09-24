"""Amelia 1.8.3 EM semantics expressed with PyTorch linear algebra.

Inputs are already transformed/standardized. This is not the complete public
Amelia preprocessing pipeline. Algorithm provenance: Honaker, King, Blackwell;
Amelia 1.8.3 R/emb.r and src/em.cpp (GPL >= 2), see docs/algorithm-contract.md.
"""

import warnings
from dataclasses import dataclass

import numpy as np
import torch

from .backends import resolve_backend


class NumericalError(RuntimeError):
    """The requested Amelia computation cannot produce finite valid parameters."""


@dataclass
class Pattern:
    rows: torch.Tensor
    observed: torch.Tensor
    missing: torch.Tensor
    values: torch.Tensor


def _symmetric(matrix):
    upper = torch.triu(matrix)
    return upper + torch.triu(matrix, diagonal=1).T


def _submatrix(matrix, rows, cols):
    return matrix.index_select(0, rows).index_select(1, cols)


def _set_block(matrix, indices, block):
    matrix[indices[:, None], indices[None, :]] = block


def _patterns(x_cpu, tensor):
    masks, inverse = np.unique(np.isnan(x_cpu), axis=0, return_inverse=True)
    order = np.argsort(inverse, kind="stable")
    offsets = np.concatenate(([0], np.cumsum(np.bincount(inverse))))
    groups = []
    for group, mask in enumerate(masks):
        rows = torch.as_tensor(order[offsets[group] : offsets[group + 1]], device=tensor.device)
        observed = torch.as_tensor(np.flatnonzero(~mask), device=tensor.device)
        missing = torch.as_tensor(np.flatnonzero(mask), device=tensor.device)
        groups.append(Pattern(rows, observed, missing, tensor.index_select(0, rows)))
    return groups


def _conditional(covariance, mean, pattern, diagnostics):
    obs, mis = pattern.observed, pattern.missing
    mm = _submatrix(covariance, mis, mis)
    if obs.numel() == 0:
        return mean[mis].expand(len(pattern.rows), -1).clone(), mm
    oo = _submatrix(covariance, obs, obs)
    om = _submatrix(covariance, obs, mis)
    chol, info = torch.linalg.cholesky_ex(oo)
    if int(info.item()) == 0:
        beta = torch.cholesky_solve(om, chol)
    else:
        # Amelia's sweep uses an absolute sqrt(double epsilon) pinv threshold.
        inverse = torch.linalg.pinv(oo, atol=np.sqrt(np.finfo(float).eps), rtol=0)
        beta = inverse @ om
        diagnostics["pseudoinverse_uses"] += 1
    conditional_mean = (pattern.values[:, obs] - mean[obs]) @ beta + mean[mis]
    conditional_covariance = _symmetric(mm - om.T @ beta)
    return conditional_mean, conditional_covariance


def _prepare_priors(priors, shape):
    if priors is None:
        return None
    result = np.asarray(priors, dtype=np.float64)
    if result.ndim != 2 or result.shape[1] != 4 or not np.isfinite(result).all():
        raise ValueError("Low-level priors must contain finite row, column, mean, variance")
    indices = result[:, :2]
    if np.any(indices != np.floor(indices)) or np.any(indices < 1):
        raise ValueError("Low-level prior row/column indices are 1-based positive integers")
    if np.any(indices[:, 0] > shape[0]) or np.any(indices[:, 1] > shape[1]):
        raise ValueError("Prior indices exceed the input shape")
    if np.any(result[:, 3] <= 0):
        raise ValueError("Prior variances must be positive")
    if len(np.unique(indices, axis=0)) != len(indices):
        raise ValueError("Duplicate cell priors must be resolved by preprocessing")
    return result


def initial_theta(x, startvals=0, priors=None):
    """Return Amelia's complete-case start, or mean zero and identity covariance."""
    x = np.asarray(x, dtype=np.float64)
    p = x.shape[1]
    if np.ndim(startvals) == 2:
        theta = np.asarray(startvals, dtype=np.float64)
        if theta.shape != (p + 1, p + 1) or theta[0, 0] != -1:
            raise ValueError("startvals must be a (p+1,p+1) theta with theta[0,0]=-1")
        return theta.copy()
    if startvals not in (0, 1):
        raise ValueError("startvals must be 0, 1, or an explicit theta matrix")
    theta = np.eye(p + 1)
    theta[0, 0] = -1
    if startvals == 0:
        filled = x.copy()
        if priors is not None:
            indices = priors[:, :2].astype(int) - 1
            filled[indices[:, 0], indices[:, 1]] = priors[:, 2]
        complete = filled[~np.isnan(filled).any(axis=1)]
        if len(complete) > p:
            covariance = np.atleast_2d(np.cov(complete, rowvar=False, ddof=1))
            if np.linalg.eigvalsh(covariance).min() > 10 * np.finfo(float).eps:
                theta[1:, 1:] = covariance
                theta[0, 1:] = theta[1:, 0] = complete.mean(axis=0)
    return theta


def em_fit(
    x,
    *,
    thetaold=None,
    startvals=0,
    tolerance=1e-4,
    priors=None,
    empri=None,
    autopri=0.05,
    emburn=(0, 0),
    allthetas=False,
    device="cpu",
    dtype="float64",
):
    """Fit on prepared data; priors use 1-based indices and variances, not SDs.

    emburn=(minimum, maximum), with maximum<1 meaning no iteration limit, as in
    Amelia. Reaching a finite maximum is reported as nonconvergence, not success.
    No extra ridge, covariance clipping, or precision fallback is introduced.
    """
    dev, precision = resolve_backend(device, dtype)
    x_cpu = np.asarray(x, dtype=np.float64)
    if not x_cpu.flags.writeable:
        x_cpu = x_cpu.copy()
    if x_cpu.ndim != 2 or min(x_cpu.shape) < 1 or len(x_cpu) < 2:
        raise ValueError("x must be a 2D matrix with at least two rows")
    if np.isinf(x_cpu).any():
        raise ValueError("x may contain NaN missing values but not infinity")
    if not np.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("tolerance must be finite and positive")
    if not np.isfinite(autopri) or autopri < 0:
        raise ValueError("autopri must be finite and nonnegative")
    limits = np.asarray(emburn, dtype=np.float64)
    if limits.shape != (2,) or not np.isfinite(limits).all():
        raise ValueError("emburn must contain two finite numeric iteration limits")
    # Upstream compares its integer counter directly to numeric limits. A
    # fractional cap therefore rounds upward; every maximum below 1 is unlimited.
    minimum = max(0, int(np.ceil(limits[0])))
    maximum = 0 if limits[1] < 1 else int(np.ceil(limits[1]))
    if empri is not None and (not np.isfinite(empri) or empri < 0):
        raise ValueError("empri must be finite and nonnegative")
    prior_cpu = _prepare_priors(priors, x_cpu.shape)
    n, p = x_cpu.shape
    x_tensor = torch.as_tensor(x_cpu, dtype=precision, device=dev)
    if bool(torch.isinf(x_tensor).any().item()):
        raise NumericalError("Observed input exceeds the selected dtype range")
    theta_cpu = (
        np.diag([-1.0] + [1.0] * p)
        if not np.isnan(x_cpu).any()
        else (
            initial_theta(x_cpu, startvals, prior_cpu)
            if thetaold is None
            else np.asarray(thetaold, dtype=float)
        )
    )
    if (
        theta_cpu.shape != (p + 1, p + 1)
        or not np.isfinite(theta_cpu).all()
        or theta_cpu[0, 0] != -1
    ):
        raise ValueError("Initial theta must be finite, (p+1,p+1), with theta[0,0]=-1")
    theta = torch.tensor(theta_cpu, dtype=precision, device=dev).clone()
    if not bool(torch.isfinite(theta).all().item()):
        raise NumericalError("Initial parameters exceed the selected dtype range")
    empirical = int(empri or 0)
    hold = empirical * torch.eye(p, dtype=precision, device=dev)
    diagnostics = {
        "device": str(dev),
        "dtype": dtype,
        "pseudoinverse_uses": 0,
        "empri_initial": empirical,
        "eigenvalue_check_device": "cpu" if dev.type == "mps" else str(dev),
        "explicit_cpu_work": ["initialization", "missingness_grouping"]
        + (["eigenvalue_diagnostics"] if dev.type == "mps" else []),
    }
    history, parameters = [], []
    with torch.inference_mode():
        if not np.isnan(x_cpu).any():
            theta[0, 1:] = theta[1:, 0] = x_tensor.mean(dim=0)
            centered = x_tensor - theta[0, 1:]
            theta[1:, 1:] = _symmetric(centered.T @ centered / (n - 1))
            diagnostics.update(
                iterations=0,
                converged=True,
                complete_sample=True,
                patterns=1,
                empri_final=empirical,
            )
        else:
            patterns = _patterns(x_cpu, x_tensor)
            # Prior association is done once on the CPU, not once per EM step.
            row_priors = {}
            if prior_cpu is not None:
                for row in np.unique(prior_cpu[:, 0]).astype(int):
                    items = prior_cpu[prior_cpu[:, 0] == row]
                    row_priors[row - 1] = items
            pattern_priors = []
            for pattern in patterns:
                local = []
                for i, row in enumerate(pattern.rows.cpu().tolist() if row_priors else []):
                    if row in row_priors:
                        items = row_priors[row]
                        means = torch.zeros(p, dtype=precision, device=dev)
                        precisions = torch.zeros_like(means)
                        indices = torch.as_tensor(items[:, 1].astype(int) - 1, device=dev)
                        precisions[indices] = torch.as_tensor(
                            1 / items[:, 3], dtype=precision, device=dev
                        )
                        means[indices] = torch.as_tensor(
                            items[:, 2] / items[:, 3], dtype=precision, device=dev
                        )
                        local.append((i, precisions[pattern.missing], means[pattern.missing]))
                pattern_priors.append(local)
            cvalue = 1
            while (cvalue > 0 or len(history) < minimum) and (
                not maximum or len(history) < maximum
            ):
                filled = torch.nan_to_num(x_tensor, nan=0.0)
                correction = torch.zeros((p, p), dtype=precision, device=dev)
                for pattern, local_priors in zip(patterns, pattern_priors):
                    if pattern.missing.numel() == 0:
                        continue
                    means, conditional_cov = _conditional(
                        theta[1:, 1:], theta[0, 1:], pattern, diagnostics
                    )
                    correction_part = len(pattern.rows) * conditional_cov
                    if local_priors:
                        inverse_cov = torch.linalg.inv(conditional_cov)
                        for row, precision_vector, precision_mean in local_priors:
                            posterior_cov = torch.linalg.inv(
                                inverse_cov + torch.diag(precision_vector)
                            )
                            means[row] = posterior_cov @ (inverse_cov @ means[row] + precision_mean)
                            correction_part += posterior_cov - conditional_cov
                    filled[pattern.rows[:, None], pattern.missing[None, :]] = means
                    current = _submatrix(correction, pattern.missing, pattern.missing)
                    _set_block(correction, pattern.missing, current + correction_part)
                totals = filled.sum(dim=0)
                second = filled.T @ filled + correction
                center = torch.outer(totals, totals) / n
                if empirical > 0:
                    second = (n / (n + empirical + p + 2)) * (second - center + hold) + center
                new_theta = torch.empty_like(theta)
                new_theta[0, 0] = -1
                new_theta[0, 1:] = new_theta[1:, 0] = totals / n
                new_theta[1:, 1:] = _symmetric(second / n - torch.outer(totals / n, totals / n))
                if not bool(torch.isfinite(new_theta).all().item()):
                    raise NumericalError("EM produced non-finite parameters")
                cvalue = int((torch.triu((new_theta - theta).abs()) > tolerance).sum().item())
                theta = new_theta
                iteration = len(history) + 1
                previous_count = history[-1][0] if history else 0
                nonmonotone = int(cvalue > previous_count and iteration > 20)
                if (
                    nonmonotone
                    and autopri > 0
                    and sum(row[2] for row in history[-20:]) > 3
                    and empirical < autopri * n
                ):
                    # Preserve upstream integer conversion and fixed initial hold.
                    empirical = int(empirical + 0.01 * n)
                # MPS internally sends larger eigh operations to CPU even with
                # its general fallback disabled. Make that operation explicit,
                # retain the requested dtype and record it in diagnostics.
                diagnostic_covariance = theta[1:, 1:].cpu() if dev.type == "mps" else theta[1:, 1:]
                singular = int(
                    bool((torch.linalg.eigvalsh(diagnostic_covariance) <= 0).any().item())
                )
                history.append((cvalue, nonmonotone, singular))
                if allthetas:
                    parameters.append(theta.cpu().double().numpy().copy())
            diagnostics.update(
                iterations=len(history),
                converged=cvalue == 0,
                complete_sample=False,
                patterns=len(patterns),
                empri_final=empirical,
            )
    output = theta.cpu().double().numpy()
    if not np.isfinite(output).all():
        raise NumericalError("EM produced non-finite parameters")
    if not diagnostics["converged"]:
        warnings.warn(
            "Amelia EM reached emburn maximum before convergence", RuntimeWarning, stacklevel=2
        )
    result = {
        "theta": output,
        "iter_hist": np.asarray(history, dtype=np.int64).reshape(-1, 3),
        "diagnostics": diagnostics,
    }
    if allthetas:
        result["theta_history"] = parameters
    return result
