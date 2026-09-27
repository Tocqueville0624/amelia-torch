# Release criteria

[简体中文](release-gates.zh-CN.md) · [Documentation](README.md)

Status: 2026-09-27. The first complete release may combine original-R reference, hybrid and native-subset routes, provided dependencies and execution boundaries are explicit. Original R graphics do not need Python reimplementation; delegated CPU features must not be described as native GPU work. The current public snapshot has not completed acceptance.

## Interface inventory

The original exports include amelia/default/molist, ameliabind, transform.amelia, with.amelia, mi.combine, mi.meld, moPrep, compare.density, overimpute, disperse, tscsPlot, missmap, write.amelia and AmeliaView; registered methods include append, print/summary and plots. Internal `allthetas` is not a public `amelia.default` argument. See [compatibility](amelia-compatibility.md) for option-level status.

## Acceptance record

| Gate | Completed bounded scope | Remaining requirement |
|---|---|---|
| G1: downstream methods | Bind/error cases; transform then append; with/lm and both mi.combine interval modes; four moPrep branches; summary/plot; CSV/table/DTA readback; actual Python/RDS/R example | These methods remain original R CPU. Preserve upstream interval/p-value quirks; PDF file checks are distinct from visual checks |
| G2: public EM boundaries |33 CPU64 cases: initial values/writeback, min/max iterations, complete bootstrap, actual rejected resampling, bounds exhaustion, empty rows and original error codes; Mac pathological autopri audit; eight MPS32 edge assertions | Equivalent bounded CUDA32/64 edge script not yet executed. Mac pathological output/status differs and is not a valid quality sample; untriggered Linux/Windows branches remain uncovered |
| G3: Python/R types and sessions | Numeric and noms fits/RDS; nullable empty IDs, Unicode, duplicate index; explicit unsupported dtype and dependency failures; Unicode/space environment paths; frontend rejection | No general Arrow, extension-dtype or interactive GUI claim; original RDS is authoritative |
| G4: reference parallelism | Python snow2 library inheritance/repeatability/worker error; caller-owned R cluster and subsequent RNG; Unix multicore | Hybrid stays serial; Windows explicitly skips Unix fork and uses snow. A GPU replicate scheduler is not an added release prerequisite |
| G5: inference | Mac five-route 2,100 calls/10,500 fits, all converged; MAR and bounded stress passed | MCAR frozen criteria did not all pass; CUDA protocol not run. Do not mark accepted |
| G6: platforms and interactive use | `ef729c0` Windows/macOS/Linux CPU: 307 Python, nine R files and example each; Intel no-Torch isolated reference wheel; Mac installed RStudio workflow; T4/3080 fixed CUDA and performance evidence | New CUDA edge checks and inference remain; Windows GUI and original AmeliaView not validated. Source installation and isolated wheel evidence have different scopes |
| G7: performance | Three 100k-row datasets: complete Mac native/hybrid and Windows 18+12 configurations; T4 native 18 complete/hybrid 11 of 12 recovered; separate Python full-call and independent-MCAR stress records | Total process RAM/VRAM and capacity/OOM limits unmeasured. Retain null telemetry, narrow-input slowdowns and partial T4 status |
| G8: reproducible distribution | Fixed reference source/hash, GPL attribution, licensed samples/downloads, scripts and audited records public | Update final claims only after applicable remaining gates close; no complete-release tag, PyPI or CRAN claim yet |

## Statistical limits

Mac G5 used the frozen protocol, not thresholds fitted to results. Original R and hybrid MCAR coverage upper 90% interval was 99.009876%, slightly above 99%; native's paired lower bound was −5.028703 percentage points, below −5. CPU/MPS classifications agree. Independent record validity is not statistical acceptance. The separate 1,000-MCAR proposal remains unexecuted and is not an automatic new requirement or replacement for failed results.

Retain the original MCAR/MAR generators, seeds, minimum 200-replicate screen and prespecified bias/coverage/width/Monte Carlo comparisons. Include bounded high-correlation/high-missingness stress and all nonconvergence, pseudoinverse, correction, nonfinite and OOM outcomes. There is no requirement to enumerate every possible parameter combination or force a positive GPU result.

## Product and timing limits

Windows `810591e` completed 210 calls/1,050 imputations with limited quality audits passing. That does not complete G5. T4's missing YearCUDA32 result stays unknown; replacement-host failures do not repair the old suite.

G7's Python reference/hybrid CPU64 full calls on Covertype 100k included new Rscript startup and binary/RDS transport: first calls approximately 12.144/11.966 s, later medians 11.959/12.128 s (two each). No OS cache reset was used; subtracting older R-memory timings does not measure bridge overhead. Household 5000×7 independentMCAR retained two all-missing rows, leaving 14 heldout cells unscored per imputation. RMSE is null, status heldout_incomplete and exit 1 despite convergence; these are stress records, not successful quality-speed samples.

A standard RStudio package workflow does not imply rewriting or GPU-enabling AmeliaView. If AmeliaView is advertised as validated, record an actual original-GUI launch/load/close in a suitable Tcl/Tk environment. Current Mac Data Viewer/plot evidence is separate.

## Evidence links

[G1](validation/2026-09-26-g1/downstream-extended.md) · [G2](validation/2026-09-26-g2/README.md) · [G3](validation/2026-09-26-g3/README.md) · [G4](validation/2026-09-26-g4/README.md) · [G5](validation/2026-09-26-g5-mps/README.md) · [G6](validation/2026-09-26-g6-rstudio/README.md) · [G7](validation/2026-09-26-g7/README.md) · [Windows](validation/2026-09-27-windows-rtx3080/README.md).

Close a gate with its executed report and source identity, reusing already adequate evidence. Full raw datasets need not enter Git: attributed samples plus fixed download scripts satisfy the data-distribution design. No further fitting or test budgets are scheduled during the current evidence-documentation phase.
