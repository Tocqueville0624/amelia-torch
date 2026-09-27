# Mac G5 推断结果

[English](README.md) · [文档目录](../../README.zh-CN.md)

**执行完整，统计标准未全通过。** 2026-09-26 五路线各 200MCAR+200 MAR+20 压力数据集，n300/m5，共 2,100 调用/10,500 拟合。全部收敛、观察值保留、应补值有限，无失败/OOM/拟合警告。混合/原生无伪逆或正 final empri，原版不可得内部计数保持 null。R/混合最多 28 轮，原生 24 轮。

MAR 标准及有界压力有效性全部通过。MCAR原版 R 及两混合的绝对 coverage 失败，原生 CPU64/MPS32配对 coverage 失败。CPU/MPS 分类一致，不是 GPU 独有缺陷证据。路线执行状态 0，driver 因统计标准返回 1；独立审计 exit 0 仅表示记录/重算一致，不是验收通过。

| 路线族 | MCAR偏差/覆盖率 | MAR 偏差/覆盖率 |
|---|---|---|
| 原版 R / hybrid CPU64 / hybrid MPS32 |−.001053 /195/200 (97.5%)|.001829 /191/200 (95.5%)|
| native CPU64 / native MPS32 |−.000688 /192/200 (96%)|.002905 /194/200 (97%)|

显示精度隐藏少量设备差异，全部 SE、宽度、MCSE 及逐路线值见 summary.json。使用有限 m 的 Rubin t，无 Barnard–Rubin。

## 未通过项

原版 R/混合MCAR精确 90%coverage 区间为 **[94.815666%,99.009876%]**，比 99%上限高.009876 个百分点，不是点估计低覆盖或算法错误证明。

原生相对 R 配对 coverage 差−1.5 个百分点：一对仅原生覆盖、四对仅 R 覆盖，MCSE 1.115784 个百分点。保守 90%discordance 区间 **[−5.028703,+2.206633]个百分点**，低于−5 下限.028703 个百分点，门槛未改。其他偏差、配对系数、SE/宽度及混合配对 coverage 通过。原生/R 随机实现不同；拟合成功不能关闭 G5。

## 配对输出与记录

输入/seed 映射已重建。hybrid CPU64 相对 R 的 pooled 系数最大差为 400 主数据 2.3315e−15、20 压力 2.7978e−14，全部逐份轮数一致。MPS32为 4.5024e−7/4.3418e−5，两份轮数变化：mcar-189 首份 6→7、stress_mcar-000 第三份 15→16。混合 coverage 分类同 R，但零 discordance 仍给区间[−1.827534,+1.827534]个百分点，不写成零不确定性。

保留逐份回归 q/U、pooling、EM 及拟合时质量检查，未存全部完成矩阵。离线审计重算记录统计量，不声称事后从完整矩阵再查观察值。

Mac 26.6.2 arm64/Python 3.12.13/NumPy 2.5.3/Torch 2.14.0/R 4.5.3/Amelia 1.8.3，单线程、MPS fallback 0 且特征值显式 CPU。UTC 22:17:49–22:36:26 约 18.6 分钟含 checkpoint，不作速度比较；G7 计时结束后执行，source guard 通过。原JSON16,027,250 bytes，SHA `3ad4e3de9892e0a1e69512fc0330778ded622e45a70e9604cdf1390328ccb57c`。源码 ZIP 含 16 个匹配文件及归属。冻结协议仍为 `7ea7882bccc8d92102a67786bc9c09c2055ce29d97350abfbcf4f74f2187e454`，九项审计测试通过，未执行补充模拟。

输入哈希重建需匹配NumPy/BLAS，跨平台浮点差不能自动判为篡改。另行安排复现须新输出目录。

![MCAR覆盖率及冻结界限](mcar-coverage.png)

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[summary.json](summary.json) · [mcar-coverage.png](mcar-coverage.png) · [mcar-coverage.pdf](mcar-coverage.pdf) · [inference-suite.json.gz](inference-suite.json.gz) · [measured-source.zip](measured-source.zip) · [sha256.json](sha256.json)

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 PYTORCH_ENABLE_MPS_FALLBACK=0 \
  .venv/bin/python scripts/validate_inference_suite.py --mode formal \
  --routes r-reference hybrid-cpu64 hybrid-mps32 native-cpu64 native-mps32 \
  --time-budget-seconds 7200 --output results/local/g5-mps-formal-new

.venv/bin/python scripts/summarize_inference_suite.py \
  results/local/g5-mps-formal-new/inference-suite.json \
  --output results/local/g5-mps-audit-new
```
