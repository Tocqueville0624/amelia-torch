# Amelia 1.8.3 reference fixtures

These are small synthetic inputs and outputs from the unmodified official R
package. Rebuild from the repository root with:

```sh
Rscript scripts/export_reference_fixtures.R
```

The exporter requires **Amelia 1.8.3**. It records the official archive URL and
SHA-256 in every file. It deep-copies R inputs because the C++ EM core mutates the
theta allocation. There are no user datasets, private paths, machine serials, or
downloaded third-party observations in these fixtures.

| File | Purpose |
|---|---|
| `no_prior.json` | Shared prepared input and explicit initial theta; single step, convergence, conditional moments and random imputation |
| `empirical_prior.json` | Same input with `empri=3.75`, truncated to 3 by upstream C++ |
| `cell_prior.json` | Internal 1-based cell priors with standardized means and **variances** |
| `no_complete_rows.json` | No fully observed rows, zero/identity initial-value fallback |
| `minimum_iterations.json` | `emburn=(35,80)` runs at least 35 iterations even after convergence |
| `maximum_iterations.json` | `emburn=(0,2)` stops after 2 iterations, explicitly not converged |
| `complete_internal.json` | No-missing internal shortcut returns sample covariance and ignores empirical prior |
| `preprocessing.json` | Observed-data sample standardization, row ordering, initial values |
| `public_continuous.json` | Real public `Amelia::amelia` preprocessing-to-EM path with no bootstrap, explicit theta, nontrivial column order and a wholly missing row; no cross-library random-draw comparison |
| `edge_contract.json` | Real R checks: wholly missing row remains missing, input error codes, log inverse version behavior |
| `adaptive_stress.json` | Diagnostic near exact singularity; **not a strict cross-platform numerical/history acceptance gate** |

JSON `null` inside numeric inputs represents missing data. Matrices are encoded as
row-major nested arrays. Prior indices and sorting permutations use R's 1-based
indices. `initial_theta` is in the prepared coordinate system, with `-1` in its
top-left cell, mean in the first row/column, and covariance in the remaining block.

`standard_normals` contains the actual standard Gaussian inputs consumed by the
reference imputation, replayed by resetting the R stream. The exporter independently
checks that these values and analytic conditional moments reproduce
`Amelia:::amelia_impute` to maximum absolute error below `1e-11`. Use the exported
array to test another runtime; do not use the seed as a cross-library contract.

The complete internal fixture is not evidence that public `Amelia::amelia()`
accepts a fully observed original dataset. The public default rejects it (code 39).
The distinction matters because a bootstrap of an incomplete original dataset can
still be completely observed.

These fixtures cover the continuous low-level core. They do **not** establish
categorical, temporal, public-prior-format, bounds, R object, or full EMB API parity.
See `docs/algorithm-contract.md` and `docs/amelia-compatibility.md` for the complete
contract and implementation status.
