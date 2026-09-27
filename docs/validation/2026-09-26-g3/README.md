# G3 types and sessions

[简体中文](README.zh-CN.md) · [Documentation](../../README.md)

On 2026-09-26 Mac arm64/Python 3.12.13/R 4.5.3/Amelia 1.8.3/Torch 2.14.0,29 new cases plus 17 reference and 7 hybrid cases passed: 53/53, no skips, 29.11 s. Per-file hashes identify the working source, including frontend changes after fa08a52.

Reference/hybrid each ran numeric and nominal models with nullable empty integer/string IDs, Unicode names/categories and duplicate Python index. RDS was read by independent original R and Python. In-memory duplicate indices remain; RDS rereading does not invent Python-only metadata. External Date/custom numeric IDs become plain Python strings/numbers while authoritative RDS retains original classes/attributes.

Datetime, complex, mixed-object and sparse inputs fail explicitly; Arrow is not generally accepted. Missing Rscript, wrong Amelia version, missing hybrid DLL/Torch and unavailable CUDA fail without switching devices. Temporary copies/import injection preserve installed libraries. A Unicode/space venv and R-library path actually completed hybrid CPU64 using shared dependencies via PYTHONPATH; it was not a clean dependency installation.

The defect fixed here allowed frontend=True to reach a subprocess without the required shared R/Tcl/Tk GUI state. `_invoke` now rejects anything except omitted/Boolean False before starting R, including extend/RDS/arglist paths. Tests intercept process starts; no GUI was opened. Normal False/default behavior remains.

Independent R confirmed integer-empty IDs promote to double and a bounded noms case returns an empty character ID as string 1; all-missing analysis rows remain NA. These are upstream outputs, not bridge corrections. Discovery counts 9 pass/6 fail, 25/2,25/4 and final 53 passed remain in summary; causes distinguish the real frontend bug from incorrect test assumptions/library setup. A later standalone 10-case guard check passed without R-required skips. This local report does not certify later hosted code; subsequent CI is linked separately.

## Records

This report describes the dated run and measured source below. Later project status is recorded in the [evidence summary](../2026-09-27-evidence-summary.md).

[summary.json](summary.json) · [pytest.txt](pytest.txt)

```sh
python -m pytest -q tests/test_reference_boundaries.py tests/test_reference.py tests/test_hybrid_reference.py
ruff check src/amelia_torch/reference.py tests/test_reference_boundaries.py
```
