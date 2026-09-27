# G1 downstream methods

[简体中文](downstream-extended.zh-CN.md) · [Documentation](../../README.md)

On 2026-09-26, `downstream_extended.R` completed without skipped branches on Mac arm64, R 4.5.3/Amelia 1.8.3/ameliatorch 0.0.0.9000, Python 3.12.13/Torch 2.14.0, hybrid CPU64. It added small API checks without changing fitting code; the subsequent seven-file R package check passed. Hosted checks of later commits are separate evidence.

Coverage: ameliabind on two m=2 results, preservation of all four old draws and original errors for differing missingness/empri; transform interaction plus m=1 append and archived calls; with/lm→mi.combine with both interval modes at 0.90; summary/compare/overimpute PDFs; separate tab-delimited tables and combined DTA with factor labels, custom draw_id and orig.data=FALSE; four 60-row moPrep branches (error.proportion, subset/gold.standard, proxy formula, existing molist augmentation); actual Python/RDS/R/Python readback. Unknown backend after original bind stays unknown.

The main synthetic input has 72 rows, a/b/y, ID and factor. Tolerances: theta 1e−7, results/downstream 1e−6, export readback 1e−12, analytic prior SD 1e−14; old data/categories/masks/model arguments use strict equality. broom 1.0.12 passed; a private dependency-probe environment also triggered the original missing-broom error without uninstalling packages. This is fault injection, not a clean missing-dependency OS.

Preserved upstream behavior: mi.combine reverses confidence endpoints and can return signed-tail p-values>1; compatibility does not validate their interpretation. Specify separate=TRUE when forwarding sep to table export, bind foreign:: write.dta in the caller for DTA, and load Amelia's namespace before S3 generics after readRDS. Reference and hybrid examples both completed RDS/CSV/PDF/JSON roundtrips. PDF structure checks are not GUI visual review; this gate does not establish inference/GPU quality.

## Records

This report describes the dated run and measured source below. Later project status is recorded in the [evidence summary](../2026-09-27-evidence-summary.md).

[downstream_extended.R](../../../r-package/tests/downstream_extended.R) · [downstream.R](../../../r-package/tests/downstream.R) · [python_r_downstream.py](../../../examples/python_r_downstream.py) · [downstream-extended.json](downstream-extended.json)

```sh
R_LIBS_USER="$PWD/.R-library" RETICULATE_PYTHON="$PWD/.venv/bin/python" \
  Rscript r-package/tests/downstream_extended.R
```
