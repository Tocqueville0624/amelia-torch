# Windows RTX 3080：原生 Python 与完整 R 混合路线

[English](README.md) · [文档目录](../../README.zh-CN.md)

**90 列、10 万行任务：原生 CUDA64 用时 22.115 秒，原版 R 串行为 230.560 秒，整体快 10.43 倍；相对同机原生 PyTorch CPU64，GPU 收益为 1.49 倍。** 完整 R 混合 CUDA64 用时 101.640 秒，GPU 收益为 1.09 倍。低维任务多数无 GPU 收益。上述 10.43 倍包含实现和工作流差异；现有跨主机记录不足以确定 3080 与 T4 显卡本身的速度比。

2026-09-27 UTC，本地 Windows 11 / RTX 3080 完成三组各 100,000 行公开数据的同机比较。原生/R 套件 **18/18 配置**、R 混合套件 **12/12 配置**完成并通过独立的收敛、观察值保留及完整 heldout 评分检查。合计 **210 次调用、1,050 份插补**，其中正式计时 150 次、预热 60 次。所有结果均保留。

测量源码为 [`810591e6a77956a49dfef5de1d4a2274fefe9e07`](https://github.com/Tocqueville0624/amelia-torch/tree/810591e6a77956a49dfef5de1d4a2274fefe9e07)。本次 Windows 测量与 Colab 历史记录独立；后者的缺失结果、暂停记录及 G5 未完成状态保持原样。

## 性能比较

在这些连续型基准任务中，原生 PyTorch 路线整体耗时最低，但 Python 语言本身不是已隔离的原因。实现、数值库、随机流和工作流范围均有差异；native 尚不支持原版 Amelia 的全部类别、变换、边界及面板选项。不能为了使用更快的路线忽略所需统计功能。

90 列任务的原生 CUDA64 为 **22.115 秒**，CUDA32 为 **20.160 秒**。相对原版 R 串行的 230.560 秒，分别约快 **10.43 倍、11.44 倍**；相对原版 R 四进程的 121.730 秒，分别约快 **5.50 倍、6.04 倍**。相对同机、同精度原生 PyTorch CPU，GPU 收益仅为 **1.49 倍、1.31 倍**。前两个比值包含移植和工作流差异，不能全算成显卡贡献。

完整 R 混合路线在 90 列数据上为 CUDA64 **101.640 秒**、CUDA32 **100.340 秒**；比各自混合 CPU 路线快 **1.09 倍、1.05 倍**，比原版 R 四进程快 **1.20 倍、1.21 倍**。它保留 R 的预处理、bootstrap、随机补值和后处理，还包含桥接、传输及串行副本调度。将它与 native 相减并不能测出“通信时间”。

7–10 列任务上的 CUDA 多数与同精度 CPU 相近或更慢。固定开销、传输、同步和小矩阵调度可能抵消计算收益；此实验没有做分阶段 profiling，不能把差值确定归因于通信。三组数据**行数均为 100,000**，数据内容、列数和缺失模式也不同；这不是只改变数据规模的受控实验。较大计算量可能更适合 GPU，但行数、列数、缺失模式、迭代次数和显存容量都会影响结果。

## 跨主机记录

| 原生 CUDA 路线 | 本地 RTX 3080 | 此前 Colab T4 | T4 耗时 / 3080 耗时 |
|---|---:|---:|---:|
| Year Prediction MSD，float64 | 22.115 s | 42.049 s | 1.90× |
| Year Prediction MSD，float32 | 20.160 s | 37.364 s | 1.85× |

这些记录说明 **3080 这台机器在该任务上更快**，不能单独证明 3080 芯片普遍比 T4 快多少。本地为 Ryzen 5 5600X、4 线程、Windows、Torch 2.14.0/CUDA13.2；T4 为共享 Colab Xeon、2 线程、Linux、Torch 2.10.0/CUDA 12.8，测量 revision 也不同。native CUDA 中仍有 CPU 工作。因此这只是跨主机观察值，不是受控 GPU 硬件对比。原版 R 的 10–11 倍差值更不能用来推导 3080/T4 的性能比。[T4 原始记录](../2026-09-26-colab-native/README.zh-CN.md)。

## 耗时

每项生成 `m=5` 份插补，2 次预热后正式运行 5 次。以下单位为秒，取正式耗时中位数。IQR 是重复间离散程度，不是置信区间；各项 IQR 和逐次值见 JSON。

| Dataset | R serial | R ×4 | Native CPU64 | Native CUDA64 | Native CPU32 | Native CUDA32 |
|---|---:|---:|---:|---:|---:|---:|
| Covertype, 10 variables | 15.280 | 8.340 | 5.484 | 4.955 | 4.715 | 4.900 |
| Household Power, 7 variables | 10.200 | 5.540 | 3.452 | 3.592 | 3.340 | 3.871 |
| Year Prediction MSD, 90 variables | 230.560 | 121.730 | 32.979 | 22.115 | 26.478 | 20.160 |

| Dataset | Hybrid CPU64 | Hybrid CUDA64 | Hybrid CPU32 | Hybrid CUDA32 |
|---|---:|---:|---:|---:|
| Covertype, 10 variables | 16.670 | 17.790 | 17.170 | 17.860 |
| Household Power, 7 variables | 11.680 | 12.420 | 11.390 | 11.950 |
| Year Prediction MSD, 90 variables | 110.620 | 101.640 | 104.920 | 100.340 |

| Dataset | Native CPU64/CUDA64 | Native CPU32/CUDA32 | Hybrid CPU64/CUDA64 | Hybrid CPU32/CUDA32 |
|---|---:|---:|---:|---:|
| Covertype, 10 variables | 1.107× | 0.962× | 0.937× | 0.961× |
| Household Power, 7 variables | 0.961× | 0.863× | 0.940× | 0.953× |
| Year Prediction MSD, 90 variables | 1.491× | 1.313× | 1.088× | 1.046× |

上述速度比大于 1 表示同机 CUDA 更快；每个比值均使用同一路线、同一精度的 CPU/CUDA 中位数。未删去失败后选择成功子集。

## 输入、环境与计时边界

| 数据 | 输入 | 人工缺失率 | 模式数 |
|---|---:|---:|---:|
| UCI Covertype | 100,000 × 10 | 30% | 8 |
| UCI Household Power | 100,000 × 7 | 28.57% | 7 |
| UCI Year Prediction MSD | 100,000 × 90 | 30% | 8 |

选取完整行后添加 block-MCAR 缺失；各路线复用同一份准备数据。不是全量来源数据，也不是逐格独立 MCAR 或 MAR。来源、CC BY 4.0 归属、下载哈希及处理规则见 [数据说明](../../datasets.zh-CN.md)、[清单](../../../data/manifest.json)和归档中的 `data/`。

- 硬件：AMD Ryzen 5 5600X（6 核、12 逻辑线程）；NVIDIA Ge Force RTX 3080（10 GiB），驱动 595.95。Windows 11，版本 10.0.26200。
- 环境：Python 3.12.14、PyTorch 2.14.0+cu132、NumPy 2.5.3；R 4.5.3、Amelia 1.8.3。GPU 探针及 R 桥接记录随归档保留。
- 预算：PyTorch/BLAS 4 线程；原版 R snow4 使用 4 个工作进程，每个工作进程 1 个 BLAS 线程。混合路线的插补副本仍串行调度。
- 配置：ordinary bootstrap、初值 0、tolerance `1e-4`、最多 300 轮、无显式 `empri`、`autopri=0.05`；正式 seed 20260923–20260927，预热 seed 20360923–20360924。CUDA 不启用 TF32。
- native 从内存输入计时到全部 CPU NumPy 完成矩阵返回，包含预处理、bootstrap、EM、随机补值、GPU 传输与同步；不含 R/Python 桥。
- R 从内存输入计时到完整结果返回；混合路线含桥接及 R 侧流程，原版 snow4 含工作进程创建/销毁。各路线均排除文件读取、解释器冷启动/首次包导入、事后评分和报告写入。
- 配置顺序在各套件内固定随机化，顺序执行。原生/R 和混合套件在不同时间批次运行，系统负载和温度未完全隔离，差异没有做显著性检验。

## 正确性与未完成项

独立审计覆盖全部预热和正式调用，检查预期配置、种子序列、成功状态、有限正耗时、每份拟合收敛、观察值保留和所有 heldout 评分；[原生/R 审计](benchmark-summary.json)与[混合审计](hybrid-summary.json)均通过。固定案例验证另有 native 两个精度各 3 例、完整 R GPU 两个精度各 3 例，均通过，详见归档的 `validation/`。

[配对汇总比较](paired-reference.json)核验了 12 个混合配置与原版 R 的输入、种子和 R RNG 设置，比较全部 7 次调用。没有设定数值等价阈值，也没有逐元素比较完整插补矩阵。跨这些配对的最大相对差包括：归一化 heldout RMSE 约 **0.059%**、协方差约 **0.95%**、Rubin 均值组间方差约 **3.05%**；个别迭代次数最多相差 7 轮。这些统计量的差异不能简化为“输出完全一样”。native 使用 NumPy PCG64，不能用相同整数 seed 与 R 配对随机抽样。

本次未执行 CUDA G5 正式推断模拟，不改变此前 Mac MCAR 冻结门槛未全通过的结论。性能检查和固定案例通过不等于统计推断验收。总进程 RAM/VRAM 峰值、更多缺失机制、混合类型、全量来源数据和显存容量极限不在本次结论内。

## 原始记录与离线复核

[benchmark-records.tar.gz](benchmark-records.tar.gz) 含 **43 个 JSON 文件**：30 个逐次 benchmark 报告、2 个 suite、7 个探针/固定案例报告、数据清单与 3 个准备记录。payload 保留原字节，归档文件名和 owner/time 元数据统一；不含安装环境、私人路径日志、原始数据、完整插补矩阵或参数 NPZ。报告中的参数文件名是当时本地文件引用，不能把它当作归档已包含该文件。

归档大小 **3,018,276 bytes**；SHA-256：

```text
6e7c8c82c04315be26f175c95ec9dabcc872e78942bd4c4f38b1aec6855a798f
```

[archive-index.json](archive-index.json) 给出每个 payload 与三个独立摘要的哈希。摘要中的原始时间、源码指纹、缺失遥测和限制原样保留：主套件未逐进程记录源码不变字段、原版主套件未当时记录每份 CSV 哈希；后续混合套件记录了复用主套件 CSV 的哈希。不能事后补造这些证据。

在仓库根目录解压后，可仅审核已有 JSON，以下命令不会启动插补：

```sh
python -m tarfile -e docs/validation/2026-09-27-windows-rtx3080/benchmark-records.tar.gz results/local/rtx3080-published
python scripts/summarize_benchmarks.py --input-dir results/local/rtx3080-published/native --output-dir results/local/rtx3080-published-native-audit --methods cpu64 cpu32 cuda64 cuda32 r_serial r_snow4
python scripts/summarize_hybrid.py --input-dir results/local/rtx3080-published/hybrid --output-dir results/local/rtx3080-published-hybrid-audit
python scripts/compare_hybrid_reference.py --reference-dir results/local/rtx3080-published/native --hybrid-dir results/local/rtx3080-published/hybrid --reference-methods cpu64 cpu32 cuda64 cuda32 r_serial r_snow4 --output results/local/rtx3080-published-paired.json
```

重跑性能实验须先按 [安装说明](../../setup.zh-CN.md) 配好 CUDA、R 及本地 R 库，并按 [复现说明](../../reproduce.zh-CN.md) 准备数据。主套件命令为 `python scripts/run_benchmark_suite.py --gpu cuda --threads 4 --workers 4 --output-dir results/local/benchmarks/rtx3080-new-main`；混合命令为 `python scripts/run_hybrid_suite.py --methods cpu64 cpu32 cuda64 cuda32 --threads 4 --csv-dir results/local/benchmarks/rtx3080-new-main/inputs --output-dir results/local/benchmarks/rtx3080-new-hybrid`。保留同一机器、同一环境及独立新输出目录，不覆盖历史测量。
