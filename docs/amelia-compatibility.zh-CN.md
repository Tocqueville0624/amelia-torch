# Amelia 1.8.3 兼容性

[English](amelia-compatibility.md) · [文档目录](README.zh-CN.md)

状态日期：2026-09-27。当前为开发快照，不是完整替代品。reference 指 CPU 上未修改的 R Amelia；hybrid 保留其流程、替换 EM；native 是连续数据实现。版本语义见[算法契约](algorithm-contract.zh-CN.md)。

| 功能 | 原生路线 | 混合/原版参考证据及限制 |
|---|---|---|
| 标准化、条件矩、EM、对称 theta | 已实现，CPU64 原版样例对照 | 混合 CPU64 公共参数/history 对照 |
| `startvals=0/1`、显式 theta | 已实现，不修改原生输入 | ordinary/none m2 已测；保留 double 更新、integer 转换、归档别名及初始 history |
| 完整 bootstrap 特例 | 样本协方差 n−1，忽略 empri/theta | 公共实际抽样已测；history NA、不回写初值 |
| `tolerance`、`emburn` | 上三角规则、最少/最多迭代 | 最少 35 轮、最多 2 轮已测，警告/元数据区分未收敛 |
| `empri`、`autopri` | 整数截断、p+2 分母、固定初始 hold | Mac 公共 CPU64 实际触发；病态轨迹/状态有差异，不算有效质量样本；Linux/Windows 原版未触发该分支 |
| 低层 cell priors | 支持标准化均值/方差 | 原版预处理提供坐标，已有代表性 CPU/MPS 案例 |
| 公共四/五列 priors、row 0 优先级 | 不支持 | 原版预处理代表案例通过，保留单行上游特例 |
| ordinary、`boot.type="none"` | 支持，Python 为 `boot_type`，使用 NumPy RNG | 公共拒绝重抽与 R RNG 两层状态已测，含 Inversion/Box–Muller 及后续抽样 |
| 条件随机补值 | 显式正态输入样例通过 | 保留原版 R/C 抽样 |
| 观察值、顺序、全空行 | 保留；全空行仍缺失 | 公共/G3/大数据检查，保留已记录的上游特例 |
| 空列/单观察值/常量、无缺失输入 | 明确校验，含 code 4/43/39 | 有界公共 code 4/43/34/39 和关闭检查后的完整输入已测 |
| `idvars`、`logs`、`sqrts`、`lgstc` | 不支持 | 代表性 CPU64 案例，保留 log 逆变换特例 |
| `noms`、`ords` | 不支持 | factor/ordered factor 已测，使用原版随机类别恢复 |
| `ts`、`cs`、`polytime`、`splinetime`、`intercs`、`lags`、`leads` | 不支持 | 代表性面板/basis 案例，不覆盖全部组合 |
| `bounds`、`max.resample`、`overimp` | 不支持 | 公共案例；上限 1 时实际夹值 9 格，上限 0 为 code 52；边界抽样分布未验收 |
| `p2s` | 接受 0/1/2，进度格式不同 | 统计输出已测，进度明确标 PyTorch |
| `incheck`、`collect`、`arglist`、追加、molist | 不支持原版同名公共语义 | 已测有界组合，含 RNG 消耗、保存参数和局部 moPrep |
| `parallel`、`ncpus`、`cl` | 无公共副本调度器 | 混合仅串行；原版 Python snow2、R caller cluster、Unix multicore 已测；Windows 用 snow |
| 内部 `allthetas` | 独立矩阵 history 格式 | 原版上三角向量及初列已核对 |
| 官方 `amelia`/`mi` 类 | 独立原生结果 | 保留官方类并附后端元数据 |
| bind、transform、with/pooling、moPrep | 未移植 | G1 公共分支 CPU 已测，下游方法仍为 R CPU |
| summary/plot、density/overimpute/disperse/missmap/tscsPlot | 未移植 | 数值返回与 PDF 已查，Mac RStudio 有单独有限视觉记录 |
| CSV/table/DTA 导出 | 未移植 | 读回、factor 标签、合并输出、自定义 impvar、orig.data=FALSE 已测 |
| Python 类型桥接/RDS | 原生仅数组输出 | G3 有界类型/会话案例；不支持类型与 frontend GUI 明确拒绝；权威 RDS 保留原对象 |

## 平台证据

| 平台/任务 | 已记录结果 |
|---|---|
| Windows/macOS/Linux hosted CPU | `ef729c0` 每平台 307 项 Python、九个 R 文件和下游示例；不含 GPU |
| Intel Mac 原版参考 | `ad9bed2` 无 Torch 隔离 wheel、实际拟合和 RDS 流程；不承诺 Intel Torch/GUI |
| Mac MPS32 | 固定案例、八项公共边界断言、三组 100k 数据；慢于同精度 CPU |
| Linux T4 CUDA32/64 | 固定案例通过；原生/参考 18 配置完整；混合回收 11/12，最后 Year CUDA32 未知 |
| Windows RTX 3080 CUDA32/64 | 每精度三个原生、三个 R 固定案例；原生/参考 18、混合 12 配置完整，共 210 调用/1,050 插补 |
| RStudio | Mac 已安装包 reference/hybrid CPU64、保存读回、Data Viewer、诊断图；Windows GUI 和 AmeliaView 未验收 |
| Python 完整原版/混合调用 | G7 Covertype 100k 包括新 R 进程、二进制传输和 RDS 回传；不同于原生/R 内存计时 |
| 独立逐格 MCAR 压力 | G7 Household 5000×7 保留两条全空行，每份 14 个 heldout 未评分、RMSE null，不算质量成功计时 |

## 统计验收

Mac 五路线 G5 完成 10,500 次拟合，MAR 和有界压力检查通过；MCAR 绝对/配对覆盖率标准未全通过，其中包括原版 R 的一项标准。CUDA G5 和新增 CUDA 公共边界尚未完成。固定案例、低 RMSE 与拟合成功不证明分布等价。R `mi.combine` 区间/p 值特例作为兼容证据保留，不代表认可其推断正确性。

详细记录：[G1](validation/2026-09-26-g1/downstream-extended.zh-CN.md)、[G2](validation/2026-09-26-g2/README.zh-CN.md)、[G3](validation/2026-09-26-g3/README.zh-CN.md)、[G4](validation/2026-09-26-g4/README.zh-CN.md)、[G5](validation/2026-09-26-g5-mps/README.zh-CN.md)、[Windows](validation/2026-09-27-windows-rtx3080/README.zh-CN.md)、[摘要](validation/2026-09-27-evidence-summary.zh-CN.md)。

## 支持声明规则

不支持的参数明确报错。记录 R 依赖、CPU 工作、设备/精度、同步、失败、未收敛及伪逆。速度比较使用同机、同任务、同精度和相同计时边界，必要时包含接口成本。相同种子不能配对不同 RNG 库。仅依据实际执行且注明版本的证据扩大支持声明；成功安装不等于完整发布验收。
