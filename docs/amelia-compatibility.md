# Amelia 1.8.3 功能兼容矩阵

最后审计：2026-09-23；G1 下游方法补充：2026-09-26。以下将**官方参考**、**正在开发的 native PyTorch 路径**、**开发中的 R 过渡兼容路径**分开。固定算法契约见 [algorithm-contract.md](algorithm-contract.md)。用户已明确：**完整兼容验收后才算首版**。本项目暂不是 Amelia 全 API 的替代品；“已有 fixture”“代码已写”和“验证通过”不能混用。

目前可调用 `amelia_torch.amelia()` 完成连续数值数据的标准化、bootstrap、EM、随机补值及原始尺度恢复；Mac CPU float64 的 R 参考样例对照和 R 源码接口测试已通过。MPS float32 已通过三个小型 EM 参考样例，但这不足以证明完整统计质量或性能优势。开发验证记录汇总至 [2026-09-23 development](validation/2026-09-23-development/README.md)。

用户已允许明确标注依赖与CPU工作的 R 过渡路径。当前已有三个 R 入口：已通过已安装包CPU测试的 native `amelia_torch()`；原封调用官方 Amelia 1.8.3、已通过逐值输出及R RNG对照的 `amelia_compat(engine="reference")`；保留原版流程、在私有环境替换 EM 的实验性 `amelia_torch_compat()`。后者已通过下表所列代表性CPU组合案例，完整边界尚未验收。下表最后一列指实验性 Torch 兼容路径，**不把官方CPU委托当作GPU实现**。Python到R参考桥另行验证。详见 [R interface](r-interface.md)。

| 功能 | 官方 Amelia 1.8.3 | Native PyTorch 当前状态 | R过渡Torch兼容路径（CPU代表案例已测） |
|---|---|---|---|
| 已标准化连续矩阵 EM | 参考实现 | CPU float64 内核已实现；R fixture 对照已通过 | 委托/适配代码已写，待验证 |
| 分缺失模式条件均值与协方差 | 已有 | 已实现；显式条件矩 fixture | 委托/适配代码已写，待验证 |
| M 步、分母 n、对称 theta | 已有 | 已实现；单步/终值对照通过 | 委托/适配代码已写，待验证 |
| `startvals=0/1`、显式 theta | 已有 | 已实现；包含完整行数及正定阈值 | 委托/适配代码已写，待验证 |
| 完整 bootstrap 样本 shortcut | 样本协方差 n−1，忽略 empri | 已实现；有参考 fixture | 委托/适配代码已写，待验证 |
| `tolerance` 上三角绝对差规则 | 已有 | 已实现；逐轮对照通过 | 委托/适配代码已写，待验证 |
| `emburn` 最少/最多迭代 | 默认 c(0,0)，无最大值 | 已实现；min/max 参考 fixtures | 委托/适配代码已写，待验证 |
| `empri`、整数截断和 p+2 分母 | 已有 | 已实现；3.75→3 对照通过 | 委托/适配代码已写，待验证 |
| `autopri` 自适应更新 | 已有；固定初始 hold 特例 | 已实现逻辑；病态触发仅诊断，未宣称跨设备严格一致 | 委托/适配代码已写，待验证 |
| 低层 cell priors：mean/variance | 已有 | 已实现；条件矩及EM fixture通过 | 委托/适配代码已写，待验证 |
| 公共 cell priors：mean/SD | 已有 | **未实现公共坐标转换** | CPU组合案例通过；单行prior上游特例见算法契约 |
| 五列 confidence priors | 已有 | **未实现** | CPU组合案例通过；完整边界未覆盖 |
| row=0 全变量 priors、优先级 | 已有 | **未实现** | CPU全变量与cell prior组合案例通过 |
| 原始数据观察值标准化 | 已有，nobs−1 SD | 连续数据公共流程已实现；有尺度等变及原始尺度恢复测试 | 委托/适配代码已写，待验证 |
| `ordinary` bootstrap 和拒绝重抽 | 已有 | 连续数据公共 EMB 已实现；使用 NumPy RNG，不保证与R同seed同抽样 | 委托/适配代码已写，待验证 |
| `boot.type="none"` 公共选项 | 已有 | 公共 `boot_type="none"` 已实现；R别名及调用测试通过 | m=2 CPU案例通过；R/C RNG修复后Inversion/Box-Muller draws及后续R RNG对照通过 |
| 基于参数的随机补值 | 已有 | `impute_prepared` 已实现；显式R标准正态fixture通过 | 委托/适配代码已写，待验证 |
| 保留观察值及原始行列顺序 | 公共输出保证 | 公共数组输出已实现并测试；R源码接口保留matrix/data.frame及名称，完整R类型语义未实现 | 委托/适配代码已写，待验证 |
| 全缺失分析行 | 移除拟合，最终保持NA | 公共移除/恢复已实现；Python/R源码测试通过，R保留原NA/NaN | 委托/适配代码已写，待验证 |
| 全缺失列/单一观察值/常量 | 公共校验拒绝 | 连续数据校验已实现，错误码4/43；尚未覆盖原版全部检查组合 | 委托/适配代码已写，待验证 |
| 无缺失原始数据 | 公共默认code39 | 公共接口以code39拒绝，测试通过；内部完整样本shortcut仍可用 | 委托/适配代码已写，待验证 |
| `idvars` | 不入模型，保留格式 | **未实现** | CPU组合案例通过；单行prior上游特例见算法契约 |
| `logs` | 有版本特例，见算法契约 | **未实现**；不得自行更改逆变换 | CPU组合案例通过 |
| `sqrts`、`lgstc` | 已有 | **未实现** | CPU组合案例通过 |
| `noms` 名义类别 | k−1虚拟变量+随机类别抽样 | **未实现** | CPU factor组合案例通过 |
| `ords` 有序类别 | 范围内二项随机抽样 | **未实现** | CPU ordered factor组合案例通过 |
| `ts`、`cs` | 时间/分组标识处理 | **未实现** | CPU panel组合案例通过 |
| `polytime`、`splinetime` | 指定时间basis | **未实现** | CPU两类时间basis案例通过 |
| `intercs` | 固定效应/时间交互项 | **未实现** | CPU TRUE/FALSE组合案例通过 |
| `lags`、`leads` | 组内排序、边界缺失 | **未实现** | CPU panel组合案例通过；完整边界未覆盖 |
| `bounds`、`max.resample` | 有限联合拒绝抽样后夹边界 | **未实现** | CPU组合案例通过；边界分布质量未验收 |
| `overimp`、恢复原观察值档案 | 已有 | **未实现** | CPU组合案例通过 |
| `p2s` | 原版进度输出选项 | 接受0/1/2并可打印进度；**未复刻原版日志格式** | 委托/适配代码已写，待验证 |
| `incheck`、`collect` | 原版检查/执行选项 | **未实现同名公共行为** | 委托/适配代码已写，待验证 |
| `arglist`、已有amelia/molists扩展 | 已有S3方法 | **未实现** | CPU saved-arglist、追加历史draw、局部moPrep对象案例通过 |
| `parallel`、`ncpus`、`cl` | no/multicore/snow | **未实现公共副本调度** | 仅串行副本调度；原版并行走reference入口，均待测试 |
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
| Windows CUDA（RTX 3080） | 原版无CUDA内核 | **未到机测试**，不可宣称加速 | 未到机测试 |
| macOS CPU float64 | 本机R参考实测 | CPU确定性参考测试通过 | 已安装包代表案例通过 |
| macOS MPS float32 | 原版无MPS内核 | 基础探针及3个小EM参考样例通过；完整质量/性能验收未完成 | 委托/适配代码已写，待验证 |
| Linux CPU/CUDA | GitHub Ubuntu CPU runner已测 | CPU CI通过；CUDA未测 | CPU CI通过；CUDA未测 |
| 安装包、RStudio分发、CRAN/PyPI | 官方包已有 | Python开发环境可调用；Mac R安装/build及包测试通过；**未发布正式包** | Mac R CMD check零错误/警告/NOTE；RStudio会话待测 |
| 三个大公开数据集端到端比较 | 不适用 | 3组各10万行native数值子集正式基准已完成并审计，性能见独立验证记录 | 该路径基准尚未运行 |

