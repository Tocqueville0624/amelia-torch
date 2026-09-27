# 本机包回归

[English](README.md) · [文档目录](../../README.zh-CN.md)

2026-09-26，Apple Silicon。完整Python235 项及 Ruff 通过，包含当时未提交的三项 G7 审计检查，不能归为旧 CI 计数。逐文件身份见 checks.json。

新 R 源码 tarball 在独立临时目录运行 `R CMD check --no-manual --no-build-vignettes`，含九个 R 文件，0 错误/0 警告/0 NOTE，Status: OK。build/check 日志已替换本机路径；并行检查在允许 worker socket 的环境执行。此为本机代码/打包回归，不是新 GPU 性能、推断或RStudio视觉证据。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[checks.json](checks.json) · [build.log](build.log) · [check.log](check.log)
