# Amelia 1.8.3 功能兼容矩阵

最后审计：2026-09-26；G1–G4 有界功能、G7 产品计时与历史 Mac 基准已更新。以下将**官方参考**、**正在开发的 native PyTorch 路径**、**开发中的 R 过渡兼容路径**分开。固定算法契约见 [algorithm-contract.md](algorithm-contract.md)。用户已明确：**完整兼容验收后才算首版**。本项目暂不是 Amelia 全 API 的替代品；“已有 fixture”“代码已写”和“验证通过”不能混用。

目前可调用 `amelia_torch.amelia()` 完成连续数值数据的标准化、bootstrap、EM、随机补值及原始尺度恢复；Mac CPU float64 的 R 参考样例对照和 R 源码接口测试已通过。MPS float32 已通过三个小型 EM 参考样例及三个 R 公共组合案例，三组 10 万行数值子集的 native/hybrid 性能也已实测；本机结果均未显示 MPS 相对同精度 CPU 的加速。这些证据不足以证明完整统计推断等价。开发验证记录汇总至 [2026-09-23 development](validation/2026-09-23-development/README.md)。

用户已允许明确标注依赖与CPU工作的 R 过渡路径。当前已有三个 R 入口：已通过已安装包CPU测试的 native `amelia_torch()`；原封调用官方 Amelia 1.8.3、已通过逐值输出及R RNG对照的 `amelia_compat(engine="reference")`；保留原版流程、在私有环境替换 EM 的实验性 `amelia_torch_compat()`。后者已通过下表所列代表性CPU组合案例，完整边界尚未验收。下表最后一列指实验性 Torch 兼容路径，**不把官方CPU委托当作GPU实现**。Python到R参考桥另行验证。详见 [R interface](r-interface.md)。

