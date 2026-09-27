# Colab environment recovery and interruption

[简体中文](README.zh-CN.md) · [Documentation](../../README.md)

**Cloud experiments were paused after the GPU quota was exhausted.** This directory preserves environment recovery and failure records; it is not a CUDA acceptance result. The replacement VM used algorithm source `ef729c093e162f4d6ebd797c95a9da8072ac968a`. Its records were not merged into the old performance experiment.

The public notebook template came from `b4f0b14683e4e92cfb43ccd91a40cf95746fecba`, file SHA-256 `aa10c6c58db14c0cc851e1ce36f19791057665b1b2498cef767098cef6e83ae3`. Only initialization, installation planning, installation and the correctness stage were started. The complete template was not successfully executed. Retries used separate directories and retained previous failures.

## Recorded stages

| Stage | Result |
|---|---|
| Installation plan | Completed with Amelia 1.8.3 and its archive hash pinned. |
| Initial installation | Failed after apt upgraded R to 4.6.1. Preinstalled Rcpp headers and vctrs binaries were incompatible, producing R_Namespace Registry / SETLENGTH errors. |
| R baseline recovery | Restored official CRAN apt version 4.5.3-1.2204.0. The plan downgraded four R packages without removing packages; the failed library was renamed and preserved, and an empty project library was created. |
| Installation retry | Passed without another system upgrade; algorithm source was unchanged. |
| First validation attempt | CUDA probe and Ruff version lookup passed. Ruff 0.15.8 reported E402 for imports following dynamic loading, stopping the run. |
| Ruff alignment | Installed official PyPI Ruff 0.16.8 in the project environment, matching the locally validated version. No lint rules were ignored or algorithm changes made. |
| Second validation attempt | Probe, version lookup and lint passed; 306 Python tests passed and one failed. The run stopped before the nine R files, later CUDA edge cases and G5. |

The failure was test_unicode_space_python_and_r_library_paths_execute_actual_hybrid. Its temporary interpreter, in a path containing Chinese characters and spaces, raised ModuleNotFoundError when importing NumPy, before the imputation call. The test supplied the project's purelib path, while this Colab environment used shared dependencies. This cloud dependency-inheritance gap was not repaired and retested. The 306 passing tests remain valid recorded executions, but the suite did not pass.

A later local import-style change passed 49 related tests before the pause; it was not part of the fixed ef729c0 cloud run. An R installation guard remains an unvalidated local draft. The installer issue is unresolved. Rcpp's R 4.6 API adaptation has an [upstream issue](https://github.com/RcppCore/Rcpp/issues/1468); the archived compiler logs are the evidence for this failure.

## Records

[recovery-summary.json](recovery-summary.json) identifies seven recoverable checkpoints and their stages. The [archive](recovered-stage-records.tar.gz) contains 54 recovered text files, totaling 79,449 compressed bytes. SHA-256: `8cdf7a06e01a5eac4212edd5490eda119246343aad84604977c6d81ba2a3acee`.

Each stage retains a separate manifest, log and exit status. [archive-index.json](archive-index.json) lists payload sizes and hashes; packaged files were read back and matched the recovered bytes. Original checkpoint envelopes remain local. The public archive contains readable recovered records with normalized container metadata and unchanged failure statuses.

![Colab GPU quota notification](colab-quota.jpg)

The screenshot, taken at the pause without account identifiers, establishes GPU unavailability at that time. It does not establish why the earlier VM disappeared or the outcome of its final Year CUDA32 call. No paid compute, CPU continuation or additional 1,000-replicate MCAR study followed.

See the limited [privacy review](privacy-review.json), [file checksums](SHA256SUMS.json) and [evidence summary](../2026-09-27-evidence-summary.md).
