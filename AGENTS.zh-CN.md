# 仓库维护规范

[English](AGENTS.md) · [文档目录](docs/README.zh-CN.md)

本规范适用于代码、文档及自动化贡献，用于保持统计契约和公开证据的完整性。

## 范围与状态

- 目标为 Python 与 R/RStudio 跨平台完整复现 Amelia 1.8.3。原生连续子集、原版 R 参考、R/PyTorch 混合为独立接口。允许明确标注 R 依赖；完整验收后才标记首个完整版本。
- 当前仅整理文档和审查既有证据。实验明确恢复前，不新增拟合、模拟或测试任务，不扩展预算或申请付费算力。允许静态文档、链接和校验值检查。
- Windows `810591e` 完成 18 原生/参考、12 混合配置，共 210 调用/1,050 插补。T4 `905cc79` 原生/参考完整，混合回收 11/12。Mac G5 完成 10,500 拟合但 MCAR 标准未全通过。CUDA G5 和新增 CUDA 边界尚未完成。状态依据[证据摘要](docs/validation/2026-09-27-evidence-summary.zh-CN.md)，不能从文件名推断完成。
- 分发名 `amelia-torch`、导入名 `amelia_torch`、R 包 `ameliatorch`、GPL-3.0-only。维护者 Sheng Wan <swan0624@uw.edu>；公开仓库 Tocqueville0624/amelia-torch。实际参与确认后再添加贡献者署名。

## 环境

使用 Python 3.12、uv、`.venv` 和项目 `.R-library`，固定原版 Amelia 1.8.3。Mac arm64 lock 不用于 Windows CUDA 或 Intel Mac。Windows 解释器为 `.venv\Scripts\python.exe`，Unix 为 `.venv/bin/python`。遵循[安装](docs/setup.zh-CN.md)与[复现](docs/reproduce.zh-CN.md)说明，保留忽略目录中的环境、原始数据和恢复记录。

恢复测试后，Python 检查为 `.venv/bin/python -m pytest -q` 和 `.venv/bin/ruff check src tests scripts`。R 源码桥接检查为 `R_LIBS_USER="$PWD/.R-library" RETICULATE_PYTHON="$PWD/.venv/bin/python" AMELIATORCH_R_SOURCE=r-package Rscript r-package/tests/bridge.R`。混合源码检查仍需已安装的 C helper。设备探针为 `python -m amelia_torch.diagnostics --require-device mps` 或 `cuda`。受限进程可能隐藏 GPU 或阻止 snow localhost socket，须记录实际执行环境。

忽略目录 `results/local/cloud-recovery-*/resume-state.json` 仅是恢复提示，不证明任务执行。私有 notebook 链接、账号元数据不得公开。每阶段在计时外用 checkpoint/recovery 脚本备份完整报告到 VM 外并核验哈希，不拼接替代 VM 耗时。系统包安装曾将 R 4.5.3 升至 4.6.1 并破坏共享扩展；自动保护尚未验证。本地 `unfinished-cloud-bootstrap-guard.patch` 是待审草稿，不是已完成修复。

## 算法约束

- [算法契约](docs/algorithm-contract.zh-CN.md)固定语义。开放新参数前建立原版对照，不支持参数明确拒绝。
- 保留观察值标准化→bootstrap→条件矩 EM→原始输入抽样→顺序/单位恢复。条件协方差不可省略，均值填充不是 EMB。
- 保留观察值及全空分析行：全空行排除拟合、输出仍缺失。保留单行 prior、log 变换及缺失 ID 等已记录上游特例。空列、常量、少观察值、病态和未收敛须明确处理。
- 保留初值、样本协方差分母、整数 empri、autopri 固定初始 hold、上三角停止规则及完整 bootstrap 特例。不静默加 ridge、裁剪协方差或降精度。
- 原版 C EM 原位更新显式 double R startvals，须保留调用者、归档及后续插补影响，先存 allthetas 初列。integer 和完整 bootstrap 例外不回写。原生 Python 不改输入；参考导出须深复制 theta。
- reticulate 前后保留 R 内部 RNG 与可见 `.Random.seed` 两层状态，不把注册 helper 简化为赋值。原版抽样可能令可见向量滞后。原生使用 NumPy PCG64；同整数 seed 不配对随机流。确定性比较用显式随机数组，推断用独立分布检查。
- CPU float64 为参考；MPS/CUDA float32 须显式选择并有独立质量证据。MPS 特征值检查在 CPU 执行并记录，fallback=0 不证明全 GPU。
- 保留 reticulate 虚拟环境解释器路径，不解析可执行文件符号链接。已初始化解释器须重启 R 再切换。m、大 seed 正确转换不截断。原生结果不得伪装官方类；真实原版对象保留官方类及引擎元数据。

## 证据与发布

- 按同机、同任务、同精度完整调用比较原版 R 串行/并行和 Torch CPU。GPU 同步且计入传输/输出；R 与 Python→R 接口成本分别测量。跨 3080/T4 耗时是跨主机观察，不是独立 GPU 速度比；未经剖析不能称差值为通信成本。
- 保留预热、全部重复/失败、源码/环境/数据哈希、收敛、伪逆和 CPU 工作记录。代码修改后不改写历史测量源码指纹。未测内存为 null，不是 0。
- 检查观察值、应补值有限、heldout 完整评分、偏差、Rubin 覆盖率和蒙特卡洛误差。RMSE相近不证明逐值一致。已保存 Mac Covertype 最大差 0.173 个真值列 SD，保留范围，不泛称可忽略。
- G5 阈值/预算在执行前冻结，协议 SHA 为 `7ea7882bccc8d92102a67786bc9c09c2055ce29d97350abfbcf4f74f2187e454`。保留未通过分类；独立 1,000 次MCAR方案尚未执行，不授权扩展模拟。
- 区分块状MCAR、独立逐格MCAR和 MAR，报告 n/p/m/模式数/实际缺失率。100k 样本不是全量数据。CPU CI 不代表 GPU/GUI，未触发的原版 autopri 分支仍未覆盖。
- 保留GPL和 CC BY 4.0 归属。Git 纳入许可小样本、清单和下载脚本，不纳入虚拟环境、R 库、大原包、私人数据、私人路径或机器标识。
- 按实际证据更新路线、兼容表和报告。编辑文档时不改原始归档/实验输出，单独记录文档校验值修订。公开 Markdown 均须有内容对应的中英文及切换链接；面向研究者和外部审阅者，使用简洁客观标题及正文，删除助手向所有者汇报的叙述。

## 提交署名

Sheng Wan 授权的项目提交使用本仓库 Git 身份 `Sheng Wan <swan0624@uw.edu>`。不自动添加 Codex 或其他 AI 工具的 `Co-Authored-By`。保留真实人类贡献者、上游作者、许可证和来源归属。此元数据规则不表示全部工作均为手工编写。不得修改全局 Git 配置。

历史测量提交编号和源码哈希作为原始证据保留。通过[历史迁移映射](docs/history/README.zh-CN.md)查找文件树完全一致的新提交。文档及复现入口改动须与仅修改提交元数据的历史重写分开提交。
