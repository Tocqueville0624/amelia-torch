# Hosted CPU CI: 620213e

[简体中文](cross-platform-ci.zh-CN.md) · [Documentation](../../README.md)

[Run35953184726](https://github.com/Tocqueville0624/amelia-torch/actions/runs/35953184726) passed on Windows, macOS and Ubuntu at `620213e56866bf83c9f16207a1b8e79654ede03c`, completing 2026-09-24 UTC/September 23 Pacific. Each ran 149 Python tests, lint, R source installation and five R files, with Python 3.12/R 4.5.3/Amelia 1.8.3.

R scope: native bridge, reference delegation, hybrid CPUEM, provenance and downstream/RNG checks. This is CPU regression evidence, not performance, CUDA/MPS, physical RTX 3080 or full compatibility acceptance.

The first run passed Mac/Ubuntu but Windows had 132 passing checks and one path-resolution failure: the placeholder executable lacked a Windows suffix. The fixture now uses `.exe` on Windows and is looked up, never executed. The first correction passed 133 tests on each platform; the later 149-test run is recorded separately. No statistical algorithm, tolerance or reference version changed.

## Records

This report describes the dated run and measured source below. Later project status is recorded in the [evidence summary](../2026-09-27-evidence-summary.md).

[cross-platform-ci.json](cross-platform-ci.json)
