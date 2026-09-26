# 开发路线与验收

用户目标：为求职展示完成项目的能力，在忠实复现 Amelia 1.8.3 流程与算法的前提下实现 Python/PyTorch 包，研究 GPU 是否真实加速，并让不同平台研究者从 Python 和 R/RStudio 调用。2026-09-23 已进入实现阶段；**native 连续数值子集及原版 R 过渡兼容接口可用，完整验收仍是目标**。逐项状态以 [兼容表](amelia-compatibility.md) 和 [开发验证记录](validation/2026-09-23-development/README.md) 为准。

已确认产品决策：完整兼容验收后才算首版；允许明确标注的 R 过渡依赖；项目分发名为 `amelia-torch`，许可证为 `GPL-3.0-only`；维护者为 Sheng Wan（`swan0624@uw.edu`）；仓库包含可分享小样本及完整数据下载脚本；GitHub 用户名为 `Tocqueville0624`。[公开开发仓库](https://github.com/Tocqueville0624/amelia-torch)已建立。用户后来授权直接在云端 CUDA 机器测试并留存记录，不再依赖本地 RTX 3080；正在使用免费 Colab T4。其他已确认决定不再作为阻塞项。

## M0：调研与初始化（已完成）

- 完成官方资料与相关项目核对，记录可行性及风险。
- 建立 Python 包目录、设备检查、基础测试、R 桥接示例、依赖版本快照与本地 Git。
- 验证 CPU/MPS 基础算子、R 原版 smoke 和 R→Python→GPU 链路。
- 初始环境验证保存在 `docs/validation/2026-09-23/`；当前算法实现进展见 M1/M2，初始 CUDA 到机及 R 包状态仅属当时快照；当前进展见 M3/M4。

## M1：CPU 参考实现与连续数据 EMB（主体已实现，完整验收未完成）

- 已有固定到 Amelia 1.8.3 的 [算法契约](algorithm-contract.md)、源码来源记录、兼容表和可重建 R 参考样例。
- 已实现多元正态条件矩、分缺失模式 EM、初值/迭代限制/经验先验、连续数据标准化、bootstrap、随机条件补值及原始尺度恢复。公共入口为 `amelia_torch.amelia()`。
- CPU float64 已通过 R 参考样例的单步/收敛参数和显式随机输入补值对照；公共接口测试验证观察值保留、顺序与尺度恢复、种子可重复及全缺失行语义。
- 低层 cell prior 已有参考对照，但公共 prior 坐标转换、类别、变换、边界、时间结构等未完成；不支持的公共选项明确报错。
- 剩余验收：扩展兼容边界测试，并将已有 CPU64 的 400 次 MCAR/MAR 偏差/覆盖率/Rubin pooling 初筛扩展到原版与所发布 GPU 路线；许可与来源文件已公开。数值测试通过不能替代统计质量验收。

## M2：GPU 原型与瓶颈分析（进行中）

- 已有显式 device/dtype 和 MPS 计算路径；CPU float64 为参考，MPS float32 为实验。三个小型 EM 参考样例已在本机 MPS 上通过，不能据此宣布完整质量或性能成功。
- 三组公开数据的下载、来源与处理流程已建立，见 [数据说明](datasets.zh-CN.md)。数据交付采用小样本加完整下载脚本。各10万行数值子集的 native 与完整 R 混合正式基准已完成并独立审计；性能结果以验证记录为准，本路线文档不重复速度数字。
- Mac 同机已完成 R 串行/并行、PyTorch CPU/MPS 以及完整 R 混合入口比较，包含标准化、传输、随机补值、输出恢复与混合入口的 R 桥接开销。下一步在同一 CUDA 云主机复现。Python直接调用耗时不能冒充 R 端调用耗时。
- 验收：误差与统计质量门槛通过，解释优势和弱势场景、收敛差异与内存限制，再据真实瓶颈决定缓存、批量计算与设备驻留优化。

## M3：云端 CUDA 及跨平台验证（进行中）

- 核验驱动、显存、wheel 与实际 CUDA 算子；同机运行 R 串行/并行、PyTorch CPU 与 GPU。
- CUDA float64/float32 分别验证；Windows 无CUDA安装和 Linux CPU 也需独立运行。三个操作系统的 hosted CPU CI 已实际通过，Windows包亦已用Rtools编译；不能替代 CUDA 或所有系统配置的到机测试。云端 Linux CUDA 与 Windows CPU 的证据分开报告，不冒称 Windows GPU 已测试。
- 2026-09-26 已从保存的 Colab notebook 恢复旧会话输出：149 项 Python、五组 R 及 CUDA32/64 native/hybrid 固定案例通过；Ruff 二进制缺失阻止了后续性能实验，旧 VM 临时 JSON 未保存。现已修复环境恢复逻辑并重连 T4，下一轮须重新保存结构化记录。
- 保存完整结果、配置与绘图脚本，做可重复的端到端演示。
- 验收：明确是否加速、在哪些配置加速、超过哪个基线；负面结果也保留。

## M4：R 接口、完整兼容与作品集交付（本地包可安装，未正式交付）

- 已建立 R 包骨架和 [源码接口](r-interface.md)：延迟初始化、显式解释器选择、设备检查、自有结果类及参数别名。Mac 上真实 R→Python CPU32/64 插补、matrix/data.frame 名称与观察值保留、全缺失行和大seed诊断测试已通过。
- R 维护者、名称和许可证元数据已更新；Mac R 4.5.3 安装、源码构建及全部七个 R 包测试文件通过（2026-09-26），最终 `R CMD check` 为零错误、零警告、零NOTE，见[更新后的包检查记录](validation/2026-09-26-g1/packaging.md)。官方下游摘要、诊断图、pooling、CSV导出、arglist/追加/molists和allthetas已有小型CPU对照；已安装包的 RStudio 会话和完整类型/模型边界均未验收。
- 已获准实施保留原版 R 预处理/抽样/输出的过渡方案。纯官方CPU入口 `amelia_compat(engine="reference")` 已通过官方结果及R RNG逐值一致对照；实验性 `amelia_torch_compat()` 已通过变换、类别、先验、边界、overimputation和panel组合的CPU float64代表案例。后者只替换EM，不修改 Amelia namespace，当前限定串行副本调度。完整兼容仍待验收；Python到R参考桥另行验证。
- 2026-09-26 新增 G1 下游工作流及 G2 的 33 个 CPU 公共边界案例；显式 double startvals 原位更新已复现，integer/完整样本例外与后续 RNG 也已对照。当前本机 161 项 Python 测试通过，完整验收缺口见 [release-gates](release-gates.md)。
- 完整功能必须逐项对照后才计入首版验收。已有 CI 配置、兼容表、实验代码和数据说明；已在确认的 `Tocqueville0624` 账号公开开发仓库；下一步扩展接口边界和 GPU 验收。公开开发仓库不等于首版验收完成。
- 用户应能解释一个条件矩计算、一个数值难点、一个性能瓶颈、一个失败实验和一次设计取舍，避免只展示生成的代码量。

## 经本轮验证的后续注意项

- 全缺失分析行已加入专门测试：与原版一致，排除拟合但保留缺失输出；不能为了“补满”擅自改动。全缺失列仍明确拒绝。
- sandbox 中 MPS 不可见不等于硬件不支持；必须记录实际运行上下文。
- reticulate 需指向虚拟环境解释器，不能解析最终可执行文件符号链接；仅规范化父目录可避免 `./.venv` 重复调用误判。
- reticulate 自动转换 Python 大整数会截断 seed 诊断；R桥接已改为显式转换并核对原始值。相同 R/Python seed 仍不代表相同随机输入。
- R混合路径需分别保留C内部RNG与R可见`.Random.seed`：只保存R变量会在`boot.type="none"`多份插补时重复draw。注册C snapshot/restore桥已修复，并通过Inversion/Box-Muller、最终seed、后续runif/rnorm对照；源码安装需要C工具链。
- 后续 Agent 完成阶段后更新这里和验证记录；`AGENTS.md` 只保留稳定约束与当前阶段，详细结果放文档。
