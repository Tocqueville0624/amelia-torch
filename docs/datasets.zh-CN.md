# 三组公开数据及可复现准备

核验日期：2026-09-23（America/Los_Angeles）。这三组原始压缩包已实际下载，完成 SHA-256 固定、全部 ZIP 成员 CRC 检验及数据流逐行读取；字段数、数值列、行数、天然缺失数均已核对。这里只报告数据准备完成，**不表示已完成三组大规模插补或证明 GPU 加速**。

## 选择及规模

| 数据集 | 原始行数 | 本阶段数值列 | 实测压缩包字节 | 实测文本字节 | 单份完整 float64 矩阵 |
|---|---:|---:|---:|---:|---:|
| Covertype | 581,012 | 10 | 11,251,206 | 75,169,317 | 44.3 MiB |
| Household Power | 2,075,259 | 7 | 20,640,916 | 132,960,755 | 110.8 MiB |
| Year Prediction MSD | 515,345 | 90 | 211,011,981 | 448,576,698 | 353.9 MiB |

压缩包合计 **242,904,103 字节，约 231.7 MiB**。下载前本机可用磁盘约 21.9 GiB，足以保存这三组；脚本默认保留 5 GiB 空闲。上表矩阵内存不含 bootstrap、多个插补副本、掩码、分组、R/Python 转换及临时计算空间，不应拿它作为算法峰值内存。以 Year Prediction 为例，单独保存 5 份 float64 输出就约需 1.73 GiB。

来源、原始地址、精确字节、压缩与解压数据 SHA-256、逐行核验结果、列选择和引用都在 [`data/manifest.json`](../data/manifest.json)。哈希为本项目下载后计算的固定版本指纹，并非 UCI 提供的数字签名。

### Covertype：较大行数、较窄矩阵

