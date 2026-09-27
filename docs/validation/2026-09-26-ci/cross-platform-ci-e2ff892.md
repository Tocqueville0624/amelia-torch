# Hosted CPU CI: e2ff892

[简体中文](cross-platform-ci-e2ff892.zh-CN.md) · [Documentation](../../README.md)

[Run36276160870](https://github.com/Tocqueville0624/amelia-torch/actions/runs/36276160870) passed at `e2ff8926f4ac4b432c4d6acf8fbc1cd42c93a0f2` on 2026-09-26, independently verified from job APIs and full logs. Ubuntu 24.04.5 x64/Python 3.12.14, macOS 26.6.2 arm64/Python 3.12.10 and Windows Server 2025 x64/Python 3.12.10 each passed **235 Python tests**, Ruff, nine R files, C-helper source installation and the Python/RDS/R downstream example, without Python skips. Pytest seconds in that order: 62.62 / 49.90 / 82.62; these are not imputation benchmarks.

R 4.5.3 and exact Amelia 1.8.3 were verified. Torch was 2.14.0 on Mac and 2.14.0+cpu elsewhere. Nine R files: bridge, compatibility, torch-compat, public-edge-cases, autopri-boundary, reference-parallel, reference_metadata, downstream and downstream_extended. The commit includes G3/G4/autopri/G7 work.

Pathological autopri reference/hybrid code, update count and fixed-hold checks respectively were: Ubuntu `(2,0,0)/(2,3,3)`; Mac `(2,2,2)/(1,3,3)`; Windows `(2,0,0)/(1,1,1)`. Original R did not trigger correction on Linux/Windows: coverage is partial. Engine/BLAS histories may differ; code 1 alone does not prove convergence. These pathological cases are not valid inference samples.

Python snow2 and caller-owned R snow clusters ran on all systems. Unix multicore ran on Mac/Linux; Windows explicitly skipped fork. Hybrid remains serial. Source hashes for 94 files came from verified commit blobs, not runtime fingerprints of installed files. Raw runner paths, worker IDs and full logs remain private.

This is fresh source-install CPU regression, not R CMD check, a three-platform wheel matrix, GPU or GUI validation. The separate Intel wheel at ad9bed2 retains its own scope. Setup requires R dependencies and the project R package before integration tests; exact Amelia version checks do not lock every dependency. Later source or documentation changes do not rewrite these results.

## Records

This report describes the dated run and measured source below. Later project status is recorded in the [evidence summary](../2026-09-27-evidence-summary.md).

[cross-platform-ci-e2ff892.json](cross-platform-ci-e2ff892.json) · [cross-platform-ci-e2ff892.sha256.json](cross-platform-ci-e2ff892.sha256.json) · [cross-platform-ci.json](cross-platform-ci.json) · [SHA256SUMS.json](SHA256SUMS.json)
