# Saved Mac CPU32/MPS32 output comparison

[简体中文](README.zh-CN.md) · [Documentation](../../README.md)

Offline comparison of retained Mac native artifacts, without refitting, retiming or a new acceptance threshold. All 15 original configurations and nine native NPZ files were audited before comparing three same-precision CPU32/MPS32 pairs. Every compared observed value matched the prepared input exactly; imputed values did not match elementwise.

Scope is five theta matrices and the first 1,000 restored rows of the **first measured repeat**, seed 20260923, n=100k/m=5. This prefix is neither a new random audit sample nor the first 1,000 source UCI rows. Remaining 99k rows and other repetitions' full matrices were not saved. NPZ float64 storage does not change the recorded float32 computation. Input hashes, suite, precision, PCG64, standardization/order and bootstrap-attempt counts were checked. Actual bootstrap indices/normal arrays were not retained, and filename/runner conventions—not runtime parameter hashes—link NPZ to repeats. Current hashes do not independently prove historical binding.

| Dataset | Maximum original-unit difference | Maximum difference/truth SD | Per-imputation RMS/truth SD range |
|---|---:|---:|---:|
| Covertype |154.452222|.173004|.000726–.007961|
| Household |.082111|.014022|.000090–.001172|
| Year |2.680015|.003465|.000263–.000302|

Truth SD uses each complete prepared column's full 100k rows, ddof 1, not prefix SD or observed-only preprocessing SD. RMS measures inter-route differences, not predictionRMSE or a typical-cell error. Maxima in original and standardized units can occur at different cells; empty-score columns are null.

| Covertype imputation | CPU/MPS iterations | Theta max | Original-unit max | SD max | SD RMS |
|---|---|---:|---:|---:|---:|
|1|74/63|.002517581|154.452222|.104302|.007162|
|2|96/82|.002280414|130.440632|.173004|.007961|
|3|59/57|.000343919|19.906016|.017190|.001253|
|4|42/42|.000210285|.428221|.013890|.000726|
|5|54/51|.000605583|23.913383|.023477|.001913|

Each comparison has 3,000 masked prefix cells. Raw maximum 154.452222 is imputation 1/Roadways; normalized maximum 0.173004 is imputation 2/Vertical_Distance_To_Hydrology, raw 10.014974/SD 57.888827. Even equal iteration counts can yield different output. No per-step history or complete random arrays support assigning a cause to rounding, RNG or a decomposition.

Original JSON48,736 bytes/hash `0d38b4ef871c759727efef2bac71316f1bb08f910222286fce410c73d45cafe6`; standardized JSON250,799 bytes/hash `6f0014a18d3e34035fa1adce5db36f2b54b0521766dd77f0614ad5d20740857e`. Gzip retains raw bytes withmtime 0. Original fields, all nine NPZ hashes and original suite/report identities were unchanged; added scale fields retain separate analyzer versions. NPZ and full prepared data are not bundled here. Forty-five focused checks, 108 with related audits, passed without fitting. Checkable pairing is not statistical equivalence.

## Records

This report describes the dated run and measured source below. Later project status is recorded in the [evidence summary](../2026-09-27-evidence-summary.md).

[2026-09-23-development](../2026-09-23-development/) · [compare_native_parameters.py](../../../scripts/compare_native_parameters.py) · [comparison-original.json.gz](comparison-original.json.gz) · [comparison-standardized.json.gz](comparison-standardized.json.gz) · [sha256.json](sha256.json)

```sh
python scripts/compare_native_parameters.py \
  --input-dir results/local/benchmarks/main \
  --prepared-dir data/prepared \
  --gpu mps --r-workers 4 \
  --output results/local/native-parameter-comparison-new/mac.json
```
