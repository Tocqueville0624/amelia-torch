# amelia-torch

[English](README.md) · [安装](docs/setup.zh-CN.md) · [文档目录](docs/README.zh-CN.md)

基于 Amelia 1.8.3 bootstrap 期望最大化（EM）方法的 Python/R 多重插补工具，以 PyTorch 支持 CPU 和 GPU 计算。多重插补生成多份完成数据，使分析能够计入缺失值带来的不确定性。

**开发版本。** 原生后端支持连续数值数据。高级选项通过原版 R Amelia 流程提供，可选择原版 EM 或 PyTorch EM。统计验证尚未完成；目前从源码安装，未发布 PyPI 或 CRAN。

## 项目贡献

- 实现 Amelia EM 计算的 PyTorch 后端，与固定版本 R 实现对照。
- 提供 Python/R 接口，在兼容路线保留数据类型和 R 结果对象。
- 在三组公开数据上提供可复现的 CPU、NVIDIA CUDA 和 Apple MPS 基准，保留运行更慢的配置及尚未完成的验证结果。

本项目实现并评估既有统计方法。基准数据用于计算性能评估，不是社会科学代表性样本。

## 结果

Windows 11 / RTX 3080：每组数据 100,000 行，每次调用生成五份插补。下表为两次预热后五次正式重复的中位数，单位秒。CPU 方法预算为四线程；并行 R 使用四个 worker，各一个 BLAS 线程。“64”表示双精度。

| 数据 | R 串行 | R ×4 | 原生 CPU64 | 原生 CUDA64 | 混合 CPU64 | 混合 CUDA64 |
|---|---:|---:|---:|---:|---:|---:|
| Covertype, 10 列 | 15.280 s | 8.340 s | 5.484 s | 4.955 s | 16.670 s | 17.790 s |
| Household Power, 7 列 | 10.200 s | 5.540 s | 3.452 s | 3.592 s | 11.680 s | 12.420 s |
| Year Prediction MSD, 90 列 | 230.560 s | 121.730 s | 32.979 s | 22.115 s | 110.620 s | 101.640 s |

90 列任务中，原生 CUDA64 比原生 CPU64 快 **1.49 倍**，比串行 R 快 10.43 倍。与 R 的差异还包含实现和流程差异：原生路线支持的功能较少。R 混合路线比自身 CPU 版本快 1.09 倍。若干较窄任务的 GPU 收益有限或更慢。详见 [Windows 方法与原始结果](docs/validation/2026-09-27-windows-rtx3080/README.zh-CN.md)。

独立 Linux T4 实验中，原生 CUDA64 比同机 CPU64 快 1.21–1.91 倍。其混合套件未完整取回，所有已保存 CUDA 配置均慢于并行 R。实测 M4 上的 Apple MPS 慢于同精度 CPU。详见[跨平台结果](docs/validation/2026-09-27-evidence-summary.zh-CN.md)。

## 接口

| 路线 | Python | R | 范围 |
|---|---|---|---|
| 原版参考 | `amelia_reference()` | `amelia_compat()` | CPU 上的原版 R Amelia 1.8.3，不需要 PyTorch |
| 混合 | `amelia_torch_compat()` | `amelia_torch_compat()` | 原版 R 预处理、bootstrap、抽样与输出，仅用 PyTorch 替换 EM |
| 原生 | `amelia()` | `amelia_torch()` | 连续数值数据；不支持的高级选项明确报错 |

默认 CPU float64。CUDA float64/float32 和 MPS float32 须显式选择。混合路线逐份生成插补；参考路线保留 R 并行选项。请按分析所需变量和模型选项查阅[兼容表](docs/amelia-compatibility.zh-CN.md)。

## 安装与使用

安装 Python 3.12 后，克隆仓库并建立虚拟环境：

```sh
git clone https://github.com/Tocqueville0624/amelia-torch.git
cd amelia-torch
python3.12 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell 将后两条命令替换为 `py -3.12 -m venv .venv` 和 `.venv\Scripts\Activate.ps1`。

原生和混合路线需要 PyTorch，CPU/CUDA 安装版本通过[官方选择器](https://pytorch.org/get-started/locally/)确定。R 相关路线还需要 R 和 Amelia 1.8.3。项目依赖安装如下：

```sh
python -m pip install -e '.[reference]'
Rscript scripts/setup_r.R
R CMD INSTALL --library=.R-library r-package
```

最后一条命令构建 R 接口，需要 C 编译工具链。各平台细节及无 Torch 的原版参考安装见[安装说明](docs/setup.zh-CN.md)。

安装依赖后的 Python 混合路线示例：

```python
import numpy as np
from amelia_torch import amelia_torch_compat

x = np.random.default_rng(42).normal(size=(300, 4))
x[::5, 1] = np.nan
fit = amelia_torch_compat(x, m=5, seed=42, r_library=".R-library")
completed = fit.imputations[0]
fit.save_rds("fit.rds")
```

R/RStudio 示例，在仓库根目录开启新的会话：

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

两例均使用 CPU float64。加速器可设为 `device="cuda", dtype="float64"` 或 `device="mps", dtype="float32"`。合并推断须保留全部插补数据。参见 [R 用法](docs/r-interface.zh-CN.md)、[Python/R 数据交换](docs/python-reference-bridge.zh-CN.md)和[示例](examples/README.zh-CN.md)。

## 验证与限制

已记录检查覆盖 Windows、macOS、Linux 的 CPU 安装、固定 CUDA 案例、观察值保留及收敛。这些检查不证明完整统计等价。

预设 Mac 推断研究完成 10,500 次拟合。随机缺失（MAR）与有限压力标准通过，但**完全随机缺失（MCAR）标准未全部通过**，其中也包括原版 R 的一项标准。CUDA 推断验证尚未完成。更多缺失模式、全量来源数据、内存极限和部分平台组合仍未验证。参见[验证摘要](docs/validation/2026-09-27-evidence-summary.zh-CN.md)及[发布标准](docs/release-gates.zh-CN.md)。

## 复现与归属

仓库包含许可样本、下载脚本、校验值和原始基准记录。完整 UCI 来源压缩包约 232 MiB，单独下载。[数据](docs/datasets.zh-CN.md) · [复现](docs/reproduce.zh-CN.md) · [历史迁移与编号映射](docs/history/README.zh-CN.md) · [贡献指南](CONTRIBUTING.zh-CN.md)。

GPL-3.0-only。维护者 Sheng Wan。Amelia 方法及原版实现作者为 James Honaker、Gary King 和 Matthew Blackwell。数据适用独立许可。参见[第三方归属](THIRD_PARTY.zh-CN.md)、[贡献者](CONTRIBUTORS.zh-CN.md)及[引用元数据](CITATION.cff)。本项目与 Amelia 原作者无隶属关系。
