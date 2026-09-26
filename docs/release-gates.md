# 首版验收缺口：Amelia 1.8.3 功能与产品边界

初次审计日期：2026-09-23，正式 hybrid 性能实验开始后，初审仅做源码与接口盘点。2026-09-26 补充 G1 小型 CPU64 实测及独立 Python/R 示例，具体范围见下方证据。下列未勾选项是可执行的剩余验收任务，不是已发现算法均错误，也不是要求遍历任意参数组合。

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
| `ameliabind` | G1 已直接合并两个兼容结果、保留每份旧数据；不同 missingness/model arguments 返回原版错误；合并 RDS 无 backend 时 Python 保持 unknown | 仍沿用原版仅检查 missingness/arguments 的限制，不声称检查所有原始数据值 |
| `transform.amelia` | G1 已测派生列、`missMatrix`、`transform.calls`、旧份数据不变；RDS 跨 Python/R 后继续追加 | 使用原版 R CPU 方法，没有移植为 native Python 方法 |
| `with.amelia`、`mi.combine` | G1 已对照 `with(fit, lm(...))` 及 `conf.int=FALSE/TRUE, conf.level=.90` 全部返回列；broom 可用及缺失探测分支已测 | 原版 1.8.3 区间端点倒序、带符号上尾 p 值行为明确保留；不能把兼容对照当成这些值的统计正确性证明 |
| `mi.meld` | 原版/混合结果和手算 Rubin SE 已比对 | 已有核心证据；与 `mi.combine` 区别写清，不重复声称另一种自由度修正已验证 |
| `moPrep`；S3 default/molist | 已测 `error.sd`、局部 caller、自包含 RDS；G1 又测 `error.proportion`、`subset/gold.standard`、proxy formula、已有 molist 增补及 prior/overimp 档案 | 指定有限分支已覆盖；保留原版错误检查与统计公式 |
| `compare.density`、`overimpute`、`disperse`、`tscsPlot`、`missmap` | 小数据 numeric return 对照及 PDF 文件检查已通过；`disperse` 继续执行官方 CPU EM | 无需重写为 GPU；RStudio 中人工确认至少一张图正常显示，不能把 PDF 魔数/大小检查称为视觉检查 |
| S3 `print.amelia`、`summary.amelia` | 输出文本对照通过 | 已有证据 |
| S3 `summary.mi`、`plot.amelia` | G1 已直接对照 summary 表与文本；plot 的 compare/overimpute 分支均生成 PDF 并清理设备 | 文件检查不等于 RStudio 图形视觉验收，后者仍在 G6 |
| `write.amelia` | CSV 及 G1 table/DTA 均读回核验；combined `orig.data=FALSE`、自定义 `impvar`、factor 标签/行数均通过 | `sep` 转发需显式 `separate=TRUE` 避免 R 部分匹配；DTA caller 显式绑定 `foreign::write.dta` |
| `AmeliaView` | 未启动、未测试 | 这是原版 R/Tcl/Tk GUI。若对外列为可用功能，在可用图形环境做一次官方启动/载入/关闭检查并明确其仍走原版 CPU。用户要求 RStudio 调包，不自动产生重写 GUI 或给原版 GUI 注入 GPU 的新需求 |

`amelia.default` 的实际 formals 包括：`x, m, p2s, frontend, idvars, ts, cs, polytime, splinetime, intercs, lags, leads, startvals, tolerance, logs, sqrts, lgstc, noms, ords, incheck, collect, arglist, empri, priors, autopri, emburn, bounds, max.resample, overimp, boot.type, parallel, ncpus, cl, ...`。`allthetas` 是内部 EM/诊断接口，**不是** `amelia.default` 的同名公开参数；已有内部格式对照不能宣称公共函数新增了此参数。

## 可关闭的首版验收任务

### G1：公开下游工作流（指定本机例子已完成）

- [x] `downstream_extended.R` 在本机 CPU64 完成 direct bind、transform 后追加、with/pooling、moPrep 四分支、summary/plot、table/DTA 对照；不增加大规模模拟。
- [x] 独立 [Python/R 示例](../examples/README.md) 在 reference 与 CPU64 hybrid 两模式均实际完成 save_rds → R 变换/追加/绘图/导出 → Python 读回，并核对派生值及旧份数据。
- [x] 示例安装说明列出 broom/rlang/foreign/TclTk；broom 可用分支实际通过，缺失分支以私有依赖探测环境触发原版明确错误，没有卸载或修改安装的 namespace。

