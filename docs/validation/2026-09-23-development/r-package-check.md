# R package verification, 2026-09-23

The development R package `ameliatorch` version `0.0.0.9000` was installed and
tested on macOS 26.6.2, Apple Silicon, R 4.5.3, Amelia 1.8.3, and reticulate 1.47.0.
The selected interpreter was the project's Python 3.12 virtual environment,
with the installed `amelia-torch` distribution version `0.0.1.dev0`.

The following installed-package tests passed:

| Test file | Checked behavior |
|---|---|
| `r-package/tests/bridge.R` | Explicit Python selection; lazy initialization; CPU float64/float32 native imputation; matrix/data.frame labels; observed values; wholly missing rows; seeds; result shape; rejected options |
| `r-package/tests/compatibility.R` | Direct official-reference output equality and identical R RNG state; saved-result extension; combined factor/ordered/log/panel/prior/bounds case; no Python initialization |
| `r-package/tests/reference_metadata.R` | Fresh, appended, unknown, and legacy backend provenance; no fitting |
| `r-package/tests/torch-compat.R` | Original R pipeline with CPU float64 Torch EM; representative transforms, factors, priors, bounds, overimputation, and panel cases against the official package |
| `r-package/tests/downstream.R` | Summaries, headless PDF diagnostics, pooling, CSV export, saved arguments, extension, locally scoped moPrep, allthetas, and Inversion/Box–Muller random-state regression |

The first three tests and downstream checks were run directly against the installed package. All five
also passed inside `R CMD check` on a source tarball built in a separate temporary
directory. After correcting the R RNG bridge, caller-frame handling, an
unqualified `tail` call, and an unnecessary Rd caret escape, a fresh source build
and check including the compiled C helpers completed with **zero errors,
zero warnings, and zero notes**. The final result was `Status: OK`; see the
[sanitized check log](r-package-check.log) and [source hashes](r-package-check-sources.json).
The C code compiled with Apple clang 16.0.0; the check also passed native routine
registration and compiled-code checks. See the [downstream details](r-downstream-validation.md)
for the two regressions discovered by expanded coverage.

CRAN and Bioconductor package-index network requests were unavailable during the
check. Installed dependency checks still passed. This run does not verify remote
repository availability, CRAN submission acceptance, a fresh installation on
another operating system, CUDA/MPS correctness, or an interactive RStudio session.

## Reproduction

From the repository root, configure the existing project environments explicitly:

```sh
export R_LIBS_USER="$PWD/.R-library"
export RETICULATE_PYTHON="$PWD/.venv/bin/python"
R CMD INSTALL --library="$R_LIBS_USER" r-package
Rscript r-package/tests/bridge.R
Rscript r-package/tests/compatibility.R
Rscript r-package/tests/reference_metadata.R
Rscript r-package/tests/downstream.R
```

Build and check from a separate temporary directory, passing the absolute package
source directory to `R CMD build`:

```sh
R CMD build --no-manual --no-build-vignettes <project>/r-package
R CMD check --no-manual --no-build-vignettes ameliatorch_0.0.0.9000.tar.gz
```

On Windows, point `RETICULATE_PYTHON` to the selected environment's
`Scripts/python.exe`; use that platform's environment-variable syntax.

## Reference fixture correction

The combined reference test initially used a one-row prior. In Amelia 1.8.3,
dropping this matrix's dimensions can cause error 49 when its row and column
indices are equal, and can select unintended cells during output restoration.
Both direct official and wrapped calls showed the same result. The ordinary
combined-case fixture now uses two prior rows. The wrapper was not changed to
alter upstream behavior; the dedicated single-prior compatibility boundary is
documented in the [algorithm contract](../../algorithm-contract.md).
