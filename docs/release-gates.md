# 首版验收缺口：Amelia 1.8.3 功能与产品边界

审计日期：2026-09-23，正式 hybrid 性能实验开始后。此次仅读取源码、现有测试和验证报告，并读取已安装 Amelia 1.8.3 的 namespace exports/formals；没有运行拟合、模拟或性能测试，也没有修改冻结源码。下列未勾选项是可执行的剩余验收任务，不是已发现算法均错误，也不是要求遍历任意参数组合。

用户已同意明确标注的原版 R 过渡依赖，因此首版可以由原版 reference、R/PyTorch hybrid 和 native 子集共同提供能力。**无需先把每个 R 图形函数改写为 Python 才能交付，但不能把委托给原版 CPU 的功能标成原生 GPU 实现。** 用户要求完整功能完成才算首版；当前开发快照、成功打包和局部速度结果不等于首版验收。

## 已有保证与不能外推的部分

| 路径 | 已验证的保证 | 当前边界 |
|---|---|---|
| R `amelia_compat(engine="reference")` | 调用精确版本 Amelia 1.8.3；代表性连续/类别/变换/先验/时间模型、追加与局部 `moPrep` 对象和原版对照；不初始化 Python | 完整统计实现来自原版 CPU；未覆盖下列所有公开工作流；原版版本特例仍存在 |
| Python `amelia_reference` | typed binary/RDS 通道；数值、factor/ordered、log、先验/边界、arglist、追加、错误和来源记录有集成测试；不导入 Torch | 启动独立 Rscript；RDS 是权威结果；不能传输原 R 会话的活跃对象或任意 Python 对象；本桥不是 Python 下游绘图/建模函数全集 |
| R/Python `amelia_torch_compat` | 原版预处理/bootstrap/条件抽样/后处理，仅替换 EM；CPU64 的代表性公开工作流及 R 随机流对照通过；注册 C helper 修复无 bootstrap 多份抽样重复，保留原版可见 seed 与后续随机调用语义 | 仅串行副本调度；高级功能主要仍由原版 R CPU 执行；MPS32 三个固定公开案例通过，不等于所有模型或统计推断均验收 |
| Native `amelia_torch.amelia` / R `amelia_torch` | 连续矩阵 EMB；固定 R EM/随机输入 fixtures、公开标准化/排序、观察值与全缺失行语义；CPU64 MCAR/MAR 推断初筛；三组大数值子集基准已有审计 | 不支持公共类别、变换、cell priors、bounds、时间结构等，明确报错；NumPy 随机流，不承诺同 R seed 逐值相同；返回自有结构 |

现有实测依据：[开发验证索引](validation/2026-09-23-development/README.md)、[Python/RNG 集成记录](validation/2026-09-23-development/python-hybrid-rng.json)、[R 下游检查](validation/2026-09-23-development/r-downstream-validation.md)、[R 包检查](validation/2026-09-23-development/r-package-check.md)。这些证据已经覆盖的项目无需为“所有组合”再无限扩展。

## 实际公开接口盘点

读取 `getNamespaceExports("Amelia")` 得到 16 个导出函数。以下按实际工作流分组，区分已测试和尚缺的具体分支。