最后一列的“代码已写，待验证”仅说明原版流程委托或EM适配代码存在，不构成该功能通过验收的证据。每个公共选项和边界情况必须独立对照后才能改为支持。

G1 的 2026-09-26 新增例子、源码哈希、原版 `mi.combine` 特例及可选依赖边界见
[独立回归记录](validation/2026-09-26-g1/downstream-extended.md)。可运行
[Python/R 示例](../examples/README.md) 已在 reference 和 CPU64 hybrid 模式完成
官方 RDS 往返、R 方法调用与再次 Python 读取。这些下游方法继续在原版 R CPU
执行；新的 CI 步骤未经真实运行前不计入下方既有三平台结果。

Linux/macOS/Windows 的 hosted CPU CI 已实际通过，包含 Python 和五个 R 测试文件；详见[CI证据](validation/2026-09-23-development/cross-platform-ci.md)。GPU CI、Windows RTX 3080 到机验证，以及 RStudio 已安装包的真实会话测试仍待完成。已确定分发名 `amelia-torch`、许可证 `GPL-3.0-only`、维护者 Sheng Wan（`swan0624@uw.edu`）、小样本加完整下载脚本的数据交付方式，以及明确标注的 R 过渡方案；GitHub 用户名已确认为 `Tocqueville0624`，用户确认 Windows RTX3080 暂不能接入，本轮先公开开发快照。

## 验收与宣传规则

1. 不支持的公共选项明确拒绝；不能忽略参数继续给结果，也不能将慢速fallback计入GPU收益而不披露。
2. R runtime/reference 依赖、dtype、设备、同步、失败、未收敛和伪逆都记录；不能让用户误以为所有计算都在GPU上。
3. 对GPU收益只报告同机器、同任务、同质量门槛的端到端比较，包括 R 桥、传输与输出恢复；Mac CPU 对 Windows GPU 不是 GPU speedup。
4. 原版常见功能必须逐项测试后才能宣称兼容。只支持连续数据的内核阶段可以公开展示进展，不能用“完全复现 Amelia”描述现阶段产物。
5. 同一seed不保证逐值相等。确定性fixture比较使用实际导出的随机输入；统计声明用重复模拟与推断质量证据。

本表是审计时点的保守状态；功能推进后由负责 Agent 依据新测试证据更新，禁止仅根据函数名称把项目改成“全部支持”。
