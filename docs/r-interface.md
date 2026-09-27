# R interface

[简体中文](r-interface.zh-CN.md) · [Documentation](README.md)

`ameliatorch` provides original-reference, hybrid and native interfaces. It is a development package under GPL-3.0-only, not official Amelia or a CRAN release. [Compatibility](amelia-compatibility.md) and [release criteria](release-gates.md) define the current scope.

## Installation

Native/hybrid calls require the Python 3.12 project and compatible Torch. Reference calls require exact R Amelia 1.8.3 and do not initialize Python. The package does not install Python, Torch or CUDA automatically. Source installation needs an R-compatible C toolchain: command-line tools on Mac, matching Rtools on Windows, or the R development toolchain on Linux.

```r
.libPaths(c(file.path(getwd(), ".R-library"), .libPaths()))
install.packages("r-package", repos = NULL, type = "source", lib = ".R-library")
library(ameliatorch)
use_amelia_python(venv = ".venv")
check_environment(device = "cpu", dtype = "float64")
```

Loading the package is lazy. Alternatively set `python="/path/to/environment/bin/python"` (Windows: `C:/path/to/environment/Scripts/python.exe`) or `RETICULATE_PYTHON` before initialization. Preserve interpreter symlinks. Restart R to change an already initialized interpreter. See [reticulate environment selection](https://rstudio.github.io/reticulate/reference/use_python.html); the package does not invoke automatic `py_require()` provisioning.

## Reference and hybrid

`amelia_compat(x, ..., engine="reference")` calls the original public S3 generic without changing preprocessing or R RNG. Official classes and fields remain, with `amelia_torch_backend` metadata identifying CPU reference work. Append operations retain historical/current source and imputation counts; unknown history stays unknown.

`amelia_torch_compat(x, ..., device="cpu", dtype="float64")` retains R preparation, bootstrap, draws and output, substituting EM via private function lookup environments without modifying Amelia's namespace. Replicate scheduling is serial. Representative CPU64 transformations, nominal/ordinal variables, priors, bounds, overimputation, panel terms and downstream methods have been compared. Original diagnostics remain CPU work.

Both use original R argument names, including `boot.type` and `max.resample`. Missing dependencies and wrong versions fail explicitly. Registered C helpers preserve both internal R RNG and visible `.Random.seed`; simple seed assignment is insufficient. The contract also preserves upstream explicit-double-start-value writeback. Hybrid source-mode checks require an installed build with these helpers; after C changes reinstall with `R CMD INSTALL --clean --library=.R-library r-package`.

Official `mi.combine` requires optional broom; rlang is an Amelia import and foreign supplies DTA export. The original reversed interval endpoints and signed-tail p-value behavior are documented in [G1](validation/2026-09-26-g1/downstream-extended.md), not silently corrected. AmeliaView is a separate interactive R/Tcl/Tk GUI.

## Native interface

```r
fit <- amelia_torch(
  x,
  m = 5L,
  device = "cpu",
  dtype = "float64",
  seed = 2026,
  boot.type = "ordinary"
)
fit$imputations[[1L]]
fit$diagnostics
```

The wrapper calls `amelia_torch.amelia()`: observed-value standardization, bootstrap, conditional-moment EM, random imputation and unit restoration. Python returns a dictionary containing `imputations` (2D NumPy arrays) and `diagnostics`; additional parameters pass through. R creates `ameliatorch_result`, not an official `amelia` object.

Plain numeric matrices/data frames retain container type, names, order and observed values. Output data-frame columns are numeric. Factors, classed numeric and nonnumeric columns are rejected, as are unsupported model options. Entirely missing rows remain missing and retain R NA/NaN representation; other analyzed outputs must be finite. Altered observed values or filled excluded rows are rejected.

R `boot.type`/`max.resample` map to native Python `boot_type`/`max_resample`; duplicate aliases fail. This mapping does not add support for otherwise unsupported options. m must be a positive integer-valued scalar. Seed accepts exact nonnegative integers below 2^53 and is converted without 32-bit diagnostic truncation. Equal seeds do not pair R/Python draws.

## Devices and evidence

CPU64 is default. CUDA precision and MPS32 are explicit choices; unavailable devices, unsupported precision, failed operators and enabled MPS CPU fallback raise errors. There is no silent fallback or precision change.

At `ef729c0`, three-platform hosted CPU CI passed 307 Python checks, nine R files and the downstream example per platform. Windows RTX 3080 and Linux T4 have separate fixed-CUDA and performance records. An installed Mac RStudio session exercised reference/hybrid CPU64, readback, Data Viewer and a visible plot. These do not cover every GUI/device/model combination or complete statistical acceptance. See [evidence summary](validation/2026-09-27-evidence-summary.md).

## Development checks

Native source-only loading may use:

```r
.libPaths(c(file.path(getwd(), ".R-library"), .libPaths()))
source("r-package/R/environment.R")
source("r-package/R/amelia.R")
use_amelia_python(venv = ".venv")
check_environment("cpu", "float64")
```

`r-package/tests/bridge.R` requires explicit `RETICULATE_PYTHON` for real bridge checks; absent configuration is a skip. `AMELIATORCH_R_SOURCE=r-package` selects source functions but does not replace installing/checking the package. During the current documentation phase, no new test jobs are started.
