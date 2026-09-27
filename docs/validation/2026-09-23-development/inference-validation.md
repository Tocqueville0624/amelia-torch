# CPU64 inference screen

[简体中文](inference-validation.zh-CN.md) · [Documentation](../../README.md)

The initial CPU64 study completed 200 MCAR and 200 MAR datasets, each n=300/m=5: 400 multiple-imputation calls and 2,000 converged bootstrap EM fits, with no failures, warnings, adaptive priors or pseudoinverses. This is a specified-model screen, not GPU performance or original-R equivalence.

The data use standard-normal x1/x2 with correlation 0.3 and `y=1+x1+.5*x2+N(0,1)`. The target x1 coefficient is 1. y remains observed; each covariate has expected 20% missingness, about 13.33% over the full table. MCAR masks independently; MAR uses a slope 1 logistic function of observed y with a per-dataset calibrated intercept. Native ordinary bootstrap uses tolerance 1e−4, autopri=0.05, no explicit empri and maximum 500 iterations (actual 4–13). Master seed 20260923 derives separate data/mask/imputation streams; Torch/BLAS use one thread.

| Mechanism | Bias | Bias MCSE |95% interval coverage | Coverage MCSE | Exact 95% coverage interval | Mean width |
|---|---:|---:|---:|---:|---|---:|
| MCAR |−.000688|.004679|192/200=96%|1.386 pp|92.27–98.26%|.26505|
| MAR |.002905|.004810|194/200=97%|1.206 pp|93.58–98.89%|.27308|

Actual covariate missingness was 19.914/20.017%; estimate SD .06617/.06803 and mean pooled SE .06685/.06856. Intervals containing 95% are not equivalence evidence: no equivalence margins or parallel original-R simulation were used.

Each completed dataset fits homoskedastic OLS with residual variance SSE/(n−3), using QR. Rubin pooling uses Qbar, Ubar, between-imputation variance B = sum((Q_i − Qbar)²)/(m−1), total `T=Ubar+(1+1/m)B`, and finite-m t degrees of freedom `(m−1)[1+Ubar/((1+1/m)B)]²`; B=0 uses the normal limit. No Barnard–Rubin finite-complete-sample correction is applied. Bias MCSE is estimate SD/sqrt(N); coverage MCSE is sqrt(p(1−p)/N), with exact binomial intervals. Failed/unconverged records remain, including failure-as-noncoverage summaries; here none failed.

Python 3.12.13/NumPy 2.5.3/SciPy 1.18.1/Torch 2.14.0 on Mac arm64 ran the loop in about 3.62 s; this is validation cost, not a speed ratio. Eleven offline checks covered pooling/OLS/masks/failure accounting; an independent pass recomputed all 400 records and source hashes. JSON SHA `f3c8d9206ce141d7614dd753b5bca8b39565fba3c42832f27f54f00d75b9d514`. Later G5 acceptance is separate.

Reproduction (new output; Windows substitutes its interpreter/env syntax):

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python scripts/validate_inference.py \
  --replicates 200 --n 300 --m 5 --threads 1 \
  --time-budget-seconds 300 \
  --output results/local/inference_validation-repeat.json
```

## Records

This report describes the dated run and measured source below. Later project status is recorded in the [evidence summary](../2026-09-27-evidence-summary.md).

[inference-validation.json](inference-validation.json)