证据与边界：[G1 回归记录](validation/2026-09-26-g1/downstream-extended.md)。这是小型公开方法验收，仍不等于 GPU 推断质量、GUI、跨平台新增测试或完整首版验收；新 CI 配置只有真实运行后才能记为通过。

### G2：封闭混合公共入口的核心边界（本机 CPU64 已补，GPU 待测）

2026-09-26 新增 33 个公共 CPU64 案例与独立病态 autopri 审计，证据见 [G2 回归记录](validation/2026-09-26-g2/README.md)。这些检查使用实际公共 pipeline；不以 low-level fixture 代替公共入口，也不扩大为全部参数组合。

- [x] 默认、`startvals=1`、double/integer 显式 theta；m=2 ordinary/none、调用者/存档 alias、arglist/追加与 allthetas 初列实测。修复原版 double 初值原位覆盖副作用，同时保留 integer coercion 例外。`emburn` 最小 35/最大 2 轮及未收敛 warning/metadata 通过。
- [x] 固定 complete bootstrap 和全缺失列拒绝重抽输入，私有记录器保存实际抽样索引；未修改原版 namespace，记录版输出与未插桩公共调用一致。sample-covariance shortcut 及初值不变行为通过。
- [x] 固定 public exact-collinear 病态输入，本机原版/混合均触发 autopri；逐更新后的单步公式验证固定初始 hold=0。最终近零特征值令原版 code 2、混合 code 1，但混合正确记录未收敛；保留差异与全部失败状态，不算有效质量样本。其他 BLAS 若未触发则须记录未覆盖，不能由本机轨迹推断逐平台严格一致。
- [x] 极窄远端 bounds、`max.resample=1` 实际产生 9 个边界夹值；0 被原版错误码 52 拒绝，均通过公共入口对照。
- [x] 全缺失分析行保持 NA；无缺失默认 code 39 与 `incheck=FALSE` shortcut；全缺失列/常量/样本量不足的原版错误码 4/43/34 对照通过。
- [x] `incheck=FALSE`、`collect=TRUE`、`p2s=1/2` 各自与原版统计结果对照；混合进度文字明确标 PyTorch，不宣称逐字符一致。原版 `incheck` 消耗随机数的行为保留。
- [ ] 在发布支持的 GPU 精度下对新增初值/迭代边界与病态状态做有界验证；CPU64 的通过不能代替该项。

单行 priors 改动无关观察值、log 逆变换及 stale `.Random.seed` 都是已核验的原版版本行为，见[算法契约](algorithm-contract.md)。以上验收不能以偷偷修改这些行为来让测试变绿；修正版应另命名/另决定，不能混进兼容模式。

### G3：固定 Python/R 类型与会话边界（本机有限例子已完成）

- [x] reference/hybrid 各完成纯数值及含 noms 两种真实拟合/RDS 往返：全缺失 nullable integer/string ID、非 ASCII 列名/类别、重复 Python index；另跑独立未改动 R Amelia 对照。原版 integer ID→double、特定 noms 组合空字符 ID→字符串 `"1"` 的行为如实保留；RDS 不伪造 Python 重复 index。
- [x] datetime、complex、混合 object、SciPy sparse 各有明确拒绝例；外部 RDS 的 Date/自定义数值类保留在权威 RDS 中，Python view 明确只给普通字符串/数值。Arrow 没有独立验收或通用支持承诺；若将其列为支持输入，须另补一个实际代表例，不扩大为所有扩展 dtype 的组合。
- [x] 不存在 Rscript、错误 Amelia 版本、缺少 hybrid R DLL/Torch、不可用 CUDA 均明确失败；带中文/空格的实际 venv 与 R 库完成 hybrid 拟合。缺 Torch 使用子进程故障注入，路径 venv 复用已有依赖，这些不冒称干净安装；真实无 Torch wheel 安装见 G1 和下方 Intel Mac 证据。
- [x] Python reference/hybrid、extend、RDS/arglist 前门明确拒绝 `frontend=True` 及非布尔 False 参数，启动 R 之前即说明需用原版交互式 R/Tcl/Tk 会话；正常 False 流程不变。测试禁止任何子进程启动验证拒绝路径，没有启动或视觉验收 GUI。

