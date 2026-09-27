# G2 public CPU64 boundaries

[简体中文](README.zh-CN.md) · [Documentation](../../README.md)

2026-09-26, Apple Silicon/R 4.5.3/Python 3.12.13/Torch 2.14.0/Amelia 1.8.3: 33 public-edge cases, seven R files and 26 Python reference/public/hybrid checks passed. These are bounded correctness checks, not GPU performance/inference.

## Start-value semantics

Upstream startval returns valid explicit theta directly; C++ views its double allocation without copying and writes final theta back. The earlier hybrid returned a new theta without mutating caller/archived/subsequent-replicate state. A registered C helper now preserves that behavior, saving initial allthetas first. Integer inputs retain original integer buffers; complete-bootstrap shortcuts ignore and do not modify theta. Native Python inputs remain unchanged; no RNG or EM formula changed.

For 80×3, seed 77, tolerance 1e−6, autopri 0, m=2, original/hybrid iterations were double/none 10,1; integer/none 10,10; double/ordinary 10,9; integer/ordinary 9,11. Default/identity initialization, aliases, arglist/append and subsequent runif/rnorm also matched.

## Other boundaries

Minimum 35 and maximum 2 iterations matched history; cutoff metadata/warnings explicitly report nonconvergence despite original code 1. A 24×2 fixed bootstrap became complete (sample covariance, NA history, no writeback); another actually rejected an empty column then accepted the second draw. Private recorders saved indices without extra RNG or namespace changes and matched uninstrumented calls.

Entirely missing rows remain NA; default complete input code 39 and unchecked shortcut, empty-column/constant/sample-size codes 4/43/34, narrow bounds [100,100.001] with nine actual clamped cells, and max.resample 0 code 52 matched. incheck=False, collect=True, p2s=1/2 retained statistical behavior; progress explicitly labels Torch, and original validation's RNG consumption is preserved.

## Pathological autopri

A separate seed 7,200×5 exact-collinear 40%-missing case leaves n=197 after empty-row removal. boot.none, startvals 1, empri 0, autopri=0.05, tolerance 1e−15, emburn 300/300 produced original updates at 216/217/219/293/296 (final 5) and hybrid 216/217/219 (final 3). Eight same-engine one-step replays verified fixed initial hold 0 to<1e−10 and differed from the incorrect current-empri ridge formula by at least about 0.00488.

Original ended code 2; hybrid code 1 but correctly warned/recorded unconverged. This is not successful imputation equivalence. Other BLAS may not trigger the branch; report partial coverage rather than fabricate updates. Later MPS edge evidence is separate; CUDA's new edge script remains unexecuted. Historical downstream-test hashes predate the R_TESTS harness correction, whose executed version is in G1 packaging.

## Records

This report describes the dated run and measured source below. Later project status is recorded in the [evidence summary](../2026-09-27-evidence-summary.md).

[public-edge-cases.R](../../../r-package/tests/public-edge-cases.R) · [public-edge-cases.json](public-edge-cases.json) · [r-tests.json](r-tests.json) · [summary.json](summary.json) · [autopri-boundary.R](../../../r-package/tests/autopri-boundary.R) · [public-autopri.json](public-autopri.json)

```sh
R_LIBS_USER="$PWD/.R-library" R CMD INSTALL --clean --library=.R-library r-package
R_LIBS_USER="$PWD/.R-library" RETICULATE_PYTHON="$PWD/.venv/bin/python" \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  Rscript r-package/tests/public-edge-cases.R
.venv/bin/python -m pytest -q tests/test_hybrid_reference.py tests/test_reference.py tests/test_public_reference.py
```
