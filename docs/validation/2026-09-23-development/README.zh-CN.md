# Mac 开发验证

[English](README.md) · [文档目录](../../README.zh-CN.md)

M4、8 CPU/8 GPU 核、16 GB、Mac 26.6.2、Python 3.12.13/Torch 2.14.0/NumPy 2.5.3/R 4.5.3/Amelia 1.8.3 的开发实测，不是完整首版报告。默认 CPU64，MPS32显式选择，特征值诊断 CPU 执行。

## 耗时

每组 UCI 数值子集为 100,000 完整来源行、10/7/90 列，块状MCAR30/28.571/30%、8/7/8 模式，m5，两预热/五正式重复，tolerance 1e−4、最多 300 轮。下表秒数为中位数，IQR 和全部重复见JSON。

| 数据 | R 串行 | R snow4 | 原生 CPU64 | 原生 CPU32 | 原生 MPS32 | 混合 CPU64 | 混合 CPU32 | 混合 MPS32 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Covertype |8.489|4.357|2.126|1.895|3.225|7.909|7.960|10.550|
| Household Power |5.490|2.885|1.552|1.478|2.232|5.288|5.185|6.374|
| Year Prediction MSD |194.947|121.373|13.744|12.089|20.267|70.422|66.934|75.901|

原生 MPS32 比 CPU32 慢 51–70%，混合 MPS32 比混合 CPU32 慢 13–33%。Year 混合 CPU64 比串行 R 快 2.77 倍、snow4快 1.72 倍；窄输入接近串行 R、慢于 snow4。原生/R 差异包括实现、数值库、RNG 和范围，不能全归 GPU，未 profiling 定位原因。

原生 15 配置/105 调用/525 插补、混合 9/63/315 通过独立收敛、观察值、有限输出、完整 heldout 审计，含预热。原生 audit-v2 又核验计划、seed、退出码和正耗时，首轮摘要仍保留。源码 ZIP 匹配测量哈希，后续输入/错误修复不改写旧测量版本。

原生完整调用含预处理/bootstrap/EM/抽样/传输/CPU 恢复，R 混合含原版 R 及 reticulate 转换。排除读文件、冷进程/首次导入绑定、评分、写报告，snow 建群/销毁计入。Torch/R 串行请求 4 线程，snow4worker 各单BLAS线程；设置不证明实际占用。两套件不同批次/版本，后台负载未完全隔离，峰值 RAM/VRAM未测。不含Python→Rscript 启动/文件交换。

![Mac原生及R混合耗时](combined-timings.png)

## R 配对摘要

全部预热/正式按 phase/seed 及 R 版本、L'Ecuyer-CMRG/Inversion/Rejection、包、线程、参数、准备 NPZ 对齐。混合保存复用 CSV 哈希，旧参考未存同时点逐 CSV 哈希。原生PCG64不参与 R 配对。

CPU64的 105 份轮数一致。pooled 均值/协方差/标准化RMSE最大差分别：Covertype 1.00e−11/1.00e−8/9.99e−15；Household 4.82e−12/9.46e−10/1.80e−11；Year 1.02e−12/1.05e−9/保存精度内 0。

| 数据/后端 | 最大轮数差 | 最大标准化RMSE差 | 最大协方差相对差 |
|---|---:|---:|---:|
| Covertype CPU32 |8|1.82e−4|2.64%|
| Covertype MPS32 |1|5.43e−6|.208%|
| Household CPU32 |1|4.94e−5|.0592%|
| Household MPS32 |1|2.83e−5|.0502%|
| Year CPU32 |1|4.94e−5|38.4%|
| Year MPS32 |0|9.45e−8|.456%|

相对差除以绝对值>1e−12的参考元素，小分母会放大百分比。Year 38.4%来自 seed 20260923 的第 50/85 协方差，−.01000264 对−.00616254、绝对差.00384010，不是整矩阵。未设等价门槛、未保留完整完成矩阵/随机 draw，摘要不证明逐格或分布等价。

## 正确性与推断

R fixture 覆盖条件矩、初值、先验、停止、尺度/顺序和显式随机输入，theta 深复制。三个 MPS 内核、三个 R MPS 变换/类别/先验边界案例通过固定门槛，R 标准化误差<2.2e−7、离散差 0。

初始原生 CPU64 推断 400 数据/2,000 拟合完成：MCAR/MAR 覆盖 96/97%，偏差−.000688/.002905，coverage MCSE 1.39/1.21 个百分点。指定模型初筛不是 GPU 验收，后续冻结 G5 另列。

历史本机检查 128 项Python、源码外 wheel 调用、五个 R 文件及 R CMD check 零问题。RNG 回归通过保护内部 R 和可见 seed 修复 boot.none 重复 draw，Inversion/Box–Muller 及后续随机调用通过。官方下游仍 R CPU。后续平台/GPU 记录独立；本报告不验证全量来源数据、广泛缺失机制或总内存极限。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[hybrid-summary.json](hybrid-summary.json) · [suite.json](hybrid-reports/suite.json) · [hybrid-measured-source.zip](hybrid-measured-source.zip) · [hybrid-reference-comparison.json](hybrid-reference-comparison.json) · [combined-timings.png](combined-timings.png) · [combined-timings.pdf](combined-timings.pdf) · [combined-timings-metadata.json](combined-timings-metadata.json) · [benchmark-summary-audit-v2.json](benchmark-summary-audit-v2.json) · [benchmark-summary.json](benchmark-summary.json) · [suite.json](benchmark-reports/suite.json) · [measured-source.zip](measured-source.zip) · [native-timings.png](native-timings.png) · [native-timings.pdf](native-timings.pdf) · [mps-kernel-validation.json](mps-kernel-validation.json) · [mps-r-interface-validation.json](mps-r-interface-validation.json) · [local-checks.json](local-checks.json) · [python-reference-bridge.json](python-reference-bridge.json) · [python-hybrid-rng.json](python-hybrid-rng.json)
