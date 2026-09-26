# 三平台 CPU CI：8b5ede9 独立核验

本记录只对应提交 `8b5ede900ae27b7bf73e586c0b4798a225dc2fa2` 的
[运行 36278251240](https://github.com/Tocqueville0624/amelia-torch/actions/runs/36278251240)，
不沿用或覆盖旧 `e2ff892`、`fa08a52` 或 Intel Mac 结果。运行于
2026-09-26 23:03:43 UTC 创建，23:08:57 UTC 完成，三个任务均为 `success`。
通过任务 API 和完整任务日志分别核对了 checkout SHA、测试数量、九条 R 测试命令、
安装结果、下游示例及平台特有分支。

## 实际完成的范围

| 日志中的系统 / 解释器架构 | Python | Python 测试 | R 文件 | 下游示例 |
|---|---|---|---|---|
| Ubuntu 24.04.5 / x64 | 3.12.14 | 262 passed，62.97 秒 | 9 passed | passed |
| macOS 26.6.2 / arm64 | 3.12.10 | 262 passed，60.61 秒 | 9 passed | passed |
| Windows Server 2025，10.0.26100 / x64 | 3.12.10 | 262 passed，75.40 秒 | 9 passed | passed |

表中秒数是各 hosted runner 的 pytest 回归套件耗时，**不是插补性能基准，不能用于平台速度比较**。
系统版本取自任务的实际镜像日志；架构来自下载并成功安装的 wheel ABI，Mac 同时有
arm64 镜像记录。没有根据 `latest` 标签推测系统、CPU 型号或物理硬件。

三个系统的 Python 测试均没有失败或 skip，Ruff 全部通过。R 按 4.5.3 安装，
Amelia 的严格 `1.8.3` 版本断言通过；Torch 为 Mac `2.14.0`、Windows/Linux
`2.14.0+cpu`。其他必要版本、全部 step 状态和任务链接见
[独立 JSON](cross-platform-ci-8b5ede9.json)。Mac 按预定条件跳过的是专供
Windows/Linux 的 CPU wheel 安装步骤，随后正常安装 Torch，并未跳过测试步骤。

九个 R 文件为 `bridge.R`、`compatibility.R`、`torch-compat.R`、
`public-edge-cases.R`、`autopri-boundary.R`、`reference-parallel.R`、
`reference_metadata.R`、`downstream.R` 和 `downstream_extended.R`。
三个系统均成功编译安装含 C helper 的 R 源码包，并实际完成
Python→RDS→R 变换/追加/诊断 PDF/CSV→Python 读回示例。

本次源码包含中断、逐次原子写入、未完成计划和记录失败终态的新增回归；
其设计与本机验证见[中断记录修复说明](../2026-09-26-interruption-records.md)。
这些记录层测试使用模拟拟合或子进程，不是新增正式性能实验。

## 病态输入和并行分支的限制

原版与 hybrid 在病态输入处可以产生不同轨迹；任务绿色状态不表示未触发的分支也已覆盖。
本轮完整日志中的记录如下：

| 系统 | reference：code / 更新 / 固定 hold 检查 | hybrid：code / 更新 / 固定 hold 检查 |
|---|---|---|
| Ubuntu | 2 / 0 / 0 | 2 / 3 / 3 |
| macOS | 2 / 2 / 2 | 1 / 3 / 3 |
| Windows | 2 / 0 / 0 | 1 / 1 / 1 |

Linux/Windows 的原版没有触发自适应先验更新，日志明确输出 partial coverage，
因此这两个任务没有观察到该原版分支。已触发的检查验证固定初始 hold，
不要求不同 BLAS 或两引擎得到同一病态轨迹；病态案例不作为统计质量成功证据，
`code=1` 也不能单独证明收敛。

Python snow2 与 R 调用方持有 snow cluster 的测试在三个系统实际执行。
Unix multicore 在 macOS/Linux 执行，Windows 明确记录不执行 Unix fork、已测试 snow。
这些结果不表示 hybrid 开放了多 worker。

## 证据与边界

JSON 保存从已核验 checkout 提交的 Git blob 计算的 101 个源、测试、示例和复现文件
SHA-256，以及完整原始任务日志的哈希。CI 没有单独对安装后文件做逐文件 fingerprint，
不能把这些提交哈希描述为运行中的源码保护。原始完整日志、runner/worker 标识、
环境路径和编译产物不复制到仓库。

本次为 hosted CPU 的源码安装回归，不是 wheel 安装矩阵、`R CMD check`、
CUDA/MPS 验证、交互式 RStudio 验收或首版完整验收。独立 Intel 无 Torch reference
wheel 的[历史证据](intel-mac-reference.md)仍属于 `ad9bed2`，不能算成本轮测试。
同样，本轮 CPU CI 不改变云端 CUDA 正式性能或 G5 的未完成状态。

本报告和 JSON 的校验值见 [SHA-256 清单](cross-platform-ci-8b5ede9.sha256.json)。
此前 `e2ff892` 三个文件、旧 `cross-platform-ci.json`、Intel 记录及历史哈希清单均保持原样。
