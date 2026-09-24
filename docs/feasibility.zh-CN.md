# Amelia → Python/PyTorch：可行性调研

调研日期：2026-09-23。区分官方资料、当前机器实测与尚待验证的工程判断；本报告不包含插补加速结果。

## 结论与项目价值

**值得做，尤其适合作为科学计算、数据科学或研究工程方向的求职作品。** 项目不必发明新统计方法；在已有方法上完成正确实现、性能分析、跨语言交付和可复现实验，本身就能体现工程能力。对纯前端或业务系统岗位，其相关性会弱一些。这是基于项目能力构成的判断，不是招聘结果保证。

最有说服力的成果是：一个边界明确的 EMB 实现、一组与原版对照的正确性证据、一份说明 GPU 在何时加速或变慢的报告，以及可在 RStudio 演示的接口。简单包装原版 R 调用、仅把数据转成 GPU tensor，或展示大矩阵乘法加速，均不足以完成目标。

合理定位为 **“Amelia-style EMB 的可验证 GPU 后端与 R 接口”**。不宣称首创 GPU 插补，不提前承诺全面替代 Amelia，不承诺固定倍数的加速。

## 原版究竟做什么

Amelia 的核心方法是 bootstrap + EM：对重抽样的数据拟合多元正态模型，再对原始数据的缺失部分作随机条件抽样，重复得到多个完整数据集。EM 本身不是通过梯度训练神经网络。方法和软件来源见 [Honaker、King、Blackwell 的 JSS 论文](https://www.jstatsoft.org/article/view/v045i07)及[官方使用文档](https://iqss.github.io/Amelia/articles/using-amelia.html)。

原版并非纯 R 解释执行：[官方源代码](https://github.com/IQSS/Amelia/blob/master/src/em.cpp)已有 RcppArmadillo/C++ 核心；[公开 API](https://iqss.github.io/Amelia/reference/amelia.html)已有多进程并行。Windows 使用 `snow`；正式 RStudio 基准也优先使用 PSOCK/snow，避免 fork 环境差异。故“Python 比 R 快”不是成立的前提。

完整 Amelia 还包含变量变换、类别/顺序变量、时间和横截面结构、先验、边界及诊断。第一版仅做连续型数值矩阵的核心方法，后续逐项扩展并记录兼容性。原版 1.8.3 是本次安装并测试的基线，来源与许可见其 [DESCRIPTION](https://github.com/IQSS/Amelia/blob/master/DESCRIPTION)。

## 与现有项目的关系

| 已有工作 | 已覆盖内容 | 本项目可形成的区别 |
|---|---|---|
| [Amelia](https://github.com/IQSS/Amelia) | EMB、多重插补、C++ 核心、CPU 并行、成熟 R 使用流程 | PyTorch CPU/CUDA/MPS 后端、精度对照、GPU 性能边界 |
| [MIDASpy / rMIDAS](https://www.jstatsoft.org/article/view/v107i09) | Python/R 多重插补，去噪自编码器；[实现支持 GPU 配置](https://github.com/MIDASverse/MIDASpy) | 保持 EMB 统计方法，避免将不同模型的速度差解释为同一算法加速 |
| [impyute](https://impyute.readthedocs.io/) | Python 插补，含标为 EM 的实现 | “有 EM”不等于完整 Amelia EMB；需核对多元条件矩、bootstrap 与随机抽样语义 |
| [Autoimpute](https://github.com/kearnz/autoimpute) | Python 单次/多重插补与下游分析工具 | 并非本次找到的 Amelia GPU 移植版本 |
| [PyPOTS](https://pypots.com/ecosystem/) | 多种时间序列插补模型与评估生态 | 不把神经网络插补当成 EMB 的等价替代 |

公开检索使用了 `Amelia Python imputation GPU`、`Amelia torch imputation`、`bootstrap EM Python imputation`、`Amelia CUDA imputation` 及 GitHub 域名限定，核对了上述项目的官方说明和 Amelia 源码。**未发现成熟、明确以 Amelia EMB + PyTorch GPU + R 接口为定位的同类实现；这不是不存在任何相关仓库的证明。** 搜索中同名语言模型项目与缺失数据软件无关。发布前再做一次名称和近似项目检索。

## 可以加速哪些部分，为什么可能不快

以下为待验证的工程假设：

- EM 的条件均值、协方差和充分统计量涉及密集线性代数，数据足够大时可能受益于 GPU。
- 将相同缺失模式的行分组，可以复用条件矩阵分解；对多个 bootstrap 副本进行有限批处理，可能提高 GPU 利用率。
- 不同 EM 迭代相互依赖，不能任意并行；副本收敛步数也可能不同。
- 若每行缺失模式都不同，按模式分组会产生很多小任务，Python 循环和 GPU 启动开销可能抵消收益。应记录实际模式数与组大小分布。
- 小型社会科学数据、较少变量或 `m=5` 的任务可能已经被原版高效完成；GPU 的传输、启动、同步、R/NumPy 转换开销可能更大。
- 原版已有 CPU 并行，单线程基线会夸大项目收益。CPU 优化、算法向量化、精度变化和硬件加速必须分别报告。

因此先做 CPU 双精度正确版本并剖析耗时，再设计 GPU 计算，避免先写大型兼容层。即使最后仅在某类大数据上加速，或没有稳定加速，可靠的负面结果和瓶颈分析仍能成为完整作品。

## 这台 Mac 的可行性：已实际验证

| 项目 | 本次观察 |
|---|---|
| 硬件 | iMac，Apple M4，8 核 CPU / 8 核 GPU，16 GB 统一内存 |
| 系统 | macOS 26.6.2，arm64 |
| 原有工具 | R 4.5.3（arm64）、RStudio、Git、编译命令行工具、uv，已有 Python 3.12.13 |
| Python 环境 | 新建项目 `.venv`，安装 PyTorch 2.14.0、NumPy 2.5.3、SciPy 1.18.1、pytest、ruff |
| R 环境 | 项目 `.R-library` 新装 Amelia 1.8.3、reticulate 1.47.0 及所需依赖；复用已有 jsonlite 2.0.0 |
| Python CPU | float64/float32 基础算子检查通过 |
| Python GPU | MPS float32 的乘法、Cholesky、solve、求和、索引、正态抽样检查通过；CPU 自动回退关闭 |
| R 桥接 | R → reticulate → 项目 Python → PyTorch → MPS 实测通过 |
| 原版检查 | 200×3 合成数据，2 份插补结果完整且已观测值保持不变 |

**Mac 足以完成当前项目开发，不需要先购买新机器。** [PyTorch MPS 文档](https://docs.pytorch.org/docs/main/notes/mps.html)说明 MPS 不支持 float64；基准采用 CPU float64，MPS float32 单列为实验路径。本次 2×2 算子检查不能证明所有大小、病态矩阵或整个 EM 都正确。CUDA 代码路径仍要上 NVIDIA 机器验证。

运行限制的实测经验：受限执行环境曾返回 `mps_available=false`；在获得工具权限的本机进程中，MPS 可用且检查通过。遇到这一现象应先检查进程权限，不能判定 M4 不支持 GPU。`reticulate` 的解释器路径必须保留 `.venv/bin/python`；对该符号链接使用 `normalizePath()` 会选到基础解释器，丢失项目依赖。

初始化时磁盘可用约 24 GiB，足以完成本次依赖安装；大数据实验采用分块、按需生成和有限副本批次，避免同时物化 `m` 份大矩阵。这里不建议为本项目安装完整 Xcode、Mac CUDA 工具包或 Docker；现有工具已足够本阶段。

## Windows + RTX 3080：适合做最终 CUDA 测试

NVIDIA 将 RTX 3080 列为 [CUDA compute capability 8.6](https://developer.nvidia.com/cuda/gpus)，官方列有 [10 GB / 12 GB 显存版本](https://www.nvidia.com/en-us/geforce/graphics-cards/30-series/rtx-3080-3080ti/)；[PyTorch 官方安装页支持 Windows + CUDA](https://pytorch.org/get-started/locally/)。因此该机器适合作为本项目的 CUDA 测试机，通常不必先租云 GPU。

但此会话尚未连接 Windows：CPU、系统内存、显存版本、Windows 版本、驱动、PyTorch wheel 支持均未实测。到机后记录 `nvidia-smi`、实际设备属性和编译支持，并运行 float64/float32 检查。3080 的 FP64 能力与 FP32 不对等，不能把宣传的单精度算力当成双精度性能保证；参见 [NVIDIA GA102 白皮书](https://www.nvidia.com/content/PDF/nvidia-ampere-ga-102-gpu-architecture-whitepaper-v2.pdf)。

优先原生 Windows 完成 RStudio → reticulate → CUDA；WSL2 可另作实验但不是前置条件。最终加速比必须在 Windows **同一台机器**上对照 R 原版、Python CPU 与 CUDA，不能用 Mac 上 R 的耗时除以 Windows GPU 耗时。详见[基准方案](benchmark-plan.zh-CN.md)。

## RStudio 接口与交付路径

最终目标是普通 R 包，由 `reticulate` 调用 Python 核心；RStudio 是运行环境，无需开发专用 IDE 插件。[官方 reticulate 包开发文档](https://rstudio.github.io/reticulate/articles/package.html)支持该模式。开发期显式绑定项目虚拟环境，未来分发时再设计 Python/CUDA 依赖管理，避免自动装到错误环境。

接口应保留列名、行顺序和已观测值，返回多份插补数据、收敛状态、设备及精度信息。R 数值默认双精度，与 MPS 精度转换必须显式；NumPy → R 输出有转换成本，见[官方转换说明](https://rstudio.github.io/reticulate/articles/calling_python.html)。未经完整契约测试，不应把新对象伪装成原版 `amelia` 类。

## 来源与许可边界

Amelia 元数据标注 `GPL (>= 2)`。本次只安装原版作为外部基线，没有将其源代码复制进项目。后续逐行移植或复制代码前，记录来源、版本和适用许可，再确定兼容的项目许可证；不直接给潜在衍生代码套 MIT。当前项目尚未选择发布许可。独立实现也必须引用算法作者，并区分既有方法与新增工程贡献。

测试只用合成或许可清晰的公开数据；发布材料不包含机器序列号、私人路径、保密工作数据。所有性能结论以可检查的结果文件为依据。
