# R interface contract (development)

`r-package/` contains the development R package `ameliatorch` for the confirmed
Python distribution `amelia-torch`. The license is `GPL-3.0-only`, and the
maintainer is Sheng Wan (`swan0624@uw.edu`). These decisions and the package
metadata are now confirmed; local installation, package build, and package tests
have passed on macOS with R 4.5.3.
It is not a CRAN release or the official Amelia package. The user requires full
compatibility before the first version is considered complete.

As of 2026-09-23, the Python public continuous-data EMB implementation exists and
the installed native R interface has passed real CPU imputation tests. The user has
also approved an explicitly labeled transitional R runtime route. Two further R
interfaces have passed representative CPU runtime comparisons: official delegation
through `amelia_compat()` and the experimental R pipeline with a Torch EM kernel
through `amelia_torch_compat()`. These cases are not a full compatibility audit.
The Python-to-R interfaces have their own transport and integration evidence.
The repository will ship small samples and full-data download scripts. Only the
Windows connection arrangements remain open among these product decisions.
The confirmed GitHub account is `Tocqueville0624`. See the [compatibility matrix](amelia-compatibility.md) and
[development evidence](validation/2026-09-23-development/README.md).

## Install and select an environment

For a native or Torch compatibility call, first install the Python project in a
Python 3.12 environment according to the setup guide. CUDA wheels are a separate
explicit installation decision. The pure official reference call does not
initialize or require Python. The R package does not download Python, PyTorch,
CUDA, or other programs.

Installing this R package from source requires an R-compatible C toolchain. Its
small registered C helpers preserve the R random state across reticulate calls;
they do not implement another imputation algorithm. Source-mode testing of the
hybrid R code also requires the installed package and its compiled helpers.

Installing the R package from source now requires an R-compatible C compiler.
Its small registered C helpers preserve R RNG state around reticulate calls;
they add no external library dependency. Use the platform's R build toolchain
(Command Line Tools on this Mac, matching Rtools on Windows, or a C compiler on
Linux). A future prebuilt R binary would not require compiling on the user's machine.

From the repository root:

```r
.libPaths(c(file.path(getwd(), ".R-library"), .libPaths()))
install.packages("r-package", repos = NULL, type = "source", lib = ".R-library")
library(ameliatorch)
use_amelia_python(venv = ".venv")
check_environment(device = "cpu", dtype = "float64")
```

Local developers can also test the native source files without installing or
distributing the package:

```r
.libPaths(c(file.path(getwd(), ".R-library"), .libPaths()))
source("r-package/R/environment.R")
source("r-package/R/amelia.R")
use_amelia_python(venv = ".venv")
check_environment("cpu", "float64")
```

The hybrid `torch_compat.R` source path additionally requires an installed build
of `ameliatorch` to load its registered RNG helpers. Source-only loading cannot
replace compiling that DLL/shared library. After C changes, reinstall with
`R CMD INSTALL --clean --library=.R-library r-package` before hybrid source tests.

Alternatively, provide `python = "/path/to/environment/bin/python"` (Windows:
`python = "C:/path/to/environment/Scripts/python.exe"`) or explicitly set
`RETICULATE_PYTHON` before any Python operation. Interpreter symlinks are preserved.
Loading the R package does not initialize Python. A session that has already
initialized a different interpreter must be restarted.

