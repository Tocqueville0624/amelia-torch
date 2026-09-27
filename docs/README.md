# Documentation

[简体中文](README.zh-CN.md) · [Project README](../README.md)

The project provides Python/R multiple-imputation interfaces and records of compatibility, performance and statistical validation against Amelia 1.8.3. Start with the [project README](../README.md), then select a guide below. Every Markdown document has English and Chinese versions.

## Usage

- [amelia-torch](../README.md)
- [Multiple-imputation workflow](project-walkthrough.md)
- [R workflow prompt](r-user-agent-prompt.md)
- [R interface](r-interface.md)
- [Python/R compatibility bridge](python-reference-bridge.md)
- [Installation](setup.md)
- [Examples](../examples/README.md)

## Methods and reproduction

- [Architecture](architecture.md)
- [Roadmap](roadmap.md)
- [Amelia 1.8.3 algorithm contract](algorithm-contract.md)
- [Amelia 1.8.3 compatibility](amelia-compatibility.md)
- [R Amelia benchmark runner](reference-benchmark-runner.md)
- [Reproduction](reproduce.md)
- [Validation and benchmark plan](benchmark-plan.md)
- [Public datasets](datasets.md)
- [Feasibility and prior art](feasibility.md)
- [Release criteria](release-gates.md)
- [Colab CUDA procedure](cloud-cuda.md)

## Validation records

- [Evidence summary](validation/2026-09-27-evidence-summary.md)
- [Windows RTX 3080 benchmarks](validation/2026-09-27-windows-rtx3080/README.md)
- [Initial environment checks](validation/2026-09-23/README.md)
- [Recovered Colab outputs](validation/2026-09-23-colab-recovered/README.md)
- [Hosted CPU CI: 620213e](validation/2026-09-23-development/cross-platform-ci.md)
- [Hosted CPU CI: fa08a52](validation/2026-09-26-ci/README.md)
- [Hosted CPU CI: e2ff892](validation/2026-09-26-ci/cross-platform-ci-e2ff892.md)
- [Hosted CPU CI: 8b5ede9](validation/2026-09-26-ci/cross-platform-ci-8b5ede9.md)
- [Intel Mac reference-only wheel](validation/2026-09-26-ci/intel-mac-reference.md)
- [Linux T4 correctness checks](validation/2026-09-26-cuda/README.md)
- [Local package regression](validation/2026-09-26-regression/README.md)
- [Interruption and report persistence](validation/2026-09-26-interruption-records.md)
- [CPU64 inference screen](validation/2026-09-23-development/inference-validation.md)
- [R downstream checks](validation/2026-09-23-development/r-downstream-validation.md)
- [R package check: 2026-09-23](validation/2026-09-23-development/r-package-check.md)
- [G1 downstream methods](validation/2026-09-26-g1/downstream-extended.md)
- [G1 packaging](validation/2026-09-26-g1/packaging.md)
- [G2 public CPU64 boundaries](validation/2026-09-26-g2/README.md)
- [Accelerator edge protocol and CPU64 check](validation/2026-09-26-g2/accelerator-edges.md)
- [G2 MPS32 public boundaries](validation/2026-09-26-g2/accelerator-edges-mps32.md)
- [G3 types and sessions](validation/2026-09-26-g3/README.md)
- [G4 reference parallelism](validation/2026-09-26-g4/README.md)
- [G5 prespecified inference protocol](validation/g5-prespecified/README.md)
- [Proposed independent MCAR follow-up](validation/g5-mcar-followup-proposed.md)
- [Mac G5 inference results](validation/2026-09-26-g5-mps/README.md)
- [G6 Mac RStudio workflow](validation/2026-09-26-g6-rstudio/README.md)
- [G7 Python call costs and MCAR stress](validation/2026-09-26-g7/README.md)
- [Saved Mac CPU32/MPS32 output comparison](validation/2026-09-26-native-parameter-comparison/README.md)
- [Mac performance figures](validation/2026-09-26-performance-figures/README.md)
- [Mac development validation](validation/2026-09-23-development/README.md)
- [Linux T4 native benchmarks](validation/2026-09-26-colab-native/README.md)
- [Linux T4: partial R hybrid benchmarks](validation/2026-09-26-colab-hybrid-partial/README.md)
- [Colab environment recovery and interruption](validation/2026-09-27-colab-recovery/README.md)

## Contributing and attribution

- [Git history migration and revision map](history/README.md)
- [Contributors](../CONTRIBUTORS.md)
- [Contributing](../CONTRIBUTING.md)
- [Third-party attribution and licenses](../THIRD_PARTY.md)
- [Repository maintenance guidelines](../AGENTS.md)
- [Maintenance guidelines alias: CLAUDE](../CLAUDE.md)
- [Small attributed data samples](../data/samples/README.md)
- [Amelia 1.8.3 reference fixtures](../tests/fixtures/reference_amelia/README.md)

## Document revisions and original records

This documentation revision starts from commit `939409a`. Translation, navigation and prose changes add no experiments. Raw JSON, logs, figures, archives and measured-source fingerprints retain their recorded contents; embedded files in historical archives remain at their archived versions. Documentation checksum changes are recorded separately in the [editorial review manifest](documentation-review.json), without altering experimental results.

documentation-review.json retains hashes from the previous editorial review; subsequent changes are recorded in the [migration editorial audit](history/editorial-audit.json).
