# Hosted CPU CI：e2ff892

[English](cross-platform-ci-e2ff892.md) · [文档目录](../../README.zh-CN.md)

[运行36276160870](https://github.com/Tocqueville0624/amelia-torch/actions/runs/36276160870)于 2026-09-26 在 `e2ff8926f4ac4b432c4d6acf8fbc1cd42c93a0f2` 通过，依据任务 API 和完整日志独立核验。Ubuntu 24.04.5 x64/Python 3.12.14、macOS 26.6.2 arm64/Python 3.12.10、Windows Server 2025 x64/Python 3.12.10 各通过 **235 项Python**、Ruff、九个 R 文件、C helper 源码安装和Python/RDS/R 下游示例，无Python跳过项。对应 pytest 秒数为 62.62 / 49.90 / 82.62，不是插补基准。

核验 R 4.5.3 和精确 Amelia 1.8.3；Mac Torch 2.14.0，其他 2.14.0+cpu。九个 R 文件为 bridge、compatibility、torch-compat、public-edge-cases、autopri-boundary、reference-parallel、reference_metadata、downstream、downstream_extended。提交包含 G3/G4/autopri/G7。

病态 autopri 的原版/混合 code、更新次数、固定 hold 检查依次为：Ubuntu `(2,0,0)/(2,3,3)`；Mac `(2,2,2)/(1,3,3)`；Windows `(2,0,0)/(1,1,1)`。Linux/Windows 原版未触发校正，属于部分覆盖。不同引擎/BLAS轨迹可不同，code 1 不独自证明收敛；病态案例不算有效推断样本。

三平台均执行Python snow2和 R caller-owned snow cluster。Unix multicore 在 Mac/Linux 执行，Windows 明确跳过 fork，混合仍串行。94 个源码哈希来自核验提交的 Git blob，不是安装后文件的运行期指纹。原始 runner 路径、worker ID 和完整日志不公开。

此为新环境源码安装 CPU 回归，不是 R CMD check、三平台 wheel 矩阵、GPU 或 GUI 验证。ad9bed2 的 Intel wheel 另有范围。安装应先准备 R 依赖及项目 R 包，再运行集成测试；精确 Amelia 校验不锁定全部依赖。后续代码或文档变化不改写本结果。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[cross-platform-ci-e2ff892.json](cross-platform-ci-e2ff892.json) · [cross-platform-ci-e2ff892.sha256.json](cross-platform-ci-e2ff892.sha256.json) · [cross-platform-ci.json](cross-platform-ci.json) · [SHA256SUMS.json](SHA256SUMS.json)