证据：[G3 记录](validation/2026-09-26-g3/README.md)：新增 29 项与现有 24 项 reference/hybrid 回归共 53 passed。新 frontend 修复与 G3 边界已在 `e2ff892` 三平台 CI 通过；交互式 RStudio/AmeliaView 仍属于 G6 的未测范围。

R `moPrep` 默认保存调用表达式而非数据。跨进程必须使用已物化数据的自包含 RDS；现有测试和文档已经说明。Python-only index/扩展 dtype 不写入原版 RDS、重新读盘默认追加走 reference、hybrid 原对象 `extend` 保持原引擎，也都是已明确的产品契约，不应被误记成算法缺陷。

### G4：验证明确选择的并行 CPU 过渡路径（本机小例通过）

- [x] Python 产品入口 snow2 / L'Ecuyer-CMRG 实测 m=3，显式 R 库、开发默认库和正常 R_LIBS_USER 继承三条路线逐值可重复；实际 worker R 异常传播为 AmeliaReferenceError。不是用原版 benchmark 的 snow4 代替。
- [x] R reference 入口 supplied-cl 复用相同两个 worker，完整结果及 worker 后续 RNG 对照原版；调用后 cluster 仍存活，最后由调用者关闭。
- [x] 本机 Unix multicore 2-worker 路由对照原版逐值通过；测试在 Windows 明确记录不运行 fork，使用 snow/serial 路线。

证据：[G4 并行回归记录](validation/2026-09-26-g4/README.md)。这些新增测试已在 `e2ff892` 三平台 CI 通过；Windows 明确不运行 Unix fork，实际使用 snow。

Hybrid 已明确拒绝多 worker 调度。用户允许有说明的 CPU 过渡路径，所以这些功能可以通过 reference 完成；**不把 GPU 多副本调度器作为新造出的首版阻塞项**，但 API/文档必须告诉用户使用哪一条路线，不能静默切引擎。

### G5：完成 GPU 的统计质量验收

2026-09-26 Mac 正式五路线执行和独立审计已完成：全部 2,100 次多重插补调用、10,500 次拟合收敛，MAR 全部通过、压力案例全部有效；**MCAR 预设区间门槛未全通过，因此本节不勾为完成**。原版 R 与两条 hybrid 的覆盖率上界为 99.009876%，native 相对 R 的配对差下界为 -5.028703 个百分点；分别略超 99% 和 -5 个百分点的冻结门槛。CPU/MPS 结论一致。完整记录见 [MPS 正式报告](validation/2026-09-26-g5-mps/README.md)。独立补充方案仅为待用户选择的提案，不能自动扩大预算或覆盖旧结果。

- [ ] 复用已经定义的 MCAR/MAR 数据生成和种子，增加原版 R、hybrid CPU64、所发布 GPU/dtype 的并列推断检查；至少沿用现有各 200 次的初筛预算。报告偏差、pooled SE、覆盖率、区间宽度及 Monte Carlo 误差，并在运行前固定可接受差异。已有 400 次 native CPU64 模拟不能证明 GPU 或原版对照等价。
- [ ] 增加一个高相关/较高缺失率的小型压力案例，保留不收敛、伪逆、autopri、非有限输出和 OOM 状态。既有三个 MPS 固定公开案例是精度证据，不足以替代推断质量或压力记录。

不要求在首版穷尽任意数据机制，也不把 1,000 次模拟建议或 MNAR 拓展升级为新的硬性要求。负面速度结果、有限适用范围和明确失败都是可接受研究成果；伪装通过不是。

### G6：关闭用户要求的平台实测缺口

