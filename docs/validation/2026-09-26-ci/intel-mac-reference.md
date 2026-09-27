# Intel Mac reference-only wheel

[简体中文](intel-mac-reference.zh-CN.md) · [Documentation](../../README.md)

[Run36274875989](https://github.com/Tocqueville0624/amelia-torch/actions/runs/36274875989) passed 2026-09-26 at `ad9bed2dfd33a7b0e0a6e4050eafc031b1726f3e`. Logs verified macOS 15.7.9, actual x86_64, Python 3.12.10, R 4.5.3 and Amelia 1.8.3.

An isolated venv built/installed `amelia_torch-0.0.1.dev0-py3-none-any.whl[reference]`, imported from site-packages, and asserted Torch was neither installed nor loaded. Original R dependencies and the project R source package installed. The example completed original-R fitting, RDS exchange, R transform/append/headless PDF/CSV, Python readback, derived values and preservation of earlier imputations.

This covers reference CPU installation and a real downstream workflow, not the full pytest suite, Intel hybrid/Torch, GPU or interactive GUI. The commit predates the G3 frontend fix. No wheel hash was uploaded/printed, so its field remains null; a wheel built elsewhere cannot supply that missing evidence.

## Records

This report describes the dated run and measured source below. Later project status is recorded in the [evidence summary](../2026-09-27-evidence-summary.md).

[intel-mac-reference.json](intel-mac-reference.json)
