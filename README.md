# amelia-torch

An **unofficial, experimental** Python/PyTorch implementation of Amelia's bootstrap–EM multiple imputation, with Python and R interfaces and reproducible CPU/GPU experiments.

**Development snapshot — not the first complete release.** The target is the full statistical workflow of **Amelia 1.8.3**. Advanced compatibility currently uses an explicitly labeled R dependency. CPU float64 is the default; GPU acceleration is a question tested by this project, not a promised result.

[![CPU checks](https://github.com/Tocqueville0624/amelia-torch/actions/workflows/tests.yml/badge.svg)](https://github.com/Tocqueville0624/amelia-torch/actions/workflows/tests.yml)

[中文研究与结果](docs/validation/2026-09-23-development/README.md) · [Installation](docs/setup.zh-CN.md) · [Compatibility matrix](docs/amelia-compatibility.md) · [Algorithm contract](docs/algorithm-contract.md)

## Choose an execution path

| Path | Python | R | Computation and current scope |
|---|---|---|---|
| Original reference | `amelia_reference()` | `amelia_compat()` | Unmodified R Amelia 1.8.3 on CPU; PyTorch is not required |
| Experimental compatibility | `amelia_torch_compat()` | `amelia_torch_compat()` | Original R preprocessing, bootstrap, random draws and postprocessing; PyTorch EM on the explicitly selected device |
| Native continuous prototype | `amelia()` | `amelia_torch()` | Python/PyTorch continuous numeric EMB; unsupported advanced options raise errors |

The compatibility engine preserves official R result objects; the native engine has its own result structure. Hybrid replicate scheduling is currently serial. Original parallel execution remains available through the reference path. See the matrix for tested cases and unverified boundaries; delegation to R does not prove complete compatibility.

## Install from this repository

Use Python 3.12 and R with Amelia **1.8.3**. Create a virtual environment first. On supported platforms, install the appropriate CPU or CUDA PyTorch wheel using the [official selector](https://pytorch.org/get-started/locally/), then:

```sh
python -m pip install -e '.[reference]'
Rscript scripts/setup_r.R
R CMD INSTALL --library=.R-library r-package
```

For development tests, install `'.[dev,reference]'`. Apple Silicon users can install `'.[torch,reference]'`; MPS requires explicit float32. Building the R package from source requires a C compiler (Xcode command-line tools on macOS, Rtools on Windows). The original Python-to-R reference path does not require this R package or PyTorch. Intel Mac and CUDA installations still need platform verification. Nothing has been published to PyPI or CRAN.

The project-local R library is selected explicitly in the examples. See [setup instructions](docs/setup.zh-CN.md) for `uv`, Windows, dependency snapshots, and GPU probes.

## Python

```python
import numpy as np
from amelia_torch import amelia_torch_compat

x = np.random.default_rng(42).normal(size=(300, 4))
x[::5, 1] = np.nan
fit = amelia_torch_compat(x, m=5, seed=42, r_library=".R-library")  # CPU float64
completed = fit.imputations[0]
fit.save_rds("fit.rds")  # Open the original result with readRDS() in R
```

Pandas data frames preserve supported numeric, logical, string and categorical types through a binary bridge. Use original Amelia option names and **1-based R indices**; names such as `boot.type` can be passed with `**{"boot.type": "none"}`. Examples, RDS round trips and limitations are in the [Python bridge guide](docs/python-reference-bridge.md).

For the continuous native path without R:

```python
from amelia_torch import amelia
fit = amelia(x, m=5, seed=42)
completed = fit["imputations"][0]
```

## R / RStudio

Start a fresh R session in the repository root:

```r
.libPaths(c(file.path(getwd(), ".R-library"), .libPaths()))
library(ameliatorch)
use_amelia_python(venv = ".venv")
set.seed(42)
x <- data.frame(a = rnorm(300), b = rnorm(300), c = rnorm(300))
x$b[seq(1, 300, 5)] <- NA_real_
fit <- amelia_torch_compat(x, m = 5, p2s = 0)  # CPU float64
summary(fit)
Amelia::compare.density(fit, var = "b")
```

Explicit accelerators use `device="cuda", dtype="float64"` or `device="mps", dtype="float32"` in either language. CUDA remains untested on the target RTX 3080. MPS eigenvalue checks run explicitly on CPU; original R workflow steps also remain on CPU in the hybrid path. There is no silent precision downgrade or automatic GPU-to-CPU fallback. [R interface guide](docs/r-interface.md).

## Measured results

On this M4/16 GB Mac, three public datasets were evaluated at **100,000 rows each**, with 5 imputations, 2 warmups and 5 measured repetitions. Median seconds for the native Python route:

| Dataset | R serial | R ×4 | Torch CPU64 | Torch MPS32 |
|---|---:|---:|---:|---:|
| Covertype, 10 variables | 8.489 | 4.357 | 2.126 | 3.225 |
| Household Power, 7 variables | 5.490 | 2.885 | 1.552 | 2.232 |
| Year Prediction MSD, 90 variables | 194.947 | 121.373 | 13.744 | 20.267 |

**MPS was slower than Torch CPU on these tasks.** The speed difference from the local R baseline combines implementation and numerical-library effects; it is not evidence of GPU speedup. The table includes native preprocessing, bootstrap, imputation and transfers, but excludes R-to-Python calling overhead. [View the timing chart](docs/validation/2026-09-23-development/native-timings.png). Full repetitions, quality gates, source snapshots and limitations are in the [validation report](docs/validation/2026-09-23-development/README.md).

A separate, specified joint-normal simulation completed 400 independent datasets / 2,000 EM fits. CPU64 Rubin-pooled 95% coverage was 96% under MCAR and 97% under MAR; Monte Carlo uncertainty and model limitations are reported. This does not establish validity for arbitrary data or full cross-language distributional equivalence.

## Reproduce and contribute

```sh
python -m pytest -q
python -m ruff check src tests scripts
python scripts/download_datasets.py --datasets all --max-download-mib 300
```

[Full reproduction commands](docs/reproduce.zh-CN.md) cover preparation, R reference fixtures, accelerator checks, timing and inference. The repository includes licensed small samples, data attribution, checksums and complete download scripts. Full raw archives (about 232 MiB) stay outside Git. [Dataset documentation](docs/datasets.zh-CN.md).

Windows, macOS and Linux hosted CPU checks have passed for the development code, including Python and five R integration test files. They do not validate CUDA/MPS performance or every operating-system configuration. [CI evidence](docs/validation/2026-09-23-development/cross-platform-ci.md).

Amelia's documented and observed semantics, including upstream edge cases, take precedence over convenient rewrites. Entirely missing analysis rows remain missing. A known Amelia 1.8.3 single-row-prior indexing defect is explicitly documented, rather than silently changed. Read the [contract](docs/algorithm-contract.md), [roadmap](docs/roadmap.zh-CN.md), [first-release gates](docs/release-gates.md), [contributor guide](CONTRIBUTING.md) and [agent instructions](AGENTS.md).

GPL-3.0-only. Maintainer: **Sheng Wan**. Original Amelia authors and data sources are credited in [THIRD_PARTY.md](THIRD_PARTY.md) and [CITATION.cff](CITATION.cff). This project is not affiliated with or endorsed by the Amelia authors.
