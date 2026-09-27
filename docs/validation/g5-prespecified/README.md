# G5 prespecified inference protocol

[简体中文](README.zh-CN.md) · [Documentation](../../README.md)

Protocol frozen 2026-09-26 before the expanded R/GPU study; machine-readable [protocol.json](protocol.json) is authoritative. SHA-256 `7ea7882bccc8d92102a67786bc9c09c2055ce29d97350abfbcf4f74f2187e454`, committed at 06b0fe8. These operational limits apply to this synthetic model, not all research questions. Later [Mac results](../2026-09-26-g5-mps/README.md) did not pass every criterion; CUDA formal execution remains incomplete. Do not change seeds/margins, discard failures or automatically expand budgets after results.

## Design

Per route: 200 independent MCAR and 200 MAR datasets, n=300, m=5, master seed 20260923, standard-normal covariates with correlation 0.3,`y=1+x1+.5*x2+N(0,1)`, target coefficient 1. y remains observed; covariate expected missingness 0.2 (13.33% for all three columns). MCAR is cell-independent; MAR uses the original observed-y logistic/intercept calibration. All routes read shared little-endian float64 inputs with SHA-256 and R-MD5 transfer verification. Each R route uses one persistent batch process; this is not timing evidence.

Routes: original R reference; hybrid CPU64/CUDA64/CUDA32/MPS32; native CPU64/CUDA64/CUDA32/MPS32, selected explicitly. Fixed ordinary bootstrap, tolerance 1e−4, autopri=0.05, empri NULL, emburn 0/500, Torch 1 thread, CUDA TF32 off, no silent fallback. R uses L'Ecuyer-CMRG/Inversion/Rejection. R imputation seed equals native uint32 seed modulo(2^31−1), with 0 valid. Data/mask seeds are unchanged; native retains original uint32/PCG64. This does not pair native and R random streams.

## Primary criteria

The entire marginal 90% interval must lie within each bound, for each route/scenario. Nonsignificance is insufficient.

| Quantity | Acceptable interval range |
|---|---|
| Mean coefficient bias vs truth 1 |[−.02,.02]|
|95% Rubin interval coverage |[.90,.99]|
| Paired mean coefficient difference vs R |[−.01,.01]|
| Paired coverage difference vs R |[−.05,.05]|
| Geometric mean pooled-SE ratio vs R |[.95,1.05]|
| Geometric mean interval-width ratio vs R |[.95,1.05]|

Original R must meet the first two absolute checks. Old native CPU64 results were already known: this is a prospective extension, not a blind registration on entirely unknown data. Marginal 90% intervals do not provide joint familywise 90% equivalence. All required comparisons must pass; 200 replicates may yield insufficient precision.

## Pooling and uncertainty

Each completed dataset fits homoskedastic OLS, variance SSE/(n−3), R lm/vcov or native QR. The same Python pool_scalar computes `T=Ubar+(1+1/m)B` and finite-m Rubin t degrees of freedom, without Barnard–Rubin adjustment. This is separate from original mi.combine quirks.

Bias and paired coefficient differences use dataset-level mean, sample SD/sqrt(N) MCSE and t_(N−1,.95) intervals. Pair first, then estimate uncertainty. Absolute coverage uses exact Clopper–Pearson 90% intervals; descriptive 95% intervals remain separately reported. Paired coverage uses discordance probabilities p+ and p−: exact 95% intervals for each, combined as [L+−U−, U+−L−] by union bound for at least 90% coverage. Even zero discordance yields nonzero interval width. Its MCSE uses paired indicator differences. SE/width ratios use mean paired log-ratio t intervals followed by exponentiation, not ratios of arithmetic means.

Report mean bias, pooled SE, width, MCSE, coverage and failures. A successful subset is descriptive only, never an acceptance population.

## Integrity and stress

Preserve every planned dataset and m fits, convergence, exact observations, finite required values, device/precision, input/seed alignment, exit status and unchanged source. Missing/duplicate records or nonzero process exits cannot disappear. Original iterHist, warnings, code/message remain; inaccessible empri/pseudoinverse counts are null, not 0. Native/hybrid supply their diagnostics. Records retain per-fit regression/quality checks; they do not imply permanent publication of every completed matrix.

An independent SeedSequence namespace [20260923,2, replicate] supplies 20 stress datasets per route, n=300, m=5, covariate correlation 0.95, MCAR 0.5, y observed. Stress has no small-sample coverage/equivalence gate. Failures or incomplete records set stress_requires_review; primary status is separate. This is not MNAR or high-dimensional validation.

R batches are terminated at the wall-time budget while completed checkpoints remain. Native checks time between m=5 calls, each bounded by 500 EM iterations; this is not a strict per-second native terminator. Keep planned-but-unexecuted entries and do not overwrite a timeout by extending its budget.

## Commands

Smoke uses three datasets per primary mechanism plus two stress cases, with no formal acceptance eligibility:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
  .venv/bin/python scripts/validate_inference_suite.py --mode smoke \
  --routes r-reference hybrid-cpu64 native-cpu64 \
  --time-budget-seconds 120 --output results/local/g5-smoke-new
```

Formal CUDA route selection:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
  .venv/bin/python scripts/validate_inference_suite.py --mode formal \
  --routes r-reference hybrid-cpu64 hybrid-cuda64 hybrid-cuda32 \
           native-cpu64 native-cuda64 native-cuda32 \
  --time-budget-seconds 1800 --output results/local/g5-cuda-formal
```

A 7200 s wall budget may be fixed before execution without changing sample count, seeds or margins. MPS uses its explicit 32-bit routes, never MPS64. Windows changes interpreter/environment syntax. Each formal route plans 420 datasets/2,100 fits; unselected routes have no acceptance claim.

`inference-suite.json` is the complete report: protocol/hash, input/seed records, source and installed R-library fingerprints, versions, diagnostics, descriptive summaries and gates. Local config/log files can contain private paths and are not publication artifacts. Synthetic binary inputs are regenerable. The driver refuses overwrite; smoke exit 0 is not formal success.

## Recorded smoke

The three CPU routes completed 8 datasets each, 24 calls/120 fits, all converged/finite/observations preserved. R 4.5.3/Amelia 1.8.3 and Torch 2.14.0 were recorded. Original/hybrid input and mapped seed matched; maximum pooled coefficient difference 1.521e−14. Formal gates remained insufficient_evidence and formal_acceptance_passed=false. Smoke report SHA `07f50cf5140aeeef22d98481ce7462f352944c66f93d318c4f8e1a0553c5d2c1`; source guards held. An earlier named-list JSON failure was retained, then repaired. Forty tests (29 new gate/seed/failure plus 11 existing pooling/generation), R syntax and Ruff passed. This smoke did not include GPU routes.

## Records

This report describes the dated run and measured source below. Later project status is recorded in the [evidence summary](../2026-09-27-evidence-summary.md).

[protocol.json](protocol.json) · [validate_inference.py](../../../scripts/validate_inference.py) · [smoke-cpu-report.json](smoke-cpu-report.json)
