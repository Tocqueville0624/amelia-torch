"""Native continuous-data EMB interface; unsupported features fail explicitly."""

import warnings

import numpy as np

from .backends import resolve_backend
from .em import NumericalError, em_fit
from .imputation import impute_prepared


class AmeliaInputError(ValueError):
    """A validated input failure, carrying the corresponding Amelia error code."""

    def __init__(self, code, message):
        self.code = code
        super().__init__(f"Amelia input error {code}: {message}")


def _stack(x, reorder_columns):
    missing = np.isnan(x)
    columns = (
        np.argsort(missing.sum(axis=0), kind="stable") if reorder_columns else np.arange(x.shape[1])
    )
    rows = np.lexsort(missing[:, columns].T)
    return x[rows][:, columns], rows, columns


def amelia(
    x,
    m=5,
    *,
    seed=None,
    device="cpu",
    dtype="float64",
    tolerance=1e-4,
    empri=None,
    autopri=0.05,
    startvals=0,
    emburn=(0, 0),
    boot_type="ordinary",
    p2s=0,
    **options,
):
    """Bootstrap-EM multiple imputation for continuous numeric matrices.

    This version implements the continuous, no-cell-prior/no-bound subset of
    Amelia 1.8.3. It is not yet a full drop-in replacement. All other options
    raise NotImplementedError instead of silently changing their meaning.

    Missing values are NaN. Entirely missing rows remain missing as in Amelia.
    Parameters are in standardized, reordered coordinates, matching Amelia's
    theta convention; diagnostics contain scale/column metadata.
    """
    if options:
        raise NotImplementedError(
            "The native pipeline has not yet implemented these Amelia options: "
            + ", ".join(sorted(options))
        )
    resolve_backend(device, dtype)
    if isinstance(m, bool) or int(m) != m or m < 1:
        raise ValueError("m must be a positive integer")
    m = int(m)
    if boot_type not in {"ordinary", "none"}:
        raise ValueError("boot_type must be ordinary or none")
    if p2s not in (0, 1, 2):
        raise ValueError("p2s must be 0, 1, or 2")
    columns = list(map(str, x.columns)) if hasattr(x, "columns") else None
    original = np.array(x, dtype=np.float64, copy=True)
    if original.ndim != 2 or original.shape[1] < 2:
        raise ValueError("The native API currently requires a matrix with at least two columns")
    if np.isinf(original).any():
        raise ValueError("Infinite values are not supported; missing values must be NaN")
    missing = np.isnan(original)
    # R's NA_real_ has a distinct NaN payload; normalize missing cells only.
    original[missing] = np.nan
    if not missing.any():
        raise AmeliaInputError(39, "The data has no missing values")
    retained = ~missing.all(axis=1)
    data = original[retained]
    n, p = data.shape
    counts = (~np.isnan(data)).sum(axis=0)
    if np.any(counts < 2):
        raise AmeliaInputError(4, "Each modeled variable needs at least two observed values")
    location = np.nanmean(data, axis=0)
    scale = np.nanstd(data, axis=0, ddof=1)
    if not np.isfinite(location).all() or not np.isfinite(scale).all():
        raise NumericalError("Observed-value standardization overflowed")
    if np.any(scale == 0):
        raise AmeliaInputError(43, "Constant variables must be excluded from the imputation model")
    if 2 * p > n + (empri or 0):
        raise AmeliaInputError(34, "Too few observations for the number of modeled variables")
    if 4 * p > n + (empri or 0):
        warnings.warn(
            "Few observations relative to modeled variables", RuntimeWarning, stacklevel=2
        )
    prepared, row_order, column_order = _stack((data - location) / scale, True)
    generator = np.random.default_rng(seed)
    imputations, fits = [], []
    for replicate in range(m):
        attempts = 0
        while True:
            attempts += 1
            indices = generator.integers(0, n, size=n) if boot_type == "ordinary" else np.arange(n)
            bootstrap = prepared[indices]
            if not np.isnan(bootstrap).all(axis=0).any():
                break
        bootstrap, _, _ = _stack(bootstrap, False)
        fitted = em_fit(
            bootstrap,
            startvals=startvals,
            tolerance=tolerance,
            empri=empri,
            autopri=autopri,
            emburn=emburn,
            device=device,
            dtype=dtype,
        )
        # Original Amelia rejects singular final covariance before drawing.
        if np.linalg.eigvalsh(fitted["theta"][1:, 1:]).min() < np.finfo(float).eps:
            raise RuntimeError("Amelia code 2: fitted covariance is not invertible")
        completed = impute_prepared(
            prepared,
            fitted["theta"],
            standard_normals=generator.standard_normal(prepared.shape),
            device=device,
            dtype=dtype,
        )
        restored = np.empty_like(data)
        restored[row_order[:, None], column_order[None, :]] = completed
        restored = restored * scale + location
        output = original.copy()
        active_rows = np.flatnonzero(retained)
        active_mask = np.isnan(data)
        for column in range(p):
            rows = active_rows[active_mask[:, column]]
            output[rows, column] = restored[active_mask[:, column], column]
        if not np.isfinite(output[retained]).all():
            raise NumericalError("Output scale restoration produced non-finite values")
        fitted["diagnostics"]["bootstrap_attempts"] = attempts
        imputations.append(output)
        fits.append(fitted)
        if p2s:
            print(f"Imputation {replicate + 1}/{m}: {fitted['diagnostics']['iterations']} EM steps")
    converged = all(fit["diagnostics"]["converged"] for fit in fits)
    return {
        "imputations": imputations,
        "m": m,
        "theta": np.stack([fit["theta"] for fit in fits], axis=-1),
        "mu": np.stack([fit["theta"][0, 1:] for fit in fits], axis=-1),
        "covMatrices": np.stack([fit["theta"][1:, 1:] for fit in fits], axis=-1),
        "iterHist": [fit["iter_hist"] for fit in fits],
        "missMatrix": missing.copy(),
        "diagnostics": {
            "engine": "torch-native-continuous",
            "reference_version": "1.8.3",
            "scope": "continuous numeric matrices; no cell priors, bounds, transformations or time structure",
            "device": device,
            "dtype": dtype,
            "seed": seed,
            "converged": converged,
            "replicates": [fit["diagnostics"] for fit in fits],
            "column_names": columns,
            "column_order_zero_based": column_order.tolist(),
            "scale_mean_original_order": location.tolist(),
            "scale_sd_original_order": scale.tolist(),
            "wholly_missing_rows_retained": int((~retained).sum()),
            "rng": "NumPy PCG64; same seed does not reproduce R draws",
        },
    }
