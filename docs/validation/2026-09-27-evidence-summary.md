# Evidence summary

[简体中文](2026-09-27-evidence-summary.zh-CN.md) · [Documentation](../README.md)

The project remains a **development snapshot**. GPU performance depends on the task and interface. Windows RTX 3080 benchmarks are complete for the specified continuous-data workloads, but full statistical acceptance remains unfinished. Colab experiments are paused. This summary incorporates published records without adding fits or simulations.

## Performance

All datasets contain 100,000 rows, with 10, 7 and 90 numeric columns respectively. Each configuration produces five imputations per call, with two warmups and five measured repetitions. Times are medians in seconds. Ratios compare the same host, implementation and precision; a value above one indicates faster GPU execution.

| Windows RTX 3080 dataset | R serial | R snow4 | Native CPU64 | Native CUDA64 | CPU64/CUDA64 | Hybrid CPU64 | Hybrid CUDA64 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Covertype | 15.280 | 8.340 | 5.484 | 4.955 | 1.107× | 16.670 | 17.790 |
| Household Power | 10.200 | 5.540 | 3.452 | 3.592 | 0.961× | 11.680 | 12.420 |
| Year Prediction MSD | 230.560 | 121.730 | 32.979 | 22.115 | 1.491× | 110.620 | 101.640 |

For Year, native CUDA64/32 gained 1.49×/1.31× over native CPU, and hybrid gained 1.09×/1.05× over hybrid CPU. Native's 10.43×/11.44× difference from serial R includes implementation, library and workflow differences. Native supports fewer options than the hybrid. Narrow tasks mostly showed little gain or a slowdown. All 30 Windows configurations, 210 calls and 1,050 imputations are recorded in the [Windows report](2026-09-27-windows-rtx3080/README.md).

| Linux T4 dataset | Native CPU64 | Native CUDA64 | CPU64/CUDA64 | Hybrid CPU64 | Hybrid CUDA64 |
|---|---:|---:|---:|---:|---:|
| Covertype | 9.870 | 6.172 | 1.599× | 32.198 | 24.776 |
| Household Power | 5.592 | 4.616 | 1.212× | 21.808 | 16.782 |
| Year Prediction MSD | 80.326 | 42.049 | 1.910× | 250.898 | 178.274 |

The [T4 native suite](2026-09-26-colab-native/README.md) completed 18 configurations, 126 calls and 630 imputations. Native float32 ratios were 1.645×, 1.760× and 1.754×. The host budget was two CPU threads; original R snow2 used two workers with one BLAS thread each.

The [T4 hybrid record](2026-09-26-colab-hybrid-partial/README.md) contains only eleven of twelve configurations: 77 calls and 385 imputations. Five recovered same-precision CPU/CUDA pairs gained 1.281–1.407×, but **all five CUDA configurations were slower than original R snow2**. Year CUDA32 is unknown. The full suite, process exit codes and source checks were lost; this is a limited report audit, not a passed complete suite.

| M4 Mac dataset | Native CPU32 | Native MPS32 | Hybrid CPU32 | Hybrid MPS32 |
|---|---:|---:|---:|---:|
| Covertype | 1.895 | 3.225 | 7.960 | 10.550 |
| Household Power | 1.478 | 2.232 | 5.185 | 6.374 |
| Year Prediction MSD | 12.089 | 20.267 | 66.934 | 75.901 |

On these Mac tasks, MPS was about 51–70% slower for native and 13–33% slower for hybrid than CPU32. MPS requires explicit float32 selection; it cannot replace default float64. See the [Mac report](2026-09-23-development/README.md).

## Scope of comparison

Inputs were sampled from complete source rows and masked with block MCAR: 30%/28.57%/30% missingness and 8/7/8 patterns. These are neither full-source workloads nor independent-cell MCAR/MAR experiments. Three datasets with the same row count and different contents do not establish a general scaling law. Full compressed source archives total about 232 MiB; attribution, hashes, licensed samples and download scripts are provided in the [dataset guide](../datasets.md).

Five-repeat IQRs describe dispersion, not confidence intervals for speed differences. Timings include the documented transfers and outputs; R hybrid also includes the bridge and retained R stages. No profiling isolates communication cost. Cross-host RTX 3080/T4 or Mac/CUDA time ratios confound CPUs, thread budgets, operating systems, software and source versions. Recorded Torch allocation peaks are not total VRAM or host RAM.

## Numerical and statistical validation

| Evidence | Recorded result | Remaining scope |
|---|---|---|
| Windows/macOS/Linux CPU CI at ef729c0 | Per platform: 307 Python tests, nine R files and a downstream example passed. | CPU CI does not establish GPU or all system combinations. |
| Fixed CUDA cases | T4 completed its original fifteen-stage verification; RTX 3080 passed native and R hybrid cases in both precisions. | Later CUDA edge cases and formal G5 remain incomplete. |
| Installed Mac RStudio workflow | Reference/hybrid CPU64, RDS/CSV, Data Viewer and diagnostic plots passed. | Original AmeliaView remains unvalidated. |
| Mac G5, five routes | 2,100 calls and 10,500 fits completed; MAR and bounded stress criteria passed. | Prespecified MCAR criteria did not all pass. |
| Replacement Colab VM | Second validation attempt: 306 Python tests passed, one failed. | Stopped before nine R files, later CUDA edge cases and G5. |

Windows hybrid/reference paired summaries showed maximum relative differences of about 0.059% in normalized heldout RMSE, 0.95% in covariance and 3.05% in Rubin between-imputation variance, with up to seven iterations' difference. There was no prespecified equivalence threshold or full-matrix comparison. Native uses a different random stream from R.

For saved Mac CPU32/MPS32 outputs, Covertype's maximum imputed-cell difference reached **0.173 truth-column standard deviations**. This comparison covers the first 1,000 rows of the first measured call and establishes neither a general error bound nor its cause. See the [saved-output comparison](2026-09-26-native-parameter-comparison/README.md).

In Mac G5, original R and hybrid MCAR coverage was 195/200 (97.5%). The upper end of its prespecified 90% Monte Carlo interval, 99.009876%, exceeded the 99% limit. Native coverage was 192/200 (96%); its paired difference interval versus R extended to −5.028703 percentage points, beyond the −5 limit. CPU and MPS classifications agreed. These results neither pass all criteria nor establish a GPU-specific defect. Thresholds remain unchanged. See the [G5 report](2026-09-26-g5-mps/README.md) and [frozen protocol](g5-prespecified/README.md).

## Release status

Available evidence covers three Python/R interfaces, pinned original semantics, cross-platform CPU installation, an installed RStudio workflow, public-data benchmarks, same-host GPU gains and slowdowns, and retained statistical failures. The project is not yet a fully accepted replacement for Amelia and is not published on PyPI or CRAN.

The [replacement Colab record](2026-09-27-colab-recovery/README.md) retains R/library conflicts, Ruff-version differences and a temporary environment's missing NumPy dependency. Its seven checkpoints and 54 text records document recovery attempts, not completed acceptance. Cloud installation guards and dependency inheritance require validation before further cloud work. The additional 1,000-replicate MCAR design remains a [separate unexecuted proposal](g5-mcar-followup-proposed.md). Any future measurement must retain independent provenance rather than fill gaps in an old session.
