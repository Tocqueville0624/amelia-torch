# G7：Python 完整调用成本与独立 MCAR 压力记录

这轮有界实验完成了九次预定公开调用、每次五份插补。10 万行 Covertype 的 Python reference 与 CPU64 hybrid 调用均约 12 秒，六次调用均通过收敛、观察值保持和全部 heldout 计分检查。独立逐格 MCAR 压力输入的三个引擎都按原版规则留下两条全空行，因此每份结果有 14 个 heldout 未计分；这些结果保留为压力记录，**不能标成质量全部通过的速度样本**。

## 预定计划与测量范围

[计划](plan.json) 在 2026-09-26 22:07:03 UTC 保存后才开始拟合，九次调用于 22:09:03 UTC 全部结束。计划固定输入及元数据 SHA-256、16 个计算源文件指纹、执行顺序和质量规则。实际工作区包含尚未提交改动，因此报告中的 Git revision 仅作背景标签；**测量源码以指纹和[源码快照](measured-source.zip)为准**。快照的 16 个测量文件全部与计划一致，另含许可证、依赖声明及数据复现文件，见[核验清单](source-snapshot.json)。

所有调用固定 `m=5`、seed=20260926、R `L'Ecuyer-CMRG / Inversion / Rejection`、ordinary bootstrap、startvals=0、tolerance=1e-4、emburn=(0,300)、autopri=.05、empri=NULL、单副本串行调度。线程环境变量请求 4 线程，并非实测所有 BLAS 线程池。MPS 明确指定 float32，CPU 明确 float64，MPS fallback=0；特征值诊断仍明确在 CPU 执行。

公开 Python 调用从输入数组开始计时，到完整 NumPy 插补结果和 RDS 字节已回到 Python、R 子进程退出并清理临时文件为止。包含 typed binary 传输、新 Rscript 启动、R 包加载、hybrid 的独立 Python/Torch 初始化、原版前后处理及抽样、EM 和设备传输。GPU 工作必须完成并回传 CPU 结果后才能返回。

NPZ 读取、父 Python 进程的模块导入、评分、哈希和报告写入在计时外。再次向用户指定目录执行 `save_rds` 的落盘不在计时内；生成、传回及读取完整 RDS 字节已在计时内。每一次调用均创建**新的 R 进程**。“首次/后续”只区分本轮父 Python 进程中的调用次序，不声称冷操作系统缓存或持续预热的 R 会话。此前同机已有开发运行，也未清空磁盘缓存。

本次与旧 R 内存计时不是同批配对，源码、时间段及启动边界不同，不能硬相减来估计纯桥接成本。其他协作拟合在计时期间暂停，但没有完整测量或隔离操作系统后台负载。

## 10 万行 Python 产品调用

Covertype 完整数值子集为 100000×10，人工 block-MCAR 缺失率 30%，8 种模式，300000 个 heldout，无全空行。来源、许可及抽样规则沿用[数据清单](../../../data/manifest.json)和[复现说明](../../reproduce.zh-CN.md)，输入摘要及精确 NPZ 指纹保存在计划内。

| 路线 | 首次调用（秒） | 后续 1（秒） | 后续 2（秒） | 后续中位数（秒） |
|---|---:|---:|---:|---:|
| Python → 官方 R reference | 12.144 | 12.114 | 11.804 | 11.959 |
| Python → R + Torch CPU64 hybrid | 11.966 | 12.047 | 12.210 | 12.128 |

每次五份插补均收敛；迭代数均为 52/41/43/72/59。全部观察值不变，所有 heldout 均有限并计分，没有意外非有限值。各引擎自己的三次调用返回 RDS 摘要完全一致，未要求两个引擎的 RDS 字节相同。只有两次后续重复，这些数字是描述性成本记录，不足以判断约百分之一的差距是否稳定。

每次返回的五个 NumPy 数组合计 40000000 字节；reference RDS 为 18627244 字节、hybrid RDS 为 18628077 字节。这些是结果体积，**不是峰值内存**。

## 独立逐格 MCAR 压力例

