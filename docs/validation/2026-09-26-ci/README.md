# Hosted CPU CI: 2026-09-26

[Run 36274202726](https://github.com/Tocqueville0624/amelia-torch/actions/runs/36274202726) completed successfully at commit **`fa08a5207d197a3f82ced7913a67bc448c8ecacc`**. The report was checked against both the run/job API and complete job logs. Raw logs and runner paths are not published here.

| Actual runner | Python | Pytest result | R test files | Downstream example |
|---|---|---:|---:|---|
| macOS 26.6.2, arm64 | 3.12.10 | 161 passed, 24.12 s | 7 passed | passed |
| Windows Server 2025, x64 | 3.12.10 | 161 passed, 38.48 s | 7 passed | passed |
| Ubuntu 24.04.5, x64 | 3.12.14 | 161 passed, 22.25 s | 7 passed | passed |

All jobs used R 4.5.3 and exact Amelia 1.8.3. PyTorch was 2.14.0 on macOS and 2.14.0+cpu on Windows/Linux. The architecture is taken from the actual interpreter setup logs (and the macOS arm64 image), not inferred from `*-latest` labels.

The seven R files were `bridge.R`, `compatibility.R`, `torch-compat.R`, `public-edge-cases.R`, `reference_metadata.R`, `downstream.R`, and `downstream_extended.R`. Source-package installation and the compiled C helpers succeeded. Each platform ran the Python→R downstream example, including RDS transfer, transformation/append, headless PDF, and export/readback. Python lint also passed.

The macOS-only skip of the “Install CPU PyTorch on Windows and Linux” step is its intended platform condition; macOS installed PyTorch in the normal package step. There were no skipped Python tests.

These results include the bounded G1 downstream and G2 start-value tests present in this commit. They **do not include later G3 frontend/type-boundary tests, G4 parallel regressions, or later autopri probes**. No CUDA/MPS, Intel Mac, interactive GUI, or complete first-release claim follows from this CPU workflow. A source install is not an independent wheel-install matrix.

[Portable JSON with job links and step outcomes](cross-platform-ci.json)

A separate subsequent commit completed an actual Intel Mac installed-wheel reference workflow without Torch: [Intel Mac evidence](intel-mac-reference.md). Its result is independent of the three-platform matrix above.
