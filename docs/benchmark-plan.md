# Validation and benchmark plan

[简体中文](benchmark-plan.zh-CN.md) · [Documentation](README.md)

This is the original research plan, not a completion checklist. [Evidence](validation/2026-09-27-evidence-summary.md) identifies executed Mac/T4/Windows workloads. The later frozen G5 protocol governs formal statistical criteria. Keep slow, failed and out-of-memory outcomes.

## Baselines

Compare original R Amelia 1.8.3 serial and PSOCK/snow parallel (float64), native Torch CPU64/32, CUDA64/32, and Mac MPS32. Match input, missingness mask, m, initialization convention, bootstrap, stopping rule and iteration budget. Align empri/autopri explicitly; distinguish matched-iteration kernel checks from convergence-driven full calls. Record BLAS, core counts, threads and workers, avoiding oversubscription. The planned parallel grid includes 1/2/4 and a reasonable upper worker count≤m; only executed configurations count as evidence. Prefer snow in RStudio.

## Correctness

1. Compare conditional mean/covariance, sufficient statistics, one EM step and final parameters to analytic cases and CPU64. Retain variance in second moments.
2. Compare original R on shared preparation, explicit bootstrap indices and initial theta. Equal seeds do not pair RNG libraries. Parameters must use the same transformed coordinates.
3. Draw on original inputs, retaining observed values and variation across imputations. Bitwise equality across backends is not required.
4. Assess MCAR and observed-variable MAR using mean/covariance, regression bias, pooled SE, 95% coverage, interval width and Monte Carlo uncertainty. RMSE/MAE are secondary; MNAR is a model-assumption stress case.
5. Cover complete data, empty columns/rows, constants, near-collinearity, p≥n, high missingness, bootstrap-empty columns, nonfinite values and iteration limits. Reject unsupported cases explicitly; preserve original all-missing-row behavior.

Initial suggested well-conditioned kernel tolerances were CPU64 atol 1e−8/rtol 1e−6 and float32 atol 1e−5/rtol 1e−4. They do not establish inference validity or guarantee ill-conditioned behavior. Changes need condition/size justification before viewing performance. At least 200 independent datasets formed the initial screen; 1,000 key coverage replicates were a suggestion, not an automatic budget or release requirement. Report Monte Carlo SE/intervals and prespecify equivalence margins; nonsignificance is not equivalence.

## Workload dimensions

The proposed staged grid covers n=1k/10k/100k, then 1M if memory permits; p=10/30/100; m=5/20 and possibly 50; missingness 10/30/50%; repeated/block/monotone and independent-cell patterns; well-conditioned and high-correlation inputs. Record pattern count K, group sizes and complete-row share. Real social-science workflows require separate licensing and domain validation; built-in Amelia examples are API examples, not GPU-scale workloads.

Memory estimates include input/output, masks, active replicates, sufficient statistics, group caches and workspace. Use bounded batches; retain OOM entries. This grid is not claimed to be fully executed.

## Timing

The primary measure is same-host full-call time from in-memory input to all m CPU/R-consumable results, including preparation, bootstrap, EM, draws, reconstruction and transfers. Add the R interface separately, including reticulate conversion. Distinguish cold process/import time from warm-session calls; do not compare GPU kernel time with full R calls.

Use two warmups and at least five timed repeats, fixed seeds and randomized/interleaved order. Report raw times, medians, IQR, per-imputation iterations and convergence. Data generation is outside algorithm timing but retains hashes and preparation time. Synchronize accelerators before starting/stopping timing. See [CUDA execution](https://docs.pytorch.org/docs/2.14/notes/cuda.html#asynchronous-execution) and [numerical precision](https://docs.pytorch.org/docs/2.14/notes/numerical_accuracy.html).

Stage profiling should cover preparation, grouping, EM, draws, bridge and transfers. Record drivers/runtime, TF32, fallback, dtype, batch size, memory and background load. Accuracy comparisons explicitly use IEEEFP 32; TF32/mixed precision require separate experiments. Unmeasured stages are not inferred by subtracting unrelated timings.

## Interpretation and records

Report correctness, inference, compatibility and speed separately. `speedup=baseline_full_call/candidate_full_call` must name the baseline. A suggested engineering target is≥1.5× versus a reasonable best CPU baseline; it is not a promised or retroactive statistical threshold. Include weak/negative cases and measured crossover ranges; outperforming Torch CPU does not imply outperforming parallel R.

Retain run IDs, UTC times, commit/dirty status, versions, OS/CPU/GPU/driver, data/config hashes, seeds, n/p/m/K, dtype, times, memory, convergence, quality and failures. Local large records use `results/local/`; publish reviewed portable evidence in `docs/validation/`, excluding private paths and device identifiers.
