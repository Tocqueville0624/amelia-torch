# 发布标准

[English](release-gates.md) · [文档目录](README.zh-CN.md)

状态日期：2026-09-27。首个完整版本可由原版 R 参考、混合及原生子集共同提供功能，但须明确依赖和执行边界。原版 R 绘图无需重写为Python，委托 CPU 功能不得称作原生 GPU 实现。当前公开快照尚未完成验收。

## 接口范围

原版导出包括 amelia/default/molist、ameliabind、transform.amelia、with.amelia、mi.combine、mi.meld、moPrep、compare.density、overimpute、disperse、tscsPlot、missmap、write.amelia、AmeliaView；注册方法另含追加、print/summary 及 plot。内部allthetas不是 amelia.default 公共参数。参数状态见[兼容表](amelia-compatibility.zh-CN.md)。

## 验收记录

| 项目 | 已完成的有界范围 | 剩余要求 |
|---|---|---|
| G1 下游方法 | 合并/错误、transform 后追加、with/lm 及 mi.combine 两种区间设置、moPrep四分支、summary/plot、CSV/table/DTA 读回、实际Python/RDS/R 示例 | 方法仍是原版 R CPU；保留区间/p 值特例；PDF 文件检查与视觉检查区分 |
| G2 公共 EM 边界 |33 个 CPU64 案例：初值/回写、最少/最多迭代、完整 bootstrap、实际拒绝重抽、bounds 耗尽、全空行和原版错误码；Mac 病态 autopri；八项 MPS32 断言 | 同脚本CUDA32/64 尚未执行；Mac 病态输出/状态有差异，不算质量成功；Linux/Windows 未触发分支仍未覆盖 |
| G3 类型与会话 | 数值/noms 拟合与 RDS；nullable 空 ID、Unicode、重复 index；不支持类型和缺依赖明确失败；中文/空格路径；frontend 拒绝 | 不承诺通用 Arrow/扩展类型/交互 GUI；原版 RDS 为权威 |
| G4 原版并行 | Python snow2库继承/重复/worker 错误；R caller cluster 及后续 RNG；Unix multicore | 混合仍串行，Windows 跳过 Unix fork、使用 snow；不新增 GPU 副本调度器为首版前置条件 |
| G5 推断 | Mac 五路线 2,100 调用/10,500 拟合均收敛，MAR 与有界压力通过 | MCAR冻结标准未全通过，CUDA方案未执行，不标验收完成 |
| G6 平台和交互 | `ef729c0`三平台各 307 项Python、九个 R 文件和示例；Intel 无 Torch 隔离参考 wheel；Mac 已安装包RStudio；T4/3080 固定CUDA和性能 | 新CUDA边界/推断未完成；Windows GUI 和原版AmeliaView未测；源码安装与隔离 wheel 范围不同 |
| G7 性能 | 三组 100k 行：Mac 原生/混合、Windows 18+12 配置完整；T4 原生 18 完整、混合 11/12；另有Python完整调用与独立MCAR压力 | 总进程 RAM/VRAM及容量/OOM 极限未测；保留 null、低维慢速及 T4 部分状态 |
| G8 可复现分发 | 固定原版来源/哈希、GPL归属、许可样本/下载、脚本和审计记录公开 | 适用剩余项关闭后再更新最终声明；尚无完整版本标签、PyPI/CRAN发布 |

## 统计限制

Mac G5 依据冻结方案，未按结果修改阈值。原版 R 和混合MCAR覆盖率 90%区间上界 99.009876%，略超 99%；原生配对下界−5.028703 个百分点，低于−5。CPU/MPS 分类一致。记录审计有效不等于统计验收通过。独立 1,000 次MCAR提案未执行，不自动增加要求或替代未通过结果。

保留原MCAR/MAR 生成器、种子、至少 200 次初筛预算及预设偏差/覆盖率/宽度/蒙特卡洛比较。包含有界高相关/高缺失压力及全部未收敛、伪逆、校正、非有限和 OOM 结果。不要求遍历所有参数组合，也不要求制造正面 GPU 结论。

## 产品与计时边界

Windows `810591e` 的 210 调用/1,050 插补通过有限质量审计，不完成 G5。T4 缺失的 YearCUDA32 保持未知，替代主机失败不补齐旧套件。

G7 Covertype 100k 的Python reference/hybrid CPU64完整调用含新 Rscript、二进制/RDS 传输：首次约 12.144/11.966 秒，后续各两次的中位数 11.959/12.128 秒。未清空 OS 缓存，不能与旧 R 内存计时相减为桥接成本。Household 5000×7 独立MCAR保留两条全空行，每份 14 个 heldout 未评分；尽管收敛，RMSE为 null、状态 heldout_incomplete、exit 1，属于压力记录，不是质量成功的加速样本。

普通RStudio调包不意味着重写或 GPU 化AmeliaView。若列为已验证功能，须在适当 Tcl/Tk 环境实际记录原版 GUI 启动/载入/关闭。当前 Mac Data Viewer/图形证据与其分开。

## 证据链接

[G1](validation/2026-09-26-g1/downstream-extended.zh-CN.md) · [G2](validation/2026-09-26-g2/README.zh-CN.md) · [G3](validation/2026-09-26-g3/README.zh-CN.md) · [G4](validation/2026-09-26-g4/README.zh-CN.md) · [G5](validation/2026-09-26-g5-mps/README.zh-CN.md) · [G6](validation/2026-09-26-g6-rstudio/README.zh-CN.md) · [G7](validation/2026-09-26-g7/README.zh-CN.md) · [Windows](validation/2026-09-27-windows-rtx3080/README.zh-CN.md)。

关闭验收项须附实际报告和源码身份，复用已有充分证据。完整原包无需进入 Git，带归属样本和固定下载脚本符合数据交付设计。当前证据整理阶段不安排新增拟合或测试预算。
