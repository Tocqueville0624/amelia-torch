# Mac CPU32/MPS32已保存输出对照

[English](README.md) · [文档目录](../../README.zh-CN.md)

对保留的 Mac 原生文件离线比较，未重拟合、重计时或新增验收阈值。先审计原 15 配置和九个原生 NPZ，再比较三组同精度 CPU32/MPS32。检查范围内观察值与准备输入精确一致，补值并非逐值相同。

范围为**首个正式重复**seed 20260923、n100k/m5 的五份 theta 及恢复顺序后前 1,000 行；不是新随机样本或 UCI 前 1,000 行。其余 99k 行和其他重复完整矩阵未保存。NPZ 存 float64 不改变记录中的 float32 计算。已查输入哈希、套件、精度、PCG64、尺度/顺序和 bootstrap 次数；未保存真实索引/正态数组，NPZ 与重复由文件名/runner 规则关联，非运行期参数哈希。现有哈希不能独立证明历史绑定。

| 数据 | 最大原单位差 | 最大差/真值 SD | 各份 RMS/真值 SD 范围 |
|---|---:|---:|---:|
| Covertype |154.452222|.173004|.000726–.007961|
| Household |.082111|.014022|.000090–.001172|
| Year |2.680015|.003465|.000263–.000302|

SD 取完整准备 truth 列 100k 行、ddof 1，不是前缀 SD 或仅观察值标准化 SD。RMS 为两路线差，不是预测RMSE或典型格误差。原单位/标准化最大值可在不同格，无可评分格的列为 null。

| Covertype份数 | CPU/MPS 轮数 | theta 最大差 | 原单位最大差 | SD 最大差 | SD RMS |
|---|---|---:|---:|---:|---:|
|1|74/63|.002517581|154.452222|.104302|.007162|
|2|96/82|.002280414|130.440632|.173004|.007961|
|3|59/57|.000343919|19.906016|.017190|.001253|
|4|42/42|.000210285|.428221|.013890|.000726|
|5|54/51|.000605583|23.913383|.023477|.001913|

每份比较 3,000 前缀缺失格。原最大 154.452222 在第一份 Roadways；标准化最大.173004 在第二份 Vertical_Distance_To_Hydrology，原差 10.014974/SD 57.888827。轮数相同也会输出不同；缺逐步参数/完整随机数组，不能归因于舍入、RNG 或分解。

原JSON48,736 bytes/哈希 `0d38b4ef871c759727efef2bac71316f1bb08f910222286fce410c73d45cafe6`；标准化JSON250,799 bytes/哈希 `6f0014a18d3e34035fa1adce5db36f2b54b0521766dd77f0614ad5d20740857e`。gzip 保留原字节、mtime 0；旧字段、九个 NPZ 哈希及套件/报告身份未变，仅增加尺度并单列分析工具版本。本目录不含 NPZ/全准备数据。45 项针对检查、含相关审计共 108 项通过，无新拟合。配对契约可查不等于统计等价。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[2026-09-23-development](../2026-09-23-development/) · [compare_native_parameters.py](../../../scripts/compare_native_parameters.py) · [comparison-original.json.gz](comparison-original.json.gz) · [comparison-standardized.json.gz](comparison-standardized.json.gz) · [sha256.json](sha256.json)

```sh
python scripts/compare_native_parameters.py \
  --input-dir results/local/benchmarks/main \
  --prepared-dir data/prepared \
  --gpu mps --r-workers 4 \
  --output results/local/native-parameter-comparison-new/mac.json
```
