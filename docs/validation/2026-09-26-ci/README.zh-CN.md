# Hosted CPU CI：fa08a52

[English](README.md) · [文档目录](../../README.zh-CN.md)

[运行36274202726](https://github.com/Tocqueville0624/amelia-torch/actions/runs/36274202726)于 2026-09-26 在 `fa08a5207d197a3f82ced7913a67bc448c8ecacc` 通过。API 及完整日志核对 checkout、安装和实际命令。

| 平台 | Python | Python检查 | R 文件 | 下游示例 |
|---|---|---:|---:|---|
| macOS 26.6.2 arm64 |3.12.10|161 通过，24.12 s|7|通过|
| Windows Server 2025 x64 |3.12.10|161 通过，38.48 s|7|通过|
| Ubuntu 24.04.5 x64 |3.12.14|161 通过，22.25 s|7|通过|

固定 R 4.5.3/Amelia 1.8.3；Mac Torch 2.14.0，其他 2.14.0+cpu。lint、C helper 源码安装、Python→RDS→R 变换/追加/PDF/导出读回通过，无Python跳过项。Mac 条件跳过仅为 Windows/Linux 专用 wheel 安装步骤。

此提交覆盖有界 G1 和早期 G2，不含后续 G3/G4/autopri。CPU 检查不是性能、GPU/GUI 验收、隔离 wheel 矩阵或 Intel Mac 结果；Intel 原版安装另有版本化报告。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[cross-platform-ci.json](cross-platform-ci.json)
