# Installation

[简体中文](setup.zh-CN.md) · [Documentation](README.md)

Run from the repository root. Use a project Python environment and `.R-library`; do not copy environments across operating systems. Source installation of the R package needs a C toolchain for registered RNG helpers: Xcode Command Line Tools on Mac, matching Rtools on Windows, or R development tools on Linux.

## Apple Silicon

The recorded environment used Python 3.12.13 and R 4.5.3. `requirements-macos-arm64.lock` is an exact Mac package snapshot without distribution hashes, not a Windows CUDA or Intel Mac lock.

```sh
UV_CACHE_DIR="$PWD/.cache/uv" uv venv --python 3.12 .venv
UV_CACHE_DIR="$PWD/.cache/uv" uv pip install --python .venv/bin/python -r requirements-macos-arm64.lock
UV_CACHE_DIR="$PWD/.cache/uv" uv pip install --python .venv/bin/python --no-build-isolation --no-deps -e .
Rscript scripts/setup_r.R
R CMD INSTALL --library=.R-library r-package
```

`setup_r.R` uses CRAN binaries on Mac/Windows, checks installation and adds missing dependencies or upgrades reticulate below 1.41 only in the project library. Restart R if an upgraded package is already loaded. This installer is not a complete R/BLAS dependency lock.

If CRAN's current Amelia version differs, setup stops. The fixed-source fallback requires the R C/C++/Fortran build toolchain. It checks SHA-256 `7699455ca3e9dabd60ad0ec69185ece3f24a597ef8da18033ea0b7a32356967f` and tries only CRAN current/Archive locations for 1.8.3:

```sh
python -c "from pathlib import Path; from scripts.cloud_bootstrap import fetch_amelia; p=Path('.cache/Amelia_1.8.3.tar.gz'); p.parent.mkdir(parents=True, exist_ok=True); print(fetch_amelia(p))"
Rscript -e 'lib <- file.path(getwd(), ".R-library"); dir.create(lib, showWarnings=FALSE); .libPaths(c(lib, .libPaths())); install.packages(c("Rcpp", "RcppArmadillo", "rlang", "foreign"), repos="https://cloud.r-project.org", lib=lib); install.packages(".cache/Amelia_1.8.3.tar.gz", repos=NULL, type="source", lib=lib); stopifnot(as.character(packageVersion("Amelia")) == "1.8.3")'
Rscript scripts/setup_r.R
```

Use the active project Python (or explicit `.venv/bin/python` / `.venv\Scripts\python.exe`). This pins Amelia itself, not all R dependencies.

Verification commands for a separately scheduled validation run:

```sh
PYTORCH_ENABLE_MPS_FALLBACK=0 .venv/bin/python -m amelia_torch.diagnostics --require-device mps --output results/local/mac_probe.json
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests scripts
Rscript scripts/smoke_amelia.R
Rscript scripts/smoke_r_bridge.R
```

If a restricted process cannot see MPS, record the failure and check from a permitted native terminal. Do not enable automatic CPU fallback. Missing required devices or failed operator checks produce a nonzero exit.

## RStudio

Open `Amelia_Project.Rproj`. For reference-only use, including no-Torch Intel Mac, start a fresh R session and run:

```r
source("scripts/smoke_amelia.R")
```

This checks original Amelia without initializing Python. `ameliatorch::amelia_compat()` additionally requires the project R package; Python `amelia_reference()` does not. For Torch native/hybrid use:

```r
source("scripts/smoke_r_bridge.R")
source("scripts/smoke_amelia.R")
```

The scripts select the project library and environment. Restart R before changing an initialized Python interpreter. Install the R package with `R CMD INSTALL --library=.R-library r-package`. [R interface](r-interface.md) documents explicit selection and lazy loading. The [Mac RStudio record](validation/2026-09-26-g6-rstudio/README.md) covers installed-package imputation/readback and a visible diagnostic plot. Data Viewer does not require XQuartz; original AmeliaView's Tcl/Tk requirements are separate.

## Windows CUDA

The [Windows record](validation/2026-09-27-windows-rtx3080/README.md) used Windows 11/RTX 3080, Python 3.12.14, Torch 2.14.0+cu132, R 4.5.3, Amelia 1.8.3 and Rtools 45. It covers fixed CUDA cases and 30 benchmark configurations, not Windows RStudio GUI acceptance or all possible Windows installations.

Copy/clone source only. Install NVIDIA drivers, Python 3.12, R and matching Rtools. Record `nvidia-smi`; its CUDA label describes driver capability, not necessarily Torch's runtime. In PowerShell:

```powershell
uv venv --python 3.12 .venv
```

Select a compatible Windows/Pip/CUDA wheel using the [official PyTorch selector](https://pytorch.org/get-started/locally/). Replace its `pip install` with `uv pip install --python .venv\Scripts\python.exe`, retain the CUDA index, and install only the needed torch package. Record deviations from the measured version. Prebuilt wheels are preferred; a CUDA Toolkit is not implied unless custom extension compilation requires it.

```powershell
uv pip install --python .venv\Scripts\python.exe -e ".[dev,reference]"
.venv\Scripts\python.exe -m amelia_torch.diagnostics --require-device cuda --output results/local/windows_probe.json
Rscript scripts/setup_r.R
R CMD INSTALL --library=.R-library r-package
.venv\Scripts\python.exe -m pytest -q
Rscript scripts/smoke_amelia.R
Rscript scripts/smoke_r_bridge.R
```

Ensure Rscript is on PATH, or run corresponding scripts from RStudio. A successful `nvidia-smi` is not a Torch CUDA check: verify the reported GPU, memory, wheel/runtime and operator results. Use new experiment output directories; do not overwrite evidence.

## Reference-only and Intel Mac

Torch is optional. Upstream [macOS x86_64 wheel deprecation](https://dev-discuss.pytorch.org/t/pytorch-macos-x86-builds-deprecation-starting-january-2024/1690) means current Torch installation cannot be assumed for every Mac. Install the original-R Python route without Torch:

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e '.[reference]'
Rscript scripts/setup_r.R
Rscript scripts/smoke_amelia.R
```

This requires R, Amelia 1.8.3 and jsonlite; it does not run Torch-dependent probes or the full Torch test suite. Use `amelia_reference()`; install the project R package only if R-side `amelia_compat()` is needed. Windows uses `.venv\Scripts\python.exe`.

`pip install '.[torch,reference]'` is suitable where supported Torch wheels exist. CPU/CUDA wheels should still be chosen explicitly. Top-level project import must not load Torch. A real x86_64 hosted runner passed isolated wheel[reference] installation, no-Torch fitting and the RDS downstream workflow at `ad9bed2`; [record](validation/2026-09-26-ci/intel-mac-reference.md). It does not validate Intel hybrid/Torch, MPS or interactive GUI.
