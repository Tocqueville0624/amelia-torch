# amelia-torch

[简体中文](README.zh-CN.md) · [Documentation](docs/README.md)

Multiple imputation with Amelia's bootstrap–EM method, available from Python and R, with an experimental PyTorch CPU/GPU backend.

**Development snapshot.** This unofficial project targets the complete workflow of **Amelia 1.8.3**. The native implementation currently supports continuous numeric data; advanced options use an explicitly identified R compatibility route. Full statistical acceptance is pending. It is not published on PyPI or CRAN.

[![CPU checks](https://github.com/Tocqueville0624/amelia-torch/actions/workflows/tests.yml/badge.svg)](https://github.com/Tocqueville0624/amelia-torch/actions/workflows/tests.yml)

## Documentation

| Need | Guide |
|---|---|
| Install on Mac, Windows or Linux | [Installation](docs/setup.md) |
| Impute data and return results to R | [R interface](docs/r-interface.md) · [Python bridge](docs/python-reference-bridge.md) |
| Choose a supported workflow | [Compatibility](docs/amelia-compatibility.md) · [Examples](examples/README.md) |
| Understand the method and project contribution | [Walkthrough](docs/project-walkthrough.md) · [Architecture](docs/architecture.md) |
| Assess the evidence | [Results summary](docs/validation/2026-09-27-evidence-summary.md) · [Release criteria](docs/release-gates.md) |
| Reproduce or contribute | [Reproduction](docs/reproduce.md) · [Contributing](CONTRIBUTING.md) · [All documents](docs/README.md) |

## Contributions

Multiple imputation produces several completed datasets so downstream analyses can account for missing-data uncertainty. This project examines whether the same statistical workflow can run faster with tensor libraries and GPUs, while remaining usable across Python and R.

The contribution is an implementation and evaluation of an existing method: a PyTorch EM backend, typed Python/R exchange, reference comparisons, and reproducible experiments on three public datasets. It does not introduce a new imputation estimator. The benchmark datasets are computational workloads, not representative social-science samples.

## Interfaces

| Route | Python | R | Scope |
|---|---|---|---|
| Original reference | `amelia_reference()` | `amelia_compat()` | Unmodified R Amelia 1.8.3 on CPU; no PyTorch required |
| Hybrid compatibility | `amelia_torch_compat()` | `amelia_torch_compat()` | Original R preparation, bootstrap, draws and output; PyTorch replaces EM |
| Native continuous | `amelia()` | `amelia_torch()` | Continuous numeric EMB; unsupported advanced options raise errors |

CPU float64 is the default. CUDA float64/float32 and MPS float32 require explicit selection. Hybrid replicates are scheduled serially; the reference route retains original R parallel execution. Compatibility routes retain official R result objects; native results use a separate structure. Review the [compatibility matrix](docs/amelia-compatibility.md) before selecting a route.

## Installation and usage

Clone the repository and create a Python 3.12 virtual environment:

```sh
git clone https://github.com/Tocqueville0624/amelia-torch.git
cd amelia-torch
python3.12 -m venv .venv
source .venv/bin/activate
```

On Windows, replace the last two commands with `py -3.12 -m venv .venv` and `.venv\Scripts\Activate.ps1` in PowerShell. Native and hybrid routes also require a compatible PyTorch installation; choose its CPU/CUDA wheel using the [official installation selector](https://pytorch.org/get-started/locally/). The reference route can run without Torch. For R-backed routes:

```sh
python -m pip install -e '.[reference]'
Rscript scripts/setup_r.R
R CMD INSTALL --library=.R-library r-package
```

The last command builds the R interface and requires a C toolchain. The Python reference route does not require that interface package. Platform-specific setup, including a reference-only Intel Mac route, is in the [installation guide](docs/setup.md).

Python, after installing the hybrid dependencies:

```python
import numpy as np
from amelia_torch import amelia_torch_compat

x = np.random.default_rng(42).normal(size=(300, 4))
x[::5, 1] = np.nan
fit = amelia_torch_compat(x, m=5, seed=42, r_library=".R-library")
completed = fit.imputations[0]
fit.save_rds("fit.rds")
```

R/RStudio, in a fresh session at the repository root:

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

Both examples use CPU float64. An explicit accelerator uses `device="cuda", dtype="float64"` or `device="mps", dtype="float32"`. Retain **all** imputations for downstream pooling. A [copyable R workflow prompt](docs/r-user-agent-prompt.md) helps specify data, model, privacy and output requirements before using a coding assistant.

## Results

On Windows 11 with an RTX 3080, each of three datasets used 100,000 rows and five imputations per call. Medians below use five measured repetitions after two warmups, with a four-thread CPU budget and four single-threaded R workers.

| Dataset | R serial | R ×4 | Native CPU64 | Native CUDA64 | Hybrid CPU64 | Hybrid CUDA64 |
|---|---:|---:|---:|---:|---:|---:|
| Covertype, 10 columns | 15.280 s | 8.340 s | 5.484 s | 4.955 s | 16.670 s | 17.790 s |
| Household Power, 7 columns | 10.200 s | 5.540 s | 3.452 s | 3.592 s | 11.680 s | 12.420 s |
| Year Prediction MSD, 90 columns | 230.560 s | 121.730 s | 32.979 s | 22.115 s | 110.620 s | 101.640 s |

For the 90-column task, native CUDA64 was **1.49× faster than native CPU64**, and **10.43× faster than serial R**. The latter includes implementation and workflow differences; native supports fewer features. The complete R hybrid route gained **1.09×** over hybrid CPU64. Narrower tasks showed little GPU benefit or a slowdown. These results do not establish that Python or GPUs are always faster. [Windows report: float32 results, all repetitions, quality checks and source hashes](docs/validation/2026-09-27-windows-rtx3080/README.md).

Separate Linux T4 measurements found native CUDA64 gains of 1.21–1.91× over same-host CPU64. The recovered T4 hybrid records cover only 11/12 configurations, and all five retained CUDA configurations were slower than original R snow2. On the tested M4 Mac, MPS was slower than same-precision CPU. Cross-host timings are not controlled GPU comparisons. [Evidence summary](docs/validation/2026-09-27-evidence-summary.md).

## Validation and limitations

- Windows recorded 210 calls and 1,050 imputations with convergence, observed-value preservation and complete-heldout checks passing. Fixed CUDA cases passed on Windows RTX 3080 and Linux T4. These checks do not establish full distributional equivalence.
- Hosted CPU checks at `ef729c0` passed on Windows, macOS and Linux: 307 Python tests, nine R test files and a downstream example per platform. Intel Mac separately passed a reference-only installation without Torch. A Mac RStudio workflow was also exercised.
- The prespecified Mac inference study completed 10,500 fits. MAR and bounded stress checks passed; **MCAR statistical criteria did not all pass**, including one criterion for original R. CUDA inference acceptance remains unfinished. Thresholds and negative results are retained.
- Native advanced features, broader missingness patterns, full-source-data workloads, memory limits and some GUI/platform combinations remain outside the validated scope. The [release criteria](docs/release-gates.md) distinguish these gaps from completed checks.

The repository supplies attributed samples, checksums, download scripts and raw benchmark records. Full UCI archives total about 232 MiB and remain outside Git. [Data and licenses](docs/datasets.md). Colab experiments are paused; CUDA statistical acceptance remains pending.

## License and attribution

GPL-3.0-only. Maintainer: **Sheng Wan**. Amelia's method and original implementation are credited to **James Honaker, Gary King and Matthew Blackwell**. Dataset licenses remain separate. See [third-party attribution](THIRD_PARTY.md), [contributors](CONTRIBUTORS.md) and [citation metadata](CITATION.cff). This project is not affiliated with or endorsed by the Amelia authors.
