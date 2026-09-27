# Hosted CPU CI：620213e

[English](cross-platform-ci.md) · [文档目录](../../README.zh-CN.md)

[运行35953184726](https://github.com/Tocqueville0624/amelia-torch/actions/runs/35953184726)在 `620213e56866bf83c9f16207a1b8e79654ede03c` 的 Windows/macOS/Ubuntu 通过，完成于 2026-09-24 UTC/太平洋时间 9 月 23 日。各执行 149 项Python、lint、R 源码安装和五个 R 文件，Python 3.12/R 4.5.3/Amelia 1.8.3。

R 范围含原生桥、原版委托、混合 CPU EM、来源和下游/RNG 检查。这是 CPU 回归，不是性能、CUDA/MPS、实体 RTX 3080 或完整兼容验收。

首轮 Mac/Ubuntu 通过，Windows 为 132 通过/一项路径解析失败：占位可执行文件缺 Windows 后缀。fixture 改为 Windows 使用.exe，只查找不执行。首次修正各平台 133 项通过，后续 149 项另记。未改变算法、容差或原版版本。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[cross-platform-ci.json](cross-platform-ci.json)
