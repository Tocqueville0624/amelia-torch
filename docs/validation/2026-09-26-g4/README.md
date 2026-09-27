# G4 reference parallelism

[简体中文](README.zh-CN.md) · [Documentation](../../README.md)

2026-09-26, Mac/R 4.5.3/Amelia 1.8.3: real small-process checks retained original CPU statistics without modifying the core or measuring GPU scheduling/speed.

Python snow2 used 96×3, m=3, seed 9127, L'Ecuyer-CMRG through explicit r_library, project-default discovery and inherited R_LIBS_USER (automatic discovery disabled for that case). All three calls matched elementwise, retained observations, filled finite outputs and converged; imputations were distinct. An invalid length-two boot.type under incheck=False caused an actual worker bootx error, propagated as AmeliaReferenceError without fabricated successful RDS.

R caller-owned two-worker PSOCK clusters matched original results and subsequent runif(6), retained the same live workers, and were closed by the caller. Unix multicore 2, m=3 matched original output. Windows explicitly skips fork and uses snow/serial; hybrid remains serial without implicit engine switching.

Two Python cases passed in 1.86 s, a test duration not a benchmark. An initial restricted context blocked localhost sockets before execution; a permitted context then ran the checks. This is a local record; later three-platform CI supplies separate evidence.

## Records

This report describes the dated run and measured source below. Later project status is recorded in the [evidence summary](../2026-09-27-evidence-summary.md).

[test_reference_parallel.py](../../../tests/test_reference_parallel.py) · [reference-parallel.R](../../../r-package/tests/reference-parallel.R) · [r-parallel.json](r-parallel.json) · [summary.json](summary.json)

```sh
.venv/bin/python -m pytest -q tests/test_reference_parallel.py
R_LIBS_USER="$PWD/.R-library" Rscript r-package/tests/reference-parallel.R
```
