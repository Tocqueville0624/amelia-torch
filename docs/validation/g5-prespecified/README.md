# G5：正式模拟前固定的统计质量方案

方案固定于 **2026-09-26**；[protocol.json](protocol.json) 是机器读取的门槛。正式结果尚未产生。先提交方案和脚本，再用该提交运行正式模拟；结果不利或不精确时保留“未通过/证据不足”，不得换种子、扩大界限或丢掉失败后重新宣称通过。这些是此合成模型的操作性标准，并非所有研究问题的科学可接受界限。

## 数据与路线

主场景严格复用 [`validate_inference.py`](../../../scripts/validate_inference.py) 的生成函数和 Rubin pooling。MCAR、MAR 各 **200** 个独立数据集，`n=300,m=5`，主种子 `20260923`；协变量相关 `.3`，`y=1+x1+.5*x2+noise`，目标为 `x1` 真系数 1，y 始终观测。MCAR 每个协变量单元以 `.2` 概率缺失；MAR 的缺失概率仅依赖观测 y，采用原来的样本内 logistic 截距校准。整个三列表的期望缺失率约 13.33%，不是 20%。

每份数据用同一个小端 float64 二进制文件供所有路线读取；记录数据、掩码与插补种子、输入 SHA-256 和 R 内置 MD5 传输核验。原版 R、hybrid CPU64、选定 GPU/精度路线共用数据。每条 R 路线只启动一个持续 batch 进程，避免 400 次 R/Python 冷启动；此次不是性能基准。

- `r-reference`：原版 Amelia 1.8.3，全程 R CPU。
- `hybrid-cpu64`、`hybrid-cuda64`、`hybrid-cuda32`、`hybrid-mps32`：完整原版 R 工作流，EM 按显式设备/精度运行，保留 R CPU 工作及逐份诊断。
- `native-cpu64`、`native-cuda64`、`native-cuda32`、`native-mps32`：连续矩阵 native 工作流，单列为不同随机实现。

所有路线固定 `tolerance=1e-4, autopri=.05, empri=NULL, emburn=c(0,500)`、ordinary bootstrap；Torch 1 线程，GPU 不静默换设备或精度，CUDA TF32 关闭。R/hybrid 使用 `RNGkind("L'Ecuyer-CMRG", "Inversion", "Rejection")`。

旧生成器派生的 native 插补种子是 uint32，可能超过 R 上限。映射在正式运行前固定为：

```text
r_imputation_seed = original_native_uint32_imputation_seed % (2**31 - 1)
```

0 是有效 R seed。**数据与掩码种子保持原样；native 仍使用原始未映射种子及 NumPy PCG64。** 所有 R/hybrid 路线共享映射后的 R seed。不能据此声称 native 与 R 使用同一随机流或逐值相等。报告逐份记录两种插补种子。

## 主场景预定门槛

所有区间必须**完整落在**对应界限内；仅“差异不显著”不能通过。

| 项目，每路线/场景分别判断 | 90% 区间的可接受范围 |
|---|---|
| 相对真值 1 的平均系数偏差 | `[-.02,.02]` |
| 95% Rubin 区间覆盖率 | `[.90,.99]` |
| 相对原版 R 的配对平均系数差 | `[-.01,.01]` |
| 相对原版 R 的配对覆盖率差 | `[-.05,.05]` |
| 每数据集 pooled SE 比值的几何平均 | `[.95,1.05]` |
| 每数据集区间宽度比值的几何平均 | `[.95,1.05]` |

原版 R 自身必须过前两项绝对检查；其失败必须展示，不能统称为 GPU 问题。±.02 是目标系数 1 的 2%，配对 ±.01 是 1%；覆盖率以百分点计，SE/width 以比例计。这些界限已在新的 R/GPU 正式结果出现前固定并经项目负责人确认；旧 native CPU64 的 400 次结果此前已知，因此这是前瞻性扩展验证，不是全新未知数据的盲注册。

每项置信度为 **边际 90%**，不声称所有路线/场景联合的 familywise 90% 等价保证。全部必需比较都需通过。200 次仍可能无法把区间缩到界限之内，这应记为证据不足或超出预设界限，不在结果出现后自动增加预算。

## 公式与 Monte Carlo 不确定性

每份完成数据拟合同方差 OLS `y ~ 1+x1+x2`，方差使用 `SSE/(n−3)`；R 使用 `lm/vcov`，native 使用原有 QR 公式。各份系数和采样方差统一送入既有 Python `pool_scalar`：`T=Ubar+(1+1/m)B`、原有限 m 的 Rubin t 自由度，**不采用 Barnard–Rubin 有限完整样本修正**。原版 `mi.combine` 的版本特例不是这里的统计公式；兼容复现与统计推断检查分开。

- **偏差、配对系数差**：200 个独立数据集上的样本平均；`MCSE=sd(dataset-level values, ddof=1)/sqrt(N)`，90% CI 用 `t_(N−1,.95)`。配对差先在同一数据集相减，再计算 MCSE，不能当两组独立均值处理。
- **绝对覆盖率**：Clopper–Pearson 精确二项 90% 区间；描述 MCSE 为 `sqrt(p(1−p)/N)`。同时保留旧汇总的精确 95% 覆盖率区间，明确它与验收用 90% 区间不同。
- **配对覆盖率差**：令 `p+` 为“待测覆盖、R 未覆盖”的概率，`p−` 为相反事件的概率。分别为两种 discordance 概率求精确 95% Clopper–Pearson 区间；取 `[L+−U−, U+−L−]`，用 union bound 得到至少 90% 的保守区间。MCSE 为配对 `I_test−I_R` 的样本 SD 除以 `sqrt(N)`。即使零 discordance，也不会返回宽度为零的精确区间。
- **SE/width 比值**：逐数据集取 `log(test/reference)`，对其平均使用同一 t 区间后指数变换；报告 log 尺度的配对 MCSE。这里检验几何平均比值，不是两个算术平均值的比值。
- 报告每路线 bias、平均 pooled SE、平均区间宽度及其 MCSE、覆盖率和失败计数。带失败时成功子集的量仅作描述，不能用于验收通过。

