# Repository maintenance guidelines

[简体中文](AGENTS.zh-CN.md) · [Documentation](docs/README.md)

These rules apply to code, documentation and automated contributions. They preserve the statistical contract and the integrity of published evidence.

## Scope and status

- Target the full Amelia 1.8.3 workflow across Python and R/RStudio. The native continuous subset, original-R reference and R/PyTorch hybrid are distinct interfaces. Explicit R dependencies are permitted; complete acceptance is required before a first full release.
- Current work is documentation and review of existing evidence. Do not start additional fits, simulations or test jobs, expand experiment budgets, or acquire paid compute until experiments are explicitly resumed. Static document, link and checksum inspection is permitted.
- Windows `810591e` completed 18 native/reference and 12 hybrid configurations: 210 calls/1,050 imputations. T4 `905cc79` native/reference is complete; hybrid is 11/12 recovered. Mac G5 completed 10,500 fits but MCAR criteria did not all pass. CUDA G5 and new CUDA edge checks remain unfinished. Use the [evidence summary](docs/validation/2026-09-27-evidence-summary.md), not completion inferred from filenames.
- Package name `amelia-torch`, import `amelia_torch`, R package `ameliatorch`, GPL-3.0-only. Maintainer Sheng Wan <swan0624@uw.edu>; public repository Tocqueville0624/amelia-torch. Add contributor attribution only after actual participation is confirmed.

## Environment

Use Python 3.12 with uv and `.venv`, and project `.R-library`. Pin original Amelia 1.8.3. The Mac arm64 lockfile is not a Windows CUDA or Intel Mac lock. Windows uses `.venv\Scripts\python.exe`; Unix uses `.venv/bin/python`. Follow [installation](docs/setup.md) and [reproduction](docs/reproduce.md). Preserve ignored environments, raw data and local recovery records.

When testing resumes, Python checks are `.venv/bin/python -m pytest -q` and `.venv/bin/ruff check src tests scripts`. R bridge source checks use `R_LIBS_USER="$PWD/.R-library" RETICULATE_PYTHON="$PWD/.venv/bin/python" AMELIATORCH_R_SOURCE=r-package Rscript r-package/tests/bridge.R`. Hybrid source checks also require the installed compiled C helpers. Device probes use `python -m amelia_torch.diagnostics --require-device mps` or `cuda`. Restricted processes may hide GPUs or block snow localhost sockets; record the actual execution context.

Cloud recovery records in ignored `results/local/cloud-recovery-*/resume-state.json` are hints, not proof of execution. Do not publish private notebook URLs or account metadata. Back up complete reports outside the VM after each stage, outside timing, using checkpoint/recovery scripts and verified hashes. Never splice timings across replacement VMs. System-package installation previously upgraded R 4.5.3 to 4.6.1 and broke shared extensions; automatic protection remains unvalidated. The local `unfinished-cloud-bootstrap-guard.patch` is an unreviewed draft, not a completed fix.

## Algorithm constraints

- [Algorithm contract](docs/algorithm-contract.md) controls semantics. Add an original-version reference comparison before exposing a new option. Reject unsupported options explicitly.
- Preserve observed-value standardization → bootstrap → conditional-moment EM → draws on original input → order/unit restoration. Retain conditional covariance; mean filling is not EMB.
- Preserve observed entries and entirely missing analysis rows (excluded from fitting, still missing in output). Retain documented single-row-prior, log-transform and missing-ID exceptions. Reject or report empty columns, constants, insufficient observations, ill-conditioning and nonconvergence.
- Preserve initial values, sample-covariance denominators, integer empri, fixed initial autopri hold, upper-triangle stopping and the complete-bootstrap shortcut. Do not silently add ridge, clip covariance or lower precision.
- Explicit double R startvals mutates in the original C EM. Preserve caller/archive/subsequent-imputation effects and save initial allthetas first. Integer and complete-bootstrap exceptions do not write back. Native Python inputs remain unchanged. Reference fixture export must deep-copy theta.
- Preserve both R's internal RNG and visible `.Random.seed` around reticulate. Do not replace registered helpers with simple seed assignment. Original draws can leave the visible vector stale. Native uses NumPy PCG64; equal integer seeds do not pair streams. Deterministic comparisons use explicit random arrays; inference requires separate distributional checks.
- CPU float64 is the reference. MPS/CUDA float32 requires explicit selection and independent quality evidence. MPS eigenvalue checks run on CPU and must be recorded; fallback=0 does not establish an entirely GPU implementation.
- Preserve reticulate's virtual-environment interpreter path without resolving its executable symlink. Restart R before changing an initialized interpreter. Convert m and large seeds without truncation. Native results must not impersonate official Amelia classes; actual reference objects retain them with engine metadata.

## Evidence and publication

- Compare same-host, same-task, same-precision full calls against original R serial/parallel and Torch CPU. Synchronize GPU timing and include transfer/output costs; measure R and Python-to-R interface costs separately. Cross-host 3080/T4 timings are observations, not isolated GPU speed ratios. No profiling means no claim that a timing difference equals communication cost.
- Preserve warmups, every repeat/failure, source/environment/data hashes, convergence, pseudoinverse and CPU-work telemetry. Do not change historical measured-source fingerprints after code changes. Unmeasured memory is null, not zero.
- Check observed values, finite required outputs, complete heldout scoring, bias, Rubin coverage and Monte Carlo uncertainty. RMSE similarity does not prove elementwise equality. The saved Mac Covertype comparison reached 0.173 truth-column SD; retain its scope and do not label all differences negligible.
- G5 thresholds and budgets were frozen before execution at protocol SHA `7ea7882bccc8d92102a67786bc9c09c2055ce29d97350abfbcf4f74f2187e454`. Preserve failed classifications. The separate 1,000-MCAR proposal is unexecuted and does not authorize more simulation.
- Distinguish block MCAR, independent-cell MCAR and MAR; report n/p/m/pattern count and actual missingness. 100k-row samples are not full datasets. Hosted CPU CI does not establish GPU or GUI coverage; untriggered original autopri branches remain uncovered.
- Keep GPL attribution and CC BY 4.0 data attribution. Licensed samples, manifests and download scripts belong in Git; `.venv`, `.R-library`, raw large archives, private data, personal paths and machine identifiers do not.
- Update roadmap, compatibility and reports with actual evidence. Keep raw archives and experimental outputs unchanged during editorial work; record documentation-only checksum revisions separately. Every public Markdown document must have equivalent English/Chinese versions and language links. Use concise, objective headings and prose for researchers and external reviewers; remove assistant-to-owner status narratives.

## Commit attribution

AI-assisted commits use the executing model's actual name and a valid `Co-Authored-By:` trailer. Do not fabricate identities, authorship or email addresses.