| 功能 | 官方 Amelia 1.8.3 | Native PyTorch 当前状态 | R过渡Torch兼容路径（CPU代表案例已测） |
|---|---|---|---|
| 已标准化连续矩阵 EM | 参考实现 | CPU float64 内核已实现；R fixture 对照已通过 | CPU64 公共/内部 allthetas 对照通过；仅 EM 交给 Torch |
| 分缺失模式条件均值与协方差 | 已有 | 已实现；显式条件矩 fixture | 使用同一 Torch EM 内核；CPU64 公共连续与先验案例通过 |
| M 步、分母 n、对称 theta | 已有 | 已实现；单步/终值对照通过 | CPU64 公开终值、allthetas 及完整样本 shortcut 对照通过 |
| `startvals=0/1`、显式 theta | 已有 | 已实现；包含完整行数及正定阈值 | G2 CPU64 m=2 ordinary/none 通过；double 原位更新与 integer coercion、调用者/归档别名均匹配 |
| 完整 bootstrap 样本 shortcut | 样本协方差 n−1，忽略 empri | 已实现；有参考 fixture | G2 固定 seed 公共 bootstrap 实际触发；样本 cov、history NA、显式初值保持不变通过 |
| `tolerance` 上三角绝对差规则 | 已有 | 已实现；逐轮对照通过 | CPU64 公共 history 及 G2 emburn 上下限对照通过 |
| `emburn` 最少/最多迭代 | 默认 c(0,0)，无最大值 | 已实现；min/max 参考 fixtures | G2 CPU64 35轮下限/2轮上限、history、未收敛 warning/metadata 通过 |
| `empri`、整数截断和 p+2 分母 | 已有 | 已实现；3.75→3 对照通过 | 使用已测 EM 内核；CPU 公共 empri 及 MPS 先验组合案例通过，非全部病态边界 |
| `autopri` 自适应更新 | 已有；固定初始 hold 特例 | 已实现逻辑；病态触发仅诊断，未宣称跨设备严格一致 | G2 public CPU64 两引擎实际更新，8次后续公式检查证实 hold 固定；近零特征值下状态/轨迹差异完整记录，不算有效质量样本 |
| 低层 cell priors：mean/variance | 已有 | 已实现；条件矩及EM fixture通过 | 原版转换后进入同一 EM 内核；CPU/MPS 公共先验组合通过 |
| 公共 cell priors：mean/SD | 已有 | **未实现公共坐标转换** | CPU组合案例通过；单行prior上游特例见算法契约 |
| 五列 confidence priors | 已有 | **未实现** | CPU组合案例通过；完整边界未覆盖 |
| row=0 全变量 priors、优先级 | 已有 | **未实现** | CPU全变量与cell prior组合案例通过 |
| 原始数据观察值标准化 | 已有，nobs−1 SD | 连续数据公共流程已实现；有尺度等变及原始尺度恢复测试 | 原版 R 委托；CPU64 连续、变换与公开结果对照通过 |
| `ordinary` bootstrap 和拒绝重抽 | 已有 | 连续数据公共 EMB 已实现；使用 NumPy RNG，不保证与R同seed同抽样 | G2 公共两次抽样实际索引对照，第一次全缺失列拒绝、第二次接受；私有记录器不改输出 |
| `boot.type="none"` 公共选项 | 已有 | 公共 `boot_type="none"` 已实现；R别名及调用测试通过 | m=2 CPU案例通过；R/C RNG修复后Inversion/Box-Muller draws及后续R RNG对照通过 |
| 基于参数的随机补值 | 已有 | `impute_prepared` 已实现；显式R标准正态fixture通过 | 原版 R/C 抽样；ordinary/none m>1 与两种 normal RNG/后续流回归通过 |
| 保留观察值及原始行列顺序 | 公共输出保证，单行 priors 等版本特例见契约 | 公共数组输出已实现并测试；R源码接口保留matrix/data.frame及名称，完整R类型语义未实现 | 原版输出层；公共/G3 类型与大数据逐份检查通过，保留已记录上游特例 |
| 全缺失分析行 | 移除拟合，最终保持NA | 公共移除/恢复已实现；Python/R源码测试通过，R保留原NA/NaN | G2 公共 CPU64 保持全空行且其余缺失补齐通过 |
| 全缺失列/单一观察值/常量 | 公共校验拒绝 | 连续数据校验已实现，错误码4/43；尚未覆盖原版全部检查组合 | G2 全空列/常量及样本量不足的 code 4/43/34 对照通过；未逐项重复所有检查组合 |
| 无缺失原始数据 | 公共默认code39 | 公共接口以code39拒绝，测试通过；内部完整样本shortcut仍可用 | G2 默认 code39 与 incheck=FALSE 完整样本输出通过 |
| `idvars` | 不入模型，保留格式 | **未实现** | CPU组合案例通过；单行prior上游特例见算法契约 |
| `logs` | 有版本特例，见算法契约 | **未实现**；不得自行更改逆变换 | CPU组合案例通过 |
| `sqrts`、`lgstc` | 已有 | **未实现** | CPU组合案例通过 |
| `noms` 名义类别 | k−1虚拟变量+随机类别抽样 | **未实现** | CPU factor组合案例通过 |
| `ords` 有序类别 | 范围内二项随机抽样 | **未实现** | CPU ordered factor组合案例通过 |
| `ts`、`cs` | 时间/分组标识处理 | **未实现** | CPU panel组合案例通过 |
| `polytime`、`splinetime` | 指定时间basis | **未实现** | CPU两类时间basis案例通过 |
| `intercs` | 固定效应/时间交互项 | **未实现** | CPU TRUE/FALSE组合案例通过 |
| `lags`、`leads` | 组内排序、边界缺失 | **未实现** | CPU panel组合案例通过；完整边界未覆盖 |
| `bounds`、`max.resample` | 有限联合拒绝抽样后夹边界 | **未实现** | CPU组合与 G2 实际耗尽后9格夹边界、max.resample=0 code52 通过；边界分布质量未验收 |
| `overimp`、恢复原观察值档案 | 已有 | **未实现** | CPU组合案例通过 |
| `p2s` | 原版进度输出选项 | 接受0/1/2并可打印进度；**未复刻原版日志格式** | G2 CPU64 0/1/2 统计结果通过；明确使用 PyTorch 进度文字 |
| `incheck`、`collect` | 原版检查/执行选项 | **未实现同名公共行为** | G2 incheck=FALSE、collect=TRUE 公共 CPU64 结果通过；保留原版检查消耗 RNG 的行为 |
| `arglist`、已有amelia/molists扩展 | 已有S3方法 | **未实现** | CPU saved-arglist、追加历史draw、局部moPrep对象案例通过 |
| `parallel`、`ncpus`、`cl` | no/multicore/snow | **未实现公共副本调度** | Hybrid 仅串行；reference 的 Python snow2 库继承/重复/worker错误、R supplied-cl ownership 与本机 Unix multicore 已测（G4）；Windows 不提供 Unix fork |
| `allthetas` 内部诊断格式 | 参数向量×初值及每轮 | 有native矩阵历史；**不是同格式** | CPU初值+每轮上三角向量及iter.hist对照通过 |
| 官方 `amelia` / `mi` 返回类 | 已有 | 自有结果结构，**不得伪装官方类** | 原版输出层class/arguments通过；代表性官方下游及G1指定分支已在CPU64小例实测 |
| `ameliabind` / `transform.amelia` | 已有 | **未移植** | CPU64直接合并、错误分支、派生列、transform.calls及追加旧份保留通过；bind丢失来源后保守标unknown |
| `with.amelia` / `mi.combine` | 已有，存在1.8.3公式特例 | **未移植** | CPU64 with/lm、两种conf.int及.90区间全部返回列对照；保留官方端点倒序及带符号p值，不代表推断公式正确 |
| `moPrep` 的四个补充分支 | proportion、gold standard、proxy、已有molist增加 | **未移植** | CPU64 priors/overimp/RDS及original/reference/hybrid小例通过；局部caller/error.sd另有既存测试 |
| `summary.mi` / `plot.amelia` | 已有 | **未移植** | summary文本/表及plot compare/overimpute PDF分支通过；不等于视觉验收 |
| `write.amelia` CSV/table/DTA | 已有 | **未移植** | CPU64逐份/合并文件读回、factor标签、orig.data=FALSE和自定义impvar通过 |
| `compare.density` / `overimpute` / `disperse` 等诊断 | 已有 | **未移植** | 这些方法及missmap/tscsPlot已在小案例输出PDF并对照；仍执行官方CPU代码 |
| Rubin pooling | `mi.meld`等可用于结果分析 | 验证脚本及手算对照测试已编写；**完整统计质量验收未完成** | mi.meld和mi.combine功能对照已测；总体统计质量仍需独立模拟，不能以功能测试代替 |
| R调用native连续数据接口 | 不适用 | Mac源码桥接CPU32/64测试通过；用自有 `ameliatorch_result` | 与此列过渡方案不同 |
| Windows CPU | 官方参考与本包在 GitHub Windows runner 通过 | hosted CPU CI通过；用户RTX3080电脑未接入 | hosted CPU CI通过；不代表CUDA |
| 云端 CUDA / Windows CUDA | 原版无CUDA内核 | 用户已授权云端替代不可接入的 RTX 3080；完整 CUDA 验收进行中，不以设备探针宣称通过 | 云端 CUDA 仍需同机完整质量/速度验收；Linux 云端不冒称 Windows CUDA 已测 |
| macOS CPU float64 | 本机R参考实测 | CPU确定性参考测试通过 | 已安装包代表案例通过 |
| macOS MPS float32 | 原版无MPS内核 | 3个 EM 样例和三组大数据已测；MPS 比同机 CPU32 慢 51%–70%，推断质量验收仍待完成 | 变换/类别/先验边界3公共案例及三组大数据通过有限性等门槛；MPS 比同机 hybrid CPU32 慢13%–33%，不是全部 GPU 质量验收 |
| Linux CPU/CUDA | GitHub Ubuntu CPU runner已测 | CPU CI通过；CUDA未测 | CPU CI通过；CUDA未测 |
| 安装包、RStudio分发、CRAN/PyPI | 官方包已有 | Python开发环境可调用；Mac R安装/build及包测试通过；**未发布正式包** | Mac R CMD check零错误/警告/NOTE；RStudio会话待测 |
| 三个大公开数据集端到端比较 | 本机原版串行/snow4已测 | 3组各10万行native数值子集正式基准已完成并审计 | CPU64/CPU32/MPS32 共9配置63调用315插补已审计；完整 R 调用包含桥接，排除进程初始化；不宣称全量/全部缺失机制 |
| Python → R 完整公开调用成本 | 官方 CPU 引擎，经 binary/RDS 传输 | 与 native 内存计时边界不同 | G7 100k Covertype m5 reference/hybrid CPU64 各首次+2次后续，均约12秒；每次新R进程，不能与旧R计时相减 |
| 独立逐格 MCAR 有界压力 | 原版全空行仍NA | 本轮未新增 native 压力计时 | G7 5000×7、125模式、m5 的 reference/CPU64/MPS32 已记录；14 heldout/份未评分，完整RMSE=null，不算有效速度质量样本 |
| Intel Mac 无 Torch reference 安装 | 官方 R CPU | 未承诺当前 Intel Torch wheel/hybrid | ad9bed2 的真实 x86_64 hosted runner 完成隔离 wheel[reference]、无Torch及Python/RDS/R方法往返；不代表GUI或Intel hybrid |

