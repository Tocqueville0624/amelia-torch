# Roadmap

[简体中文](roadmap.zh-CN.md) · [Documentation](README.md)

Status: 2026-09-27. The project remains a development snapshot targeting Amelia 1.8.3 compatibility through native, reference and hybrid routes. R dependencies are explicit. A complete first release requires the applicable [release criteria](release-gates.md), not a positive speed result.

| Area | Completed evidence | Remaining scope |
|---|---|---|
| Reference and native implementation | Versioned algorithm contract, synthetic fixtures, continuous EMB and explicit unsupported-option errors | Native advanced transformations, categories, public priors/bounds and panel options are unsupported; advanced workflows currently use R |
| Interfaces | R package; Python typed binary/RDS bridge; bounded downstream, type and parallel-reference checks | Broader combinations require evidence before support claims |
| CPU platforms | Windows/macOS/Linux CI at `ef729c0`; Intel Mac isolated reference-only wheel without Torch | Results remain limited to recorded installations and branches |
| Accelerators | MPS fixed cases; Linux T4 and Windows RTX 3080 fixed CUDA cases | New CUDA public-edge checks and complete inference acceptance |
| Performance | Three 100k-row datasets: Mac native/hybrid; T4 native/reference; Windows native/reference and hybrid | T4 hybrid is only 11/12 recovered configurations; memory limits and broader missingness remain unverified |
| Inference | Mac five-route study: 10,500 completed fits, MAR and bounded stress checks passed | Prespecified MCAR criteria did not all pass; CUDA G5 not run |
| Interactive use | Installed Mac RStudio reference/hybrid CPU64 workflow, readback and diagnostic plot | Windows GUI and original AmeliaView remain unvalidated |
| Distribution | Public source, GPL attribution, licensed samples, download and reproduction scripts | No complete release, PyPI or CRAN distribution |

## Evidence

[Current summary](validation/2026-09-27-evidence-summary.md) links complete and partial records. Windows measured `810591e`: 18 native/reference and 12 hybrid configurations, 210 calls and 1,050 imputations, with limited convergence and output checks passing. These records do not complete CUDA statistical acceptance or repair missing T4 results.

The original T4 host completed 15 correctness stages and the native/reference performance suite, then was lost after 11 hybrid configurations were backed up. The replacement host stopped at stage 4/20 with 306 Python tests passing and one temporary-environment NumPy import failure. Subsequent R, new CUDA edge checks and G5 did not run. Colab remains paused; no further fitting, simulation or test budget is scheduled during evidence documentation.

## Outstanding work

1. Review the cloud installer's R-version handling and isolated-environment dependency failure before reuse. A local draft is not a validated fix.
2. Complete the bounded CUDA edge checks and prespecified inference protocol when experiments resume. Retain existing failed classifications. The independent 1,000-MCAR follow-up remains a proposal, not an executed or mandatory replacement study.
3. Profile complete calls before selecting performance optimizations; preserve algorithm and RNG semantics. Record actual memory use or leave unmeasured fields null.
4. Update compatibility claims and release status only with corresponding reports. A public development repository or successful package build does not establish complete acceptance.

Maintenance rules, including upstream edge behavior and historical evidence preservation, are in [AGENTS.md](../AGENTS.md).
