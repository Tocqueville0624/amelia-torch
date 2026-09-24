# Contributing

This repository is developing a faithful Amelia 1.8.3 implementation and compatibility interfaces. A complete first release requires the full agreed feature set, verified installation and correctness, and honest platform-specific performance evidence. A passing kernel test does not satisfy that release gate.

Start with [AGENTS.md](AGENTS.md), the [algorithm contract](docs/algorithm-contract.md), and the [compatibility matrix](docs/amelia-compatibility.md). Record upstream sources and GPL attribution for each ported feature. Do not silently change statistical methods, precision, defaults, unsupported arguments, or missing-data handling.

Develop in an isolated Python environment and project R library. Before submitting a change, run relevant Python and R tests. New feature tests should compare the original fixed-version implementation and cover meaningful edge cases, rather than merely restating the new code. Cross-language random tests need explicit random input or distributional checks; equal seeds alone do not pair R and NumPy streams.

Performance runs are separate from tests and package installation. Run compared implementations sequentially, preserve every run and failure, synchronize accelerators, and record code, environment and dataset fingerprints. Do not alter measured source files mid-suite. Keep negative performance results. Record all CPU work in GPU/hybrid paths.

Do not commit virtual environments, local R libraries, private data, raw large archives, machine identifiers, or logs containing personal paths. Public data samples and derived results need their original attribution and separate license. Full data are reproduced with the pinned download scripts.

Maintainer and future collaboration arrangements are in [CONTRIBUTORS.md](CONTRIBUTORS.md). Contributions are made under the project's GPL-3.0-only license. Do not add another person as an author or collaborator before their participation is confirmed.
