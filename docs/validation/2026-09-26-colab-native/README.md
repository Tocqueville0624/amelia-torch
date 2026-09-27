# Linux T4 native benchmarks

[简体中文](README.zh-CN.md) · [Documentation](../../README.md)

On 2026-09-26, one Linux/Tesla T4 host completed 18 configurations, 126 calls and 630 imputations at `905cc79ce20e65fe5b673039d4e411db73cd7544`. All recorded convergence, observation and complete-heldout checks passed. These continuous low-pattern block-MCAR results do not certify the full R hybrid, Windows or inference acceptance.

## Timings

Median seconds of five measured m=5 calls after two warmups; IQR/raw repetitions are retained, not confidence intervals. No failed runs were discarded.

| Dataset | R serial | R snow2 | Native CPU64 | Native CPU32 | CUDA64 | CUDA32 |
|---|---:|---:|---:|---:|---:|---:|
| Covertype |23.016|20.827|9.870|9.296|6.172|5.650|
| Household Power |16.239|14.649|5.592|6.553|4.616|3.724|
| Year Prediction MSD |206.580|175.359|80.326|65.550|42.049|37.364|

CPU64/CUDA64 ratios: 1.599/1.212/1.910; CPU32/CUDA32: 1.645/1.760/1.754. Compare only same host, route and precision. R differences also include libraries/layout/workflow and R L'Ecuyer versus nativePCG64; equal seeds do not pair draws.

![T4 native timings and IQR](native-timings.png)

## Inputs and timing boundary

100k×10/7/90 inputs have 300k/200k/2.7 Mheldout, 30/28.57/30% missingness and 8/7/8 patterns, with no empty rows. Sampling seed 20260923 and block mask seed 20260924 follow complete-source-row selection. Household excludes 25,979 naturally empty rows; its actual mask is 2/7. Not full-source-data, independentMCAR or MAR.

Ordinary bootstrap, tolerance 1e−4, max 300, autopri=0.05, no initial empirical prior; measured seeds 20260923–27, warmup 20360923–24. Fixed randomized order ran serially. Native timing includes preparation, bootstrap, EM, draws, transfer/synchronization and CPU arrays; R includes full result and snow cluster setup/teardown. File reads, cold imports/startup, scoring and reports are excluded. No R/Python bridge is included in native.

## Environment and memory

Linux x86_64 kernel 6.6.122+, Xeon 2 GHz, two visible/affinity CPUs, 13,286,944 KiB RAM, Tesla T4 driver 580.82.07, CUDA 12.8, Python 3.12.13, Torch 2.10.0+cu128, NumPy 2.0.2, R 4.5.3/Amelia 1.8.3, TF32 off. Torch reports 15,637,086,208 GPU bytes; nvidia-smi 15,360 MiB. Native/serial budget 2 threads, snow2 workers×1BLAS thread; earlier setup's 4 thread suggestion was corrected before timing, not retroactively.

Peak Torch allocated bytes (64/32): Covertype 43,655,680/26,947,584; Household 33,933,312/21,924,864; Year 319,183,360/165,269,504. These active-tensor peaks are not totalVRAM, cache/context or host RAM; unmeasured totals remainnull. No OOM was recorded, not a capacity-limit test. CPU preparation/grouping remains.

## Audit and provenance

The audit covers 36 warmups+90 measured calls, 180+450 imputations (R 210, native 420). Native pseudoinverse/final empri counts were 0; original R does not expose them. R's 42 call warning lists were empty; native had logs but no separate per-call warning field. Mean normalizedRMSE was approximately 1.058/.999/1.085, not coverage/unbiasedness evidence.

The suite ran UTC 21:59:19–23:32:16, exit 0; this includes scheduling/preparation/scoring and is not a single-call time. Earlier correctness at fa08a52 and repaired ensurepip/Ruff installation are retained separately. Twelve native reports record clean 905cc79; nine suite source hashes match Git blobs. Missing historical predeclared-grid/per-process-before-after telemetry is not fabricated: audit-plan.json is a later explicit audit expectation.

Archive:65 payloads+manifest=66 files, including 18 reports, six R configs, suite, preparation, JSON/logs;1,068,401 bytes, SHA `b14f55dfb5e94e4121239de19bef96392cdd7cd4d12fd6b90c68184e75abb70e`. Payload hashes match originals; only container owner/time metadata were normalized. No raw/prepared arrays, RDS, environments or parameter NPZ are included. Parameter filenames do not prove a completed CPU/CUDA parameter comparison. CC BY 4.0 attribution is retained. Offline extraction/re-audit reproduced the summary byte-for-byte, without fitting; resource-and-count-audit supplements rather than rewrites originalJSON.

## Records

This report describes the dated run and measured source below. Later project status is recorded in the [evidence summary](../2026-09-27-evidence-summary.md).

[native-timings.png](native-timings.png) · [native-timings.pdf](native-timings.pdf) · [native-timings-plotted-data.csv](native-timings-plotted-data.csv) · [native-timings-metadata.json](native-timings-metadata.json) · [environment-summary.json](environment-summary.json) · [source-transition.json](source-transition.json) · [benchmark-summary.json](benchmark-summary.json) · [audit-plan.json](audit-plan.json) · [cloud-native-records.tar.gz](cloud-native-records.tar.gz) · [archive-index.json](archive-index.json) · [checkpoint-manifest.json](checkpoint-manifest.json) · [SHA256SUMS.json](SHA256SUMS.json) · [resource-and-count-audit.json](resource-and-count-audit.json) · [packaging-verification.json](packaging-verification.json)

```sh
mkdir -p results/local/colab-native-review
# Extract into a new directory; preserve previous results.
tar -xzf docs/validation/2026-09-26-colab-native/cloud-native-records.tar.gz \
  -C results/local/colab-native-review
.venv/bin/python scripts/summarize_benchmarks.py \
  --input-dir results/local/colab-native-review/results/local/cloud/native \
  --output-dir results/local/colab-native-review-audit \
  --methods r_serial r_snow2 cpu64 cpu32 cuda64 cuda32 --rows 100000
```