- [x] Linux x64/macOS arm64/Windows x64 hosted CPU CI 在 `e2ff892` 已实际通过：开发代码安装、R 源码包/C helper 编译、各 235 项 Python 与九个 R 测试文件及下游示例，见[CI证据](validation/2026-09-26-ci/cross-platform-ci-e2ff892.md)。Linux/Windows 原版病态 autopri 未触发，分支覆盖须单列；单独 wheel 安装仍需与源码安装分开记录。
- [ ] 云端 CUDA 核验（用户已授权替代本地 3080）：记录实际系统/驱动/runtime/显存，执行 CUDA64/CUDA32 正确性与质量检查；在**同一云端 GPU 机器**完成原版 R 串行/合理 snow、Torch CPU64/CPU32 与 CUDA 对照。Mac 与 Windows 的耗时不能拼成 GPU 加速比。
- [x] 无 CUDA 的 Windows hosted runner已验证 reference 与 CPU 路线；Intel Mac 在 `ad9bed2` 的独立任务实际核验 x86_64、隔离 wheel[reference]、Torch 未安装、原版拟合与 Python/R 下游往返，见[Intel 证据](validation/2026-09-26-ci/intel-mac-reference.md)。这不代表 Intel hybrid/Torch、交互式 GUI 或任何 CUDA 路线已测；GPU 仍由上一项单独验收。
- [ ] 已安装包在 RStudio 实际会话跑一次数据框插补、检查解释器选择、展示/保存结果和一个诊断图。当前 Rscript、headless PDF 与包检查不能替代这一用户流程。

### G7：收尾三组大数据与产品耗时证据（本机有界范围已完成）

- [x] 三组各 10 万行的 hybrid 主套件已完成并独立审计：9 配置、63 次调用、315 份插补，完整计划、每份收敛/有限 heldout/观察值、seed/m、2 次预热和 5 次正式重复、源码与后端记录均通过；见[原始记录与审计](validation/2026-09-23-development/README.md)。MPS32 比同机 hybrid CPU32 慢约 13%–33%，保留负面结果。
- [x] 另测 100000×10 Covertype Python reference/hybrid CPU64 完整公开调用，包含新 Rscript 启动、typed transport 和 RDS 字节回传；各 1 次首次及 2 次后续调用、m=5。首次约 12.144/11.966 秒，后续中位数 11.959/12.128 秒。每次均新 R 进程，未清空 OS 缓存；旧 R 内存计时不能硬相减为桥接开销，也不把首次称为冷 OS 测量。
- [x] 5000×7 独立 MCAR 输入的 125 种模式已原样实测 reference/CPU64/MPS32 各一次 m=5。所有拟合收敛且保留观察值，但原版规定的两条全空行令每份 14 个 heldout 未评分；完整 RMSE=null、质量状态 heldout_incomplete、执行器 exit1，全部保留为压力结果，不算质量成功加速样本。峰值内存未测为 null。
- [ ] CUDA 测试记录实际内存需求/OOM；未测的峰值 RAM/VRAM 继续为 null，不能填 0 或声称已测。速度表解释 MPS/CUDA 相对本机 Torch CPU 和合理 R CPU 并行的结果，不能只挑有利基线。

新增有限测量的预定计划、九次全部结果、独立审计、源码快照与边界见 [G7 记录](validation/2026-09-26-g7/README.md)。纯评分/审计测试与 G2/G4 R 测试已在 `e2ff892` 后续 hosted 运行验收，平台分支覆盖限制见 CI 记录。以上不外推至高维逐格 MCAR 或全量数据。

“GPU 比原版快”是待检验命题，不是必须制造的正面结论。三组公开数据、小样本加可核验完整下载脚本的交付方案已获用户同意，不再要求把全部大文件提交 Git，也不把全量行数实验新增为发布前必做项。

### G8：以可复现开发成果公开，再按证据标记首版

- [x] 原版精确版本安装/校验、GPL 来源、数据许可/哈希、复现命令及已审计开发结果已公开。`e2ff892` 全新三平台 runner 完成源码安装/编译及公开示例；Intel 独立隔离 wheel[reference] 完成无 Torch 最小复现。二者覆盖范围分开记录，不声称所有安装组合或 PyPI/CRAN 已发布。
- [ ] 用最终证据更新兼容表和 README：逐条区分通过、明确转到 reference、未测/不支持；保留上游已知特例和 GPU 适用边界。首版标签应等上述适用验收项关闭，不能因 128 个现有测试或 `R CMD check` 成功就自动签发。

本文件只列本次盘点发现的有限缺口。后续关闭项目时应附对应测试/报告，而不是将清单扩大为无穷参数笛卡尔积；任何与这里重复的已测证据可以直接引用并勾选。
