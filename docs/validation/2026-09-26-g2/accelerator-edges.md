# GPU 公共边界验证脚本与 CPU64 演练

`scripts/validate_r_accelerator_edges.R` 为 G2 新增边界提供有界、独立验证。2026-09-26 仅完成 macOS arm64 **CPU64 演练**：7 个常规公共案例、1 个病态 autopri 案例及单列 CPU64 allthetas/alias 检查通过。**MPS/CUDA 尚未运行此脚本**，CPU 结果不能关闭 G2 的 GPU 项。

## 运行前固定的案例和门槛

普通输入固定为 R seed 6101 的 80×3 数据，拟合 seed 77。7 个案例为 `startvals=1` 的 m=2 ordinary/none、显式 double theta 的 m=2 ordinary/none、integer theta 不回写、emburn 最小 35 轮及最大 2 轮。每个引擎拿到独立序列化深拷贝的输入和 theta，原版 double 矩阵原位覆盖不会污染另一引擎或下一案例。

| 计算精度 | EM tolerance | theta 误差门槛 | 按观察值标准差缩放后的输出门槛 |
|---|---:|---|---|
| float64 | 1e-6 | atol 1e-7 + rtol 1e-7 × abs(reference) | atol 1e-6 + rtol 1e-7 × abs(reference) |
| float32 | 1e-5 | atol 1e-5 + rtol 1e-4 × abs(reference) | atol 1e-5 + rtol 1e-4 × abs(reference) |

这些门槛在 GPU 运行前写死，不提供依据失败结果调宽的 CLI 选项。每份同时检查观察值精确保留、有限补值、原版类、缺失位置、指定 device/dtype、调用者与归档 theta alias、可见 `.Random.seed` 及后续 runif/rnorm。普通案例要求收敛；emburn 最大 2 轮案例明确要求未收敛状态及 warning。迭代历史保存供审计，不把浮点精度下完整轨迹逐值相同设为普通 GPU 门槛。

病态输入固定 R seed 7、200×5、第五列为前两列之和、400 个随机缺失单元格，拟合 seed 102、autopri=.05、empri=0、最多/最少 300 轮。它只核对**各引擎自己的**最终 theta 对应的原版协方差有效性规则、返回 code、补值/NA、convergence warning 和 empri 诊断；保留全部原版/混合状态，不要求近奇异情况下 eigenvalue 符号、autopri 次数或轨迹相同。某个平台未触发 autopri 时如实标记覆盖不足，不伪造更新。该案例不计为统计质量成功样本。

allthetas 是内部 EM 诊断，不是新增公共 amelia 参数。脚本另外比较一次原版与**CPU64**内部 allthetas：初始列在 alias 回写前保留、最终 caller theta 一致。这个检查始终明确标 CPU64，不算 GPU allthetas 覆盖。

## CPU64 实际结果

见 [完整便携 JSON](r-accelerator-edges-cpu64.json)。identity 第二份重新迭代；显式 double、boot.none 的第二份只需 1 轮，integer 初值保持未改。最小 35、最大 2 轮均符合契约。

病态原版 code=2、最终 empri=5；混合 code=1、最终 empri=3，两者都达到 300 轮且未收敛。报告保留这些差异、每轮历史、警告、CPU 工作与伪逆诊断。通过的是状态与诊断契约，不是两条病态轨迹数值等价，也不是该结果适合统计推断。

## 后续 GPU 运行

先安装对应提交的 Python/R 包，并按环境说明绑定 `RETICULATE_PYTHON`。停止其他计时任务后，独立执行：

```sh
Rscript scripts/validate_r_accelerator_edges.R cuda float64 results/local/edges-cuda64.json
Rscript scripts/validate_r_accelerator_edges.R cuda float32 results/local/edges-cuda32.json
Rscript scripts/validate_r_accelerator_edges.R mps float32 results/local/edges-mps32.json
```

CPU 演练将 device/dtype 改为 `cpu float64`。MPS64 在计算前拒绝；MPS 强制 `PYTORCH_ENABLE_MPS_FALLBACK=0`，仍记录显式 CPU 工作。设备不可用和其他异常保存失败 JSON，退出非零；每个完成案例及时落盘，后续失败不抹去先前结果。当前脚本未计时、未测峰值内存，不替代 GPU 推断质量或正式性能基准。
