# 加速器边界方案与 CPU64 检查

[English](accelerator-edges.md) · [文档目录](../../README.zh-CN.md)

2026-09-26，validate_r_accelerator_edges.R 的 CPU64 演练通过七个普通公共案例、一个病态案例和独立 CPU64 allthetas/alias 检查。本报告本身不是 GPU 执行；后续 MPS 另有报告。

普通数据 R seed 6101、80×3、拟合 seed 77，案例含 startvals 1 ordinary/none m2、显式 double ordinary/none m2、integer 不回写、最少 35/最多 2 轮。每引擎接收深复制输入/theta。

| 精度 | EM 容差 | theta 界限 | SD 缩放输出界限 |
|---|---:|---|---|
| float64 |1e−6|1e−7+1e−7×abs(reference)|1e−6+1e−7×abs(reference)|
| float32 |1e−5|1e−5+1e−4×abs(reference)|1e−5+1e−4×abs(reference)|

门槛在 GPU 执行前固定，无按结果放宽选项。核验观察值、有限补值、类/掩码、device/dtype、caller/归档别名、R 可见 seed 及后续 draw。正常例要求收敛，两轮截止要求警告/未收敛，不要求完整浮点 history 一致。

病态 seed 7、200×5、第五列=前两列之和，400 个遮盖格，拟合 seed 102、autopri=0.05、empri 0、300 轮。按各引擎自己的最终特征值规则、code、输出及诊断检查，不要求近奇异轨迹一致。CPU64原版 code 2/empri 5，混合 code 1/empri 3，均未收敛；未触发分支须明确记录。

内部allthetas oracle 始终 CPU64，不算 GPU 覆盖或新增公共参数。脚本拒绝 MPS64、强制 MPS fallback 0，失败保留已有JSON且非零退出；不产生计时、峰值内存或推断结论。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[r-accelerator-edges-cpu64.json](r-accelerator-edges-cpu64.json)

```sh
Rscript scripts/validate_r_accelerator_edges.R cuda float64 results/local/edges-cuda64.json
Rscript scripts/validate_r_accelerator_edges.R cuda float32 results/local/edges-cuda32.json
Rscript scripts/validate_r_accelerator_edges.R mps float32 results/local/edges-mps32.json
```
