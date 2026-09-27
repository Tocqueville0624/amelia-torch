# Accelerator edge protocol and CPU64 check

[简体中文](accelerator-edges.zh-CN.md) · [Documentation](../../README.md)

The 2026-09-26 CPU64 dry run of `validate_r_accelerator_edges.R` passed seven ordinary public cases, one pathological case and a separate CPU64 allthetas/alias check. This report itself is not a GPU execution; the subsequent MPS run has its own report.

Normal data use R seed 6101,80×3, fitseed 77. Cases cover startvals 1 ordinary/none m=2, explicit double ordinary/none m=2, integer no-writeback, minimum 35 and maximum 2 iterations. Each engine receives deep-copied input/theta.

| Precision | EM tolerance | Theta bound | SD-scaled output bound |
|---|---:|---|---|
| float64 |1e−6|1e−7+1e−7×abs(reference)|1e−6+1e−7×abs(reference)|
| float32 |1e−5|1e−5+1e−4×abs(reference)|1e−5+1e−4×abs(reference)|

Bounds were fixed before GPU execution, without a result-driven relaxation option. Assertions cover observations, finite fills, class/mask, device/dtype, caller/archive alias, R-visible seed and later draws. Normal cases require convergence; the two-iteration cutoff requires a warning and nonconvergence. Full floating histories need not match.

The pathological seed 7,200×5 case has column 5=column 1+column 2 and 400 masked cells, fitseed 102, autopri=0.05, empri 0,300 iterations. Check each engine's own final eigenvalue rule, code, output and diagnostics; do not demand identical near-singular trajectories. CPU64 original code 2/empri 5 and hybrid code 1/empri 3 were both unconverged. Missing adaptive-branch coverage must be explicit.

The internal allthetas oracle always runs CPU64 and is not GPU coverage or a new public argument. Scripts reject MPS64, force MPS fallback 0, preserve partial JSON on failure and exit nonzero. No timing/peak-memory or inference conclusion follows.

## Records

This report describes the dated run and measured source below. Later project status is recorded in the [evidence summary](../2026-09-27-evidence-summary.md).

[r-accelerator-edges-cpu64.json](r-accelerator-edges-cpu64.json)

```sh
Rscript scripts/validate_r_accelerator_edges.R cuda float64 results/local/edges-cuda64.json
Rscript scripts/validate_r_accelerator_edges.R cuda float32 results/local/edges-cuda32.json
Rscript scripts/validate_r_accelerator_edges.R mps float32 results/local/edges-mps32.json
```
