# amelia-torch

[简体中文](README.zh-CN.md) · [Installation](docs/setup.md) · [Documentation](docs/README.md)

Multiple imputation for Python and R using Amelia 1.8.3's bootstrap expectation–maximization (EM) method, with a PyTorch backend for CPU and GPU computation. Multiple imputation creates several completed datasets so an analysis can account for uncertainty from missing values.

**Development version.** The native backend supports continuous numeric data. Advanced options use the original R Amelia workflow with either its original EM routine or the PyTorch replacement. Statistical validation is incomplete; the package is available from source, not PyPI or CRAN.

## Contributions

- A PyTorch implementation of Amelia's EM calculations, with comparisons against the fixed R reference version.
- Python and R interfaces that preserve data types and R result objects on compatibility routes.
- Reproducible CPU, NVIDIA CUDA and Apple MPS benchmarks on three public datasets, including slower configurations and incomplete validation results.

The project implements and evaluates an existing statistical method. The datasets measure computational performance; they are not representative social-science samples.

## Results

Windows 11, RTX 3080: each dataset used 100,000 rows and five imputations per call. Times are median seconds over five repetitions after two warmups. CPU methods used a four-thread budget; parallel R used four workers with one BLAS thread each. “64” denotes double precision.

| Dataset | R serial | R ×4 | Native CPU64 | Native CUDA64 | Hybrid CPU64 | Hybrid CUDA64 |
|---|---:|---:|---:|---:|---:|---:|
| Covertype, 10 columns | 15.280 s | 8.340 s | 5.484 s | 4.955 s | 16.670 s | 17.790 s |
| Household Power, 7 columns | 10.200 s | 5.540 s | 3.452 s | 3.592 s | 11.680 s | 12.420 s |
| Year Prediction MSD, 90 columns | 230.560 s | 121.730 s | 32.979 s | 22.115 s | 110.620 s | 101.640 s |

On the 90-column task, native CUDA64 was **1.49× faster than native CPU64** and 10.43× faster than serial R. The comparison with R also includes implementation and workflow differences: the native route supports fewer features. The R hybrid gained 1.09× over its CPU version. Several narrower tasks gained little or ran slower on GPU. [Windows methods and raw results](docs/validation/2026-09-27-windows-rtx3080/README.md).

Separate Linux T4 runs showed native CUDA64 gains of 1.21–1.91× over same-host CPU64. Its hybrid suite is incomplete, and every retained CUDA configuration was slower than parallel R. Apple MPS was slower than the matching CPU route on the tested M4. [Results across platforms](docs/validation/2026-09-27-evidence-summary.md).

## Interfaces

| Route | Python | R | Scope |
|---|---|---|---|
| Reference | `amelia_reference()` | `amelia_compat()` | Original R Amelia 1.8.3 on CPU; no PyTorch required |
| Hybrid | `amelia_torch_compat()` | `amelia_torch_compat()` | Original R preparation, bootstrap, draws and output; PyTorch replaces EM |
| Native | `amelia()` | `amelia_torch()` | Continuous numeric data; unsupported advanced options raise errors |

CPU float64 is the default. CUDA float64/float32 and MPS float32 must be selected explicitly. Hybrid imputations run sequentially; the reference route retains R's parallel options. Check the [compatibility matrix](docs/amelia-compatibility.md) for the variables and model options required by an analysis.

## Installation and usage

With Python 3.12 installed, clone the repository and create a virtual environment:

```sh
git clone https://github.com/Tocqueville0624/amelia-torch.git
cd amelia-torch
python3.12 -m venv .venv
source .venv/bin/activate
```

In Windows PowerShell, replace the final two commands with `py -3.12 -m venv .venv` and `.venv\Scripts\Activate.ps1`.

Native and hybrid routes require PyTorch; select a compatible CPU/CUDA installation using the [official selector](https://pytorch.org/get-started/locally/). R-backed routes also require R and Amelia 1.8.3. Install their project dependencies with:

```sh
python -m pip install -e '.[reference]'
Rscript scripts/setup_r.R
R CMD INSTALL --library=.R-library r-package
```

The final command builds the R interface and requires a C toolchain. Platform details, including reference-only installation without Torch, are in the [installation guide](docs/setup.md).

Python hybrid example, after installing these dependencies:

```python
import numpy as np
from amelia_torch import amelia_torch_compat

x = np.random.default_rng(42).normal(size=(300, 4))
x[::5, 1] = np.nan
fit = amelia_torch_compat(x, m=5, seed=42, r_library=".R-library")
completed = fit.imputations[0]
fit.save_rds("fit.rds")
```

R/RStudio example, in a fresh session at the repository root:

```r
.libPaths(c(file.path(getwd(), ".R-library"), .libPaths()))
library(ameliatorch)
use_amelia_python(venv = ".venv")
set.seed(42)
x <- data.frame(a = rnorm(300), b = rnorm(300), c = rnorm(300))
x$b[seq(1, 300, 5)] <- NA_real_
fit <- amelia_torch_compat(x, m = 5, p2s = 0)
summary(fit)
Amelia::compare.density(fit, var = "b")
```

Both examples use CPU float64. Select an accelerator with `device="cuda", dtype="float64"` or `device="mps", dtype="float32"`. Keep all imputed datasets for pooled inference. See [R usage](docs/r-interface.md), [Python/R exchange](docs/python-reference-bridge.md) and [examples](examples/README.md).

## Validation and limitations

Recorded checks cover Windows, macOS and Linux CPU installations, fixed CUDA cases, observed-value preservation and convergence. They do not establish full statistical equivalence.

The prespecified Mac inference study completed 10,500 fits. Missing-at-random (MAR) and bounded stress criteria passed; **missing-completely-at-random (MCAR) criteria did not all pass**, including a criterion for original R. CUDA inference validation remains incomplete. Broader missingness patterns, full-source workloads, memory limits and some platform combinations remain unverified. See the [validation summary](docs/validation/2026-09-27-evidence-summary.md) and [release criteria](docs/release-gates.md).

## Reproduction and attribution

The repository includes licensed samples, download scripts, checksums and raw benchmark records. Full UCI source archives total about 232 MiB and are downloaded separately. [Data](docs/datasets.md) · [Reproduction](docs/reproduce.md) · [History migration and revision map](docs/history/README.md) · [Contributing](CONTRIBUTING.md).

GPL-3.0-only. Maintainer: Sheng Wan. Amelia's method and original implementation are by James Honaker, Gary King and Matthew Blackwell. Dataset licenses apply separately. See [third-party attribution](THIRD_PARTY.md), [contributors](CONTRIBUTORS.md) and [citation metadata](CITATION.cff). This project is not affiliated with the Amelia authors.
