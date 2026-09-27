# Amelia 1.8.3 参考样例

[English](README.md) · [文档目录](../../../docs/README.zh-CN.md)

样例由小型合成输入经未修改的官方 R 包生成。仓库根目录重建命令：

```sh
Rscript scripts/export_reference_fixtures.R
```

导出器要求精确 Amelia 1.8.3，每文件记录官方归档 URL/SHA。因 C++ EM 原位修改 theta，输入均深复制。样例无私人数据/路径、机器序列号或下载的第三方观测。

| 文件 | 用途 |
|---|---|
| no_prior.json | 相同准备输入和显式 theta；单步、收敛、条件矩和随机补值 |
| empirical_prior.json | empri 3.75 由上游截断为 3 |
| cell_prior.json | 低层 1 起始坐标、标准化均值与方差 |
| no_complete_rows.json | 无完整行时零均值/单位协方差初值 |
| minimum_iterations.json | emburn(35,80)，收敛后仍至少 35 轮 |
| maximum_iterations.json | emburn(0,2)，两轮停止并明确未收敛 |
| complete_internal.json | 内部完整样本返回样本协方差、忽略经验先验 |
| preprocessing.json | 观察值样本标准化、排序、初值 |
| public_continuous.json | 实际原版公共预处理到 EM，无 bootstrap、显式 theta、非平凡列序、全空行；不配对跨库随机数 |
| edge_contract.json | 全空行仍缺失、输入错误码、log 逆变换版本行为 |
| adaptive_stress.json | 近精确奇异诊断，不作为跨平台精确数值/history 验收 |

JSON null 表示数值缺失，矩阵按行嵌套。先验和排序索引用 R 的 1 起始规则。initial_theta 为准备坐标，左上−1，第一行/列均值，其余协方差。

standard_normals 保存参考补值实际消耗的正态输入，通过重置 R 流重放。导出器独立核验其与解析条件矩可在最大绝对误差 1e−11 内复现 Amelia::: amelia_impute。跨 runtime 使用数组，不把 seed 当跨库契约。

内部完整样本特例不证明公共 Amelia 接受无缺失输入，默认公共 code 39 拒绝；不完整原始数据的 bootstrap 仍可能完整。

这些样例覆盖连续低层核心，不证明类别、时间、公共 prior 格式、边界、R 对象或完整 EMB API 等价。详见[算法契约](../../../docs/algorithm-contract.zh-CN.md)和[兼容表](../../../docs/amelia-compatibility.zh-CN.md)。