保持已有 Household Power 5000×7 输入及掩码不变：缺失率 29.7057%，125 种缺失模式，10397 个 heldout，其中两条全空行包含 14 个 heldout。原版规则要求全空行不参与拟合且输出仍为 NA；实验没有删除这些 heldout、修改缺失模式或重抽一个更容易评分的输入。

| 路线 | 完整 Python 调用（秒） | 每份未评分 heldout | 严格质量状态 |
|---|---:|---:|---|
| 官方 R reference | 0.561 | 14 | heldout_incomplete |
| R + Torch CPU64 hybrid | 2.812 | 14 | heldout_incomplete |
| R + Torch MPS32 hybrid | 24.271 | 14 | heldout_incomplete |

三次调用均返回 code 1、五份插补全部收敛，迭代数均为 18/14/15/16/12；观察值完全保留，全空行保持 NA，其他行所有应补值有限。每份未评分值都来自这两条全空行，完整 heldout RMSE 因此为 null，而非偷偷只对有限子集评分。hybrid bootstrap 拟合中的模式数为 124/124/122/124/124，没有伪逆或 autopri 更新；记录中没有警告、异常或 OOM。未遇到 OOM不等于已量出显存上限。

每条路线只有一次压力调用，MPS 和 CPU 的精度也不同。此表只说明该固定输入上的实际行为与耗时，不报告通过质量门槛的加速比，不把它与低模式 block-MCAR 数据拼接成模式数的因果扩展曲线，也不能外推到 90 维独立缺失或全量数据。

## 审计、环境与复现

[全部逐次结果](results.json)保留每份质量、迭代、backend、warnings、返回体积和哈希。所有九次调用、45 份插补均返回并收敛，运行中源文件及输入 guard 全通过。执行器最终退出码为 **1**，原因是三次压力例的完整 heldout 计分失败，并非把这些失败从结果中删除。[独立审计](audit.json)的 `audit_passed=true` 表示九次计划及失败记录完整可信；`all_runs_valid_for_speed_comparison=false` 仍明确保留。

环境为本机 Apple M4 / macOS arm64、Python 3.12.13、NumPy 2.5.3、Torch 2.14.0、R 4.5.3、Amelia 1.8.3。实际版本、设备与每份诊断见结果。所有峰值 RAM/VRAM 字段为 null；没有 CUDA 运行或完整统计推断等价声明。

在安装相同依赖并准备好两个输入后，可用[执行器](../../../scripts/validate_product_costs.py)生成新的计划和结果。旧计划要求源码指纹完全匹配，否则明确拒绝；不同平台应写新计划、使用独立输出目录，不能覆盖此证据。

```sh
.venv/bin/python scripts/prepare_benchmark_data.py --dataset covertype --rows 100000 --mechanism block_mcar --missing-rate 0.3 --seed 20260923 --output data/prepared/covertype-n100000-block_mcar-rate30-seed20260923.npz
.venv/bin/python scripts/prepare_benchmark_data.py --dataset household_power --rows 5000 --mechanism mcar --missing-rate 0.3 --seed 20260923 --output data/prepared/household_power-n5000-mcar-rate30-seed20260923.npz
.venv/bin/python scripts/validate_product_costs.py --write-plan results/local/g7-new/plan.json
.venv/bin/python scripts/validate_product_costs.py --execute results/local/g7-new/plan.json --output results/local/g7-new/results.json
# 上一步保留全空 heldout 时预期退出 1；不要因此跳过审计。
.venv/bin/python scripts/summarize_product_costs.py results/local/g7-new/plan.json results/local/g7-new/results.json --output results/local/g7-new/audit.json
```

[纯评分/审计测试](../../../tests/test_product_costs.py)无需再次拟合，检查全空 heldout 不会被隐去、非收敛与观察值改动不能通过、缺失 source/input guard 和虚假的完整 RMSE 会被拒绝。新增 G2 autopri 与 G4 caller-owned cluster/Unix multicore 检查已接入 CI；配置存在不等于后续三平台运行已经通过。
