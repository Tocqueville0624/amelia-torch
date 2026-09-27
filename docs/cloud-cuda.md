# Colab CUDA procedure

[简体中文](cloud-cuda.zh-CN.md) · [Documentation](README.md)

Colab experiments are paused after quota exhaustion. This is a procedure for a future scheduled run, not evidence that its stages passed. Do not launch new work during the current documentation phase. Linux/T4, Windows/RTX 3080 and interactive RStudio records are distinct. [Current evidence](validation/2026-09-27-evidence-summary.md).

## Template and known failures

Use [the staged notebook](../examples/colab_cuda_validation.ipynb), with its [scope notes](../examples/README.md). It checks out `90699b898a55a9c29f61e01181b8d688ab08b702`, the tree-identical migration of original `ef729c093e162f4d6ebd797c95a9da8072ac968a`, includes nine R files and separate correctness, performance, G5, audit and backup stages. Static/syntax/lint and lightweight process-interruption checks passed; the template has **not** completed an end-to-end Colab run. Historical `905cc79` timings are not template execution results.

A replacement run stopped at stage 4/20:306 Python checks passed and one nested venv lacked NumPy; later R/CUDA-edge/G5 work did not run. Earlier system installation upgraded R 4.5.3 to 4.6.1 and broke existing shared extensions. R 4.5.3 restoration and a fresh project R library repaired installation, not the whole validation. The automatic installer guard remains unvalidated. Avoid `--install-system-packages` when tools already exist; review [recovery evidence](validation/2026-09-27-colab-recovery/README.md) before reuse.

## Environment

