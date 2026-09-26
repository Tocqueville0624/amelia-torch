# Mac native CPU32 / MPS32：已保存参数与样本的离线对照

这是对[原 Mac 基准](../2026-09-23-development/)留下的文件所做的补充检查，没有重新拟合、重新计时或增加统计验收门槛。三组 CPU32 / MPS32 配对都满足本工具可检查的记录契约，但保存的插补值并非逐值相同。Covertype 的缺失格最大原单位差为 **154.452222**；它仍完整保留在报告中。按各列完整 truth 的标准差衡量，该数据集的最大差为 **0.173004 SD**，发生在另一列和另一份插补，不能把这两个最大值当成同一位置。

## 范围与证据

离线入口是 [`scripts/compare_native_parameters.py`](../../../scripts/compare_native_parameters.py)。本次重新审计了原套件全部 15 个任务，并核对目录中完整的 9 个 native 参数 NPZ，再比较 CPU32 与 MPS32 的三组同精度文件。原套件还包含 R serial、R snow4、native CPU64；这些参与套件完整性审计，但不混入这三组同精度差异。

每组原始拟合使用 n=100,000、m=5。本次只读取**首个正式重复（seed=20260923）的五份 theta，以及各份恢复到原输入行列顺序的前 1,000 行**。这个前缀不是新抽取的随机检查样本，也不是 UCI 原始文件的前 1,000 行。没有保存其余 99,000 行及另外四次正式重复的完整插补矩阵，因此这些结果不覆盖它们。

工具检查了原输入 SHA256、完整套件质量审计、首个正式重复、配置与诊断中的计算精度、NumPy/PCG64 记录、标准化及列重排、每份 bootstrap 尝试次数，并将两条路线的已保存观察值分别与 prepared 原输入比较。所有被检查的观察值均精确保留。NPZ 中的数组存成 float64，并不意味着原计算使用 float64；本次计算精度来自运行配置和逐份诊断，为 float32。

NPZ 本身没有嵌入 seed、输入哈希，原测量 JSON 也未记录参数文件的运行时哈希。参数与重复的关联依据是报告中的文件名和 runner 的“保存首个正式重复”约定。本次未提供独立归档哈希清单；报告保留的是现存各原 NPZ 的 SHA256，可用于之后核验持有的原文件。它不能独立证明参数文件与原运行的密码学绑定。实际 bootstrap 索引及标准正态数组未保存；相同 seed 与已记录 bootstrap 元数据不能升级为“已经逐值证明随机抽样完全相同”。这里也不配对 R RNG 与 NumPy RNG。

## 三组描述性结果

下面每个最大值均在该数据集五份插补的已保存缺失格中求得。原单位跨列不同，不能把不同变量或数据集的原单位差直接作统一尺度比较。

| 数据集 | 最大原单位差 | 对应列 | 最大标准化绝对差 | 各份标准化 RMS 差的范围 |
| --- | ---: | --- | ---: | ---: |
| Covertype | 154.452222 | `Horizontal_Distance_To_Roadways` | 0.173004 SD | 0.000726–0.007961 SD |
| Household power | 0.082111 | `Sub_metering_2` | 0.014022 SD | 0.000090–0.001172 SD |
| YearPredictionMSD | 2.680015 | `timbre_covariance_03` | 0.003465 SD | 0.000263–0.000302 SD |

标准化对每个缺失格计算 `(MPS32 - CPU32) / s_j`，其中 `s_j` 是该列 **prepared 完整 truth 的全部 100,000 行样本标准差（ddof=1）**。它与原 benchmark 的 heldout RMSE 使用同一个尺度定义，既不是前 1,000 行的标准差，也不是 EM 预处理的仅观察值标准差。这里的 RMS 是两路线之间的差异，并非任一路线相对 truth 的预测 RMSE。RMS 也不是中位数或每个格子的“典型误差”。

标准化报告保存了每份的最大绝对差、RMS，以及每列的原单位最大差、完整 truth SD 和 `最大原单位差 / SD`。没有缺失格的列记为 null，不用 0 假装有评分结果。没有应用新的 allclose、统计等价或接受/拒绝阈值。

## Covertype：保留全部五份的对照

每份比较前缀中的 3,000 个人工缺失格；theta 的差异在其原有标准化、重排列坐标中计算。表中 CPU/MPS 迭代数来自同一个首测 seed 的逐份诊断，差异数值来自保存的 NPZ。

