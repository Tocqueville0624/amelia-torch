# 初始环境检查

[English](README.md) · [文档目录](../../README.zh-CN.md)

2026-09-23，Apple M4 iMac/16 GB，macOS 26.6.2。

- `mac-native.json`：Python 3.12.13/Torch 2.14.0 的 CPU64/32、MPS32六类基础算子通过，MPS 自动回退关闭。确定性矩阵仅 2×2；随机检查仅执行/形状/有限性，不是分布检查。
- `r-bridge.json`：R 4.5.3/reticulate 1.47.0 进入Python并执行 CPU/MPS 探针。
- `r-reference.json`：原版 Amelia 1.8.3 在 200×3 合成数据生成两份插补，观察值保留、缺失补齐；未包含全空行。
- 四项后端测试、lint/格式和相对链接检查通过；请求不可用CUDA按预期 exit 1。

本初始快照早于项目 EM 实现，是环境/原版 R 检查，不是项目插补或加速结果。本次未进行交互RStudio演示。受限进程最初隐藏 MPS，有权限的本机进程可访问。已修正解释器符号链接解析和“所有全空行均应填满”的不当断言。私人路径及完整本机会话输出不公开。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[mac-native.json](mac-native.json) · [r-bridge.json](r-bridge.json) · [r-reference.json](r-reference.json)
