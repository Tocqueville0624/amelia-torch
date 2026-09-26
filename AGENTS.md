# Amelia Project：后续 Agent 指南

## 用户目标与当前阶段
- 用户为求职展示项目能力，要求全部功能完成后才算首版，完整复现 Amelia 1.8.3 流程/算法，在 Python 与 R/RStudio 跨 Mac、Windows、有/无 CUDA 使用，并以三组较大公开数据实测性能；不能随意改变统计语义。
- 已授权安装必要程序、收集公开数据，并允许成果公开到用户 GitHub。已确认 GPL-3.0-only、名称 amelia-torch、维护者 Sheng Wan <swan0624@uw.edu>，允许原版 R 过渡兼容、小样本+全量下载脚本的数据方案。公开仓库账号已确认为 Tocqueville0624，用户确认 Windows 暂不能接入，已公开开发快照；后续授权直接使用云端 CUDA 测试并留存记录，不再依赖本地 3080。免费 Colab T4 的 CUDA32/64 固定正确性案例已在旧会话通过；9/26 已恢复旧笔记本并重连免费 T4，正式性能与统计质量仍待完成；Andrew Wang 只预留未来协作位，尚非当前作者。
- 2026-09-23：native 连续 EMB、Python/R 原版及混合兼容入口已实现；三个系统各 149 项 Python 测试与 5 个 R 测试文件通过，R 安装/build/check 零问题。Windows/macOS/Linux hosted CPU CI 已通过；尚未完整验收 Amelia 或完成 CUDA/Intel Mac实测。状态见 `docs/roadmap.zh-CN.md`、`docs/amelia-compatibility.md`。
- 2026-09-26：fa08a52 的三平台 hosted CI 各 161 项 Python、7 个 R 测试文件及下游示例通过，本机 R build/check 零问题；ad9bed2 的 Intel Mac x86_64 隔离 wheel[reference]、无 Torch 原版/RDS 工作流亦实际通过。新 G3/G4 边界及后续测试不算入这些历史通过。修复显式 startvals 的原版原位更新语义；Mac 三组 100k 样本的 native/hybrid 正式基准均完成，MPS 未比同机 Torch CPU 更快；旧测量源码哈希不得随修复改写。详见 `docs/validation/2026-09-26-ci/`、`2026-09-26-g1/`、`2026-09-26-g2/`。
- 新 T4 会话在 fa08a52 完成全部 15 步正确性验证；同机正式性能固定到 905cc79，正在运行。G5 统计门槛与各 200 次 MCAR/MAR、20 次压力方案已在 06b0fe8 固定，正式结果不得反向改变门槛；见 `docs/validation/g5-prespecified/`。仍不算完整首版验收。
- 三组 UCI 全压缩数据已下载、校验，合计约 232 MiB。数据来源/许可/哈希见 `data/manifest.json`；原始全量文件不进 Git，小样本和复现脚本已入项目。

## 环境与命令
- 使用 Python 3.12、uv、`.venv`；新增 R 包放 `.R-library`。Mac 快照 `requirements-macos-arm64.lock` 不用于 Windows CUDA；详见 `docs/setup.zh-CN.md`。
- R 基线固定 Amelia 1.8.3；本机 R 4.5.3、reticulate 1.47.0、torch 2.14.0。设备是 M4/16 GB；MPS 不支持 float64。
- Python：`.venv/bin/python -m pytest -q`；`.venv/bin/ruff check src tests scripts`。Windows Python 入口为 `.venv\Scripts\python.exe`。
- 参考 fixture：`Rscript scripts/export_reference_fixtures.R`；从未修改的 Amelia 生成。上游会原位修改 theta 参数，导出脚本须 deep copy。
- R 源码测试：`R_LIBS_USER="$PWD/.R-library" RETICULATE_PYTHON="$PWD/.venv/bin/python" AMELIATORCH_R_SOURCE=r-package Rscript r-package/tests/bridge.R`。
- 设备探针：`.venv/bin/python -m amelia_torch.diagnostics --require-device mps`；Windows CUDA 改 `cuda`。GPU 不可见先检查执行权限；sandbox 也可能阻止 R snow localhost socket。
- 数据、质量与基准复现入口见 `docs/reproduce.zh-CN.md`，验证产物放 `docs/validation/`；机器临时结果放忽略的 `results/local/`。
- Colab 每阶段在计时外保存完整 JSON/log 报告备份，见 `scripts/cloud_checkpoint.py` 与 `scripts/recover_cloud_checkpoint.py`。下载失效时可从保存 notebook 的压缩输出恢复；必须核验哈希，不把截断 stdout 当成原始 JSON。云主机按实测 CPU 配额统一线程/worker 预算，9/26 T4 VM 为两核。