[UCI 官方页](https://archive.ics.uci.edu/dataset/31/covertype)描述 581,012 条林地记录、54 个特征及标签，数据无缺失。本阶段按源文件顺序保留前 10 个测量变量，排除 4 个 wilderness 哑变量、40 个 soil 哑变量及类别标签。方位角是圆周变量，部分变量是整数记录的测量值；这里用于数值吞吐与模型失配压力测试，不据此声称连续高斯假设适用于所有变量，也不把丢弃类别变量称为完成 Amelia 类别兼容。

引用：Blackard, J. (1998). *Covertype*. UCI Machine Learning Repository. DOI: [10.24432/C50K5N](https://doi.org/10.24432/C50K5N)。

### Household Power：百万行与天然缺失边界

[UCI 官方页](https://archive.ics.uci.edu/dataset/235/individual+household+electric+power+consumption)记录一个家庭近四年的分钟级电力数据。保留 7 个数值测量，Date/Time 不进入当前连续基线，原始行索引用于追踪时间位置。

本次全量读取核验发现：**25,979 行的这 7 列全部为空，共 181,853 个缺失单元**；完整数值行共 2,049,280。解析器同时识别 `?` 和空字符串，不能只依赖网页变量表的逐列缺失标记。

天然缺失值没有真值，不能计算补值误差；整行全空也无法展示基于已观测条件变量的插补能力。因此受控基准明确选择完整行后再施加人工缺失，同时在报告中保留剔除行数及完整行选择偏差。`--natural-missing preserve` 是独立的兼容性压力路径，用于核对 Amelia 全空行行为，不能把它与完整行人工掩码的质量分数混在一起。

时间依赖、计量间关系、零值和偏态仍存在。连续变量吞吐测试不会自动解决时间结构；在时间 API 兼容完成前不得把它当作时间序列插补效果验证。

引用：Hebrail, G. & Berard, A. (2006). *Individual Household Electric Power Consumption*. UCI Machine Learning Repository. DOI: [10.24432/C58K54](https://doi.org/10.24432/C58K54)。

### Year Prediction MSD：较宽矩阵

[UCI 官方页](https://archive.ics.uci.edu/dataset/203/yearpredictionmsd)描述 515,345 首歌的 90 个音色特征：12 个均值与 78 个协方差描述。源文件共 91 列；本阶段排除第 1 列发行年份，只插补 90 个数值特征。原数据没有天然缺失。

官方预测任务规定前 463,715 行训练、后 51,630 行测试，以减少艺人相关泄漏。当前任务是受控缺失的插补与性能评估，不将随机行采样结果报告为歌曲年份预测分数；未来加入预测评估必须遵循该划分。

90 维独立逐格缺失常产生接近行数的不同缺失模式，对按模式计算的算法很不利。因此既要测重复模式，也要报告独立模式下的慢、超时或内存失败，不能只挑有利的模式。

引用：Bertin-Mahieux, T. (2011). *Year Prediction MSD*. UCI Machine Learning Repository. DOI: [10.24432/C50K61](https://doi.org/10.24432/C50K61)。

三组覆盖窄/宽矩阵、百万行与不同原始分布，但不是社会科学代表性样本。算法是否保持 Amelia 语义仍靠原版逐步骤对照与已知生成机制模拟；领域数据的掩码实验只提供实际数据压力测试。更大规模的 [UCI HIGGS](https://archive.ics.uci.edu/dataset/280/higgs)可作后续选项，本阶段没有下载，也不需要它来凑第三组。

## 许可与公开数据方案

三组 UCI 官方页都明确标注 **CC BY 4.0**，允许再分发与改编。数据许可独立于软件许可；发布原包或派生样本时保留作者、标题、DOI、[CC BY 4.0 链接](https://creativecommons.org/licenses/by/4.0/)，并说明列选择、行抽样和人工缺失等修改，不暗示原作者背书。

当前仓库包含清单、下载及准备脚本和小样本；完整原包放 `data/raw/`，准备文件放 `data/prepared/`，两者均被忽略，避免意外进入 Git 历史。公开完整数据的具体托管策略待最终确认。[GitHub 官方限制](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)阻止普通 Git 中超过 100 MiB 的文件，Year Prediction 压缩包已超出。可选择固定哈希的官方下载方案，或附署名说明的 GitHub Release 数据附件；[Release 单附件上限为 2 GiB](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)，三份原包均在此范围内。此处是可行方案，尚未创建 Release 或上传数据。

## 下载与校验

以下从项目根运行；Windows 将 `.venv/bin/python` 换成 `.venv\Scripts\python.exe`。

```sh
.venv/bin/python scripts/download_datasets.py --datasets all --dry-run
.venv/bin/python scripts/download_datasets.py --datasets all --max-download-mib 300
.venv/bin/python scripts/download_datasets.py --datasets all --verify-only
```

可以只指定 `--datasets covertype`，或者多个 ID。默认要求 manifest 中固定的 SHA-256 匹配，不能以网络成功响应代替内容校验。归档下载流式写入 `.part`，总量受到预算限制，磁盘每块检查；完整校验成功才原子改名，不覆盖已完成归档。只读取 ZIP 成员，不将归档提供的路径解压到文件系统。

若传输中断，脚本尝试 HTTP Range 并验证服务器真的返回匹配的 206 响应。**本次 UCI 端点忽略 Range、返回 200，且 HEAD 不提供长度**，因此不能承诺在当前源上断点续传。脚本会保留部分文件并明确停止；`--restart` 才会重新开始该部分下载。已有完整文件始终只校验，不会被 `--restart` 覆盖。

`--accept-unpinned` 只供首次来源审计使用；本项目三个哈希已固定，正常复现无需该选项。上游内容变化必须重新调查并更新清单，不能静默接受新的归档。

## 共用输入、天然缺失与人工缺失

```sh
.venv/bin/python scripts/prepare_benchmark_data.py --dataset covertype --rows 10000 --output data/prepared/covertype-n10000-block_mcar.npz
.venv/bin/python scripts/prepare_benchmark_data.py --dataset household_power --rows 10000 --output data/prepared/household_power-n10000-block_mcar.npz
.venv/bin/python scripts/prepare_benchmark_data.py --dataset year_prediction_msd --rows 10000 --output data/prepared/year_prediction_msd-n10000-block_mcar.npz
```

这些命令已经实际执行，每组输出均为 10,000 行，具体缺失模式数依次为 **8、7、8**。Household 只有 7 个变量、每模式遮住 1 列，因此请求 8 个模式时存在重复。缺失率按整数列数取整，实际率在 JSON 中记录，不将它伪装成精确 10%。这组规模是后续算法 smoke/初测输入，不是最终大规模成绩。

另已准备以下评估输入，均使用 `--missing-rate 0.3 --seed 20260923`，基准运行时计划 `m=5`。`m` 不参与输入准备，由插补器参数决定。路径模板为 `data/prepared/{dataset}-n{rows}-{mechanism}-rate30-seed20260923.npz`；同名 JSON 保存完整元数据。

| dataset | rows | mechanism | 实际缺失率 | 模式数 K | 全空行 |
|---|---:|---|---:|---:|---:|
| covertype | 100,000 | block_mcar | 30.000% | 8 | 0 |
| household_power | 100,000 | block_mcar | 28.571% | 7 | 0 |
| year_prediction_msd | 100,000 | block_mcar | 30.000% | 8 | 0 |
| covertype | 5,000 | mcar | 29.752% | 779 | 0 |
| household_power | 5,000 | mcar | 29.706% | 125 | 2 |
| year_prediction_msd | 5,000 | mcar | 30.017% | 5,000 | 0 |

已逐份核验 `truth` 全有限、`data` 的 NaN 恰等于人工掩码、掩码之外的值逐项保持、无全空列。三份大组均无全空行。Household 小组的 2 个全空行是独立 MCAR 的实际结果，故保持原样；若实现拒绝此边界，应如实报告失败，不能删除后仍称原来的独立 MCAR 实验。Year Prediction 小组每行都是不同模式，是刻意保留的困难场景。

脚本流式扫描完整源，验证行数/字段数后，从合格行里均匀不放回抽样，并按源行顺序输出；可选 `--sampling prefix`，但须明确前缀采样并非均匀代表。完整源仅保留压缩包，不落地额外文本副本。默认 `--max-working-mib 2048` 是准备过程的保守数组预算，独立于算法内存预算；扩大规模之前仍需预估实际峰值。

`.npz` 文件中：

- `data`：所有实现共用的 NaN 输入；这是应传入插补器的数组。
- `truth`：人工遮盖前的原始观测；天然缺失仍为 NaN，只供评估使用，禁止传给插补算法或用来调参。
- `artificial_missing_mask` 与 `natural_missing_mask`：分开保存；误差只在人工遮盖且原来已观测的单元计算。
- `source_row_ids`：原始数据 0 起始行索引；`column_names`：所选列顺序。

同名 JSON 保存数据引用、源/输出哈希、形状、列、两类掩码种子、抽样及天然缺失处理、实际缺失率、全空行和不同模式数 `K`。所有方法必须使用同一份 `data` 和掩码；Amelia R 基线由同一数组导入，不能各自重新生成随机掩码。

三种人工缺失模式：

1. `--mechanism block_mcar`（默认）：预先定义有限个列块模式，行的模式与数值独立，属于块状 MCAR；不是逐单元独立 MCAR。记录完整模式表。
2. `--mechanism mcar`：各已观测单元独立随机遮盖；可能出现全空行和大量模式。保持真实生成结果并报告，不能事后为提速悄悄修补掩码。
3. `--mechanism mar`：始终保留第 1 个所选变量，其他列缺失概率仅依赖该已观测锚变量的 logistic 函数；校准总体期望缺失率并记录参数。锚变量有天然缺失时明确报错。

固定种子在当前 NumPy 环境下确定抽行和掩码；跨版本长期复现依赖保存的具体数组、行 ID、哈希和版本信息，而不是只记一个 seed。真实数据掩码下 RMSE/MAE 不能验证 Rubin pooling 的覆盖率，也不能替代模拟中的偏差/区间覆盖率检查。最终性能口径遵循 [`benchmark-plan.zh-CN.md`](benchmark-plan.zh-CN.md)。

## 验证记录与下一步

- 已完成：三包下载、固定哈希、ZIP CRC、gzip 内层读至结束、全部原始行列及数值读取；零无限值。
- 已完成：三份 10,000 行初测输入、三份 100,000 行块状缺失评估输入、三份 5,000 行独立缺失压力输入；三份每组 256 行的带引用小样本用于接口演示。
- 已完成：12 项离线测试覆盖损坏/未固定哈希拒绝、已有包离线校验、Range 被忽略时保留部分文件、行来源追踪、天然/人工缺失隔离、MAR 锚、块状模式及三个小样本的来源与真值隔离。
- 已完成：三组各 100,000 行块状 MCAR 的原版 R 串行/并行、native Torch CPU/MPS 端到端基准及独立质量审计，见[开发验证记录](validation/2026-09-23-development/README.md)。
- 待执行：逐格独立缺失压力、规模递增、真实设备 RAM/VRAM 记录、CUDA 实测。当前结果不构成其他任务的速度承诺。
