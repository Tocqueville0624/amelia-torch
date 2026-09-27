# Recovered Colab outputs

[简体中文](README.zh-CN.md) · [Documentation](../../README.md)

Recovered 2026-09-26 from a saved notebook; no new execution or performance measurement. Original VM JSON/full logs/results were unavailable. The private notebook hash is `98df0afa88b3fc805dd3bbe39496f177f4dc9330a42f36dca98a6717b06d393b`; extraction parsed JSON without executing code.

The saved cell declared `6865b6521142338c6812ce6a9f6414349321ff25`, printed bootstrap exit 0, and reported Linux Tesla T4, Python 3.12.13/Torch 2.10.0+cu128/CUDA 12.8, R 4.5.3/Amelia 1.8.3, driver 580.82.07. Torch memory 15,637,086,208 bytes and nvidia-smi 15,360 MiB are retained as reported.

Eleven of 12 validation steps exited 0: CUDA64/32 probe, 149 Python tests, five R files, three native and three hybrid cases per precision. Ruff failed with `RuffNotFound`; the overall cell ended in AssertionError. Hybrid maximum standardized errors printed as 1.427514e−15 (64-bit) and 4.646445e−7 (32-bit), with zero discrete mismatches. Reticulate NumPy warnings remain unresolved in this historical record.

Bootstrap output was limited to its last 12,000 characters and each validation process to 2,200 characters. Truncated probe JSON is not a complete report. Sanitized cells, output tails, error and extraction manifest preserve source hashes and redaction counts without account/cell metadata. No later public-edge/downstream-extension checks or dataset timing can be inferred. Extracted project code retains GPL-3.0-only attribution.

## Records

This report describes the dated run and measured source below. Later project status is recorded in the [evidence summary](../2026-09-27-evidence-summary.md).

[recovered-summary.json](recovered-summary.json) · [probe.stdout.txt](probe.stdout.txt) · [bootstrap-tail.stdout.txt](bootstrap-tail.stdout.txt) · [validation-tails.stdout.txt](validation-tails.stdout.txt) · [final-error.txt](final-error.txt) · [executed-cells.sanitized.py.txt](executed-cells.sanitized.py.txt) · [LICENSE](../../../LICENSE)
