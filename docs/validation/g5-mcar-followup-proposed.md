# Proposed independent MCAR follow-up

[简体中文](g5-mcar-followup-proposed.zh-CN.md) · [Documentation](../README.md)

**Proposed, not approved or executed; completed runs: 0.** It does not change the original protocol, driver, 200-replicate results or failed classifications. A separate frozen protocol/runner and an explicit experiment decision are required before computation. Retaining the current development snapshot is also a valid outcome.

The original MCAR90% intervals narrowly crossed limits: original R/hybrid absolute coverage upper 99.009876%; native paired lower−5.028703 percentage points. New independent simulation could improve precision without guaranteeing a pass. MAR and the 20 stress cases would not be repeated.

Design: 1,000 new MCAR datasets, n=300, m=5; seed 2026092601 with SeedSequence([2026092601,0, i]).spawn(3), i0–999. Preserve correlation 0.3,`y=1+x1+.5*x2+N(0,1)`, observed y, covariate missingness 0.2, ordinary bootstrap, tolerance 1e−4, autopri=0.05, empri NULL, emburn 0/500. Native retains uint32/PCG64; R uses modulo(2^31−1) and L'Ecuyer-CMRG/Inversion/Rejection. All routes share hashed inputs. Do not reuse the old 200 as a prefix or pool stages into an uncorrected 1,200-sample interval.

Keep all original marginal 90% criteria and formulas: bias±.02, coverage 0.90–.99, paired coefficient±.01, paired coverage±.05, geometric SE/width ratios 0.95–1.05; same OLS/Rubin without Barnard–Rubin, paired t/log intervals and exact discordance union bound. Fixed N cannot grow after borderline results.

Candidate budgets: Mac five routes(reference, hybrid CPU64/MPS32, native CPU64/MPS32),5,000 calls/25,000 fits, 7200 s; CUDA seven routes(reference, hybrid CPU64/CUDA64/CUDA32, native CPU64/CUDA64/CUDA32),7,000 calls/35,000 fits, 7200 s; both total 12,000 calls/60,000 fits and 14,400 s. These are ceilings, not duration guarantees. Select routes before running; one-thread Torch/BLAS, no MPS fallback, TF32 off, persistent R batches and checkpoints. No automatic paid resources or budget extension.

Two-host execution repeats the same new design, not 2,000 independent generated datasets. Compare each route with same-host R and report stages separately. Preserve all planned outputs/failures, original-R absolute gates and paired gates; do not stop early for favorable estimates. Incomplete execution is insufficient evidence. This proposal was motivated by first-stage results and does not claim a single-stage or familywise 90% error guarantee, nor general validity for real data/MNAR/platforms.

## Records

This report describes the dated run and measured source below. Later project status is recorded in the [evidence summary](2026-09-27-evidence-summary.md).
