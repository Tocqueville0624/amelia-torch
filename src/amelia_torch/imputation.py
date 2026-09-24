"""Conditional Gaussian draws on prepared data, following Amelia's model.

This internal routine accepts variances in cell priors. Public Amelia priors
are converted by preprocessing; passing them here unconverted is incorrect.
"""

import numpy as np
import torch

from .backends import resolve_backend
from .em import NumericalError, _conditional, _patterns, _prepare_priors


def impute_prepared(
    x,
    theta,
    *,
    priors=None,
    standard_normals=None,
    seed=None,
    device="cpu",
    dtype="float64",
):
    """Draw missing cells only; explicit normal variates enable cross-R parity.

    Bounds and preprocessing belong to the public pipeline, not this routine.
    Observed inputs are restored exactly even when GPU arithmetic uses float32.
    """
    dev, precision = resolve_backend(device, dtype)
    x_cpu = np.asarray(x, dtype=np.float64)
    if not x_cpu.flags.writeable:
        x_cpu = x_cpu.copy()
    if x_cpu.ndim != 2 or np.isinf(x_cpu).any():
        raise ValueError("x must be a 2D numeric matrix without infinities")
    theta_cpu = np.asarray(theta, dtype=np.float64)
    p = x_cpu.shape[1]
    if theta_cpu.shape != (p + 1, p + 1) or not np.isfinite(theta_cpu).all():
        raise ValueError("theta must be a finite (p+1,p+1) matrix")
    prior_cpu = _prepare_priors(priors, x_cpu.shape)
    if standard_normals is not None and seed is not None:
        raise ValueError("Provide either explicit standard_normals or seed")
    normals = (
        np.random.default_rng(seed).standard_normal(x_cpu.shape)
        if standard_normals is None
        else np.asarray(standard_normals, dtype=float)
    )
    if normals.shape != x_cpu.shape or not np.isfinite(normals).all():
        raise ValueError("standard_normals must be finite with the same shape as x")
    data = torch.as_tensor(x_cpu, dtype=precision, device=dev)
    parameters = torch.tensor(theta_cpu, dtype=precision, device=dev)
    z = torch.as_tensor(normals, dtype=precision, device=dev)
    if bool(torch.isinf(data).any().item()):
        raise NumericalError("Observed input exceeds the selected dtype range")
    if not bool(torch.isfinite(parameters).all().item()):
        raise NumericalError("Parameters exceed the selected dtype range")
    if not bool(torch.isfinite(z).all().item()):
        raise NumericalError("Normal variates exceed the selected dtype range")
    completed = data.clone()
    with torch.inference_mode():
        for pattern in _patterns(x_cpu, data):
            mis = pattern.missing
            if mis.numel() == 0:
                continue
            means, covariance = _conditional(
                parameters[1:, 1:], parameters[0, 1:], pattern, {"pseudoinverse_uses": 0}
            )
            noise = z.index_select(0, pattern.rows).index_select(1, mis)
            values = means + noise @ torch.linalg.cholesky(covariance).T
            if prior_cpu is not None:
                inverse_cov = torch.linalg.inv(covariance)
                for row, original_row in enumerate(pattern.rows.cpu().tolist()):
                    items = prior_cpu[prior_cpu[:, 0] == original_row + 1]
                    if not len(items):
                        continue
                    precisions = torch.zeros(p, dtype=precision, device=dev)
                    weighted_means = torch.zeros_like(precisions)
                    columns = torch.as_tensor(items[:, 1].astype(int) - 1, device=dev)
                    precisions[columns] = torch.as_tensor(
                        1 / items[:, 3], dtype=precision, device=dev
                    )
                    weighted_means[columns] = torch.as_tensor(
                        items[:, 2] / items[:, 3], dtype=precision, device=dev
                    )
                    posterior_cov = torch.linalg.inv(inverse_cov + torch.diag(precisions[mis]))
                    posterior_mean = posterior_cov @ (
                        inverse_cov @ means[row] + weighted_means[mis]
                    )
                    values[row] = (
                        posterior_mean + noise[row] @ torch.linalg.cholesky(posterior_cov).T
                    )
            completed[pattern.rows[:, None], mis[None, :]] = values
    result = x_cpu.copy()
    missing = np.isnan(x_cpu)
    result[missing] = completed.cpu().double().numpy()[missing]
    if not np.isfinite(result[missing]).all():
        raise NumericalError("Conditional imputation produced non-finite values")
    return result
