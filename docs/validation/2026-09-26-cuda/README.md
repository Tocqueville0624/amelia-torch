# Linux T4 correctness checks

[简体中文](README.zh-CN.md) · [Documentation](../../README.md)

On 2026-09-26, a new Colab Linux VM executed `fa08a5207d197a3f82ced7913a67bc448c8ecacc`. All 15 stages exited 0: CUDA probe, 161 Python checks, Ruff, seven R files, downstream example, and native/hybrid CUDA64/32 fixed cases. This is actual execution, not recovered old output or Windows evidence.

Each precision passed three native cases (no prior, empirical prior, cell prior) and three hybrid cases (transformed, categorical, prior/bounds; m=3). Maximum standardized hybrid errors were about 1.43e−15/4.65e−7, discrete mismatches 0. The 33 public-edge cases here ran CPU64, not CUDA. R preparation/bootstrap/draws/output remained CPU.

Environment: Tesla T4,15,360 MiB, capability 7.5, driver 580.82.07/CUDA 12.8, Python 3.12.13/Torch 2.10.0+cu128, R 4.5.3/Amelia 1.8.3/reticulate 1.47.0, two-core Xeon 2 GHz, host memory 13,286,944 KiB; TF32 disabled. Missing ensurepip used the recorded uv fallback. Ruff 0.15.8 initially lacked its binary, then passed after a venv-only same-version reinstall. Torch was unchanged. Shared-environment NumPy warnings remain in logs despite successful imports/fits.

Thirty-four files were restored from hash-checked notebook checkpoints: compressed payload 35,892 bytes, SHA `b8ad4014836ea739d20668a065483336be6ad9ce1fda026ccad31609c67e7b94`. Only project/home paths were replaced; no missing results were added. No credentials, RDS or installed libraries are included. Later performance used `905cc79`, whose src/R-package computation matched this version, with a common two-thread/two-worker budget. Small cases do not establish coverage, broad compatibility or speed.

## Records

This report describes the dated run and measured source below. Later project status is recorded in the [evidence summary](../2026-09-27-evidence-summary.md).

[validation-steps.json](correctness/validation-steps.json) · [correctness](correctness/) · [bootstrap.json](correctness/bootstrap/bootstrap.json) · [correctness-checkpoint-manifest.json](correctness-checkpoint-manifest.json)
