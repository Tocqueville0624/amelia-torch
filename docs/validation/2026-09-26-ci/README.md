# Hosted CPU CI: fa08a52

[简体中文](README.zh-CN.md) · [Documentation](../../README.md)

[Run36274202726](https://github.com/Tocqueville0624/amelia-torch/actions/runs/36274202726) passed at `fa08a5207d197a3f82ced7913a67bc448c8ecacc` on 2026-09-26. Run/job APIs and full logs verified checkout, installs and actual commands.

| Runner | Python | Python checks | R files | Downstream |
|---|---|---:|---:|---|
| macOS 26.6.2 arm64 |3.12.10|161 passed, 24.12 s|7|passed|
| Windows Server 2025 x64 |3.12.10|161 passed, 38.48 s|7|passed|
| Ubuntu 24.04.5 x64 |3.12.14|161 passed, 22.25 s|7|passed|

R 4.5.3/Amelia 1.8.3 were fixed. Torch was 2.14.0 on Mac and 2.14.0+cpu elsewhere. Lint, C-helper source installation and Python→RDS→R transform/append/PDF/export/readback passed; no Python tests skipped. The conditional Mac skip concerned only the Windows/Linux wheel-install step.

This commit covers bounded G1 and early G2 tests, not later G3/G4/autopri work. CPU tests are not benchmarks, GPU/GUI acceptance, an isolated wheel matrix or an Intel Mac result. Intel reference-only installation has its own versioned report.

## Records

This report describes the dated run and measured source below. Later project status is recorded in the [evidence summary](../2026-09-27-evidence-summary.md).

[cross-platform-ci.json](cross-platform-ci.json)