| 导出函数 / 注册方法 | 现有证据 | 有限的剩余验收 |
|---|---|---|
| `amelia`、`amelia.default`、`amelia.molist`；S3 `amelia.amelia` | 三条路径均有公开调用；普通/无 bootstrap、追加、局部 molist、self-contained molist RDS 已测 | 下节 G2 的公共边界与 G4 并行路由 |
| `ameliabind` | 每次多份输出与追加已间接执行 | 直接合并两个兼容结果；再用不同 missingness 或不同 model arguments 验证原版错误；从合并 RDS 重读时不能把丢失的 backend 记录伪造为已知 CPU |
| `transform.amelia` | 尚无独立验收；现有 `logs/sqrts/lgstc` 测试不是该函数 | 派生一列后继续追加，检查每份派生值、`missMatrix`、`transform.calls`、旧份数不变；经 RDS 跨 Python/R 后再追加 |
| `with.amelia`、`mi.combine` | 尚未测；已有 pooling 用 `lapply(lm)` 与 `mi.meld`，没有经过这两函数 | 一个 `with(fit, lm(...))`，分别比较 `mi.combine(conf.int=FALSE/TRUE, conf.level=.90)` 的估计/SE/区间/df；`rlang` 是 Amelia 的 Imports，`broom` 是 `mi.combine` 所需的 Suggests，缺后者时明确报错，不静默换 pooling 公式 |
| `mi.meld` | 原版/混合结果和手算 Rubin SE 已比对 | 已有核心证据；与 `mi.combine` 区别写清，不重复声称另一种自由度修正已验证 |
| `moPrep`；S3 default/molist | `error.sd`、局部 caller frame、自包含 molist RDS 已测 | 固定小例分别覆盖 `error.proportion`、`subset/gold.standard`、proxy formula，以及对已有 molist 再 `moPrep`；验证 prior/overimp 档案及原版结果 |
| `compare.density`、`overimpute`、`disperse`、`tscsPlot`、`missmap` | 小数据 numeric return 对照及 PDF 文件检查已通过；`disperse` 继续执行官方 CPU EM | 无需重写为 GPU；RStudio 中人工确认至少一张图正常显示，不能把 PDF 魔数/大小检查称为视觉检查 |
| S3 `print.amelia`、`summary.amelia` | 输出文本对照通过 | 已有证据 |
| S3 `summary.mi`、`plot.amelia` | 尚未直接覆盖；调用各个绘图 helper 不等于 `plot` 调度已测 | `summary(fit$imputations)` 对照；`plot(fit, which.vars=..., ask=FALSE)` 的 compare/overimpute 分支各一个 headless PDF 与设备清理检查 |
| `write.amelia` | separate/combined CSV 已读回核验 | 支持的另外两种格式 `table` 和 `dta` 各一份读回；`orig.data=FALSE`、自定义 `impvar` 的一个 combined 文件；与原版处理因素标签/行数一致 |
| `AmeliaView` | 未启动、未测试 | 这是原版 R/Tcl/Tk GUI。若对外列为可用功能，在可用图形环境做一次官方启动/载入/关闭检查并明确其仍走原版 CPU。用户要求 RStudio 调包，不自动产生重写 GUI 或给原版 GUI 注入 GPU 的新需求 |

`amelia.default` 的实际 formals 包括：`x, m, p2s, frontend, idvars, ts, cs, polytime, splinetime, intercs, lags, leads, startvals, tolerance, logs, sqrts, lgstc, noms, ords, incheck, collect, arglist, empri, priors, autopri, emburn, bounds, max.resample, overimp, boot.type, parallel, ncpus, cl, ...`。`allthetas` 是内部 EM/诊断接口，**不是** `amelia.default` 的同名公开参数；已有内部格式对照不能宣称公共函数新增了此参数。

## 可关闭的首版验收任务

### G1：补齐尚无测试的公开下游工作流

- [ ] 完成上表中的 direct `ameliabind`、`transform` 后追加、`with`→`mi.combine`、`moPrep` 四个指定分支、`summary.mi`/`plot.amelia`、table/dta 导出。用现有小合成数据与原版结果，固定 CPU64，不增加大规模模拟。
- [ ] 为这些工作流提供从 Python `save_rds` 到 R 原版方法、再回到 Python 的一条可运行示例。允许继续委托 R；不要把“仅生成 RDS”写成所有下游操作都已有 Python 方法。
- [ ] 安装说明列出 `mi.combine` 的可选 `broom` 依赖、Amelia 正常安装所带的 `rlang`，以及 GUI 的 Tcl/Tk 会话要求；验证可选依赖可用和缺失时的清晰行为。

### G2：封闭混合公共入口的核心边界

已有低层 fixtures 证明若干数学分支正确，但尚缺以下**公开 hybrid 路径**的小型回归；无需重做所有低层测试。