## 完整性与压力案例

正式主场景必须保存全部计划数据集、每数据集全部 m 份输出，且全部收敛、观察值逐值不变、应补值有限、设备/精度记录正确。非零进程退出、输入/种子不配对、重复/缺失记录、源码在运行期间变化均不能被完整结果标签掩盖。原版 R 的原始 `iterHist`、warnings、code/message 保留；公共原版对象不提供最终 empri 和伪逆次数，因此写 null/不可获得，不能填 0。hybrid/native 保存其真实诊断。

另外使用独立 SeedSequence namespace `[20260923,2,replicate]` 生成 **20** 个压力数据集：`n=300,m=5`，协变量相关 `.95`，MCAR 协变量缺失概率 `.5`，y 始终观测，生成回归公式不变。压力记录不使用小样本 coverage 或等价门槛；保留失败、未收敛、autopri、伪逆、非有限/OOM 等状态。若存在失败或不完整，`stress_requires_review=true`；主场景是否通过仍独立报告，整体不能自动标成全部验收通过。该压力范围不是 MNAR 验证或高维保证。

脚本有总墙钟预算，R 子进程超过预算会被终止，已逐数据集 checkpoint 的记录仍保留；native 在每个 `m=5` 调用之间检查预算，该小调用本身由最多 500 轮 EM 约束，所以不是严格到秒的 native 终止器。未执行的计划记录仍在 manifest 中，不能消失为成功子集。超时不提高预算后覆盖原报告。

## 命令与公开产物

先运行流程 smoke（每主场景 3 个 + 压力 2 个；**无正式质量通过资格**）：

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
  .venv/bin/python scripts/validate_inference_suite.py --mode smoke \
  --routes r-reference hybrid-cpu64 native-cpu64 \
  --time-budget-seconds 120 --output results/local/g5-smoke-new
```

正式 CUDA 方案入库后，在同一已记录机器选择显式路线：

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
  .venv/bin/python scripts/validate_inference_suite.py --mode formal \
  --routes r-reference hybrid-cpu64 hybrid-cuda64 hybrid-cuda32 \
           native-cpu64 native-cuda64 native-cuda32 \
  --time-budget-seconds 1800 --output results/local/g5-cuda-formal
```

多条 GPU 路线的冷初始化及小矩阵调度可能较慢；可在正式执行前将墙钟预算设为 7200 秒，并原样记录。该预算变化不改变 200×2 样本数、生成种子或质量界限，也不形成性能结论。

MPS 使用 `hybrid-mps32/native-mps32`，不能请求不存在的 MPS64；Windows 替换解释器路径和环境变量设置语法。未选择的路线不能写为已验收。每条正式路线计划 420 个数据集、2,100 份插补；其中 400 个数据集用于主质量门槛，20 个为压力。

唯一完整汇总是输出目录的 **`inference-suite.json`**：包含冻结 protocol/哈希、逐份生成信息、源文件哈希、运行版本/已安装 R 库指纹、完整记录/诊断、描述统计及门槛。这是可脱敏公开的汇总；`*.local-config.json` 和 `*.local.log` 带本机路径，仅留本地，不能直接发布。输入二进制都是合成数据，完全由脚本重建。脚本拒绝覆盖既有输出目录；公开前再做路径/邮箱/机器标识扫描。退出 0 不能代替读取 mode 与各门槛：smoke 的 0 只代表流程检查通过。

2026-09-26 本机 CPU 流程复测已通过：`r-reference/hybrid-cpu64/native-cpu64` 三条路线各 8 个数据集（MCAR 3、MAR 3、压力 2），每份 m=5，合计 24 次插补调用、120 次拟合，全部收敛且观察值/有限输出检查通过。原版及 hybrid 使用 R 4.5.3 / Amelia 1.8.3；hybrid 和 native 使用 Torch 2.14.0。原版/hybrid 的同输入/映射 seed 已核验，八个 pooled 系数的最大绝对差为 `1.521e-14`，这只是 smoke 精度证据。所有主场景正式 gate 仍是 `insufficient_evidence`，`formal_acceptance_passed=false`。

完整可公开 [smoke 报告](smoke-cpu-report.json) SHA-256 为 `07f50cf5140aeeef22d98481ce7462f352944c66f93d318c4f8e1a0553c5d2c1`；运行期间被跟踪源码哈希未变，报告私人路径/邮箱扫描通过。本地路径为 `results/local/g5-smoke-20260926-fixed/inference-suite.json`，R 原始过程日志另存同目录 `r-reference.local.log`、`hybrid-cpu64.local.log`。首个 smoke 暴露的 R 命名 list JSON 结构错误已修复；那次失败仍保留在 `results/local/g5-smoke-20260926/`，未覆盖。40 项测试（29 个新门槛/种子/失败测试，加 11 个已有 pooling/生成测试）与 R 语法、Ruff 检查通过。

冻结 protocol SHA-256：`7ea7882bccc8d92102a67786bc9c09c2055ce29d97350abfbcf4f74f2187e454`。**尚未执行正式 200×2 扩展模拟；此次 smoke 不覆盖 GPU 路线。**
