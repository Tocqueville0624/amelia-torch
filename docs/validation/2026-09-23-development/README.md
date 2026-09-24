# 开发验证记录（2026-09-23）

这是开发快照的实测记录，**不是首版验收报告**。完整 Amelia 1.8.3 兼容、Windows RTX 3080 CUDA、平台边界与较复杂缺失模式仍需验证。所有数字只说明指定任务和机器上的结果。

## 本机与实验任务

Apple M4、8 CPU/8 GPU 核心、16 GB RAM；macOS 26.6.2，Python 3.12.13、PyTorch 2.14.0、NumPy 2.5.3、R 4.5.3、Amelia 1.8.3。CPU float64 为默认数值参考；MPS 仅显式 float32，特征值诊断明确回到 CPU。

三个 UCI 数据集各取 100,000 行完整数值子集，使用相同的人工块状 MCAR 输入：Covertype 10 列、Household Power 7 列、Year Prediction MSD 90 列。实际缺失率分别为 30%、28.571%、30%，缺失模式数为 8、7、8。每次生成 5 份插补，2 次预热后重复 5 次计时，EM tolerance=1e-4，最多 300 轮。数据来源、完整数据规模和抽样限制见[数据说明](../../datasets.zh-CN.md)。

## Native Python 端到端耗时

单位为秒，表内为 5 次正式测量的中位数。

| 数据集 | 原版 R 串行 | 原版 R snow ×4 | Torch CPU64 | Torch CPU32 | Torch MPS32 |
|---|---:|---:|---:|---:|---:|
| Covertype | 8.489 | 4.357 | 2.126 | 1.895 | 3.225 |
| Household Power | 5.490 | 2.885 | 1.552 | 1.478 | 2.232 |
| Year Prediction MSD | 194.947 | 121.373 | 13.744 | 12.089 | 20.267 |

**本次 MPS 比同机 Torch CPU64 慢约 44%–52%，比 Torch CPU32 慢约 51%–70%。** Torch CPU64 相对这台机器的 R 串行约快 3.5–14.2 倍，相对 R 四进程约快 1.9–8.8 倍。这是实现、数值库和执行方式的综合差异，不能归因于 GPU，也不能推广到使用其他 BLAS 的 R 安装。未开展瓶颈剖析，不能把猜测当作慢速原因。

全部 105 次调用（525 份插补，包括预热）经过独立质量审计：收敛、观察值保持、人工遮盖位置全部有限并参与计分、无剩余缺失/非有限值。RMSE 接近不构成分布等价证明。R 与 NumPy 使用不同随机数库，同 seed 不代表同一 bootstrap。

- [加强后的独立质量审计、中位数/IQR与哈希](benchmark-summary-audit-v2.json)；保留[首轮汇总](benchmark-summary.json)以追溯旧格式。加强审计确认全部计划任务、每份插补、种子顺序、退出码和有限正耗时，15/15 配置仍通过。
- [逐次报告和测量配置](benchmark-reports/suite.json)
- [当时实际测量的源码快照](measured-source.zip)：与汇总中源文件 SHA-256 核对。实验后新增了溢出拒绝、更严格失败计分、只读数组兼容和 fractional emburn 处理；当前开发源码因此可能不与旧测量哈希相同。旧结果由独立汇总器审计，不用后改源码冒充当时版本。

计时包含标准化、bootstrap、EM、条件随机补值、设备传输和恢复 CPU 输出；排除文件读取、进程冷启动、评分和保存。R snow 包含 worker 创建/销毁。Torch 和 R 串行设置 4 CPU 线程，R snow 为 4 worker ×1 线程；环境变量不保证所有 BLAS 都采用相同线程策略。没有峰值 RAM/VRAM 或后台负载观测，也未完全隔离操作系统其他工作。不同方法在固定随机顺序中依次执行。

本表是原生 Python 路线，不能代替 R→Python 产品接口的计时。

## 正确性与推断质量

- 原版 R 导出的固定 EM、显式随机补值、公共连续接口 fixture 用于确定性语义对照，覆盖初值、样本协方差、先验、停止规则、尺度和行列恢复。原版会原位改变 theta；导出器先复制输入。
- [MPS 内核报告](mps-kernel-validation.json)：无先验、经验先验和 cell prior 三个固定案例通过；使用匹配容差对照 CPU64，并用原版显式标准正态对照随机补值。它不是完整统计等价检验。
- [R 用户 MPS 接口报告](mps-r-interface-validation.json)：变换、类别、先验/边界三个固定案例，保留原版 R 随机流，只用 GPU 替换 EM。预先设置的门槛全部通过，最大标准化连续输出误差小于 2.2e-7，离散输出无差异。
- [400 次推断模拟及逐次记录](inference-validation.zh-CN.md)：指定联合正态模型下，MCAR/MAR 各 200 次独立数据、每次 5 份插补，共 2,000 次 EM 全部收敛。CPU64 的 OLS 系数偏差分别 −0.000688、0.002905；Rubin pooled 95% 区间覆盖率为 96%、97%，覆盖率 Monte Carlo 标准误为 1.39、1.21 个百分点。只适用于本实验模型，不是任意模型或 GPU 的覆盖率保证。
- [Python 原版 R 桥接验证](python-reference-bridge.json)与 [R 包检查](r-package-check.md)。原版 Amelia 1.8.3 的单行 priors 索引特例可能改动无关观察值，详见[算法契约](../../algorithm-contract.md)；兼容路径保留并说明此行为。

## 尚未验收

CUDA/RTX 3080 到机结果、Intel Mac 安装、全部原版参数组合/异常/下游工作流、独立逐格 MCAR 的性能压力、全量行数实验及峰值内存测量。跨操作系统 CI 的配置不能替代运行结果。不会因为 native CPU 变快或局部测试通过就称“完整复现”或“GPU 已加速”。
