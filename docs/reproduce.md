# Reproduction

[简体中文](reproduce.zh-CN.md) · [Documentation](README.md)

Use the [installation guide](setup.md) first and run from the repository root. These are runnable procedures, not a claim that every listed experiment has been completed. Current work reviews existing evidence; new fitting/simulation/test jobs remain paused. [Current outcomes](validation/2026-09-27-evidence-summary.md) identify completed runs.

## Data and reference fixtures

```sh
.venv/bin/python scripts/download_datasets.py --datasets all --max-download-mib 300
Rscript scripts/export_reference_fixtures.R
.venv/bin/python -m pytest -q
```

Prepare shared 100,000-row inputs with approximately 30% block MCAR:

```sh
.venv/bin/python scripts/prepare_benchmark_data.py --dataset covertype --rows 100000 --mechanism block_mcar --missing-rate 0.3 --seed 20260923 --output data/prepared/covertype-n100000-block_mcar-rate30-seed20260923.npz
.venv/bin/python scripts/prepare_benchmark_data.py --dataset household_power --rows 100000 --mechanism block_mcar --missing-rate 0.3 --seed 20260923 --output data/prepared/household_power-n100000-block_mcar-rate30-seed20260923.npz
.venv/bin/python scripts/prepare_benchmark_data.py --dataset year_prediction_msd --rows 100000 --mechanism block_mcar --missing-rate 0.3 --seed 20260923 --output data/prepared/year_prediction_msd-n100000-block_mcar-rate30-seed20260923.npz
```

Household's actual masking is 2/7. All methods use the same arrays. Complete-source-row selection excludes natural entirely missing rows and introduces a documented selection boundary; see [data](datasets.md). These are neither full-source-data nor independent-cell-MCAR benchmarks.

## Native and original-R timing

MPS:

```sh
PYTORCH_ENABLE_MPS_FALLBACK=0 .venv/bin/python scripts/run_benchmark_suite.py --gpu mps
.venv/bin/python scripts/summarize_benchmarks.py --output-dir results/local/native-audit
```

Torch CPU-only (not a no-Torch reference installation):

```sh
.venv/bin/python scripts/run_benchmark_suite.py --gpu none
.venv/bin/python scripts/summarize_benchmarks.py --methods cpu64 cpu32 r_serial r_snow4 --output-dir results/local/native-audit
```

Windows CUDA, after a passing device probe and Rscript on PATH:

```powershell
.venv\Scripts\python.exe scripts/run_benchmark_suite.py --gpu cuda
.venv\Scripts\python.exe scripts/summarize_benchmarks.py --methods cpu64 cpu32 cuda64 cuda32 r_serial r_snow4 --output-dir results/local/native-audit
```

Windows CPU-only substitutes `.venv\Scripts\python.exe` in the CPU commands. Each dataset runs original R serial/snow4 and Torch CPU64/32 plus the selected GPU in a fixed randomized order. CUDA also tests 64-bit precision. There are two warmups and five measured calls, each with five imputations; maximum 300 EM iterations is explicit and reaching it is not convergence.

The default report directory is `results/local/benchmarks/main/`. Use fresh `--output-dir` for new runs and matching audit `--input-dir`. Audit every configuration, failure, convergence and heldout score rather than trusting exit 0. Do not publish local absolute paths from config files.

The suite rejects existing directories, saves the plan before child processes, and atomically updates reports after each call. Catchable interruptions are recorded; unknown exit status remains null. This preserves completed repeats without changing seeds, fits or timing and does not automatically resume. Forced termination or VM loss can leave only the latest snapshot. Export cloud checkpoints outside the VM.

Timing includes preparation, bootstrap, EM, draws, transfers and CPU results; it excludes file reads, cold process startup and scoring. R snow worker creation/destruction is included. Native timing excludes the R/Python bridge and cannot represent the R product interface.

## Inference

```sh
.venv/bin/python scripts/validate_inference.py --output results/local/inference_validation.json
```

The initial script defaults to 200 independent 300-row datasets per MCAR/MAR mechanism, m=5, checking OLS bias, Monte Carlo uncertainty and Rubin 95% coverage. It covers a specified joint-normal model, not arbitrary-data validity or cross-language equivalence. The later [frozen G5 protocol](validation/g5-prespecified/README.md) and its recorded outcomes govern formal acceptance. Windows fixed CUDA and performance runs are complete; CUDA G5 remains incomplete.

## R hybrid timing

Install ameliatorch and Torch. Reuse the main suite's CSVs. `--generate-inputs` may create new CSVs from prepared NPZ, but does not retroactively prove paired historical input identity. Choose one matching platform route; do not run all into the same output directory.

MPS:

```sh
PYTORCH_ENABLE_MPS_FALLBACK=0 .venv/bin/python scripts/run_hybrid_suite.py --methods cpu64 cpu32 mps32
.venv/bin/python scripts/summarize_hybrid.py --input-dir results/local/benchmarks/hybrid --output-dir results/local/hybrid-audit
.venv/bin/python scripts/compare_hybrid_reference.py --output results/local/hybrid-audit/hybrid-reference-comparison.json
```

Torch CPU-only (Windows substitutes its interpreter path):

```sh
.venv/bin/python scripts/run_hybrid_suite.py --methods cpu64 cpu32
.venv/bin/python scripts/summarize_hybrid.py --input-dir results/local/benchmarks/hybrid --output-dir results/local/hybrid-audit
.venv/bin/python scripts/compare_hybrid_reference.py --reference-methods cpu64 cpu32 r_serial r_snow4 --output results/local/hybrid-audit/hybrid-reference-comparison.json
```

Windows CUDA:

```powershell
.venv\Scripts\python.exe scripts/run_hybrid_suite.py --methods cpu64 cpu32 cuda64 cuda32
.venv\Scripts\python.exe scripts/summarize_hybrid.py --input-dir results/local/benchmarks/hybrid --output-dir results/local/hybrid-audit
.venv\Scripts\python.exe scripts/compare_hybrid_reference.py --reference-methods cpu64 cpu32 cuda64 cuda32 r_serial r_snow4 --output results/local/hybrid-audit/hybrid-reference-comparison.json
```

After both complete suites pass their independent audits, plot:

```sh
Rscript scripts/plot_benchmarks.R --native results/local/native-audit/benchmark-summary.json --hybrid results/local/hybrid-audit/hybrid-summary.json --output-prefix results/local/figures/timings
```

Hybrid retains R preparation/draws/output and includes R/reticulate conversion. Initial Python imports and file reads are excluded. Keep measured source unchanged; do not run other CPU/GPU fits concurrently.

The paired comparison aligns every warmup/measured call by phase+seed and checks R RNG, parameters and input provenance. Means, covariance, iterations and RMSE summaries do not establish elementwise equality. With new directories, set `--reference-dir` and `--hybrid-dir` explicitly. Plotting detects available devices and verifies PNG/vector PDF; SVG is optional when Cairo exists. Existing outputs are not overwritten.

## Fixed accelerator comparisons

```sh
PYTORCH_ENABLE_MPS_FALLBACK=0 .venv/bin/python scripts/validate_accelerator.py --device mps --dtype float32 --output results/local/mps-validation.json
PYTORCH_ENABLE_MPS_FALLBACK=0 RETICULATE_PYTHON="$PWD/.venv/bin/python" Rscript scripts/validate_r_accelerator.R mps float32 results/local/r-mps-validation.json
```

Small numerical checks are separate from formal performance/inference. Python→Rscript hybrid calls include additional process/binary-transfer costs; measure them separately from R-side hybrid calls.
