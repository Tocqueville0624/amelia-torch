# Windows RTX 3080 benchmarks

[简体中文](README.zh-CN.md) · [Documentation](../../README.md)

Original measurement IDs are retained; source links now resolve to migrated commits with identical file trees. See the [revision map](../../history/README.md).

On the 100,000-row, 90-column task, native CUDA64 took **22.115 seconds**, compared with **230.560 seconds for serial R** and **32.979 seconds for native CPU64**. The same-implementation GPU gain was 1.49×; the 10.43× difference from R also includes implementation and workflow differences. Full R hybrid CUDA64 took 101.640 seconds, a 1.09× gain over hybrid CPU64. Narrower tasks mostly showed little GPU benefit or a slowdown.

The Windows 11 / RTX 3080 experiment on 2026-09-27 UTC completed all 18 native/reference and 12 hybrid configurations. Independent convergence, observed-value and complete-heldout checks passed for all **210 calls and 1,050 imputations**: 150 measured calls and 60 warmups. All results are retained.

Measured source: [`810591e6a77956a49dfef5de1d4a2274fefe9e07`](https://github.com/Tocqueville0624/amelia-torch/tree/6476292d998185e6433e62dd2dff9a4c35afd837). These Windows measurements are independent of the incomplete Colab records and do not complete G5 inference acceptance.

## Performance comparison

Native PyTorch had the lowest overall times on these continuous-data tasks. The language itself was not isolated as a cause: implementations, libraries, random streams and supported workflows differ. Native does not yet support all of Amelia's categorical, transformation, bounds and panel options; required statistical features determine the appropriate route.

For the 90-column task, native CUDA64/32 took 22.115/20.160 seconds: 10.43×/11.44× faster than serial R and 5.50×/6.04× faster than four-worker R. Against the same-precision native CPU route, the gains were 1.49×/1.31×. Full R hybrid CUDA64/32 took 101.640/100.340 seconds, giving gains of 1.09×/1.05× over hybrid CPU and 1.20×/1.21× over R snow4.

The hybrid retains R preparation, bootstrap, draws and postprocessing, with bridge/transfer costs and serial replicate scheduling. Subtracting native time from hybrid time does not measure communication time. CUDA on the 7–10-column tasks was usually similar to or slower than the matching CPU route. Overhead, transfer, synchronization and small-matrix scheduling are possible explanations, but no stage-level profiling was performed. All datasets have 100,000 rows and differ in content, columns and patterns; this is not a controlled scaling experiment.

## Cross-host records

| Native CUDA route | Windows RTX 3080 host | Linux T4 host | T4 / RTX host time |
|---|---:|---:|---:|
| Year Prediction MSD, float64 | 22.115 s | 42.049 s | 1.90× |
| Year Prediction MSD, float32 | 20.160 s | 37.364 s | 1.85× |

The RTX 3080 host was faster on this task. This is not an isolated GPU hardware comparison: its Ryzen 5 5600X, four-thread budget, Windows, Torch 2.14.0/CUDA13.2 and source revision differ from the shared two-thread Xeon Colab host, Linux and Torch 2.10.0/CUDA 12.8. Native CUDA still performs CPU work. The larger gap from original R likewise cannot establish a 3080/T4 hardware ratio. See [T4 records](../2026-09-26-colab-native/README.md).

## Timings

Each call produced m=5 imputations. Values are median seconds over five measured repetitions after two warmups. IQRs and individual times are in the JSON reports; IQRs are not confidence intervals.

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

| Dataset | Native CPU64/CUDA64 | Native CPU32/CUDA32 | Hybrid CPU64/CUDA64 | Hybrid CPU32/CUDA32 |
|---|---:|---:|---:|---:|
| Covertype, 10 variables | 1.107× | 0.962× | 0.937× | 0.961× |
| Household Power, 7 variables | 0.961× | 0.863× | 0.940× | 0.953× |
| Year Prediction MSD, 90 variables | 1.491× | 1.313× | 1.088× | 1.046× |

Ratios above one indicate faster CUDA on the same host, route and precision. No failed runs were discarded to select a successful subset.

## Inputs and environment

| Dataset | Input | Artificial missingness | Patterns |
|---|---:|---:|---:|
| UCI Covertype | 100,000 × 10 | 30% | 8 |
| UCI Household Power | 100,000 × 7 | 28.57% | 7 |
| UCI Year Prediction MSD | 100,000 × 90 | 30% | 8 |

Complete source rows were selected before block-MCAR masking, and routes reused the prepared inputs. These are neither full-source nor independent-cell MCAR/MAR experiments. Sources, CC BY 4.0 attribution, hashes and preparation rules are in the [dataset guide](../../datasets.md), [manifest](../../../data/manifest.json) and archived data directory.

- Hardware: AMD Ryzen 5 5600X, six cores and twelve logical threads; NVIDIA Ge Force RTX 3080, 10 GiB, driver 595.95. Windows 11 version 10.0.26200.
- Software: Python 3.12.14, PyTorch 2.14.0+cu132, NumPy 2.5.3, R 4.5.3 and Amelia 1.8.3. GPU and R bridge probes are archived.
- Budget: four Torch/BLAS threads; original R snow4 used four workers with one BLAS thread each. Hybrid imputations were scheduled serially.
- Settings: ordinary bootstrap, initial value 0, tolerance 1e-4, at most 300 iterations, no explicit empri, autopri=0.05. Measured seeds 20260923–20260927; warmup seeds 20360923–20360924. TF32 was disabled.

Native timing starts from in-memory input and ends with completed NumPy matrices on CPU. It includes preparation, bootstrap, EM, draws, transfers and synchronization, but no R/Python bridge. R timing ends with the full result; hybrid includes bridging and R stages, and snow4 includes worker creation/destruction. File reads, cold interpreter/package startup, scoring and report writes are excluded.

Each suite used a fixed randomized configuration order with sequential execution. Native/reference and hybrid batches ran at different times. System load and temperature were not fully isolated; no statistical test of timing differences was performed.

## Quality and limitations

Independent audits cover every warmup and measured call: configuration and seed schedules, success status, finite positive times, convergence, observed-value preservation and complete heldout scoring. The [native/reference](benchmark-summary.json) and [hybrid](hybrid-summary.json) audits passed. Three fixed native cases and three full R GPU cases per precision also passed; their records are archived under validation/.

The [paired summary](paired-reference.json) checked inputs, seeds and R RNG settings for all twelve hybrid configurations against serial R, across seven calls each. It imposed no numerical equivalence threshold and did not compare full imputation matrices elementwise. Maximum relative differences included about **0.059%** in normalized heldout RMSE, **0.95%** in covariance and **3.05%** in Rubin between-imputation variance. Some iteration counts differed by up to seven. These findings do not establish identical outputs. Native NumPy PCG64 draws cannot be paired with R using the same integer seed.

CUDA G5 inference simulations were not run. The previous Mac MCAR criteria remain not fully passed. Performance and fixed-case checks do not complete statistical acceptance. Total process RAM/VRAM peaks, broader missingness mechanisms, mixed data types, full-source workloads and memory-capacity limits remain unvalidated.

## Records and offline audit

[benchmark-records.tar.gz](benchmark-records.tar.gz) contains **43 JSON files**: thirty individual benchmark reports, two suite records, seven probes/fixed-case reports, a data manifest and three preparation records. Payload bytes are unchanged; archive names and owner/time metadata were normalized. It excludes installed environments, private-path logs, raw data, full completed matrices and parameter NPZ files. Parameter filenames in reports refer to files on the measurement host, not included archive members.

Archive size: **3,018,276 bytes**. SHA-256: `6e7c8c82c04315be26f175c95ec9dabcc872e78942bd4c4f38b1aec6855a798f`.

[archive-index.json](archive-index.json) identifies each payload and the three independent summaries. Original timing, source fingerprints, missing telemetry and limitations are retained. The main suite lacked per-process before/after source records and contemporaneous reference CSV hashes; the later hybrid suite recorded hashes for reused CSVs. Missing historical evidence has not been reconstructed as if contemporaneous.

From the repository root, extract and audit existing JSON without imputation:

```sh
python -m tarfile -e docs/validation/2026-09-27-windows-rtx3080/benchmark-records.tar.gz results/local/rtx3080-published
python scripts/summarize_benchmarks.py --input-dir results/local/rtx3080-published/native --output-dir results/local/rtx3080-published-native-audit --methods cpu64 cpu32 cuda64 cuda32 r_serial r_snow4
python scripts/summarize_hybrid.py --input-dir results/local/rtx3080-published/hybrid --output-dir results/local/rtx3080-published-hybrid-audit
python scripts/compare_hybrid_reference.py --reference-dir results/local/rtx3080-published/native --hybrid-dir results/local/rtx3080-published/hybrid --reference-methods cpu64 cpu32 cuda64 cuda32 r_serial r_snow4 --output results/local/rtx3080-published-paired.json
```

For a separately scheduled performance run, follow [installation](../../setup.md) and [reproduction](../../reproduce.md). Run `python scripts/run_benchmark_suite.py --gpu cuda --threads 4 --workers 4 --output-dir results/local/benchmarks/rtx3080-new-main`, then `python scripts/run_hybrid_suite.py --methods cpu64 cpu32 cuda64 cuda32 --threads 4 --csv-dir results/local/benchmarks/rtx3080-new-main/inputs --output-dir results/local/benchmarks/rtx3080-new-hybrid`. Keep both runs on the same host and environment, using new output directories that preserve historical measurements.
