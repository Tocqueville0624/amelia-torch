# G2 MPS32 public boundaries

[简体中文](accelerator-edges-mps32.zh-CN.md) · [Documentation](../../README.md)

At `33220cfeee0ffc262b523adac1bff64dc5a624dc` on 2026-09-26, all eight prespecified assertions passed on installed Mac Python/R packages, exit 0, with unchanged scripts/thresholds. This is seven normal/iteration cases plus one pathological case, not all 33 CPU cases or CUDA/inference/performance acceptance.

Environment: Mac arm64, R 4.5.3/Amelia 1.8.3/reticulate 1.47.0, Python 3.12.13/Torch 2.14.0. EM used MPS32 with fallback 0; eigenvalue checks and original R workflow remained CPU. Normal EM tolerance 1e−5, theta and SD-scaled output bound 1e−5+1e−4×abs(reference).

Normal histories matched: identity none 8/8, ordinary 8/9; double none 8/1, ordinary 8/7; integer none 8/8; minimum 35 and maximum 2. Max theta difference 1.383e−7 and scaled output 2.370e−7 (about 1.01% of its bound). Observation/mask/class/alias checks, visible seed and subsequent runif/rnorm passed. The two-step case correctly warned unconverged despite original code 1.

Exact-collinear stress ran 300 iterations unconverged and code 2 in both engines. Original updates 216/217/219/293/296 ended empri 5, min eigenvalue−1.6042e−15; MPS updates 103/221/257 ended empri 3, min eigenvalue−4.6052e−8,423 pseudoinverses and 31 fit patterns. Trajectory differences are retained, not quality success.

Of 13 hybrid EM fits, 11 converged; cutoff and pathological cases did not. `all_checks_passed=true` includes correct failure handling. The allthetas oracle remained CPU64. Checkout source fingerprints matched before/after and the commit, not rehashed installed binaries. No peak-memory/timing study occurred.

## Records

This report describes the dated run and measured source below. Later project status is recorded in the [evidence summary](../2026-09-27-evidence-summary.md).

[validate_r_accelerator_edges.R](../../../scripts/validate_r_accelerator_edges.R) · [r-accelerator-edges-mps32.json](r-accelerator-edges-mps32.json) · [r-accelerator-edges-mps32.log](r-accelerator-edges-mps32.log) · [r-accelerator-edges-mps32-audit.json](r-accelerator-edges-mps32-audit.json) · [accelerator-edges-mps32-sha256.json](accelerator-edges-mps32-sha256.json)

```sh
R_LIBS_USER="$PWD/.R-library" RETICULATE_PYTHON="$PWD/.venv/bin/python" \
  PYTORCH_ENABLE_MPS_FALLBACK=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
  Rscript scripts/validate_r_accelerator_edges.R mps float32 \
  results/local/g2-mps-edges-20260926.json
```
