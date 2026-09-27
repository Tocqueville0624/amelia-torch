# 文档目录

[English](README.md) · [项目首页](../README.zh-CN.md)

本项目提供 Python/R 多重插补接口与 Amelia 1.8.3 的兼容性、性能和统计验证记录。先阅读[项目首页](../README.zh-CN.md)，再按用途选择文档。所有 Markdown 文档均有中英文版本。

## 使用指南

- [amelia-torch](../README.zh-CN.md)
- [多重插补流程](project-walkthrough.zh-CN.md)
- [R 工作流提示词](r-user-agent-prompt.zh-CN.md)
- [R 接口](r-interface.zh-CN.md)
- [Python 调用官方 R Amelia 的兼容过渡路径](python-reference-bridge.zh-CN.md)
- [安装](setup.zh-CN.md)
- [示例](../examples/README.zh-CN.md)

## 方法与复现

- [架构](architecture.zh-CN.md)
- [开发路线](roadmap.zh-CN.md)
- [Amelia 1.8.3 算法契约与参考证据](algorithm-contract.zh-CN.md)
- [Amelia 1.8.3 兼容性](amelia-compatibility.zh-CN.md)
- [R Amelia 基准执行器](reference-benchmark-runner.zh-CN.md)
- [复现实验入口](reproduce.zh-CN.md)
- [正确性与性能验证计划](benchmark-plan.zh-CN.md)
- [三组公开数据及可复现准备](datasets.zh-CN.md)
- [可行性与已有工作](feasibility.zh-CN.md)
- [发布标准](release-gates.zh-CN.md)
- [Colab CUDA 流程](cloud-cuda.zh-CN.md)

## 验证记录

- [证据摘要](validation/2026-09-27-evidence-summary.zh-CN.md)
- [Windows RTX 3080：原生 Python 与完整 R 混合路线](validation/2026-09-27-windows-rtx3080/README.zh-CN.md)
- [初始环境检查](validation/2026-09-23/README.zh-CN.md)
- [Colab历史输出恢复](validation/2026-09-23-colab-recovered/README.zh-CN.md)
- [Hosted CPU CI：620213e](validation/2026-09-23-development/cross-platform-ci.zh-CN.md)
- [Hosted CPU CI：fa08a52](validation/2026-09-26-ci/README.zh-CN.md)
- [Hosted CPU CI：e2ff892](validation/2026-09-26-ci/cross-platform-ci-e2ff892.zh-CN.md)
- [Hosted CPU CI：8b5ede9](validation/2026-09-26-ci/cross-platform-ci-8b5ede9.zh-CN.md)
- [Intel Mac无Torch参考wheel](validation/2026-09-26-ci/intel-mac-reference.zh-CN.md)
- [Linux T4正确性检查](validation/2026-09-26-cuda/README.zh-CN.md)
- [本机包回归](validation/2026-09-26-regression/README.zh-CN.md)
- [中断与报告保存](validation/2026-09-26-interruption-records.zh-CN.md)
- [CPU64推断初筛](validation/2026-09-23-development/inference-validation.zh-CN.md)
- [R下游检查](validation/2026-09-23-development/r-downstream-validation.zh-CN.md)
- [R包检查：2026-09-23](validation/2026-09-23-development/r-package-check.zh-CN.md)
- [G1下游方法](validation/2026-09-26-g1/downstream-extended.zh-CN.md)
- [G1打包](validation/2026-09-26-g1/packaging.zh-CN.md)
- [G2公共CPU64边界](validation/2026-09-26-g2/README.zh-CN.md)
- [加速器边界方案与CPU64检查](validation/2026-09-26-g2/accelerator-edges.zh-CN.md)
- [G2 MPS32公共边界](validation/2026-09-26-g2/accelerator-edges-mps32.zh-CN.md)
- [G3类型与会话](validation/2026-09-26-g3/README.zh-CN.md)
- [G4原版并行](validation/2026-09-26-g4/README.zh-CN.md)
- [G5预设推断方案](validation/g5-prespecified/README.zh-CN.md)
- [独立MCAR后续验证提案](validation/g5-mcar-followup-proposed.zh-CN.md)
- [Mac G5推断结果](validation/2026-09-26-g5-mps/README.zh-CN.md)
- [G6 Mac RStudio流程](validation/2026-09-26-g6-rstudio/README.zh-CN.md)
- [G7 Python调用成本与MCAR压力](validation/2026-09-26-g7/README.zh-CN.md)
- [Mac CPU32/MPS32已保存输出对照](validation/2026-09-26-native-parameter-comparison/README.zh-CN.md)
- [Mac性能图](validation/2026-09-26-performance-figures/README.zh-CN.md)
- [Mac开发验证](validation/2026-09-23-development/README.zh-CN.md)
- [Linux T4原生基准](validation/2026-09-26-colab-native/README.zh-CN.md)
- [Linux T4：R 混合路线的部分基准记录](validation/2026-09-26-colab-hybrid-partial/README.zh-CN.md)
- [Colab 重启、环境失败与暂停记录](validation/2026-09-27-colab-recovery/README.zh-CN.md)

## 贡献与数据归属

- [Git 历史迁移与编号映射](history/README.zh-CN.md)
- [贡献者](../CONTRIBUTORS.zh-CN.md)
- [贡献指南](../CONTRIBUTING.zh-CN.md)
- [来源、归属与许可证状态](../THIRD_PARTY.zh-CN.md)
- [仓库维护规范](../AGENTS.zh-CN.md)
- [维护指南别名：CLAUDE](../CLAUDE.zh-CN.md)
- [带归属的数据小样本](../data/samples/README.zh-CN.md)
- [Amelia1.8.3参考样例](../tests/fixtures/reference_amelia/README.zh-CN.md)

## 文档版本与原始记录

本次文档整理以提交 `939409a` 为基线。译文、导航和说明文字的调整不产生新实验。JSON、日志、图表、压缩归档和测量源码指纹保留原始记录；历史归档中的文件仍按归档时版本保存。文档校验值的调整单独记录在[文档审查清单](documentation-review.json)，不更改实验结果。

此处的 documentation-review.json 保留上次文档审查时的哈希；本次改动见[迁移文档审查](history/editorial-audit.json)。