| 插补份数 | CPU32 迭代 | MPS32 迭代 | theta 最大绝对差 | 缺失格最大原单位差 | 缺失格最大差 / SD | 缺失格 RMS 差 / SD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 74 | 63 | 0.002517581 | 154.452222 | 0.104302 | 0.007162 |
| 2 | 96 | 82 | 0.002280414 | 130.440632 | 0.173004 | 0.007961 |
| 3 | 59 | 57 | 0.000343919 | 19.906016 | 0.017190 | 0.001253 |
| 4 | 42 | 42 | 0.000210285 | 0.428221 | 0.013890 | 0.000726 |
| 5 | 54 | 51 | 0.000605583 | 23.913383 | 0.023477 | 0.001913 |

较大的最大值及 RMS 出现在前两份，但其余三份也存在差异。四份的迭代计数不同；第 4 份迭代计数相同，保存的参数和插补仍有差异。因此，迭代次数一致不意味着输出一致，次数不同也不能单独说明差异的根因。

原单位最大差 154.452222 出现在第 1 份的 `Horizontal_Distance_To_Roadways`。标准化最大差 0.173004 SD 出现在第 2 份的 `Vertical_Distance_To_Hydrology`，该处原差为 10.014974、完整 truth SD 为 57.888827。第 1–5 份标准化最大差对应的列依次是 `Horizontal_Distance_To_Hydrology`、`Vertical_Distance_To_Hydrology`、`Vertical_Distance_To_Hydrology`、`Slope`、`Vertical_Distance_To_Hydrology`。

这些是共同出现的已记录事实。没有逐 EM 步参数或完整抽样数组，不能据此把差异归因于浮点运算、随机数消耗或某个矩阵分解步骤。最大值只描述极端位置，不能替代上表保留的五份 RMS，也不能从总 RMSE 接近推断完整输出逐值一致。

## 原记录、哈希与复现

- [`comparison-original.json.gz`](comparison-original.json.gz)：增加 truth-SD 描述之前的原 JSON，48,736 字节，压缩后 9,085 字节。
- [`comparison-standardized.json.gz`](comparison-standardized.json.gz)：附加尺度描述后的原 JSON，250,799 字节，压缩后 34,403 字节。
- [`sha256.json`](sha256.json)：同时记录压缩文件和解压后原 JSON 的 SHA256、字节数与保留检查。

两份均压缩**未经重写的原 JSON 字节**，gzip 的 mtime 固定为 0。已逐项检查：旧报告每份插补的全部原有字段保持完全一致，九个参数文件的哈希相同，原测量报告与套件哈希相同。新报告只增加标准化描述，并记录分析工具版本变化；旧分析脚本指纹仍原样保留，没有用新指纹替换它。

原 JSON SHA256：

```text
original      0d38b4ef871c759727efef2bac71316f1bb08f910222286fce410c73d45cafe6
standardized  6f0014a18d3e34035fa1adce5db36f2b54b0521766dd77f0614ad5d20740857e
```

此目录没有打包九个参数 NPZ 或 prepared 全数据。持有原文件时，可核对报告中的各 NPZ 原始 SHA，并运行下面的只读对照；数据来源、许可及准备方式见[数据说明](../../datasets.zh-CN.md)。输出须使用新路径，已有报告不会覆盖：

```sh
python scripts/compare_native_parameters.py \
  --input-dir results/local/benchmarks/main \
  --prepared-dir data/prepared \
  --gpu mps --r-workers 4 \
  --output results/local/native-parameter-comparison-new/mac.json
```

若持有独立归档中的参数哈希，可另传 `--parameter-hashes`，其格式为全部参数文件 basename 到原始 SHA256 的 JSON 对象。新增输出另有 `.sha256.json` 校验文件。所有离线读文件、核验和差异计算都在原性能计时之外。

本次工具的 45 项针对性离线测试及独立复核通过；连同已有基准审计、R/hybrid 配对测试，共 108 项通过。测试覆盖损坏 NPZ、错误结构、缺失任务/文件、错误哈希、计算精度/seed/尺度/列序/bootstrap 元数据冲突、观察值共同错误及完整 truth 的 ddof=1 尺度。没有重新拟合，也没有把“配对契约可检查”写成统计等价或产品完整验收。
