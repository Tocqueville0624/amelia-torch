# Mac 性能图

[English](README.md) · [文档目录](../../README.zh-CN.md)

图形使用已审计的 2026-09-23 M4 数据，未重新拟合/计时：三组 100k 数值子集、m5、两次预热/五次正式重复。柱为中位数，误差线 IQR，不是置信区间。

![Mac完整调用耗时](mac-final.png)

左侧原生Python及原版 R，右侧含桥接的完整 R 混合调用并重复 R 基线；同数据集共用时间轴。六个同精度 CPU32/MPS32比值均小于 1，即 MPS 较慢，不证明CUDA结果。Python/R 差异包含实现与 RNG 库。

绘图器检查已审计输入完整性，不认证主机身份或统计有效性。--same-host 依据报告来源，不是参数本身创造同机证据。PNG/PDF 已生成并目视检查，八项有界输入/标签检查通过；SVG 不可用、不列为产物。数据表、元数据及哈希保留，复现须新前缀。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[mac-final.png](mac-final.png) · [mac-final.pdf](mac-final.pdf)

```sh
Rscript scripts/plot_audited_performance.R \
  --native docs/validation/2026-09-23-development/benchmark-summary-audit-v2.json \
  --hybrid docs/validation/2026-09-23-development/hybrid-summary.json \
  --native-host 'Mac M4' --hybrid-host 'Mac M4' --same-host \
  --output-prefix results/local/figures/mac-audited
```
