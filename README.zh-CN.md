# amelia-torch

[English](README.md) · [文档目录](docs/README.zh-CN.md)

基于 Amelia bootstrap–EM 方法的多重插补工具，提供 Python 和 R 接口，以及实验性的 PyTorch CPU/GPU 后端。

**当前为开发快照。** 本非官方项目以完整复现 **Amelia 1.8.3** 流程为目标。原生实现目前支持连续数值数据；高级选项通过明确标注的 R 兼容路线提供。完整统计验收尚未完成，尚未发布到 PyPI 或 CRAN。

[![CPU 检查](https://github.com/Tocqueville0624/amelia-torch/actions/workflows/tests.yml/badge.svg)](https://github.com/Tocqueville0624/amelia-torch/actions/workflows/tests.yml)

## 文档

| 需求 | 文档 |
|---|---|
| 在 Mac、Windows 或 Linux 安装 | [安装说明](docs/setup.zh-CN.md) |
| 插补数据并将结果用于 R | [R 接口](docs/r-interface.zh-CN.md) · [Python 桥接](docs/python-reference-bridge.zh-CN.md) |
| 选择受支持的流程 | [兼容表](docs/amelia-compatibility.zh-CN.md) · [示例](examples/README.zh-CN.md) |
| 理解方法与项目贡献 | [流程解读](docs/project-walkthrough.zh-CN.md) · [架构](docs/architecture.zh-CN.md) |
| 判断现有证据 | [结果摘要](docs/validation/2026-09-27-evidence-summary.zh-CN.md) · [发布标准](docs/release-gates.zh-CN.md) |
| 复现或参与开发 | [复现说明](docs/reproduce.zh-CN.md) · [贡献指南](CONTRIBUTING.zh-CN.md) · [全部文档](docs/README.zh-CN.md) |

## 项目贡献

多重插补生成多份完成数据，使下游分析能够计入缺失数据的不确定性。本项目研究：在保留相同统计流程的前提下，张量库和 GPU 能否缩短运行时间，并让研究者在 Python 与 R 之间使用这些结果。

项目贡献是既有方法的实现与评估：PyTorch EM 后端、保留类型的 Python/R 数据交换、原版对照，以及三组公开数据上的可复现实验。本项目不提出新的插补估计方法。基准数据用于计算负载评估，不是社会科学代表性样本。

## 接口

| 路线 | Python | R | 范围 |
|---|---|---|---|
| 原版参考 | `amelia_reference()` | `amelia_compat()` | 未修改的 R Amelia 1.8.3，CPU 运行，不需要 PyTorch |
| 混合兼容 | `amelia_torch_compat()` | `amelia_torch_compat()` | 保留原版 R 预处理、bootstrap、抽样和输出，仅以 PyTorch 替换 EM |
| 原生连续 | `amelia()` | `amelia_torch()` | 连续数值 EMB；不支持的高级选项明确报错 |

默认 CPU float64。CUDA float64/float32 和 MPS float32 必须显式选择。混合路线逐份调度插补；参考路线保留原版 R 并行功能。兼容路线保留官方 R 结果对象，原生路线采用独立结果结构。选择前请查阅[兼容表](docs/amelia-compatibility.zh-CN.md)。

## 安装与使用

```sh
git clone https://github.com/Tocqueville0624/amelia-torch.git
cd amelia-torch
python3.12 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell 将后两条命令替换为 `py -3.12 -m venv .venv` 和 `.venv\Scripts\Activate.ps1`。

完成上述环境设置后，原生和混合路线还需要兼容的 PyTorch；CPU/CUDA wheel 按[官方安装选择器](https://pytorch.org/get-started/locally/)选择。原版参考路线不需要 Torch。R 相关路线的安装入口为：

```sh
python -m pip install -e '.[reference]'
Rscript scripts/setup_r.R
R CMD INSTALL --library=.R-library r-package
```

最后一条命令构建 R 接口，需要 C 编译工具链。Python 原版参考路线不需要安装该接口包。各平台步骤及 Intel Mac 无 Torch 路线见[安装说明](docs/setup.zh-CN.md)。

Python 示例，需要先安装混合路线依赖：

```python
import numpy as np
from amelia_torch import amelia_torch_compat

x = np.random.default_rng(42).normal(size=(300, 4))
x[::5, 1] = np.nan
fit = amelia_torch_compat(x, m=5, seed=42, r_library=".R-library")
completed = fit.imputations[0]
fit.save_rds("fit.rds")
```

R/RStudio 示例，在仓库根目录开启新的 R 会话：

```r
.libPaths(c(file.path(getwd(), ".R-library"), .libPaths()))
library(ameliatorch)
use_amelia_python(venv = ".venv")
set.seed(42)
x <- data.frame(a = rnorm(300), b = rnorm(300), c = rnorm(300))
x$b[seq(1, 300, 5)] <- NA_real_
fit <- amelia_torch_compat(x, m = 5, p2s = 0)
summary(fit)
Amelia::compare.density(fit, var = "b")
```

两例均使用 CPU float64。加速器须显式设置 `device="cuda", dtype="float64"` 或 `device="mps", dtype="float32"`。下游合并推断应保留**全部**插补结果。[R 工作流提示词](docs/r-user-agent-prompt.zh-CN.md)可用于在调用编程助手前明确数据、模型、隐私和输出要求。

## 结果

Windows 11 / RTX 3080 实验中，每组数据使用 100,000 行，每次生成五份插补。下表为两次预热后五次正式运行的中位数；CPU 预算为四线程，原版 R 使用四个单线程工作进程。

| 数据 | R 串行 | R ×4 | 原生 CPU64 | 原生 CUDA64 | 混合 CPU64 | 混合 CUDA64 |
|---|---:|---:|---:|---:|---:|---:|
| Covertype，10 列 | 15.280 s | 8.340 s | 5.484 s | 4.955 s | 16.670 s | 17.790 s |
| Household Power，7 列 | 10.200 s | 5.540 s | 3.452 s | 3.592 s | 11.680 s | 12.420 s |
| Year Prediction MSD，90 列 | 230.560 s | 121.730 s | 32.979 s | 22.115 s | 110.620 s | 101.640 s |

90 列任务中，原生 CUDA64 比原生 CPU64 快 **1.49 倍**，比串行 R 快 **10.43 倍**。后者包含实现和流程差异，原生路线支持的功能较少。完整 R 混合路线相对混合 CPU64 的收益为 **1.09 倍**。较窄任务的 GPU 收益有限或更慢，因此不能认为 Python 或 GPU 总是更快。[Windows 完整报告：float32、逐次耗时、质量检查与源码哈希](docs/validation/2026-09-27-windows-rtx3080/README.zh-CN.md)。

独立的 Linux T4 实验中，原生 CUDA64 比同机 CPU64 快 1.21–1.91 倍。T4 混合记录只回收 11/12 个配置，五个已保存 CUDA 配置均慢于原版 R snow2。实测 M4 Mac 上，MPS 慢于同精度 CPU。不同主机之间的耗时不是受控显卡比较。详见[证据摘要](docs/validation/2026-09-27-evidence-summary.zh-CN.md)。

## 验证范围与限制

- Windows 的 210 次调用、1,050 份插补均通过已记录的收敛、观察值保留和完整人工遮盖评分检查。Windows RTX 3080 与 Linux T4 的固定 CUDA 案例通过。这些检查不证明完整分布等价。
- `ef729c0` 的 Windows、macOS、Linux CPU CI 各通过 307 项 Python 测试、九个 R 测试文件和下游示例。Intel Mac 单独通过无 Torch 原版安装；Mac RStudio 流程也有实际记录。
- 预先规定的 Mac 推断研究完成 10,500 次拟合。MAR 与有界压力检查通过，但 **MCAR 统计标准未全部通过**，其中也包括原版 R 的一项标准。CUDA 推断验收尚未完成；原门槛和负面结果完整保留。
- 原生高级功能、更多缺失机制、全量来源数据、内存极限及部分 GUI/平台组合仍不在已验证范围内。[发布标准](docs/release-gates.zh-CN.md)区分了这些缺口与已完成检查。

仓库包含带归属的小样本、校验值、下载脚本和原始基准记录。完整 UCI 压缩包约 232 MiB，不进入 Git。见[数据与许可](docs/datasets.zh-CN.md)。Colab 实验处于暂停状态；CUDA 统计验收尚未完成。

## 许可与归属

GPL-3.0-only。维护者：**Sheng Wan**。Amelia 方法及原版实现归属于 **James Honaker、Gary King 和 Matthew Blackwell**。数据适用独立许可证。参见[第三方归属](THIRD_PARTY.zh-CN.md)、[贡献者](CONTRIBUTORS.zh-CN.md)及[引用元数据](CITATION.cff)。本项目与 Amelia 原作者无隶属关系，也未获得其背书。
