# Examples

[简体中文](README.zh-CN.md) · [Documentation](../docs/README.md)

## Python/R roundtrip

After [installation](../docs/setup.md), run from the repository root:

```sh
R_LIBS_USER="$PWD/.R-library" .venv/bin/python examples/python_r_downstream.py \
  --output results/local/downstream-example --r-library .R-library
```

Use a new output directory. Windows uses `.venv\Scripts\python.exe`, `--r-library .R-library`, and Rscript on PATH or `--rscript`. The default first fit is original R reference. `--engine torch-compat` uses hybrid CPU64 for that fit; subsequent R transformation, reference append, modeling, plotting and export remain original CPU work.

The example uses an actual Amelia RDS, derives an interaction in R, appends one imputation without changing previous draws, creates PDF/combined CSV, and rereads the authoritative RDS in Python. It checks derived values and historical draws and writes `roundtrip.json` provenance.

Install the Python `[reference]` extra, Amelia 1.8.3 and ameliatorch; hybrid also requires Torch. Optional R broom enables mi.combine pooling:

```r
install.packages("broom", lib = ".R-library")
```

Without broom the example explicitly skips pooling; direct original mi.combine fails clearly. rlang is an Amelia import; foreign supplies Stata export. AmeliaView is a separate interactive Tcl/Tk GUI and is not launched here.

Amelia 1.8.3 mi.combine reverses interval endpoints and uses a signed upper-tail p-value that may exceed 1 for negative coefficients. The example retains original pooling output with intervals disabled; compatibility does not endorse its p-values. Read [G1](../docs/validation/2026-09-26-g1/downstream-extended.md) before interpreting them.

## Colab CUDA template

[colab_cuda_validation.ipynb](colab_cuda_validation.ipynb) has Chinese explanatory cells and no account metadata. English/Chinese execution guidance is available in the [cloud procedure](../docs/cloud-cuda.md). Its stages cover installation, Python and nine R files, fixed CUDA checks, data, native/hybrid benchmarks, frozen G5, audits and recovery. Code cells have no saved outputs/execution counts. Static structure/syntax/lint and a local sleeping-child interruption check passed; **no complete end-to-end Colab run of this template has passed**.

A selected-stage attempt exposed an unintended R upgrade/shared-extension conflict and nested-venv NumPy import failure. Installation was repaired, then validation stopped at 306 Python passed/one failed; later R/CUDA/G5 stages did not run. Colab remains paused. The installer guard is not a validated fix. Read [recovery](../docs/validation/2026-09-27-colab-recovery/README.md) before reuse.

The template pins `ef729c093e162f4d6ebd797c95a9da8072ac968a`, distinct from 905cc79 historical timings. Use Python 3.12, a fresh checkout and the explicit two-core budget. Substantial stages start disabled; do not use Run all, concurrent benchmarks, automatic paid resources or changed thresholds. Failed stages block dependent computation. Interruptions terminate the process group and confirm exit before backup; unconfirmed cleanup keeps process markers set and blocks more work. This does not monitor other notebooks or escaped processes. A complete G5 report can still fail statistical criteria while passing a record audit.

JSON/log checkpoints exclude binary parameters and prepared arrays. The template separately backs up 12 native parameter NPZ files using raw-byte/hash envelopes and offers a bounded download archive. Save the notebook, confirm downloads and hashes before releasing the VM. Backups occur outside timing and cannot recover unwritten results.

[Recovered old output](../docs/validation/2026-09-23-colab-recovered/README.md), [later T4 native results](../docs/validation/2026-09-26-colab-native/README.md) and [Mac results](../docs/validation/2026-09-23-development/README.md) are separate evidence, not runs of this template.
