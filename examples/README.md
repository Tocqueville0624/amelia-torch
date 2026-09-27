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

## Free Colab CUDA validation template

[`colab_cuda_validation.ipynb`](colab_cuda_validation.ipynb) is written in Chinese
and contains no account information. It has separate manual stages for
installation, the Python suite and nine R test files, CUDA correctness checks, three public datasets,
native and R hybrid benchmarks, frozen G5 smoke/formal inference checks,
independent audits, and checkpoint/download recovery. **The template has only
received static JSON/structure, Python syntax and Ruff checks, plus a local subprocess
interruption check using a sleeping child; it has not been run end-to-end in
Colab.** Its code cells have no saved outputs or execution counts.

The checkout is pinned to `ef729c093e162f4d6ebd797c95a9da8072ac968a`, which differs
from the historical `905cc79` cloud timing version. Use free GPU access with
Python 3.12, a fresh checkout, and the explicit two-core budget assertion. Do not
use “Run all,” purchase resources automatically, change the frozen statistical
thresholds, or run benchmarks concurrently. Every substantial stage starts
disabled, retains its logs and exit statuses, and blocks dependent computation
after failure. Commands start in separate process groups; a caught interruption
terminates the group and confirms its exit before checkpointing. If cleanup
cannot be confirmed, the active-process markers remain set and both backup and
further computation stay blocked. This does not detect work in another notebook
or a process that deliberately leaves the group. A failed G5 statistical gate can
still produce a complete report for the separate audit stage; audit validity
does not mean that the statistical gate passed.

The JSON/log checkpoint excludes binary parameter files and prepared arrays.
The notebook therefore separately preserves all 12 native parameter NPZ files
as raw-byte base64 envelopes with SHA-256, and offers a bounded-scope download
archive containing those files and prepared inputs. Confirm the actual download
and save the notebook before releasing the VM. Phase checkpoints cannot recover
unwritten results or guarantee recovery if a VM disappears before that phase's
backup. They are outside benchmark timing.

Historical evidence is separate: [recovered old Colab output](../docs/validation/2026-09-23-colab-recovered/README.md),
[the later cloud native record](../docs/validation/2026-09-26-colab-native/README.md),
and [Mac development validation](../docs/validation/2026-09-23-development/README.md).
The Mac CPU/MPS measurements did not come from this notebook. Neither historical
results nor a successful audit should be represented as a new run of the
template. See [the cloud procedure](../docs/cloud-cuda.md) for interpretation and
recovery details.
