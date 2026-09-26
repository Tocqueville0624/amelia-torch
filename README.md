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

On this M4/16 GB Mac, three public datasets were evaluated at **100,000 rows each**, with 5 imputations, 2 warmups and 5 measured repetitions. The R compatibility interface retains original R preprocessing, bootstrap, random draws and postprocessing; its measured calls include the R/Python bridge and device transfers. Median seconds:

| Dataset | R serial | R ×4 | R + Torch CPU64 | R + Torch CPU32 | R + Torch MPS32 |
|---|---:|---:|---:|---:|---:|
| Covertype, 10 variables | 8.489 | 4.357 | 7.909 | 7.960 | 10.550 |
| Household Power, 7 variables | 5.490 | 2.885 | 5.288 | 5.185 | 6.374 |
| Year Prediction MSD, 90 variables | 194.947 | 121.373 | 70.422 | 66.934 | 75.901 |

The default hybrid CPU64 route recorded a 70.422-second median on the 90-variable task, compared with 194.947 seconds for serial R and 121.373 seconds for R ×4. Its two low-dimensional medians were close to serial R and slower than R ×4. **Hybrid MPS32 was 13%–33% slower than hybrid CPU32.** The reference and hybrid suites ran in separate batches; initial imports and cold startup were excluded, and background load was not fully isolated. These are measured development results, not a universal speed guarantee.

The separate native Python route had these medians; it omits the R/Python bridge and supports a narrower continuous-data workflow:

| Dataset | Native CPU64 | Native CPU32 | Native MPS32 |
|---|---:|---:|---:|
| Covertype | 2.126 | 1.895 | 3.225 |
| Household Power | 1.552 | 1.478 | 2.232 |
| Year Prediction MSD | 13.744 | 12.089 | 20.267 |

MPS was also slower than native CPU on these tasks. Differences from R combine implementation, numerical-library and workflow costs; native timings cannot stand in for the R product interface. [Combined timing chart](docs/validation/2026-09-23-development/combined-timings.png) · [Validation report, IQRs and source snapshots](docs/validation/2026-09-23-development/README.md).

With matched R RNG settings and seeds, hybrid CPU64 matched all 105 paired imputation iteration counts and closely matched the recorded numerical summaries. Float32 changed some iteration counts and summary values, including covariance entries. Full completed matrices were not retained, so this [paired summary comparison](docs/validation/2026-09-23-development/hybrid-reference-comparison.json) does not establish elementwise or bitwise equivalence. CPU64 remains the default.

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
