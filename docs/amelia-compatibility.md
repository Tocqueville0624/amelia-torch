# Amelia 1.8.3 compatibility

[简体中文](amelia-compatibility.zh-CN.md) · [Documentation](README.md)

Status: 2026-09-27. This is a development snapshot, not a complete replacement. Reference means unmodified R Amelia on CPU; hybrid retains its workflow and replaces EM; native is a continuous-data implementation. [Algorithm contract](algorithm-contract.md) defines version-specific semantics.

| Feature | Native | Hybrid/reference evidence and limits |
|---|---|---|
| Standardization, conditional moments, EM, symmetric theta | Implemented; CPU64 reference fixtures | Hybrid CPU64 public parameters/history checked |
| `startvals=0/1`, explicit theta | Implemented; native input unchanged | Public ordinary/none m=2 checked; double mutation, integer coercion, archived alias and initial history preserved |
| Complete bootstrap shortcut | Sample covariance n−1; ignores empri/theta | Public sampled case checked; history NA and no initial-value writeback |
| `tolerance`, `emburn` | Upper-triangle rule and min/max iterations | 35-iteration minimum and two-iteration cutoff checked; warnings/metadata distinguish nonconvergence |
| `empri`, `autopri` | Integer truncation, p+2 denominator, fixed initial hold | Public CPU64 correction exercised on Mac; near-singular histories/status differ and are not valid quality samples; branch not triggered in Linux/Windows original R |
| Low-level cell priors | Standardized mean/variance supported | Original preprocessing supplies coordinates; representative CPU/MPS cases |
| Public four/five-column priors, row 0 priority | Unsupported | Representative original-R preprocessing cases; single-row upstream exception retained |
| `ordinary` and `boot.type="none"` | Supported (`boot_type` in Python), NumPy RNG | Public rejection/resampling and R RNG states checked, including Inversion/Box–Muller and subsequent draws |
| Conditional random imputation | Explicit-normal fixture checked | Original R/C draws retained |
| Observed values, order, entirely missing rows | Preserved; entirely missing rows remain missing | Public/G3 and benchmark checks; documented upstream exceptions retained |
| Empty/one-observation/constant columns; fully observed input | Explicit checks, including codes 4/43/39 | Bounded public codes 4/43/34/39 and unchecked complete-input case checked |
| `idvars`, `logs`, `sqrts`, `lgstc` | Unsupported | Representative CPU64 cases; log inverse exception preserved |
| `noms`, `ords` | Unsupported | Factor/ordered-factor cases checked using original stochastic reconstruction |
| `ts`, `cs`, `polytime`, `splinetime`, `intercs`, `lags`, `leads` | Unsupported | Representative panel/basis cases; not every combination |
| `bounds`, `max.resample`, `overimp` | Unsupported | Public cases; nine actual clamped cells at limit 1, code 52 at limit 0; bounded-draw distribution not accepted |
| `p2s` | Accepts 0/1/2; different progress format | Statistical output checked; progress explicitly labels PyTorch |
| `incheck`, `collect`, `arglist`, append, molist | Original public behavior unsupported | Bounded checks including RNG consumption, saved arguments and locally scoped `moPrep` |
| `parallel`, `ncpus`, `cl` | No public replicate scheduler | Hybrid serial only; reference Python snow2, caller-owned R cluster and Unix multicore tested; Windows uses snow |
| Internal `allthetas` | Separate matrix-history format | Original upper-triangle vector format and initial column checked |
| Official `amelia`/`mi` class | Separate native result | Official class retained with backend metadata |
| Bind, transform, with/model pooling, moPrep | Not ported | G1 public branches checked on CPU; original downstream methods remain R CPU |
| Summary/plots, density/overimpute/disperse/missmap/tscsPlot | Not ported | Numeric returns and PDF outputs checked; limited Mac RStudio visual record separately available |
| CSV/table/DTA export | Not ported | Readback, factor labels, combined output, custom impvar and orig.data=FALSE checked |
| Python typed bridge and RDS | Native array output only | G3 bounded dtype/session cases; unsupported types and frontend GUI rejected; authoritative RDS retains original objects |

## Platform evidence

| Platform/workload | Recorded outcome |
|---|---|
| Windows/macOS/Linux hosted CPU | `ef729c0`: 307 Python tests, nine R files and downstream example per platform; GPU excluded |
| Intel Mac reference-only | `ad9bed2`: isolated wheel without Torch, actual fitting and RDS workflow; no Intel Torch/GUI claim |
| Mac MPS32 | Fixed cases, eight public-edge assertions and three 100k-row datasets; slower than same-precision CPU |
| Linux T4 CUDA32/64 | Fixed cases passed; native/reference 18 configurations complete; hybrid 11/12 recovered, final Year CUDA32 unknown |
| Windows RTX 3080 CUDA32/64 | Three fixed native and three R cases per precision; native/reference 18 and hybrid 12 configurations complete, 210 calls/1,050 imputations |
| RStudio | Installed Mac reference/hybrid CPU64, save/readback, Data Viewer and diagnostic plot; Windows GUI and AmeliaView not validated |
| Python full reference/hybrid call | G7 Covertype 100k includes new R process, binary transfer and RDS return; distinct from native and R-memory timing |
| Independent-cell MCAR stress | G7 Household 5000×7 retains two entirely missing rows; 14 unscored heldout cells per imputation, RMSE null, not a quality-success timing |

## Statistical acceptance

The Mac five-route G5 study completed 10,500 fits. MAR and bounded stress checks passed; MCAR absolute/paired coverage criteria did not all pass, including an original-R criterion. CUDA G5 and newer CUDA public-edge checks remain incomplete. Fixed cases, low RMSE and successful fitting do not establish distributional equivalence. R `mi.combine` interval/p-value quirks are preserved as compatibility evidence, not endorsed as correct inference.

Detailed reports: [G1](validation/2026-09-26-g1/downstream-extended.md), [G2](validation/2026-09-26-g2/README.md), [G3](validation/2026-09-26-g3/README.md), [G4](validation/2026-09-26-g4/README.md), [G5](validation/2026-09-26-g5-mps/README.md), [Windows](validation/2026-09-27-windows-rtx3080/README.md), [summary](validation/2026-09-27-evidence-summary.md).

## Support policy

Unsupported options fail explicitly. Record R dependencies, CPU work, device/precision, synchronization, failures, nonconvergence and pseudoinverses. Speed comparisons use the same host, task, precision and timing boundary, including interface costs when relevant. Same seeds do not pair different RNG libraries. Extend support claims only with executed, versioned evidence; package installation is not complete release acceptance.
