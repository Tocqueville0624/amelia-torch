# Linux T4 原生基准

[English](README.md) · [文档目录](../../README.zh-CN.md)

2026-09-26，同一 Linux/Tesla T4 主机在 `905cc79ce20e65fe5b673039d4e411db73cd7544` 完成 18 配置、126 调用、630 插补，记录的收敛、观察值和完整 heldout 检查通过。连续低模式块状MCAR结果不认证完整 R 混合、Windows 或统计推断。

## 耗时

每配置两预热后五次 m5 正式调用，秒数中位数；IQR/全部重复保留，不是置信区间，未删除失败选择成功子集。

| 数据 | R 串行 | R snow2 | 原生 CPU64 | 原生 CPU32 | CUDA64 | CUDA32 |
|---|---:|---:|---:|---:|---:|---:|
| Covertype |23.016|20.827|9.870|9.296|6.172|5.650|
| Household Power |16.239|14.649|5.592|6.553|4.616|3.724|
| Year Prediction MSD |206.580|175.359|80.326|65.550|42.049|37.364|

CPU64/CUDA64比值 1.599/1.212/1.910，CPU32/CUDA32为 1.645/1.760/1.754，仅同机/同路线/同精度比较。R 差异还含库/布局/流程及 R L'Ecuyer 与原生PCG64，同 seed 不配对 draw。

![T4原生耗时及IQR](native-timings.png)

## 输入与计时

100k×10/7/90，heldout 300k/200k/2.7M，缺失 30/28.57/30%，8/7/8 模式，无全空行。完整来源行筛选后 seed 20260923 抽样、20260924 块状遮盖；Household排除 25,979 天然全空行，实际遮盖 2/7。不是全量、独立MCAR或 MAR。

ordinary、tolerance 1e−4、最多 300、autopri=0.05、无初始经验先验；正式 seed 20260923–27、预热 20360923–24，固定随机顺序串行。原生计入预处理/bootstrap/EM/抽样/传输同步/CPU 数组；R 计入完整结果及 snow 建群销毁。读文件、冷导入/启动、评分/写报告不计；原生不含 R 桥接。

## 环境与内存

Linux x86_64 kernel 6.6.122+、Xeon 2 GHz、可见/affinity 双 CPU、RAM 13,286,944 KiB、T4 驱动 580.82.07、CUDA 12.8、Python 3.12.13、Torch 2.10.0+cu128、NumPy 2.0.2、R 4.5.3/Amelia 1.8.3、TF32关。Torch 显存 15,637,086,208 bytes，nvidia-smi 15,360 MiB。原生/串行 2 线程、snow2worker 各单BLAS；早期 setup 4 线程建议在计时前调整，非事后改写。

Torch 活跃张量峰分配 bytes(64/32)：Covertype 43,655,680/26,947,584；Household 33,933,312/21,924,864；Year 319,183,360/165,269,504。不是总VRAM、缓存/context 或 host RAM，未测总量为 null。未记录 OOM 不代表容量测试，CPU 预处理/分组仍存在。

## 审计与来源

覆盖 36 预热+90 正式、180+450 插补（R 210、原生 420）。原生伪逆/final empri 均 0，原版不暴露该计数。R 42 次调用警告列表空，原生保留日志但无独立逐调用 warning 字段。归一化RMSE均值约 1.058/.999/1.085，不证明覆盖率或无偏。

套件 UTC 21:59:19–23:32:16、exit 0，含调度/准备/评分，不是单调用时间。fa08a52 早期正确性及 ensurepip/Ruff 修复另保留。12 个原生报告记录 clean 905cc79，九个套件源哈希匹配 Git blob。缺历史计划表/逐进程前后遥测不补造，audit-plan.json 是后期审计预期。

归档 65 payload+清单=66 文件，含 18 报告、六 R 配置、suite、准备记录、JSON/log；1,068,401 bytes，SHA `b14f55dfb5e94e4121239de19bef96392cdd7cd4d12fd6b90c68184e75abb70e`。payload 哈希同原始，仅容器 owner/time 规范化。不含原始/准备数组、RDS、环境或参数 NPZ；参数文件名不证明已做 CPU/CUDA参数对照。保留 CC BY 4.0 归属。离线解包审计逐字节复现摘要，无拟合；resource-and-count-audit 补充而不改原JSON。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[native-timings.png](native-timings.png) · [native-timings.pdf](native-timings.pdf) · [native-timings-plotted-data.csv](native-timings-plotted-data.csv) · [native-timings-metadata.json](native-timings-metadata.json) · [environment-summary.json](environment-summary.json) · [source-transition.json](source-transition.json) · [benchmark-summary.json](benchmark-summary.json) · [audit-plan.json](audit-plan.json) · [cloud-native-records.tar.gz](cloud-native-records.tar.gz) · [archive-index.json](archive-index.json) · [checkpoint-manifest.json](checkpoint-manifest.json) · [SHA256SUMS.json](SHA256SUMS.json) · [resource-and-count-audit.json](resource-and-count-audit.json) · [packaging-verification.json](packaging-verification.json)

```sh
mkdir -p results/local/colab-native-review
# Extract into a new directory; preserve previous results.
tar -xzf docs/validation/2026-09-26-colab-native/cloud-native-records.tar.gz \
  -C results/local/colab-native-review
.venv/bin/python scripts/summarize_benchmarks.py \
  --input-dir results/local/colab-native-review/results/local/cloud/native \
  --output-dir results/local/colab-native-review-audit \
  --methods r_serial r_snow2 cpu64 cpu32 cuda64 cuda32 --rows 100000
```