The project requires Python 3.12. The first recorded free runtime instead supplied Python 3.13.15/Torch 2.11.0+cu128/R 4.6.1. Select a suitable past runtime if available and inspect actual versions; [runtime availability](https://research.google.com/colaboratory/runtime-version-faq.html) changes. Free GPU availability/duration is not guaranteed. Do not automatically purchase resources, bypass quotas or change runtime during a CPU/CUDA comparison. [Colab resource policy](https://research.google.com/colaboratory/faq.html).

Use a fresh checkout pinned to a full 40-character commit. `cloud_bootstrap.py --expected-commit <sha>` plans only; add `--execute` for installation when scheduled. It requires the runtime's CUDA Torch>=2.10,<3, reuses its files through a system-site-packages Python 3.12 venv, and installs project/test/pandas dependencies. This is not a fully isolated lock. The Mac lockfile must not install CUDA dependencies.

The installer checks Ruff through the venv interpreter, with a recorded same-version local reinstall if metadata exists but the binary is missing. If ensurepip is absent, the uv fallback uses the same interpreter/system-site-packages setting and records its version. Torch/global packages are not intentionally replaced. R dependencies, broom/foreign and exact Amelia 1.8.3 go into `.R-library`; C helpers require compilation. Missing R/build tools produce an explicit failure. Any apt-based retry needs a fresh output directory and prior review of R-version effects; it is a Linux-VM procedure, not a Mac command.

Fixed Amelia archive SHA-256: `7699455ca3e9dabd60ad0ec69185ece3f24a597ef8da18033ea0b7a32356967f`; fallback is only the same version in CRAN Archive. Bootstrap records tracked-source hashes, commit, hardware/runtime, CPU quota, memory, versions, commands and failures, excluding serial numbers, hostnames and whole environment dumps. Existing output directories are rejected.

## Execution and timing

Run device probes, Python checks, the nine R files, downstream example and fixed CUDA64/32 comparisons before dependent workloads. Disable TF32 explicitly. Save failures and do not widen thresholds after seeing results. The older recovered notebook's 149 Python/five R results do not cover later additions.

Prepare shared 100k complete-row block-MCAR inputs for Covertype/Household/Year. Downloads total about 232 MiB and use manifest hashes/CRC with 5 GiB disk reserve. Household masking is 2/7; these are not full datasets or independent-cell-MCAR tasks. See [data](datasets.md) and [reproduction](reproduce.md).

Fix CPU budgets from actual host quota. The recorded T4 VM had two logical CPUs: native/reference used threads 2/workers 2; hybrid used threads 2; snow workers each used one BLAS thread. Other hosts need a documented common budget. Run suites sequentially without source edits or concurrent fits. For that two-core host:

```python
NATIVE = "results/local/cloud/native"
HYBRID = "results/local/cloud/hybrid"
assert not pathlib.Path(NATIVE).exists(), "Choose a fresh result directory"
run(PYTHON, "scripts/run_benchmark_suite.py", "--gpu", "cuda", "--output-dir", NATIVE,
    "--rows", "100000", "--m", "5", "--warmups", "2", "--repeats", "5",
    "--threads", "2", "--workers", "2")
```

```python
assert not pathlib.Path(HYBRID).exists(), "Choose a fresh result directory"
run(PYTHON, "scripts/run_hybrid_suite.py", "--methods", "cpu64", "cpu32", "cuda64", "cuda32",
    "--csv-dir", f"{NATIVE}/inputs", "--output-dir", HYBRID,
    "--rows", "100000", "--m", "5", "--warmups", "2", "--repeats", "5", "--threads", "2")
```

These snippets use PYTHON, REPO and `run()` initialized by the staged notebook. Each configuration uses m=5, two warmups and five timed repetitions. Native/reference compares R serial/snow2 and Torch CPU/CUDA64/32; hybrid reuses the main CSV. Full-call timing includes preparation, EM, draws, transfers and CPU output. File reads, installation, process startup and scoring are excluded. R-side hybrid includes reticulate conversion but not Python→Rscript process/binary exchange. CPU controls still consume the allocated GPU session's quota.

## Audit and backup

```python
run(PYTHON, "scripts/summarize_benchmarks.py", "--input-dir", NATIVE,
    "--output-dir", "results/local/cloud/native-audit",
    "--methods", "r_serial", "r_snow2", "cpu64", "cpu32", "cuda64", "cuda32")
run(PYTHON, "scripts/summarize_hybrid.py", "--input-dir", HYBRID,
    "--output-dir", "results/local/cloud/hybrid-audit")
```

Audit planned configuration completeness, all repeats, convergence, observed values, finite outputs and complete heldout scoring. Exit 0 alone is insufficient. Ratios use same-host baselines; inference criteria remain separate. Preserve partial directories and logs after interruption; do not resume by overwriting them or merge different VMs into one suite.

After each major stage and failures, outside timing, export a full download archive and save the notebook. Confirm local hashes before releasing the VM. Review raw logs/config paths before publication. Optional Drive mounting requires separate authorization and is not needed for execution.

A portable checkpoint can be printed into notebook output:

```python
checkpoint_text = subprocess.check_output(
    [PYTHON, "scripts/cloud_checkpoint.py", "--label", "validation-20260926"],
    cwd=REPO, text=True)
print(checkpoint_text, flush=True)
```

`cloud_checkpoint.py` includes JSON/log/text reports, prepared-data JSON and public manifests; it records raw/portable hashes and replaces project/home paths. It excludes credentials, raw data, RDS, dependencies and binary parameters. Keep checkpoint output outside the collected directory. Use `--phase g5-formal`, native or hybrid for a single existing direct phase directory; decompression is limited to 64 MiB. This does not recover unwritten results.

Recover a saved notebook or complete checkpoint JSON locally:

```sh
.venv/bin/python scripts/recover_cloud_checkpoint.py saved-notebook.ipynb \
  --label validation-20260926 --output-dir results/local/recovered-validation
```

Recovery does not execute notebook code. It validates gzip, paths and hashes and refuses overwrite. The staged notebook separately stores 12 native parameter NPZ files as hash-checked raw-byte envelopes and offers an input/parameter download archive. Checkpoints cannot guarantee recovery when a VM disappears before backup; truncated stdout is not the original JSON.
