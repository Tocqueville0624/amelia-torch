# Linux T4: partial R hybrid benchmarks

[简体中文](README.zh-CN.md) · [Documentation](../../README.md)

**Eleven of twelve configurations were recovered.** The final Year Prediction MSD CUDA32 result is unknown. The 77 recorded calls and 385 imputations passed limited checks of convergence, devices and output completeness; this is not a verified complete suite. All five retained CUDA configurations were slower than original R snow2.

The Colab connection was lost around 01:47 UTC on 2026-09-27. A replacement session at approximately 01:51 UTC contained neither the project nor its variables or processes. The final visible output from the old session was Year CUDA32 starting. These observations establish neither the last result nor its exact termination time. See [interruption observations](interruption-observation.json).

## Timings

Seconds are medians of five measured calls, each producing five imputations, after two warmups. Raw repetitions and IQRs are retained in the archive and [partial summary](partial-evidence-summary.json). IQRs are not confidence intervals. R baselines come from the earlier complete [native suite](../2026-09-26-colab-native/README.md) on the same original VM.

| Dataset | R serial | R snow2 | Hybrid CPU64 | Hybrid CPU32 | Hybrid CUDA64 | Hybrid CUDA32 |
|---|---:|---:|---:|---:|---:|---:|
| Covertype | 23.016 | 20.827 | 32.198 | 31.744 | 24.776 | 23.366 |
| Household Power | 16.239 | 14.649 | 21.808 | 19.630 | 16.782 | 15.323 |
| Year Prediction MSD | 206.580 | 175.359 | 250.898 | 231.786 | 178.274 | Unknown |

Same-precision CPU/CUDA median ratios were 1.300 and 1.359 for Covertype, 1.299 and 1.281 for Household, and 1.407 for Year float64. No Year float32 ratio can be calculated. Compared with serial R, Household CUDA32 and Year CUDA64 took 5.64074% and 13.70220% less time; the other three CUDA configurations took longer. All five were slower than R snow2. These comparisons include implementation and workflow differences, not an isolated hardware effect.

## Inputs and timing

The hybrid retains original R preparation, bootstrap, conditional draws and postprocessing; reticulate delegates EM to PyTorch. Timing includes these steps, transfer and return of the complete R result. Initial Python binding/imports, process startup, CSV reads, scoring and report writes are excluded. Continuous-session observations and recorded environments support the same-host comparison; baseline and hybrid batches ran at different times.

A read-only Colab file preview was used during Year CPU64 timing to preserve results. No concurrent fitting or source editing was recorded, but background load was not fully isolated. The lost suite prevents complete reconstruction of scheduling and per-process source checks.

Inputs were 100,000 × 10/7/90, sampled from complete source rows before block-MCAR masking. Heldout counts were 300,000/200,000/2,700,000, with 8/7/8 patterns and 30%/28.57%/30% missingness. They are subsets with few missingness patterns, not full-source, independent-cell MCAR or MAR experiments. Attribution and preparation metadata are in the native report and archived data manifest.

Each configuration used m=5, ordinary bootstrap, tolerance 1e-4, emburn=[0,300], autopri=0.05 and no initial empirical prior. Measured R seeds were 20260923–20260927; warmup seeds were 20360923–20360924. R used L'Ecuyer-CMRG / Inversion / Rejection. The host/Torch budget was two threads; hybrid used parallel=no, ncpus=1. R serial used two BLAS threads; snow used two workers with one BLAS thread each.

The original VM ran Linux x86_64, Tesla T4, Python 3.12.13, Torch 2.10.0+cu128, R 4.5.3, Amelia 1.8.3 and reticulate 1.47.0. Reports identify the actual device, precision, interpreter and thread counts; CUDA TF32 was disabled. CPU work remains part of the workflow. See the [environment record](../2026-09-26-colab-native/environment-summary.json).

## Quality and memory

The eleven reports contain 22 warmups and 55 measured calls: 110 and 275 imputations. Recorded checks found convergence, unchanged observations, finite required outputs and complete heldout scoring. Warning/error, pseudoinverse and positive final empirical-prior counts were zero. These findings say nothing about the unknown twelfth result. Report status=ok does not establish a subprocess exit code of zero.

Paired by R seed and phase with serial R, all 210 imputations in the six retained float64 configurations had matching iteration counts. Of 175 float32 imputations, 18 differed: Covertype CPU32/CUDA32 had 3/1 differences, Household had 7/7, and Year CPU32 had none. All retained fits still reported convergence.

The largest absolute paired difference in normalized heldout RMSE was about 7.0e-14 for float64 and 3.81e-5 for float32. These are descriptive JSON-summary comparisons. Complete random arrays, RNG states and imputed matrices were not retained, so they do not establish elementwise equality, statistical equivalence, unbiasedness or adequate Rubin coverage. G5 inference, new GPU edge cases and Windows validation require separate evidence.

| Dataset | CUDA64 peak allocated bytes | CUDA32 peak allocated bytes |
|---|---:|---:|
| Covertype | 41,645,056 | 25,941,504 |
| Household Power | 31,939,584 | 20,637,696 |
| Year Prediction MSD | 300,372,992 | Unknown |

Values are maxima of torch.cuda.max_memory_allocated across each configuration's seven calls. They exclude total process VRAM, reserved cache and host RAM. Unmeasured fields remain null. No retained report records OOM; the final unknown result prevents a suite-wide claim.

## Provenance and audit

Measured source: `905cc79ce20e65fe5b673039d4e411db73cd7544`. Sixteen source fingerprints agree across the reports and with the corresponding Git blobs. Installed R bridge fingerprints agree; NPZ/archive fingerprints match native preparation metadata, and CSV provenance is consistent within datasets. Actual CSVs were not recovered, and the original native suite did not record contemporaneous CSV hashes. These records do not replace missing per-process before/after evidence.

The [raw archive](hybrid-eleven-raw-reports.tar.gz) contains eleven unchanged JSON payloads: 3,789,799 uncompressed bytes, 1,504,792 archive bytes. SHA-256: `2f5f823929b476436452d52393c3025d13d5fb55e191388de2200ae146ebcbdc`. Only container metadata were normalized. The first ten reports came from a read-only preview bundle; Year CPU64 was backed up separately. The [collection manifest](collection-manifest.json) was assembled locally afterward, not captured as a cloud checkpoint. The [ten-report review](historical-ten-report-review.json), [Year CPU64 review](historical-year-cpu64-review.json) and [original manifest](original-ten-ui-copy-manifest.json) retain their historical provisional labels and original bytes.

The full suite, per-process exit codes, before/after source checks, configuration logs and final report remain missing. The complete-suite auditor was not bypassed. [verify_reports.py](verify_reports.py) instead produces a limited_recovered_report_audit_not_suite_audit covering the retained reports, hashes, backend/quality metadata, paired summaries and five ratios.

From the repository root, audit existing records without fitting:

```sh
.venv/bin/python docs/validation/2026-09-26-colab-hybrid-partial/verify_reports.py \
  --output results/local/hybrid-partial-recheck.json
```

The output path must be new. The script reads this package and the native archive; it explicitly reports complete suite NOT verified. An extracted archive can also be checked using --reports-dir. This round-trip check previously reproduced [partial-evidence-summary.json](partial-evidence-summary.json) byte-for-byte; see [packaging verification](packaging-verification.json).

[Privacy review](privacy-review.json) covers a limited set of path, host and credential patterns. [Checksums](SHA256SUMS.json) identify the published files. New measurements must retain their own runtime and provenance; they cannot complete this historical suite retroactively.