## 算法与兼容性约束
- `docs/algorithm-contract.md` 是固定版本语义依据。每开放一项原版功能，都先建参考对照，再更新兼容表；不支持的选项明确拒绝，不能忽略后继续计算。
- 当前顺序：观察值标准化→bootstrap→条件矩及充分统计量 EM→对原始样本随机补值→恢复行列与单位。条件协方差不可丢弃；均值填充不是 EMB。
- 已观测值必须保留；Amelia 1.8.3 单行 priors 索引 bug 是已核验上游例外，兼容路径不静默修正，见算法契约。原版全空行移出拟合、最终仍为 NA；不能为了填满或计分而偷偷改变。全空列、少观察值、常量、病态和未收敛均需显式处理。
- 尊重原版初值、样本协方差分母、整数 empri、autopri 固定初始 hold、上三角收敛规则与完整 bootstrap 样本特例；不要未经论证“修正”原版行为。
- 显式 double `startvals` 在原版 C EM 中原位更新，影响调用者、归档与后续多份插补；混合路径的注册 C writeback 必须保留。integer 初值与完整 bootstrap 样本不回写；先保存 allthetas 初列。native Python 仍不改输入。
- 同一 seed 不保证 R/NumPy/GPU 相同抽样；确定性对照使用显式随机输入，分布与推断质量另行验证。native RNG 为 NumPy PCG64，兼容路线使用原版 R RNG。
- CPU float64 是数值参考。MPS/CUDA float32 必须显式选择并过独立质量门槛；不静默降精度、加 ridge 或裁剪协方差。
- MPS 的特征值诊断在 CPU 明确执行并记录，属于混合路线。fallback=0 不能独自证明纯 GPU；记录设备、dtype、伪逆、CPU工作、迭代、失败与内存。
- R 混合 EM 调用必须保留 C 内部 RNG 和可见 `.Random.seed` 两层状态；上游 C++ 抽样可能不刷新后者。注册 C helper 已通过 boot.none 多份抽样、Inversion/Box–Muller 与后续 RNG 回归，不能删为简单 R seed 保存。
- R `reticulate` 保留虚拟环境解释器路径，不解析其符号链接；已初始化解释器需重启 R 才切换。传给 Python 的 m、seed 要正确转型，不能丢失大整数 seed。
- 不假冒官方 `amelia` 返回类；导入名 `amelia_torch`、分发名 `amelia-torch`、R包名 `ameliatorch`。原R兼容路径实际使用官方产物时保留原类并标记引擎。

## 性能、质量与发布
- 按 `docs/benchmark-plan.zh-CN.md` 公平对照同机原版串行/并行、Python CPU、GPU。Mac CPU 对 Windows GPU 不能称 GPU 加速比；区分移植/BLAS收益与GPU自身收益。
- GPU 计时前后同步，包含传输与输出；R 用户产品结论还须测 R 桥接成本。保存预热、全部重复、版本/源码哈希、失败及未收敛；不能仅取成功子集宣称加速。
- 不只看 RMSE：检验观察值不变、所有应补值有限、无漏计 heldout、偏差、Rubin pooling 覆盖率与蒙特卡洛误差。全空行例外与人工 heldout 区分。
- 块状 MCAR 和逐格独立 MCAR 分开报告，记录 n/p/m/模式数/缺失率。100k 行样本不等于全量数据，未跑的压力/跨平台测试不能标完成。
- 原版 Amelia 为 GPL (>=2)；移植来源见 `THIRD_PARTY.md`，已选 GPL-3.0-only，保留根 LICENSE 与来源归属，不改为 MIT。数据 CC BY 4.0 归属须随发布保留。
- 禁止提交 `.venv`、`.R-library`、缓存、私有数据、机器序列号、含私人路径日志或本地配置。大原包用已确认的下载/Release方案，不误入 Git 历史。
- 每阶段更新 roadmap、兼容表和验证记录；AGENTS 只保留稳定约束和真实状态。不得把原型、CI配置或设备探针说成完整产品/实际通过的跨平台测试。

## Commit Attribution
- 如创建 AI 协作提交，使用执行 Agent 的真实模型名与有效 `Co-Authored-By:`；不伪造用户或其他人身份/邮箱。
