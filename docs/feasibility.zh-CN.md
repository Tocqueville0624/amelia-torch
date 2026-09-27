# 可行性与已有工作

[English](feasibility.md) · [文档目录](README.zh-CN.md)

初始调研日期：2026-09-23。本报告记录立项依据和环境初查；后续[Windows/Mac/T4结果](validation/2026-09-27-evidence-summary.zh-CN.md)已更新最初的硬件不确定性。当前许可证为GPL-3.0-only。

## 项目贡献

工程范围是可验证的 Amelia bootstrap–EM PyTorch 后端、Python/R 接口及实测性能边界，体现数值实现、原版对照、打包和可复现实验能力。统计估计方法属于已有工作；不宣称新估计方法或首个 GPU 插补系统。仅包装 R 调用或展示矩阵乘法不足以证明插补加速器的实用性。

Amelia 重抽样行、用 EM 估计多元正态模型，再对原始输入随机补值，不是梯度训练神经网络。[方法论文](https://www.jstatsoft.org/article/view/v045i07)、[使用文档](https://iqss.github.io/Amelia/articles/using-amelia.html)、[C++内核](https://github.com/IQSS/Amelia/blob/master/src/em.cpp)和[并行接口](https://iqss.github.io/Amelia/reference/amelia.html)表明原版已有编译核心与 CPU 并行，因此不能假定Python天然更快。完整兼容包括类别、变换、时间/横截面、先验、边界和诊断；连续实现只是开发子集，不是完整首版。

## 相关项目

| 项目 | 已有范围 | 本项目比较的区别 |
|---|---|---|
| [Amelia](https://github.com/IQSS/Amelia) | EMB、C++、CPU 并行、R 流程 | Torch CPU/CUDA/MPS、精度与性能比较 |
| [MIDASpy/rMIDAS](https://www.jstatsoft.org/article/view/v107i09) | 神经网络多重插补及 GPU 实现 | 保留 EMB，不把不同估计方法的速度差称作等价加速 |
| [impyute](https://impyute.readthedocs.io/) | Python插补，含标为 EM 的方法 | 核对多元条件矩、bootstrap 和随机抽样语义 |
| [Autoimpute](https://github.com/kearnz/autoimpute) | Python单次/多重插补及分析 | 初始检索未将其识别为 Amelia GPU 移植 |
| [PyPOTS](https://pypots.com/ecosystem/) | 时间序列插补模型与评估 | 不同模型族，不自动等价于 EMB |

初始检索包含 Amelia/Python/GPU、Amelia/torch、bootstrap/EM/Python、Amelia/CUDA及GitHub限定。未发现成熟且明确结合 Amelia EMB、PyTorch GPU 与 R 接口的项目；有限检索不证明相关仓库不存在。发布前仍需复核名称和近似项目。

## 计算假设

条件矩和充分统计量的密集线性代数可能受益于 GPU。缺失模式内复用分解、有限副本批处理可能降低成本。迭代相互依赖；大量独特模式产生小任务，传输、同步和接口开销可能抵消收益。必须比较原版 CPU 并行；成本归因需要 profiling，负面结果也属于有效证据。

## 开发环境

初始 Mac 为 Apple M4 iMac，8 CPU/8 GPU 核心、16 GB 统一内存、macOS 26.6.2 arm64。已有 R 4.5.3、RStudio、Git、命令行工具、uv、Python 3.12.13。项目本地环境安装 Torch 2.14.0、NumPy 2.5.3、SciPy 1.18.1、Amelia 1.8.3、reticulate 1.47.0。CPU64/32 基础算子、MPS32乘法/Cholesky/solve/求和/索引/正态抽样、R→Python→MPS 和 200×3 原版 R 例子通过初查。小探针不证明完整 EM 或速度。

MPS 不支持 float64，CPU64作为参考。受限进程曾隐藏 MPS，而有权限的本机进程可用。reticulate 须保留虚拟环境解释器符号链接。初始化时约 24 GiB空闲是历史观察，不代表当前容量。

## CUDA与 R 交付

RTX 3080 可执行CUDA，但 FP64 与 FP32 能力不同，宣传 FP32 算力不预测双精度收益，参见[NVIDIA架构白皮书](https://www.nvidia.com/content/PDF/nvidia-ampere-ga-102-gpu-architecture-whitepaper-v2.pdf)。其 Windows 安装和基准后续已实测并单列记录。R 串行/并行和 Torch CPU/CUDA须同机比较；Mac CPU 对 Windows GPU 不是独立 GPU 收益。

标准 R 包通过[reticulate](https://rstudio.github.io/reticulate/articles/package.html)即可在RStudio调用，不需 IDE 插件。保留名称、顺序、观察值、多份输出及诊断，记录[转换成本](https://rstudio.github.io/reticulate/articles/calling_python.html)。原生对象不得伪装官方类。

## 许可与证据

Amelia 声明GPL(>=2)，项目随后采用GPL-3.0-only 并保留[来源归属](../THIRD_PARTY.zh-CN.md)。实验使用合成或许可明确的公开数据，发布记录不含私人路径、机器序列号或保密工作数据。性能结论以记录的任务与测量条件为限。