最后一列引用的是已执行的有限案例，不表示所有参数组合或 GPU 精度均通过。每个新增公共选项与有界分支仍应保留独立对照证据。

G1 的 2026-09-26 新增例子、源码哈希、原版 `mi.combine` 特例及可选依赖边界见
[独立回归记录](validation/2026-09-26-g1/downstream-extended.md)。可运行
[Python/R 示例](../examples/README.md) 已在 reference 和 CPU64 hybrid 模式完成
官方 RDS 往返、R 方法调用与再次 Python 读取。这些下游方法继续在原版 R CPU
执行；新的 CI 步骤未经真实运行前不计入下方既有三平台结果。

同日 [G2 公共边界记录](validation/2026-09-26-g2/README.md) 包含 33 个 CPU64
案例、显式初值 alias 修复，以及两条 public 病态轨迹的 autopri/固定 hold 检查。
近奇异案例的结果码和轨迹有已记录差异，不能算有效质量样本；新增 GPU 精度验收仍待完成。
[G4 并行记录](validation/2026-09-26-g4/README.md) 是本机 reference CPU 路线的真实
worker 测试，新增 Windows/Linux CI 尚未运行，不表示 hybrid 开放了多 worker。

[Mac 性能与 MPS 公共精度记录](validation/2026-09-23-development/README.md)保存全部成功/慢速结果及实际测量源码；低模式 block-MCAR 的有限性门槛不等于推断分布等价。新增 [G7 记录](validation/2026-09-26-g7/README.md)单列 Python 完整调用与独立 MCAR 未完整评分压力样本；峰值 RAM/VRAM 未测为 null。G3 类型/会话及明确错误的有限证据见 [G3 记录](validation/2026-09-26-g3/README.md)，Python frontend GUI 前门明确拒绝。