- [ ] `startvals=1` 与显式 theta 各一例；`emburn` 最小迭代/最大迭代各一例，核对 public history、收敛标志与 warning。CPU64 先与原版对照，再在支持的 GPU 精度下检查合法状态。
- [ ] 固定一例 bootstrap 恰好完整和一例会先抽到全缺失列后重抽的输入/种子，核对 sample-covariance shortcut 与拒绝重抽。记录实际触发证据，不能只碰巧运行成功。
- [ ] 固定一例会触发 `autopri` 更新或奇异处理的病态输入，检查更新记录、初始 prior hold 不被重建、最终失败/成功不被误标；病态特征值符号可依 BLAS 不同，不能要求临界舍入下的完全相同历史。现有 `adaptive_stress.json` 只是诊断样例。
- [ ] 一个 public bounds 极窄且 `max.resample=0` 或很小的案例，确实触发原版耗尽后的边界处理；普通范围内样例不能证明该分支。
- [ ] 一个带全缺失分析行、一个完全无缺失、一个全缺失列/常量列，以及一个 `p` 相对 `n` 不足的 public hybrid 输入：对照原版的输出/错误码，不把 low-level native 的测试代替该入口。
- [ ] 一个合法输入比较 `incheck=FALSE`、`collect=TRUE` 及 `p2s=1/2` 的统计输出/执行行为。上游 `collect` 当前未改变 EM 数学，不能因此发明新统计逻辑；hybrid 进度文字与原版不完全相同，应明确说明。

单行 priors 改动无关观察值、log 逆变换及 stale `.Random.seed` 都是已核验的原版版本行为，见[算法契约](algorithm-contract.md)。以上验收不能以偷偷修改这些行为来让测试变绿；修正版应另命名/另决定，不能混进兼容模式。

### G3：固定 Python/R 类型与会话边界

- [ ] 完成一次真实拟合/RDS 往返：被排除的 id 列为全缺失 nullable integer/string，非 ASCII 列名/类别，以及重复 Python index。现有纯编码测试还不是完整 R 往返证据；列名字符串化碰撞已明确拒绝，不必重新发明索引规则。
- [ ] 对不在承诺范围的 datetime、复杂/混合 object、稀疏/Arrow 类输入各取一个代表例，确认拒绝或要求用户显式转换；对外部 RDS 的 Date/自定义列类，确认 Python view 不会声称保留了未编码的 dtype，原 RDS 仍完整。无需为了首版自行移植每一种 Python/R 扩展类。
- [ ] 测试不存在 Rscript、错误 Amelia 版本、缺少 hybrid R DLL/torch、不可用设备四类依赖失败，并覆盖一个带空格/中文的用户库/解释器路径；错误要指明修复步骤。当前测试已有部分检查，跨平台安装必须使用实际打包产物复核。
- [ ] 明确 `frontend=TRUE` 和 `AmeliaView` 的 R GUI 会话路由；Python 子进程没有原会话 Tcl/Tk 状态时应清晰失败，不能挂起或暗示可控制现有 GUI。无需允许 Python 对象传送 live PSOCK cluster、连接、外部指针或 GUI 环境。

R `moPrep` 默认保存调用表达式而非数据。跨进程必须使用已物化数据的自包含 RDS；现有测试和文档已经说明。Python-only index/扩展 dtype 不写入原版 RDS、重新读盘默认追加走 reference、hybrid 原对象 `extend` 保持原引擎，也都是已明确的产品契约，不应被误记成算法缺陷。

### G4：验证明确选择的并行 CPU 过渡路径

- [ ] 用 Python `amelia_reference(parallel="snow", ncpus=2, r_rng_kind="L'Ecuyer-CMRG")` 做一个小例的可重复输出、worker 项目库/正常用户库可见性与错误传播测试。原版 benchmark 的 snow4 成功不等于 Python 产品入口已测。
- [ ] 在 R reference 入口测试一个调用者提供的 `cl`：既能复用 worker，也不会替调用者关闭 cluster；用相同显式 worker RNG streams 对照原版。
- [ ] 在支持 fork 的平台测试一次原版 `parallel="multicore"` 路由；Windows 按原版平台能力报告限制，不能伪装其拥有 Unix fork。

Hybrid 已明确拒绝多 worker 调度。用户允许有说明的 CPU 过渡路径，所以这些功能可以通过 reference 完成；**不把 GPU 多副本调度器作为新造出的首版阻塞项**，但 API/文档必须告诉用户使用哪一条路线，不能静默切引擎。

### G5：完成 GPU 的统计质量验收

