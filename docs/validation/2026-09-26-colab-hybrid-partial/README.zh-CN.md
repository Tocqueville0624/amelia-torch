# Linux T4：R 混合路线的部分基准记录

[English](README.md) · [文档目录](../../README.zh-CN.md)

**本次原 Colab 运行时已丢失；已备份 11 个配置，最后一个 YearPredictionMSD CUDA32 的结果未知。这里不是完整套件通过记录。** 已保存的 77 次调用、385 份插补通过了有限的逐报告收敛、设备和输出完整性核对。五组已有同精度 CPU/CUDA 配对的中位数速度比为 1.281–1.407 倍，但五个已保存 GPU 配置全部比同机原版 R snow2 慢，不能据此宣称普遍优于 Amelia。

2026-09-27 约 01:47 UTC 观察到 Colab 断线；约 01:51 UTC 的替代会话中，项目目录、实验变量和进程均不存在。旧会话最后可见的输出是 Year CUDA32 starting，无法据此确定最后一项的结果或终止时刻。会话观察记录见 [interruption-observation.json](interruption-observation.json)。

## 耗时

单位为秒；每格是 5 次正式 `m=5` 调用的中位数，每个已有配置另保留 2 次预热。所有原始重复和 IQR 均在归档及 [部分审计摘要](partial-evidence-summary.json)。IQR 描述重复间离散程度，不是置信区间。表中原版 R 两列来自同一原运行时此前完整完成的 [native 主基准](../2026-09-26-colab-native/README.zh-CN.md)，不是在断线后重跑所得。

| 数据 | R 原版串行 | R 原版 snow2 | R hybrid CPU64 | R hybrid CPU32 | R hybrid CUDA64 | R hybrid CUDA32 |
|---|---:|---:|---:|---:|---:|---:|
| Covertype | 23.016 | 20.827 | 32.198 | 31.744 | 24.776 | 23.366 |
| Household power | 16.239 | 14.649 | 21.808 | 19.630 | 16.782 | 15.323 |
| YearPredictionMSD | 206.580 | 175.359 | 250.898 | 231.786 | 178.274 | **未取得，结果未知** |

下表只在 R hybrid 路线内比较同 dtype 的 `CPU 中位数 / CUDA 中位数`；大于 1 表示这组已记录 CUDA 调用更快。它不是置信区间，也不是把实现、系统负载等差异全部归因于 GPU 的因果估计。

| 数据 | 精度 | CPU 中位数（秒） | CUDA 中位数（秒） | 速度比 |
|---|---|---:|---:|---:|
| Covertype | float64 | 32.198 | 24.776 | 1.300× |
| Covertype | float32 | 31.744 | 23.366 | 1.359× |
| Household power | float64 | 21.808 | 16.782 | 1.299× |
| Household power | float32 | 19.630 | 15.323 | 1.281× |
| YearPredictionMSD | float64 | 250.898 | 178.274 | 1.407× |

Year float32 没有可计算的 GPU 比值，不从 native 路线或 float64 借值补齐。R 原版与 hybrid 的时间同时包含不同实现、桥接和数据布局成本，不能把相对原版的全部差值归因于 GPU。五个已取得 CUDA 配置均比 R snow2 慢；与 R 串行相比，Household CUDA32 耗时短 5.64074%，Year CUDA64 耗时短 13.70220%，其余三个 CUDA 配置耗时更长。因此本批记录支持的较窄结论是：**已保存的五组同精度 hybrid CPU/GPU 配对中，CUDA 更快；它没有一致超过原版 Amelia。**

## 计时与数据边界

这条路线保留原版 R 的预处理、bootstrap、随机补值与后处理，通过 reticulate 将 EM 交给 PyTorch。计时包含这些步骤、桥接和数据传输，以及返回完整 R 结果；初始 Python 导入/绑定、进程启动、CSV 读入、事后质量评分和写 JSON 不在单次计时内。原版与 hybrid 在不同时间批次运行，连续会话观察和各报告的环境信息支持同机比较；本包不公开私人主机标识。

Year CPU64 的计时期间打开过只读 Colab 文件预览以备份结果；未并发拟合或编辑运行源码，但**背景负载并未完全隔离**。原始顺序及逐进程前后源码状态需要 suite 才能完整核验；该文件未取回，不根据零散报告重造。

三组数据分别是 100,000×10、100,000×7、100,000×90；均从完整来源行抽样后加入块状 MCAR。人工 heldout 为 300,000、200,000、2,700,000 个单元格，模式数为 8、7、8，实际缺失率为 30%、28.57%、30%。这是 **100k 样本、低模式块状 MCAR**，不是全部数据或逐格独立 MCAR/MAR。原始来源、完整行筛选、归属与 CC BY 4.0 信息保留于 [native 数据说明](../2026-09-26-colab-native/README.zh-CN.md) 及其归档中的 `data/manifest.json`。

每个已有配置均为 `m=5`、ordinary bootstrap、tolerance `1e-4`、`emburn=[0,300]`、`autopri=0.05`、无初始经验先验。正式 R seeds 为 20260923–20260927，预热为 20360923–20360924，RNGkind 为 L'Ecuyer-CMRG / Inversion / Rejection。host/Torch 预算为 2 线程，R hybrid `parallel=no,ncpus=1`；原版 serial BLAS cap 为 2，snow 为 2 worker、每 worker BLAS cap 为 1。native setup 中早期的 4 线程建议不是正式计时配置。