The explicit selection follows [reticulate's environment rules](https://rstudio.github.io/reticulate/reference/use_python.html).
No `py_require()` call is used because it can provision an ephemeral environment.

## Transitional reference and Torch compatibility interfaces

The newly written `amelia_compat(x, ..., engine = "reference")` requires exactly
official Amelia 1.8.3 and directly calls its public S3 generic. It forwards the
original input class and R arguments without preprocessing or changing the R RNG.
An official Amelia result retains its original class and fields, plus an
`amelia_torch_backend` attribute. A new fit records `reference`, `cpu`,
`gpu_used = FALSE`, and `torch_used = FALSE`. Extending a saved result separately
records the old backend, historical and new imputation counts, and the current
CPU reference call; unknown historical work remains unknown. This call runs the
original CPU implementation.
Its installed-package comparison tests passed in `r-package/tests/compatibility.R`:
unchanged outputs and R RNG state, saved-result extension, and a combined
categorical/transformed/panel/prior/bounds example.

The newly written `amelia_torch_compat(x, ..., device = "cpu", dtype = "float64")`
uses official Amelia 1.8.3 preprocessing, bootstrap, R random draws, and output
handling, with the project's EM kernel substituted through private function
lookup environments. It does not modify the Amelia namespace. It currently
allows only serial replicate scheduling, requires an explicitly selected Python
environment, and records mixed R/Torch work in an `amelia_torch_backend`
attribute. Representative CPU float64 comparisons have passed for transformations,
nominal and ordinal variables, priors, bounds, overimputation, and panel terms.
This route remains experimental; these examples do not establish complete
compatibility or acceleration.

Additional small downstream cases have exercised `print`, `summary`,
`compare.density`, `overimpute`, `missmap`, `tscsPlot`, `disperse`, `mi.meld`, CSV
export, saved arguments, result extension, locally scoped `moPrep` inputs, and
the internal `allthetas` adapter. The official downstream diagnostic functions
continue to run on the CPU. A multiple-replicate `boot.type = "none"` regression
exposed an R/C random-state boundary; registered snapshot/restore helpers now
preserve both states around reticulate calls. The expanded test file passes with
Inversion and Box–Muller generators, matching draws, the final `.Random.seed`,
and subsequent `runif()` and `rnorm()` values. See the
[downstream record](validation/2026-09-23-development/r-downstream-validation.md).

The bounded G1 extension also passed on local CPU float64: direct `ameliabind`,
`transform` followed by append, `with`/`mi.combine`, four additional `moPrep`
branches, `summary.mi`/`plot.amelia`, table/DTA readback and a real Python/RDS/R
roundtrip. See the [G1 record](validation/2026-09-26-g1/downstream-extended.md) and
the [runnable example](../examples/README.md). This is not a GPU quality or GUI
validation. `mi.combine` requires optional `broom`; `rlang` is installed with
Amelia's normal Imports, and `foreign` supplies DTA support. Official `AmeliaView`
requires an interactive R/Tcl/Tk session. The example explains the preserved
Amelia 1.8.3 reversed interval endpoints and signed-tail p-values; reproducing
these values does not endorse their inferential interpretation.

Both interfaces use the original R option names, including `boot.type` and
`max.resample`. They do not use the native wrapper's option alias mapping. Missing
dependencies and incompatible reference versions raise errors without installation.
Python-to-R transport and integration results are recorded separately in the
[development evidence](validation/2026-09-23-development/README.md).

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

This forwards to the implemented public function
`amelia_torch.amelia(x, m=5, device="cpu", dtype="float64", seed=None, **options)`.
The continuous-data pipeline performs standardization, bootstrap, EM, conditional
random imputation, and restoration to original units. An older scaffold-only
Python installation raises an explicit implementation-missing error. Operator
probes alone do not count as imputation validation.

The Python function must return a dictionary with `imputations` (a list of
two-dimensional NumPy arrays) and `diagnostics` (a dictionary). Additional result
fields, such as `mu`, `covMatrices`, and `theta`, pass through unchanged. R converts
the dictionary to an `ameliatorch_result` list. It never labels this as an `amelia`
object or claims compatibility with official Amelia downstream methods.

The native R entry point currently accepts plain numeric matrices/data frames.
It preserves row/column names, input container type, observed values, and order.
Data-frame output columns are numeric; factor, classed numeric, and non-numeric
columns raise errors. No categorical encoding, transformations, or model changes
are introduced in the wrapper. Unsupported model options must be rejected by
Python, not ignored by either layer.

As in original Amelia, wholly missing rows are retained as missing and excluded
from estimation. The wrapper preserves their original R `NA`/`NaN`
representation, requires all analyzed rows to be finite, and rejects a Python
result that changes any observed value or fills an excluded wholly missing row.

R names `boot.type` and `max.resample` map to Python `boot_type` and
`max_resample`. Supplying both aliases raises an error. Other names pass through
without guessing. `m` is a positive integer-valued R numeric scalar, converted to
a Python integer; `seed` accepts exact non-negative
integers below 2^53, converted to a Python integer. Identical numeric seed values
do not establish identical draws between R and Python.
The seed diagnostic is converted explicitly to an R double, avoiding reticulate's
32-bit integer truncation for larger Python integer seeds.

## Device and error policy

`cpu`/`float64` is the default on all operating systems. A caller may explicitly
request `mps`/`float32` on supported Macs or `cuda` with a selected precision on
a CUDA-enabled installation. Missing devices, unsupported precision, failed
operations, and active MPS CPU fallback raise errors. The package neither changes
precision nor selects a substitute device. End-to-end imputation quality on each
accelerator requires separate validation.

## Verification and remaining release work

`r-package/tests/bridge.R` checks lazy initialization, explicit interpreter
selection, invalid arguments, duplicate aliases, and actual CPU imputation
through Python. Set `RETICULATE_PYTHON` to enable the bridge tests. Tests without
it explicitly report the bridge as skipped, not passed.

`.github/workflows/tests.yml` configures Linux/macOS/Windows CPU Python tests and
R interface tests. Configuration is not evidence that remote CI ran. Hosted CPU
runners are not treated as CUDA/MPS benchmark machines. The workflow uses the
[GitHub Python matrix workflow](https://docs.github.com/en/actions/tutorials/build-and-test-code/python)
and [r-lib setup-r action](https://github.com/r-lib/actions/tree/v2/setup-r).

Before release: validate every required compatibility feature, verify supported
platforms, and exercise installed-package
RStudio sessions. The approved name, license, and maintainer are no longer pending
requirements. CI is configured for installation and interface checks when
executed; no remote workflow result is currently claimed. The destination account
`Tocqueville0624` is confirmed; completed release checks remain required.

For local source-only contract tests, set `AMELIATORCH_R_SOURCE` to `r-package`
and `RETICULATE_PYTHON` to the explicit environment interpreter before running
`Rscript r-package/tests/bridge.R`. This exercises the R functions but does not
substitute for installing/checking the packaged artifact.

Amelia 1.8.3's C++ conditional imputer advances R's internal RNG without always
updating `.Random.seed`. Entering reticulate between no-bootstrap replicates can
otherwise reload that stale vector and repeat draws. The hybrid saves both the
internal RNG state and the R-visible vector before deterministic Python work,
restores the internal state with `GetRNGstate`, then restores the original visible
vector separately. Thus the wrapper neither repeats imputation draws nor silently
repairs the upstream visible-state behavior. The two C entry points are explicitly
registered, require symbol objects, and disable dynamic symbol lookup.

### Local evidence, 2026-09-23

The installed-package contract test passed on the current Mac with the actual Python
imputer. It covered CPU float64/float32, matrix/data-frame outputs, default
ordinary bootstrap, `boot.type = "none"`, reproducible native draws, multiple
imputations, exact observed-value preservation, retained wholly missing rows,
array dimensions in the result dictionary, integer-valued R double `m`, large
seed metadata, and rejection of invalid/unsupported options. All R help files
parsed. R package installation, source build, and all five package test files have
also passed. A fresh build and `R CMD check --no-manual --no-build-vignettes`
completed with zero errors, warnings, or notes; see the
[package check record](validation/2026-09-23-development/r-package-check.md).
This does not claim remote CI, MPS, CUDA, or an interactive RStudio session;
those are distinct checks. Separately, the Python EM
kernel has passed three small MPS float32 reference cases. That evidence does not
establish R-to-MPS imputation quality or acceleration. The reference and Torch
compatibility cases listed above passed on CPU; full public-option and boundary
coverage is still incomplete. Three public-data benchmark subsets of 100,000 rows
have completed their formal native comparison; performance conclusions belong in
the separately audited development evidence.
