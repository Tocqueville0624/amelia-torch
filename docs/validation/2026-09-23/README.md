# Initial environment checks

[简体中文](README.zh-CN.md) · [Documentation](../../README.md)

2026-09-23, Apple M4 iMac/16 GB, macOS 26.6.2.

- `mac-native.json`: Python 3.12.13/Torch 2.14.0 passed six operator families on CPU64/32 and MPS32, with automatic MPS fallback disabled. Deterministic matrices were 2×2; random checks covered execution, shape and finiteness, not distributions.
- `r-bridge.json`: R 4.5.3/reticulate 1.47.0 reached Python and executed CPU/MPS probes.
- `r-reference.json`: original Amelia 1.8.3 produced two imputations on 200×3 synthetic data, retaining observed values and filling missing cells; no entirely missing row was included.
- Four backend tests, lint/format and relative-link checks passed. Requesting unavailable CUDA correctly exited 1.

This initial snapshot preceded the project's EM implementation: these are environment/original-R checks, not project imputation or acceleration results. No interactive RStudio demonstration occurred in this run. A restricted process initially hid MPS; the permitted native process exposed it. Interpreter-symlink resolution and an inappropriate “fill every all-missing row” assumption were corrected. Private paths and full local session output are excluded.

## Records

This report describes the dated run and measured source below. Later project status is recorded in the [evidence summary](../2026-09-27-evidence-summary.md).

[mac-native.json](mac-native.json) · [r-bridge.json](r-bridge.json) · [r-reference.json](r-reference.json)
