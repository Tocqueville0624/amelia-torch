# 独立MCAR后续验证提案

[English](g5-mcar-followup-proposed.md) · [文档目录](../README.zh-CN.md)

**提案，尚未批准或执行，执行数 0。** 不修改原协议、driver、200 次结果或未通过分类。计算前须另行冻结协议/runner 并明确实验决定；保留当前开发快照也是可行结果。

原MCAR90%区间略超界：原版 R/混合绝对覆盖率上界 99.009876%，原生配对下界−5.028703 个百分点。新独立模拟可提高精度，但不保证通过。MAR 和 20 个压力例不重跑。

设计：1,000 个新MCAR数据集，n300/m5，seed 2026092601，SeedSequence([2026092601,0, i]).spawn(3)，i0–999。保留相关.3、y=1+x1+.5*x2+N(0,1)、y 观测、协变量缺失.2、ordinary bootstrap、tolerance 1e−4、autopri=0.05、empri NULL、emburn 0/500。原生 uint32/PCG64，R 取模(2^31−1)及 L'Ecuyer-CMRG/Inversion/Rejection，共用带哈希输入。不以旧 200 次为前缀，不未经校正合并为 1,200 次区间。

原边际 90%标准及公式不变：bias±.02、coverage 0.90–.99、配对系数±.01、配对 coverage±.05、SE/width 几何比.95–1.05；相同 OLS/Rubin 且无 Barnard–Rubin、配对 t/log 区间和精确 discordance union bound。固定 N 不因临界结果增长。

候选预算：Mac 五路线(reference、hybrid CPU64/MPS32、native CPU64/MPS32)，5,000 调用/25,000 拟合、7200 秒；CUDA七路线(reference、hybrid CPU64/CUDA64/CUDA32、native CPU64/CUDA64/CUDA32)，7,000 调用/35,000 拟合、7200 秒；两者合计 12,000 调用/60,000 拟合、14,400 秒。为上限非时长保证。运行前固定路线，Torch/BLAS单线程、MPS 不 fallback、TF32关闭、持续 R batch/checkpoint，不自动付费或扩预算。

两主机运行是同批新设计的跨设备复核，不是 2,000 个独立生成样本。各路线对同机 R 比较，两阶段分开报告。保留全部计划输出/失败、原版绝对门槛和配对门槛，不因有利结果提前停止，不完整记证据不足。此提案由第一阶段结果促成，不宣称单阶段或 familywise 90%错误率保证，也不外推真实数据/MNAR/全部平台。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](2026-09-27-evidence-summary.zh-CN.md)。