Linux/macOS/Windows hosted CPU CI 在 `e2ff892` 已实际完成各 235 项 Python 与九个 R 测试文件，见 [CI 证据](validation/2026-09-26-ci/cross-platform-ci-e2ff892.md)；Intel no-Torch reference 的独立记录见 [Intel Mac 证据](validation/2026-09-26-ci/intel-mac-reference.md)。该版本包含 G3/G4/autopri/G7；原版病态 autopri 在 Linux/Windows 未触发，不能把绿色任务当成该分支已覆盖。CUDA 完整验收和 RStudio 已安装包的真实会话测试仍待完成。已确定分发名 `amelia-torch`、许可证 `GPL-3.0-only`、维护者 Sheng Wan（`swan0624@uw.edu`）、小样本加完整下载脚本的数据方案及明确标注的 R 过渡路径；公开仓库账号 `Tocqueville0624`，当前保持开发快照标记。

## 验收与宣传规则

1. 不支持的公共选项明确拒绝；不能忽略参数继续给结果，也不能将慢速fallback计入GPU收益而不披露。
2. R runtime/reference 依赖、dtype、设备、同步、失败、未收敛和伪逆都记录；不能让用户误以为所有计算都在GPU上。
3. 对GPU收益只报告同机器、同任务、同质量门槛的端到端比较，包括 R 桥、传输与输出恢复；Mac CPU 对 Windows GPU 不是 GPU speedup。
4. 原版常见功能必须逐项测试后才能宣称兼容。只支持连续数据的内核阶段可以公开展示进展，不能用“完全复现 Amelia”描述现阶段产物。
5. 同一seed不保证逐值相等。确定性fixture比较使用实际导出的随机输入；统计声明用重复模拟与推断质量证据。

本表是审计时点的保守状态；功能推进后由负责 Agent 依据新测试证据更新，禁止仅根据函数名称把项目改成“全部支持”。
