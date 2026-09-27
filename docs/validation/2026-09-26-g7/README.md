# G7 Python call costs and MCAR stress

[简体中文](README.zh-CN.md) · [Documentation](../../README.md)

Nine planned public calls, m=5 each, completed 2026-09-26 UTC 22:07:03–22:09:03 on M4/Mac arm64, Python 3.12.13/NumPy 2.5.3/Torch 2.14.0/R 4.5.3/Amelia 1.8.3. The plan predates fitting and pins input hashes, 16 source files, order and quality rules. The workspace was dirty, so recorded fingerprints/source ZIP—not the background commit label—identify measured code.

All used seed 20260926, L'Ecuyer-CMRG/Inversion/Rejection, ordinary bootstrap, startvals 0, tolerance 1e−4, emburn 0/300, autopri=0.05, empri NULL, serial replicates. Thread variables requested 4, not measured every BLAS pool. CPU64 and explicit MPS32/fallback 0 retain CPU eigenvalue checks.

Full Python timing runs from in-memory array through typed transfer, new Rscript, R imports, hybrid Python/Torch initialization, imputation, CPU results/RDS bytes, child exit and temporary cleanup. Parent imports, NPZ reads, scoring, hashing and later save_rds are outside. Every call starts a new R process; first/later means parent-call order, not cold OS or persistent R. Background load was not fully isolated. Older R-memory timings are not paired and cannot be subtracted as bridge cost.

| Covertype 100k×10, blockMCAR30%, 8 patterns | First | Later 1 | Later 2 | Later median |
|---|---:|---:|---:|---:|
| Reference |12.144 s|12.114 s|11.804 s|11.959 s|
| Hybrid CPU64 |11.966 s|12.047 s|12.210 s|12.128 s|

All six calls passed convergence, observations and 300,000 heldout scores, with iterations 52/41/43/72/59. Each engine's three RDS hashes matched internally, not necessarily across engines. Output arrays total 40,000,000 bytes; RDS 18,627,244/18,628,077 bytes. Sizes are not peak memory; two later repeats cannot establish a stable 1% difference.

| Household 5000×7, independentMCAR | Full call | Unscored heldout per imputation | Status |
|---|---:|---:|---|
| Reference |.561 s|14|heldout_incomplete|
| Hybrid CPU64 |2.812 s|14|heldout_incomplete|
| Hybrid MPS32 |24.271 s|14|heldout_incomplete|

Masking 29.7057%, 125 patterns, 10,397 heldout includes two entirely missing rows. They remain NA by original semantics; masks/rows were not repaired for scoring. All fits converged(18/14/15/16/12), observations stayed exact, and other fills were finite. FullRMSE isnull; hybrid fit-pattern counts 124/124/122/124/124, no pseudoinverse/correction/warning/OOM. One call per route and differing precision do not support a quality-success speedup or causal pattern-scaling curve.

All 45 fits returned/converged and source/input guards held. Driver exit 1 records incomplete stress scoring; independent audit passes record integrity while all_runs_valid_for_speed_comparison=false. Total RAM/VRAM remainsnull. This report includes noCUDA or inference-equivalence claim. New runs require a fresh plan/output directory; audit even the expected stress failure.

## Records

This report describes the dated run and measured source below. Later project status is recorded in the [evidence summary](../2026-09-27-evidence-summary.md).

[plan.json](plan.json) · [measured-source.zip](measured-source.zip) · [source-snapshot.json](source-snapshot.json) · [manifest.json](../../../data/manifest.json) · [results.json](results.json) · [audit.json](audit.json) · [validate_product_costs.py](../../../scripts/validate_product_costs.py) · [test_product_costs.py](../../../tests/test_product_costs.py)

```sh
.venv/bin/python scripts/prepare_benchmark_data.py --dataset covertype --rows 100000 --mechanism block_mcar --missing-rate 0.3 --seed 20260923 --output data/prepared/covertype-n100000-block_mcar-rate30-seed20260923.npz
.venv/bin/python scripts/prepare_benchmark_data.py --dataset household_power --rows 5000 --mechanism mcar --missing-rate 0.3 --seed 20260923 --output data/prepared/household_power-n5000-mcar-rate30-seed20260923.npz
.venv/bin/python scripts/validate_product_costs.py --write-plan results/local/g7-new/plan.json
.venv/bin/python scripts/validate_product_costs.py --execute results/local/g7-new/plan.json --output results/local/g7-new/results.json
# Expected exit 1 for unscored entirely missing rows; retain the audit.
.venv/bin/python scripts/summarize_product_costs.py results/local/g7-new/plan.json results/local/g7-new/results.json --output results/local/g7-new/audit.json
```
