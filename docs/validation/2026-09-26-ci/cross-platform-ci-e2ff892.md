# 最新三平台 CPU CI：e2ff892

[Run 36276160870](https://github.com/Tocqueville0624/amelia-torch/actions/runs/36276160870) 已在 **`e2ff8926f4ac4b432c4d6acf8fbc1cd42c93a0f2`** 全部完成并通过。审计读取完整任务 API 和逐任务日志，确认三个 checkout 的 SHA 相同、Python 数量、九条 R 测试命令、安装与公开例子均实际执行。这份记录独立于 `2816e38` 和历史 `fa08a52`；没有覆写旧 JSON 或其哈希。

| 实际运行环境 | Python | Python 测试 | R 测试文件 | 源码安装 / 公开下游例 |
|---|---|---:|---:|---|
| Ubuntu 24.04.5，x64 | 3.12.14 | 235 passed，62.62 秒 | 9 passed | passed |
| macOS 26.6.2，arm64 | 3.12.10 | 235 passed，49.90 秒 | 9 passed | passed |
| Windows Server 2025，x64 | 3.12.10 | 235 passed，82.62 秒 | 9 passed | passed |

Python 测试没有失败或 skip，Ruff 也全部通过。R 固定为 4.5.3，实际安装且校验 Amelia 1.8.3。Torch 为 Mac 2.14.0、Windows/Linux 2.14.0+cpu；其余实际版本和全部 step 状态见[独立 JSON](cross-platform-ci-e2ff892.json)。`latest` 标签本身没有被当作硬件/系统版本证据；这里使用真实镜像和解释器记录。

九个 R 文件为 `bridge.R`、`compatibility.R`、`torch-compat.R`、`public-edge-cases.R`、`autopri-boundary.R`、`reference-parallel.R`、`reference_metadata.R`、`downstream.R`、`downstream_extended.R`。这轮涵盖新 G3 类型/明确失败、G4 reference 并行、有界 autopri 与 G7 评分/审计测试。三个系统都成功编译并安装 R 包的 C helper，运行 Python→RDS→R 变换/追加/诊断 PDF/CSV→Python 读回例子。

这是源码安装后的 CPU 回归。它不是 `R CMD check`，后者的本机九文件零问题记录另存于[本机完整检查](../2026-09-26-regression/README.md)；也不代表同一矩阵验证了独立 wheel、CUDA/MPS、交互式 RStudio 或首版所有功能。

## 必须保留的分支覆盖边界

病态 `autopri` 输入允许不同 BLAS 在近零特征值处产生不同轨迹，不能用测试绿色状态掩盖未触发的分支。日志给出：

| 系统 | 原版 reference：code / 更新 / 固定 hold 检查 | hybrid：code / 更新 / 固定 hold 检查 |
|---|---|---|
| Ubuntu | 2 / 0 / 0 | 2 / 3 / 3 |
| macOS | 2 / 2 / 2 | 1 / 3 / 3 |
| Windows | 2 / 0 / 0 | 1 / 1 / 1 |

Linux 和 Windows 明确输出 partial coverage：原版没有触发自适应更新，因此该原版分支在这两个任务中仍未观察到。已触发的检查验证固定初始 hold，而非要求各系统或两引擎的病态轨迹相同。最终状态按各自 theta 与原版规则验证；病态样本不算成功统计质量证据，code 1 也不能单独作为收敛依据。

Python 的 snow2 和 R 的 caller-owned snow cluster 均在三个系统实际执行。Unix multicore 在 Mac/Linux 执行；Windows 明确记录“不运行 Unix fork，已测试 snow”，并非声称 Windows 获得 fork 支持。Mac 跳过专供 Windows/Linux 的 CPU wheel 安装 step 是预定条件，随后通过正常安装步骤获取 Torch，不是跳过测试。

## 源码和公开证据

JSON 保存本次任务链接、原始完成时刻、必要版本、portable 完成断言和 94 个源/测试/复现文件的 SHA-256。这些哈希从已核验 checkout 的 Git blob 计算；CI 没有单独对安装后工作树逐文件做 fingerprint，所以不将它描述成运行中 source guard。编译生成文件不公开。原始 runner 路径、worker 标识和完整环境日志也不复制到仓库。

本报告及 JSON 的独立校验值见 [SHA-256](cross-platform-ci-e2ff892.sha256.json)。旧 `cross-platform-ci.json`、Intel 记录和旧 `SHA256SUMS.json` 保持原样。

## G8 干净安装与最小复现的有限判断

这三个新 hosted runner 从 checkout 安装 Python 包和 R 源码包、执行真实插补与公开下游例，覆盖了全新环境的源码安装路径。[Intel Mac 独立记录](intel-mac-reference.md)另外验证隔离 venv 中的 wheel[reference] 安装、实际从 site-packages 导入、没有 Torch，以及原版拟合/RDS 下游往返。两类证据结合，足以支撑 G8 中有界的“干净安装并完成最小复现”，不要求 PyPI/CRAN 上架；也不把旧 Intel wheel 当作本次三个系统的 wheel 矩阵。

这不是逐字执行所有文档命令、Mac 依赖锁文件或全量基准的复现。静态审查发现 Windows 安装说明曾把 `pytest` 放在安装 R 依赖及本包之前；在有 Rscript 的干净机上会导致真实集成测试失败，已经向主 Agent 提交“先安装 R 依赖/本包，再 pytest”的具体修正建议。精确 1.8.3 校验会在 CRAN 版本变化时明确拒绝；归档源码 URL/SHA 的安装路径已有 cloud bootstrap，实现与声明不能把它省略后称永久锁定所有依赖。此处不修改正在运行的 G5 或核心源码。