原运行时是 Colab Linux x86_64 / Tesla T4，Python 3.12.13、Torch 2.10.0+cu128、R 4.5.3、Amelia 1.8.3、reticulate 1.47.0。每份报告核对了实际 device/dtype、解释器和线程；CUDA 报告均 TF32=false。CPU 工作仍明确存在，不称整个 R 流程为纯 GPU。完整环境来源见 [原运行时环境记录](../2026-09-26-colab-native/environment-summary.json)；新替代运行时不是本表的测量主机。

## 有限质量、数值和资源核对

11 个报告共记录 **22 次预热 + 55 次正式调用**，即 **110 + 275 份插补**。它们全部记录收敛、观察值保留、应补值有限且无漏计 heldout，warning/error、伪逆使用与正的最终经验先验计数均为 0。这些只描述已保存报告，不能说明未知第 12 项成功、失败或没有异常。报告 `status=ok` 不是整个子进程 exit 0 的替代证据。

按 R seed 和 phase 与原版串行配对，所有 6 个已保存 float64 配置的 210 份迭代次数相同。float32 的 175 份中有 18 份迭代次数不同，均仍记录收敛：Covertype CPU32/CUDA32 分别 3/1 份不同，Household CPU32/CUDA32 各 7 份，Year CPU32 为 0。逐份差异保留；不能把 float32 收敛说成轨迹完全一致。

已保存 float64 的配对 normalized heldout RMSE 最大绝对差约 `7.0e-14`，float32 约 `3.81e-5`。这仅是**JSON 摘要的描述性对照**；没有保存全部随机数、R RNG 状态或完整插补矩阵，因此不证明逐格/逐比特相同，更不证明统计等价、无偏或 Rubin 覆盖率合格。独立 G5 推断质量、GPU 边界例、Windows/RTX 3080 和完整发布门槛均不由本包代替。

以下 CUDA allocated 值取各已有配置全部 7 次调用的最大值：

| 数据 | CUDA64 最大 allocated bytes | CUDA32 最大 allocated bytes |
|---|---:|---:|
| Covertype | 41,645,056 | 25,941,504 |
| Household power | 31,939,584 | 20,637,696 |
| YearPredictionMSD | 300,372,992 | 未取得 |

这是 `torch.cuda.max_memory_allocated` 的活跃张量峰分配，不是总进程 VRAM、缓存保留量或宿主 RAM。未测 RAM/总显存与 CPU 路线的 CUDA 字段保持 `null`，不填 0。已保存报告未记录 OOM；最后一项结果未知，不能声明整套没有 OOM。

## 来源、归档与离线复核

测量固定源码为 [`905cc79ce20e65fe5b673039d4e411db73cd7544`](https://github.com/Tocqueville0624/amelia-torch/tree/905cc79ce20e65fe5b673039d4e411db73cd7544)。11 个报告中的 16 个源文件指纹一致，逐个匹配该 Git blob；安装 R bridge 指纹一致，NPZ/archive 指纹匹配已保存的 native 准备元数据，同一数据集的 CSV provenance 一致。未取回实际 CSV，原 native suite 也未保存同时点 CSV 哈希；不由这些摘要证明历史文件内容的每个环节。更不能把源文件哈希匹配说成已取得丢失的逐进程 before/after 证据。

[hybrid-eleven-raw-reports.tar.gz](hybrid-eleven-raw-reports.tar.gz) 保存 **11 个原始 JSON**，未压缩报告共 3,789,799 bytes，归档 1,504,792 bytes，SHA-256：

```text
2f5f823929b476436452d52393c3025d13d5fb55e191388de2200ae146ebcbdc
```

报告 payload 字节未经改写，只规范化 tar/gzip 容器元数据。前十份来自只读文件预览的十配置 bundle，第十一份 Year CPU64 单独备份；[collection-manifest.json](collection-manifest.json) 是**后来在本地制作的收集清单，不是云端 checkpoint**。其中明确原十配置 bundle 不包含第十一份。历史 [十份审计](historical-ten-report-review.json)、[第十一份审计](historical-year-cpu64-review.json) 与 [原十份采集清单](original-ten-ui-copy-manifest.json) 保留原字节；其“pending / local provisional”文字反映当时状态，以本说明及中断记录为最新状态。

缺失的完整 suite、每进程退出码、源码前后检查、配置/日志和第十二份报告均不补造。现有完整套件审计/绘图器要求完整 suite，本包没有绕过其门槛，也没有制造成功总图。独立 [verify_reports.py](verify_reports.py) 只核验这 11 份报告、逐份 backend/质量、采集哈希、输入元数据、原版配对摘要及五个同精度比值，输出种类明确为 `limited_recovered_report_audit_not_suite_audit`。

在仓库根目录离线复核，不运行插补：

```sh
.venv/bin/python docs/validation/2026-09-26-colab-hybrid-partial/verify_reports.py \
  --output results/local/hybrid-partial-recheck.json
```

输出路径必须不存在；脚本读取本包和已有 native 公开压缩档，使用仓库的逐报告检查函数。它不调用要求完整 suite 的汇总入口。成功提示仍明确写 **complete suite NOT verified**。也可先把本包解压到新目录，再传 `--reports-dir 解压目录/reports` 核对归档往返。该流程已实际执行，解压后的摘要与 [partial-evidence-summary.json](partial-evidence-summary.json) 逐字节一致；见 [packaging-verification.json](packaging-verification.json)。

有限私人路径、主机标识和常见凭据模式检查见 [privacy-review.json](privacy-review.json)；它不声称覆盖任意可能的秘密模式。完整文件校验见 [SHA256SUMS.json](SHA256SUMS.json)。本记录整理未新增拟合；若今后恢复/重跑缺失项，需要另存运行时、版本、全部重复和来源，新会话不能合并为本次完整套件。
