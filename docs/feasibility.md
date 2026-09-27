# Feasibility and prior art

[简体中文](feasibility.zh-CN.md) · [Documentation](README.md)

Initial assessment: 2026-09-23. This report describes the original rationale and environment checks. Later [Windows/Mac/T4 results](validation/2026-09-27-evidence-summary.md) supersede its initial hardware uncertainty. The current license is GPL-3.0-only.

## Contributions

The engineering scope is a verifiable PyTorch backend for Amelia-style bootstrap–EM, with Python/R interfaces and measured performance boundaries. It can demonstrate numerical implementation, reference testing, packaging and reproducible evaluation. The statistical estimator is established prior work; neither a new estimator nor the first GPU imputation system is claimed. A wrapper or isolated matrix-multiplication benchmark alone would not establish a useful accelerator.

Amelia resamples rows, estimates a multivariate-normal model with EM, then samples missing values on the original input. It is not gradient-based neural-network training. Its [method paper](https://www.jstatsoft.org/article/view/v045i07), [documentation](https://iqss.github.io/Amelia/articles/using-amelia.html), [C++ core](https://github.com/IQSS/Amelia/blob/master/src/em.cpp) and [parallel API](https://iqss.github.io/Amelia/reference/amelia.html) establish a compiled, CPU-parallel baseline. Python is not inherently the faster baseline. Complete compatibility includes categories, transformations, time/cross-section terms, priors, bounds and diagnostics; the continuous implementation is a development subset, not a complete first release.

## Related work

| Project | Existing scope | Distinction examined here |
|---|---|---|
| [Amelia](https://github.com/IQSS/Amelia) | EMB, C++ core, CPU parallelism, R workflow | Torch CPU/CUDA/MPS and precision/performance comparisons |
| [MIDASpy/rMIDAS](https://www.jstatsoft.org/article/view/v107i09) | Neural multiple imputation and GPU-capable implementation | Preserve EMB rather than compare different estimators as an equivalent speedup |
| [impyute](https://impyute.readthedocs.io/) | Python imputation, including an EM-labeled method | Verify joint conditional moments, bootstrap and random-draw semantics |
| [Autoimpute](https://github.com/kearnz/autoimpute) | Python single/multiple imputation and analysis | Not identified in the initial search as an Amelia GPU port |
| [PyPOTS](https://pypots.com/ecosystem/) | Time-series imputation models and evaluation | Different model families, not automatic EMB equivalents |

The initial search used Amelia/Python/GPU, Amelia/torch, bootstrap/EM/Python and Amelia/CUDA queries, including GitHub. No mature project explicitly combining Amelia EMB, PyTorch GPU and an R interface was identified. This bounded search is not proof that no related repository exists; names and related projects need review before a release.

## Computational hypotheses

Dense conditional-moment and sufficient-statistic calculations may benefit from GPU execution. Reusing factorizations within missingness groups and bounded replicate batching may help. Iterations depend on previous states; many unique patterns create small operations, while transfer, synchronization and interface overhead can outweigh gains. Original CPU parallelism is an essential comparator. Profiling is needed to attribute costs; negative results remain useful evidence.

## Development environment

The initial Mac was an Apple M4 iMac, 8 CPU/8 GPU cores, 16 GB unified memory, macOS 26.6.2 arm64. Existing R 4.5.3, RStudio, Git, command-line tools, uv and Python 3.12.13 supported local development. The project installed Torch 2.14.0, NumPy 2.5.3, SciPy 1.18.1, Amelia 1.8.3 and reticulate 1.47.0 in local environments. CPU64/32 operators, MPS32 matrix multiplication/Cholesky/solve/reduction/indexing/normal draws, R→Python→MPS, and a 200×3 original-R example passed initial checks. These small probes did not establish complete EM correctness or speed.

MPS lacks float64; CPU64 is the reference. Restricted processes initially hid MPS, while a permitted native process exposed it. Reticulate must retain the virtual-environment interpreter symlink. Initialization had about 24 GiB free disk; this is a historical observation, not a current capacity claim.

## CUDA and R delivery

RTX 3080 is a CUDA-capable target with limited FP64 relative to FP32; marketing FP32 throughput does not predict double-precision gains. [NVIDIA architecture paper](https://www.nvidia.com/content/PDF/nvidia-ampere-ga-102-gpu-architecture-whitepaper-v2.pdf). Its Windows installation and benchmarks were subsequently executed and recorded separately. Compare R serial/parallel and Torch CPU/CUDA on the same host; Mac CPU versus Windows GPU is not an isolated GPU speedup.

A standard R package using [reticulate](https://rstudio.github.io/reticulate/articles/package.html) provides RStudio access without an IDE plugin. Preserve names, order, observations, multiple outputs and diagnostics; record [conversion costs](https://rstudio.github.io/reticulate/articles/calling_python.html). Native objects must not impersonate official classes.

## Licensing and evidence

Amelia declares GPL(>=2); the project subsequently selected GPL-3.0-only and retains attribution in [THIRD_PARTY](../THIRD_PARTY.md). Experiments use synthetic or clearly licensed public data. Published records exclude private paths, machine serials and confidential work data. Performance conclusions are limited to the recorded workloads and measurement conditions.
