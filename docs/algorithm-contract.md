# Amelia 1.8.3 algorithm contract

[简体中文](algorithm-contract.zh-CN.md) · [Documentation](README.md)

The compatibility target is the **observed behavior of CRAN Amelia 1.8.3**. Mathematical definitions, implementation behavior and unverified features are distinguished. This contract does not establish a complete port or a speed advantage. Initial source audit: 2026-09-23; later edge findings are dated below.

## Reference and provenance

The [official archive](https://cran.r-project.org/src/contrib/Amelia_1.8.3.tar.gz) has SHA-256 `7699455ca3e9dabd60ad0ec69185ece3f24a597ef8da18033ea0b7a32356967f`. Upstream is GPL (>= 2); this port is GPL-3.0-only. The [manual](https://cran.r-project.org/web/packages/Amelia/Amelia.pdf) does not override version-specific source behavior.

Audited entry points are `R/prep.r::{amelia_prep,amtransform,amsubset,scalecenter,amstack,unsubset,untransform}`, `R/emb.r::{bootx,startval,emarch,amelia_impute,amelia.default}`, `src/em.cpp::{emcore,sweep,ameliaImpute,resampler}` and `R/amcheck.r::amcheck`. `scripts/export_reference_fixtures.R` exports synthetic inputs processed by unmodified Amelia to `tests/fixtures/reference_amelia/`. “Verified” here refers to executed reference evidence; port coverage is recorded in the [matrix](amelia-compatibility.md).

## Execution order

1. Validate inputs/options, resolve names and indices, and expand observation priors.
2. Transform the original input; prepare IDs, nominal dummies, time structure and overimputation.
3. Remove entirely missing analysis rows, retaining their locations for restoration.
4. Standardize once using each original column's observed mean and sample SD, with denominator `n_observed-1`. Do not restandardize each bootstrap sample.
5. Order columns by increasing missing count. Lexicographically order rows by the missingness mask in reverse column order, observed before missing. Complete rows precede contiguous pattern groups.
6. For each imputation, resample rows and remap cell priors. Regroup rows after bootstrap; keep column order fixed.
7. Construct initial values and fit EM on the bootstrap sample.
8. Draw missing values for the **original prepared input**, using the fitted parameters.
9. Reverse ordering, scaling, subsetting/category reconstruction and transformations. `impfill` ordinarily restores observed values; the single-row-prior exception below is retained.

Mean filling, MICE or neural imputation; omission of conditional covariance or bootstrap; returning the resampled data; or changing preparation order is not an equivalent acceleration.

## Coordinates and initialization

The low-level input is transformed, standardized numeric data, with NA/NaN indicating missingness. Zero is an observed value. Parameters use

$$\Theta=\begin{bmatrix}-1&\mu^T\\\mu&\Sigma\end{bmatrix}.$$

`startval` (`R/emb.r:161`) accepts a correctly sized matrix with top-left entry −1. `startvals=1` uses zero mean and identity covariance. For `startvals=0`, a temporary initialization copy first replaces prior cells by prior means, then selects complete rows. Their means and sample covariance are used only when their count is **strictly greater than p** and every covariance eigenvalue is **greater than `10*.Machine$double.eps`**; otherwise initialization is zero/identity. Complete-row covariance divides by `n_complete-1`.

CPU float64 is the numerical reference; float32 requires separate quality validation. Upstream `emcore` writes through a non-copying Armadillo view of `thetaold`. Fixture generation must deep-copy each theta with `unserialize(serialize(..., NULL))`; ordinary R assignment does not prevent alias contamination.

The public R hybrid preserves this side effect: explicit **double** `startvals` changes in the caller, archived arguments and subsequent imputations. The C helper writes back after storing the initial `allthetas` column. Integer matrices undergo upstream coercion without changing the original integer object. A complete bootstrap sample skips EM and does not write back. Native Python retains its non-mutating input contract. [Public-boundary evidence](validation/2026-09-26-g2/README.md).

## E step and cell priors

For observed indices O and missing indices M,

$$a_i=\mu_M+\Sigma_{MO}\Sigma_{OO}^{-1}(x_{i O}-\mu_O),\qquad V=\Sigma_{MM}-\Sigma_{MO}\Sigma_{OO}^{-1}\Sigma_{OM}.$$

Fill the first moment with $a_i$ and add V in the missing-by-missing block of the second moment. Complete rows need no conditional-variance correction.

Upstream `sweep` first attempts `inv_sympd`, then a pseudoinverse using absolute threshold `sqrt(double epsilon)` (`src/em.cpp:293`). Do not silently add jitter/ridge, clip eigenvalues or lower precision. Alternative solves require numerical comparison on shared inputs and pseudoinverse telemetry.

Public four-column priors are `[row,column,mean,standard_deviation]`. After `scalecenter`, the last two columns are standardized mean and **variance**; low-level `emarch`/`amelia_impute` use those coordinates and **1-based R indices**. C++ receives precision and precision-weighted mean. With diagonal prior precision Λ and weighted mean b,

$$W_i=(V^{-1}+\Lambda_i)^{-1},\qquad a_i^*=W_i(V^{-1}a_i+b_i).$$

Use both posterior moments in sufficient statistics. Adjusting only the mean is incorrect. Public five-column priors `[row,column,lower,upper,confidence]` become mean `(lower+upper)/2` and SD `(upper-lower)/(2*qnorm((1+confidence)/2))`. Row 0 applies to every missing cell in a variable; cell-specific priors take precedence. Low-level tests do not establish support for this public preprocessing.

## M step and empirical prior

For first-moment-completed rows $y_i$ and embedded conditional covariance $C_i$,

$$s=\sum_i y_i,\quad Q=\sum_i(y_i y_i^T+C_i),\quad \mu'=s/n,\quad \Sigma'=Q/n-\mu'\mu'^T.$$

The ordinary EM denominator is **n**, not n−1. Upstream casts `empri` to integer e and fixes $H=e_{initial}I$ before iteration. If current e>0,

$$\Sigma'=\frac{Q-ss^T/n+H}{n+e+p+2}.$$

Retain `p+2`, integer truncation (`3.75` becomes `3` in the fixture) and the fixed initial H. This is not an additive ridge update.

If an internal bootstrap input has no missing cells, `emarch` skips EM and returns column means, sample covariance (n−1 denominator), and `iter.hist=NA`, ignoring `empri` and the supplied theta. Public Amelia normally rejects a fully observed original input, but bootstrap can still produce this internal case.

## Stopping and autopri

- Count upper-triangle entries of Θ with `abs(new-old)>tolerance`, strictly greater, to obtain `cvalue`.
- Continue while `(cvalue>0 OR count<emburn[1]) AND (count<emburn[2] OR emburn[2]<1)`.
- Default `emburn=c(0,0)` has no maximum; experiments may set a shared explicit limit.
- `iter.hist` stores cvalue, nonmonotone flag and singularity flag. “Nonmonotone” means iteration>20 and cvalue increased, not decreasing log likelihood. Singularity means a covariance eigenvalue≤0.
- If nonmonotone, `autopri>0`, the previous 20 singularity flags sum to>3, and `e<autopri*n`, update `e=int(e+0.01*n)`. No extra cap-clamp is applied; truncation can prevent growth when n<100. H remains its initial value.

Report reaching the maximum separately from convergence. The original outer layer rejects covariance with minimum eigenvalue below double epsilon using code 2.

Internal `allthetas=TRUE` is a matrix of upper-triangle Θ vectors in column-major order, excluding the top-left entry. Its **first column is initialization**, followed by one column per iteration. It is not a public `amelia.default` argument. Native matrix-history diagnostics are a different format.

## Bootstrap, draws and RNG

Ordinary bootstrap takes n equally weighted draws with replacement; `boot.type="none"` uses the prepared original matrix. If a sampled column is wholly missing and lacks a prior, reject the whole sample and retry. Upstream has no retry limit. Preserve the version's remapping of priors across retries; an improved retry rule is a separate method.

For each incomplete group, upstream draws `n_group×p` standard normals in **column-major** order; complete groups consume none. With upper-triangular Cholesky $R^TR=V$, row noise is $z R$. Prior cells use posterior moments. Draws impute the original prepared input.

Amelia 1.8.3 C++ draws can advance R's internal RNG without refreshing `.Random.seed`. Entering reticulate between no-bootstrap replicates can reload the stale vector and repeat draws. Registered helpers in `r-package/src/rng_state.c` save the visible vector and export internal state before deterministic Python initialization/EM; on return they restore internal state and then the original visible vector separately. Saving `.Random.seed` alone, or consuming an extra `runif()` to refresh it, changes behavior. Tests cover `boot.type="none", m=2`, Inversion/Box–Muller with odd normal counts, final visible seed and subsequent `runif/rnorm`.

Bounds act at imputation, not by fitting a truncated-normal EM model. Original row-wise joint rejection runs at most `max.resample` times, then clamps violating cells to the nearest bound. Unbounded missing dimensions still follow the joint draw. Bounds must match transformed and reordered coordinates.

Equal R, NumPy or device seeds do not guarantee shared random inputs. Deterministic checks require explicit bootstrap indices and normal arrays; distributional checks require repeated inference and coverage studies. RMSE alone is insufficient.

## Preprocessing and output

IDs are excluded from modeling and ordinarily retain values/types. `ts`/`cs` become identifying columns with additional model columns generated as requested. Lags/leads use adjacent observations after cs/ts sorting, with missing group boundaries; they do not interpolate calendar gaps. Preserve upstream polynomial/spline bases, interactions and redundant-column removal order.

Nominal variables use k−1 dummies in first-observed category order. Reconstruction clips probabilities to [0,1], normalizes when needed, supplies the baseline probability and samples a category; argmax is not equivalent. Ordinal reconstruction rescales/clips to [0,1] over the observed integer range and draws a binomial integer; rounding is not equivalent.

Entirely missing analysis rows are removed and remain missing in the final output. Public checks reject non-ID columns with≤1 observation (code 4), constant columns (43), and fully observed original inputs without overimputation (39). Low-level permissive behavior does not replace public validation. Types, masks, names and ordering are API requirements.

### Version-specific exceptions

The forward log transform is `log(x-xmin+1)`, where `xmin=min(0,min(observed_x))`; inverse transformation is `exp(z)+xmin`. The 2026-09-23 roundtrip on `[-2,0,2,4,7,10]` produced original values+1 (`edge_contract.json`). No preparation correction was found. Final observed values are restored by `impfill`; missing values follow this upstream behavior. Subtracting 1 would require a separately identified corrected mode or upstream version change.

An independent public call on that date confirmed that single-row `priors=matrix(c(1,3,0.5,0.05),nrow=1)` with string IDs changes first-column rows 1 and 3. `impfill` uses `is.na(x.orig)[priors[,c(1,2)]] <- TRUE` without `drop=FALSE`; coordinates collapse to a vector and become linear indices. Reference behavior is retained with a warning. This exception must not suppress ordinary observed-value checks for multi-row priors. Regression: `tests/test_reference.py::test_single_row_prior_preserves_documented_original_indexing_quirk`.

On 2026-09-26, independent R calls confirmed an entirely NA integer ID becomes double. An entirely NA character ID stays missing in a numeric case but becomes the string `"1"` throughout a fixed 90-row `noms` case. Reference/hybrid CPU64 matched those outputs. This bounded case is not a rule for every ID combination. Regression: `tests/test_reference_boundaries.py::test_nullable_empty_ids_unicode_and_duplicate_index_actual_rds_roundtrip`; [G3](validation/2026-09-26-g3/README.md).

## Verification

The exporter requires exact Amelia 1.8.3 and saves inputs and random arrays as JSON (`null` means missing). Compare conditional moments, one M step, final Θ and histories on identical input and initial values. Fixtures cover priors, fractional empri, no complete rows, min/max iterations and the complete-input shortcut. Inject saved standard normals into imputation; compare preparation means, sample SD, order and initial values separately.

`adaptive_stress.json` records exact-collinear behavior near correction thresholds. Near-zero eigenvalue signs depend on BLAS/rounding; it is diagnostic evidence, not a cross-platform exact-history gate. Well-conditioned fixtures support strict comparisons. Accelerator checks, distributional studies and full-call benchmarks remain separate. Dated evidence cannot certify later revisions; retain errors, nonconvergence and slower-than-baseline results.
