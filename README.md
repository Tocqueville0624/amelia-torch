# amelia-torch

On a tested **100,000 × 90** dataset, native PyTorch on an RTX 3080 took **22.115 s**, versus **230.560 s** for serial R: **10.43× faster**. The GPU gain over the same native CPU64 path was **1.49×**. The full R hybrid CUDA64 path took **101.640 s**; narrower inputs showed little GPU benefit or a slowdown. [Measurements and limits](docs/validation/2026-09-27-windows-rtx3080/README.md).

An **unofficial, experimental** Python/PyTorch implementation of Amelia's bootstrap–EM multiple imputation, with Python and R interfaces and reproducible CPU/GPU experiments.

**Development snapshot — not the first complete release.** The target is the full statistical workflow of **Amelia 1.8.3**. Advanced compatibility currently uses an explicitly labeled R dependency. CPU float64 is the default; GPU acceleration is a question tested by this project, not a promised result.

[![CPU checks](https://github.com/Tocqueville0624/amelia-torch/actions/workflows/tests.yml/badge.svg)](https://github.com/Tocqueville0624/amelia-torch/actions/workflows/tests.yml)

[Initial results (Chinese)](docs/validation/2026-09-23-development/README.md) · [Project walkthrough (Chinese)](docs/project-walkthrough.zh-CN.md) · [Installation](docs/setup.zh-CN.md) · [Compatibility matrix](docs/amelia-compatibility.md) · [Algorithm contract](docs/algorithm-contract.md)

**Current evidence:** [Windows RTX 3080 report](docs/validation/2026-09-27-windows-rtx3080/README.md) · [Evidence summary (Chinese)](docs/validation/2026-09-27-evidence-summary.zh-CN.md). Local Windows testing resumed and completed all 30 benchmark configurations. Colab testing remains paused after quota exhaustion; full statistical acceptance is still pending.

## Why this project matters

Multiple imputation can become a bottleneck when an analysis needs many completed datasets or repeated runs under different modeling assumptions. amelia-torch explores whether tensor libraries and GPUs can reduce that cost while preserving Amelia 1.8.3's statistical workflow.

For academic researchers, especially social scientists, the goal is to make existing Amelia analyses easier to use across Python and R and, where possible, faster to repeat. That could lower the cost of sensitivity analyses and simulation studies. Preserving imputation uncertainty and the quality of downstream estimates is part of this goal. Faster execution is useful only when the results remain suitable for the research question.

For data practitioners in industry, the Python/R interfaces provide an experimental way to bring Amelia into analyses that span both languages. The public datasets, benchmark scripts and validation records also provide a starting point for evaluating whether a hardware change saves time in a team's own workflow. Small jobs may benefit little once setup and data transfers are included. [Amelia already supports CPU parallelism](https://search.r-project.org/CRAN/refmans/Amelia/html/amelia.html), so a useful accelerator needs to earn its place against that baseline.

The native continuous-data path was the fastest implementation family on the tested Windows inputs. On the 100,000 × 90 task, RTX 3080 CUDA64 took **22.115 seconds**, compared with **32.979 seconds** for native CPU64 and **230.560 seconds** for serial R. That is **1.49×** over the same native CPU path and **10.43×** over serial R; the latter also includes implementation and workflow differences. The complete R hybrid CUDA64 path took **101.640 seconds**, only **1.09×** faster than hybrid CPU64. Narrower Windows tasks showed little GPU benefit or a slowdown. The T4 and Mac results below retain their own host baselines; [full statistical acceptance remains pending](docs/release-gates.md).

Future GPU work should start by profiling complete imputation calls, then investigating avoidable data transfers and opportunities to batch matrix operations while preserving Amelia's statistical and random-number semantics. The practical target is less time spent waiting for a usable set of imputations, including the Python/R interface costs. Any improvement will need comparison with parallel Amelia on the same machine, along with checks on inference quality. Broader missingness patterns and real social-science workflows remain important areas for future validation. The Windows measurements below add performance evidence; broader inference and missingness studies remain unfinished, and Colab experiments remain paused.

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

For development tests, install `'.[dev,reference]'`. Apple Silicon users can install `'.[torch,reference]'`; MPS requires explicit float32. Building the R package from source requires a C compiler (Xcode command-line tools on macOS, Rtools on Windows). The original Python-to-R reference path does not require this R package or PyTorch. An isolated reference-only wheel installation has passed on Intel Mac; CUDA correctness has passed on a Linux Colab T4. Neither result establishes support for every platform configuration. Nothing has been published to PyPI or CRAN.

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

Explicit accelerators use `device="cuda", dtype="float64"` or `device="mps", dtype="float32"` in either language. Fixed CUDA cases have passed on Linux T4 and Windows RTX 3080; the Windows native/reference and hybrid benchmark suites are complete. These checks do not establish full statistical acceptance. MPS eigenvalue checks run explicitly on CPU; original R workflow steps also remain on CPU in the hybrid path. There is no silent precision downgrade or automatic GPU-to-CPU fallback. [R interface guide](docs/r-interface.md).

## Copyable prompt for R users

Copy this into your coding agent. It will ask for the data and analysis details before proceeding. Native Python currently supports a narrower workflow than original Amelia; using Python does not by itself guarantee a faster or equivalent analysis.

```text
I use R. Help me impute my data with https://github.com/Tocqueville0624/amelia-torch and return results I can use in R.

Before installing software or processing data, ask me to confirm:
- The dataset path, format and table/sheet; variables to impute, predictors, IDs/exclusions, variable types and missing-value codes.
- My downstream analysis and any categorical, transformation, bound, prior or panel/time-series requirements; ask for existing Amelia code if available.
- The number of imputations (m), seed, bootstrap method, convergence tolerance, iteration limits and regularization. Explain unfamiliar choices and suggest defaults for me to confirm.
- My OS, R/Python setup, GPU, memory/time budget, and whether installation or data upload is allowed.
- The output folder, R-readable formats and diagnostics I need.

Wait until the required details are clear. Read the repository's compatibility matrix and algorithm contract, then agree on the execution plan with me. Use native Python only when it supports my requirements; otherwise explain the reference/hybrid option. Do not drop options or change statistical assumptions to obtain a faster result. Default to CPU float64; confirm any GPU, lower-precision or trial-benchmark choice.

After agreement, create a reproducible script, run the imputations, and save every completed dataset with its row IDs and variable metadata. Preserve observed values and documented missing-row behavior; report convergence, warnings, failures and full-call elapsed time. Keep all imputations for downstream pooling. Provide R code to read and analyze them, and explain any remaining validation limits. Keep my data local unless I approve transfer.
```

## Measured results

A **Windows 11 / RTX 3080 10 GiB / Ryzen 5 5600X** run at `810591e` completed all 18 native/reference and 12 R hybrid configurations. Each dataset had 100,000 rows; each call produced five imputations, with two warmups and five measured repetitions. CPU/Torch used four threads; original R used four single-threaded workers. Median seconds:

| Dataset | R serial | R ×4 | Native CPU64 | Native CUDA64 | Native CPU32 | Native CUDA32 |
|---|---:|---:|---:|---:|---:|---:|
| Covertype, 10 variables | 15.280 | 8.340 | 5.484 | 4.955 | 4.715 | 4.900 |
| Household Power, 7 variables | 10.200 | 5.540 | 3.452 | 3.592 | 3.340 | 3.871 |
| Year Prediction MSD, 90 variables | 230.560 | 121.730 | 32.979 | 22.115 | 26.478 | 20.160 |

| Dataset | Hybrid CPU64 | Hybrid CUDA64 | Hybrid CPU32 | Hybrid CUDA32 |
|---|---:|---:|---:|---:|
| Covertype, 10 variables | 16.670 | 17.790 | 17.170 | 17.860 |
| Household Power, 7 variables | 11.680 | 12.420 | 11.390 | 11.950 |
| Year Prediction MSD, 90 variables | 110.620 | 101.640 | 104.920 | 100.340 |

On the 90-variable task, native CUDA64/CUDA32 were **10.43×/11.44× faster than serial R**, **5.50×/6.04× faster than R ×4**, and **1.49×/1.31× faster than same-precision native CPU**. Only the last comparison isolates the choice of CPU versus CUDA within the native implementation. Full R hybrid CUDA was **1.09×/1.05× faster than hybrid CPU** and **1.20×/1.21× faster than R ×4**. Native supports fewer Amelia features, so its time cannot stand in for a complete R workflow.

The narrow inputs had little CUDA benefit or a slowdown. Transfer, synchronization and small-operation overhead are plausible contributors, but no stage-level profiling was performed. All three inputs have the same row count; differing columns, values and missingness patterns prevent a general claim that more data always means more GPU benefit. The 90-variable CUDA64 run was about **1.90× faster on this 3080 host than on the earlier T4 host** (22.115 versus 42.049 seconds). Different CPUs, thread budgets, operating systems, software and revisions make that a cross-host observation, not a GPU hardware speed ratio.

All 210 calls / 1,050 imputations passed the recorded convergence, observed-value and complete-heldout checks. This does not establish elementwise equality or inference quality. [Full report, IQRs, paired discrepancies, source hashes and downloadable raw records](docs/validation/2026-09-27-windows-rtx3080/README.md).

On an M4/16 GB Mac, three public datasets were evaluated at **100,000 rows each**, with 5 imputations, 2 warmups and 5 measured repetitions. The R compatibility interface retains original R preprocessing, bootstrap, random draws and postprocessing; its measured calls include the R/Python bridge and device transfers. Median seconds:

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

A separate **Linux Colab T4** run at `905cc79`, with two CPU threads and two single-threaded R workers, completed all 18 native/reference configurations. Each used the same prepared 100,000-row input, five imputations, two warmups and five measured repetitions. Median seconds:

| Dataset | R serial | R ×2 | Native CPU64 | Native CUDA64 | Native CPU32 | Native CUDA32 |
|---|---:|---:|---:|---:|---:|---:|
| Covertype | 23.016 | 20.827 | 9.870 | 6.172 | 9.296 | 5.650 |
| Household power | 16.239 | 14.649 | 5.592 | 4.616 | 6.553 | 3.724 |
| YearPredictionMSD | 206.580 | 175.359 | 80.326 | 42.049 | 65.550 | 37.364 |

Native CUDA64 was **1.21–1.91× faster than same-machine native CPU64**; CUDA32 was 1.65–1.76× faster than CPU32. All 126 calls and 630 imputations passed the recorded convergence, observed-value and complete-heldout checks. These limited numerical checks are separate from statistical inference acceptance. The small shared-host CPU budget, block-MCAR tasks and selected numeric columns limit generalization; never compare this GPU's time with the Mac CPU time. [Full records and independent audit](docs/validation/2026-09-26-colab-native/README.md).

The subsequent R hybrid run lost its Colab runtime after **11 of 12 configurations had been backed up**. The recovered 77 calls / 385 imputations passed limited per-report checks; the last YearPredictionMSD CUDA32 outcome is unknown and the complete suite was not recovered. The five available same-precision hybrid CPU/CUDA pairs recorded ratios of 1.281–1.407×, but **all five CUDA configurations were slower than original R snow2**. Household CUDA32 and Year CUDA64 were faster than serial R. [Partial records, all timings and interruption limits](docs/validation/2026-09-26-colab-hybrid-partial/README.md). Measurements from a replacement runtime will not be spliced into this batch.

An [offline comparison of saved Mac CPU32/MPS32 outputs](docs/validation/2026-09-26-native-parameter-comparison/README.md) found differences, including a maximum of 0.173 truth-column standard deviations in the Covertype sample. Original-unit differences, all five imputation summaries and observed-value checks are retained. Only the first measured call's first 1,000 rows were saved; this description introduces no new equivalence threshold and does not attribute the cause.

With matched R RNG settings and seeds, hybrid CPU64 matched all 105 paired imputation iteration counts and closely matched the recorded numerical summaries. Float32 changed some iteration counts and summary values, including covariance entries. Full completed matrices were not retained, so this [paired summary comparison](docs/validation/2026-09-23-development/hybrid-reference-comparison.json) does not establish elementwise or bitwise equivalence. CPU64 remains the default.

A separate, specified joint-normal simulation completed 400 independent datasets / 2,000 EM fits. CPU64 Rubin-pooled 95% coverage was 96% under MCAR and 97% under MAR; Monte Carlo uncertainty and model limitations are reported. This does not establish validity for arbitrary data or full cross-language distributional equivalence.

The later [five-route Mac inference validation](docs/validation/2026-09-26-g5-mps/README.md) completed all 10,500 fits and passed its MAR and bounded stress checks. Its prespecified MCAR criteria did **not** all pass: original R and hybrid coverage intervals slightly exceeded one absolute bound, and native paired coverage intervals slightly exceeded another. CPU and MPS reached the same conclusions. The original thresholds and failed classifications are retained; successful fitting alone is not statistical acceptance.

## Reproduce and contribute

```sh
python -m pytest -q
python -m ruff check src tests scripts
python scripts/download_datasets.py --datasets all --max-download-mib 300
```

[Full reproduction commands](docs/reproduce.zh-CN.md) cover preparation, R reference fixtures, accelerator checks, timing and inference. The repository includes licensed small samples, data attribution, checksums and complete download scripts. Full raw archives (about 232 MiB) stay outside Git. [Dataset documentation](docs/datasets.zh-CN.md).

Windows, macOS and Linux hosted CPU checks passed at `ef729c0`, each with 307 Python tests, nine R test files and the downstream example. Intel Mac separately passed a reference-only wheel installation without Torch. The record identifies platform-specific branch coverage and explicitly excludes GPU validation. [CI evidence](docs/validation/2026-09-26-ci/cross-platform-ci-ef729c0.json).

An installed-package workflow also passed in an actual Mac RStudio session: reference/hybrid CPU64 imputation, interpreter selection, RDS/CSV readback, Data Viewer and a visible diagnostic plot. [RStudio evidence](docs/validation/2026-09-26-g6-rstudio/README.md). The separate original AmeliaView GUI remains untested pending XQuartz installation. [Audited Mac performance figures](docs/validation/2026-09-26-performance-figures/README.md) compare both product routes without treating CPU implementation gains as GPU gains.

The recorded Linux T4 session passed all 15 correctness-validation steps, including native and hybrid CUDA64/CUDA32 fixed cases; full structured reports are retained in the [CUDA record](docs/validation/2026-09-26-cuda/README.md). Its native/reference performance suite is complete and R hybrid evidence is partial as reported above. A replacement session stopped with 306 Python tests passing and one temporary-venv NumPy import failure, before the later R files, CUDA boundary cases or original seven-route inference study ran. Installation failures, repairs and the quota notice are retained in the [recovery record](docs/validation/2026-09-27-colab-recovery/README.md). Colab tests remain paused; the later Windows tests are recorded separately above. Fixed examples alone do not establish distributional quality or complete release acceptance.

The [Colab reproduction notebook](examples/colab_cuda_validation.ipynb) provides separate manual stages and recoverable reports. It has passed static and subprocess-interruption checks but has not itself completed an end-to-end Colab run. The attempted setup/validation stages exposed the environment issues recorded above; review them before reuse. Its pinned source is identified separately from historical measurements.

Amelia's documented and observed semantics, including upstream edge cases, take precedence over convenient rewrites. Entirely missing analysis rows remain missing. A known Amelia 1.8.3 single-row-prior indexing defect is explicitly documented, rather than silently changed. Read the [contract](docs/algorithm-contract.md), [roadmap](docs/roadmap.zh-CN.md), [first-release gates](docs/release-gates.md), [contributor guide](CONTRIBUTING.md) and [agent instructions](AGENTS.md).

GPL-3.0-only. Maintainer: **Sheng Wan**. Original Amelia authors and data sources are credited in [THIRD_PARTY.md](THIRD_PARTY.md) and [CITATION.cff](CITATION.cff). This project is not affiliated with or endorsed by the Amelia authors.
