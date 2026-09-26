# G1 packaging checks, 2026-09-26

The added downstream test and Python/R example are now configured in the
three-platform CPU workflow. The workflow explicitly installs and requires broom
and foreign, so the optional pooling branch cannot silently skip on CI.
`DESCRIPTION` lists both as Suggests. Configuration is not evidence that a new
hosted run passed; the previous CI record still covers the earlier test set.

The current `amelia-torch` wheel built successfully and was installed to a
temporary target. Imports resolved from that installed wheel rather than the
editable checkout. The embedded `_r/reference_bridge.R` matched its source
byte-for-byte. Importing both public R interfaces did not import Torch. Wheel
metadata declares NumPy/SciPy normally, pandas under `[reference]` and Torch under
`[torch]`.

A separate temporary Python 3.12.13 virtual environment then installed only
the wheel's `[reference]` extra: NumPy 2.5.3, SciPy 1.18.1, pandas 3.0.6,
python-dateutil 2.9.0.post0 and six 1.17.0. The environment had **no Torch module**.
The repository's [`python_r_downstream.py`](../../../examples/python_r_downstream.py)
ran successfully there using the existing installed R packages: official
imputation, saved RDS, R transformation/reference append, PDF/CSV/pooling, and
Python readback with unchanged old values and correct derived column.

The standalone examples are repository artifacts, not files promised inside the
Python wheel. This check verifies the Python wheel with reference-only
dependencies against the local R installation; it is not a fresh R installation,
an Intel Mac test, hosted CI, CUDA validation, or CRAN/PyPI publication.

After the explicit-startvals compatibility fix was installed and frozen, a new
source tarball built successfully. `R CMD check --no-manual --no-build-vignettes`
ran in a separate temporary directory and completed with **0 errors, 0 warnings,
0 notes**, `Status: OK`. It compiled the registered C helpers and ran all seven
R test files: bridge, compatibility, downstream_extended, downstream,
public-edge-cases, reference_metadata and torch-compat. Test dependency checks
accepted the updated Suggests. See the [sanitized check log](r-package-check.log)
and [R source hashes](r-package-source-hashes.json).

The first check found a test-harness issue: `R CMD check` exports `R_TESTS` for its
startup script, and nested Rscript processes inherited a path invalid in their
temporary directory. The new test now clears and restores only that variable
around its child process. A minimal Rscript invocation reproduced the cause;
the rebuilt package then passed the complete check. The numerical implementation
was not changed to resolve this harness failure.

Remote CRAN/Bioconductor package indexes were inaccessible during the check;
installed dependency checks still passed. This result does not verify remote
repository availability or replace the pending new hosted CI run.

Machine-independent hashes and outcomes are in [packaging.json](packaging.json).
