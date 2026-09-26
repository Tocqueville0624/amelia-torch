# Python and R downstream roundtrip

From the repository root, after the Python and R packages are installed:

```sh
R_LIBS_USER="$PWD/.R-library" .venv/bin/python examples/python_r_downstream.py \
  --output results/local/downstream-example --r-library .R-library
```

The directory must not already exist. On Windows use
`.venv\Scripts\python.exe`, pass `--r-library .R-library`, and ensure `Rscript`
is on `PATH` or pass `--rscript`. The default first call is original R reference
imputation. Add `--engine torch-compat` for the first fit to use CPU float64 Torch
EM; the R transformation, appended imputation, models, plot and export still use
the official CPU implementation. This example does not claim that every official
R method has a Python counterpart.

The example saves an actual Amelia RDS, reads it in R, derives an interaction,
appends one reference imputation while retaining the old draws, creates a PDF
and combined CSV, and reads the authoritative RDS back into Python. It checks the
derived values and old draw, and writes portable provenance to `roundtrip.json`.

Install `amelia-torch[reference]` for NumPy/pandas transport and the installed
`ameliatorch` R package with Amelia **1.8.3**. `--engine torch-compat` also needs
`amelia-torch[torch]`. R `mi.combine` additionally requires optional **broom**:

```r
install.packages("broom", lib = ".R-library")
```

Without broom, this example explicitly skips pooling and still runs its other
steps; calling official `mi.combine` directly reports that broom is required.
`rlang` is an Amelia Imports dependency, installed by normal dependency setup.
`foreign`, imported by Amelia, supplies Stata export. Official `AmeliaView` is a
separate R/Tcl/Tk GUI and requires an interactive graphical session with Tcl/Tk;
this headless example does not launch or validate that GUI.

Amelia 1.8.3's `mi.combine` returns reversed `conf.low`/`conf.high` when
`conf.int=TRUE` and uses a signed upper-tail p-value without an absolute statistic.
For negative coefficients the latter may exceed one. These upstream behaviors are
preserved for compatibility, not endorsed as valid inference. The example writes
unchanged official pooling output with confidence intervals disabled; inspect the
[downstream regression record](../docs/validation/2026-09-26-g1/downstream-extended.md)
before using its p-values or intervals. No formula is silently substituted.