- [ ] 复用已经定义的 MCAR/MAR 数据生成和种子，增加原版 R、hybrid CPU64、所发布 GPU/dtype 的并列推断检查；至少沿用现有各 200 次的初筛预算。报告偏差、pooled SE、覆盖率、区间宽度及 Monte Carlo 误差，并在运行前固定可接受差异。已有 400 次 native CPU64 模拟不能证明 GPU 或原版对照等价。
- [ ] 增加一个高相关/较高缺失率的小型压力案例，保留不收敛、伪逆、autopri、非有限输出和 OOM 状态。既有三个 MPS 固定公开案例是精度证据，不足以替代推断质量或压力记录。

不要求在首版穷尽任意数据机制，也不把 1,000 次模拟建议或 MNAR 拓展升级为新的硬性要求。负面速度结果、有限适用范围和明确失败都是可接受研究成果；伪装通过不是。

### G6：关闭用户要求的平台实测缺口

- [x] Linux/macOS/Windows hosted CPU CI 已实际通过：开发代码安装、R 源码包/C RNG helper 编译及Python与五组R测试，见[CI证据](validation/2026-09-23-development/cross-platform-ci.md)。单独构建wheel还需各平台扩展打包矩阵；本地wheel smoke已通过。
- [ ] 用户 RTX 3080 到机核验：记录实际驱动/runtime/显存，执行 CUDA64/CUDA32 正确性与质量检查；在**同一 Windows 机器**完成原版 R 串行/合理 snow、Torch CPU64/CPU32 与 CUDA 对照。Mac 与 Windows 的耗时不能拼成 GPU 加速比。
- [ ] 没有 CUDA 的 Windows hosted runner已验证 reference 与 CPU 路线；仍需一个 Intel Mac 验证不装 Torch 的 reference 安装/拟合。若暂时没有机器，状态继续标“未实测”，不能写成所有 Windows/Mac 已支持。Linux CUDA 若未测，应同样单列，而非由 Windows CUDA 自动推断。
- [ ] 已安装包在 RStudio 实际会话跑一次数据框插补、检查解释器选择、展示/保存结果和一个诊断图。当前 Rscript、headless PDF 与包检查不能替代这一用户流程。

### G7：收尾三组大数据与产品耗时证据

- [ ] 正在运行的 hybrid 套件完成后，独立核验完整任务网格、每份收敛/有效质量、种子、warmup/正式次数、代码哈希与设备记录。先审计再汇总，保留失败/慢速结果，不能仅用进程 exit 0 判成功。
- [ ] 报告各路径计时边界：目前 native 和 R hybrid 主计时均排除 CSV 读取、评分/保存；Python front door 还包含 Rscript、二进制传输和 RDS。至少以一个已准备的大输入测 Python reference/hybrid 的完整用户调用，并单列冷启动；未测前不把 R 内存中计时称为 Python 端到端速度。
- [ ] 在当前少数 block-MCAR 模式之外，用一个有界规模的独立逐格缺失输入检查模式数增长后的耗时/内存或明确失败。无需立即全量跑三个百万行数据集，但必须保留当前“10万行完整数值子集、少数模式”的适用限制。
- [ ] Windows GPU 测试记录实际内存需求/OOM；未测的峰值 RAM/VRAM 继续为 null，不能填 0 或声称已测。速度表解释 MPS/CUDA 相对本机 Torch CPU 和合理 R CPU 并行的结果，不能只挑有利基线。

“GPU 比原版快”是待检验命题，不是必须制造的正面结论。三组公开数据、小样本加可核验完整下载脚本的交付方案已获用户同意，不再要求把全部大文件提交 Git，也不把全量行数实验新增为发布前必做项。

### G8：以可复现开发成果公开，再按证据标记首版

- [ ] 将原版精确版本的安装/校验步骤、已批准许可证/来源、数据许可/下载哈希、复现命令和已审计结果放进用户授权的公开仓库；从干净目录按说明完成最小复现。无需额外等待 PyPI/CRAN 上架才可公开 GitHub 开发成果。
- [ ] 用最终证据更新兼容表和 README：逐条区分通过、明确转到 reference、未测/不支持；保留上游已知特例和 GPU 适用边界。首版标签应等上述适用验收项关闭，不能因 128 个现有测试或 `R CMD check` 成功就自动签发。

本文件只列本次盘点发现的有限缺口。后续关闭项目时应附对应测试/报告，而不是将清单扩大为无穷参数笛卡尔积；任何与这里重复的已测证据可以直接引用并勾选。
