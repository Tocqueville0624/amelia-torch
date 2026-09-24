# Bounded R downstream compatibility checks

`r-package/tests/downstream.R` uses small synthetic data on CPU float64 and
Amelia 1.8.3. These are API/format/numerical regression checks, not performance
measurements or statistical-quality acceptance tests.

The ordinary-bootstrap cases executed successfully for:

- `print` and `summary`: text identical to the original result.
- `compare.density`, `missmap`, `overimpute`, `tscsPlot`, and `disperse`: temporary
  headless PDF files generated; numeric diagnostic returns compared to original
  results with the same R random seed where applicable. `disperse` was limited to
  two short chains; overimputation and time-series drawing used ten draws.
- `mi.meld`: regression estimates and standard errors compared between engines
  and independently to the arithmetic form of Rubin's pooling rule.
- `write.amelia`: separate and combined CSV files read back and checked for
  values, row counts, and imputation identifiers.
- Saved `arglist` reuse and adding imputations to an existing result, retaining
  the earlier completed datasets.
- `moPrep` objects created within a local scope, checked through both reference
  and hybrid wrappers against the public Amelia generic.
- The internal `allthetas` adapter: initial and subsequent upper-triangle vectors,
  dimensions, and the EM iteration history compared with upstream `emarch`.

The diagnostic plotting and pooling functions are called from the original
Amelia package and execute on the CPU. Successfully passing them a hybrid result
does not make the diagnostic calculation a GPU implementation. PDF generation
was checked programmatically; this does not claim a visual design review.

## Random-state regression discovered and corrected

The final `boot.type="none", m=2` case initially failed: the first hybrid
imputation matched the original within floating-point error, but the hybrid
repeated its first draw in the second replicate. The original generated a
different draw. The deterministic EM parameters agreed. Investigation identified
an interaction between upstream C random draws and reticulate's R RNG state
boundaries. Registered C snapshot/restore helpers now preserve both the C state
and R-visible `.Random.seed` around reticulate calls, without consuming random
draws. The complete installed-package test now passes. Its nonbootstrap case
uses both Inversion and Box–Muller normal generators, with an odd number of
normals per replicate to exercise Box–Muller's cached spare. It checks completed
datasets, the final `.Random.seed`, and subsequent `runif(6)` and `rnorm(6)` values
against the original package. The regression remains in the test file.

The local-scope `moPrep` test also exposed a wrapper frame issue. The reference
wrapper now evaluates the original public call in its caller's frame, while the
hybrid wrapper resolves the saved data expression there. Both then passed the
original small `moPrep` comparison without changing the upstream algorithm.
