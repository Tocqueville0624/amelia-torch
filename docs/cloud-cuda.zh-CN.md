# Colab CUDA 流程

[English](cloud-cuda.md) · [文档目录](README.zh-CN.md)

Colab 实验因配额耗尽处于暂停状态。本文是后续安排运行的流程，不证明各阶段已通过；当前文档阶段不启动新计算。Linux/T4、Windows/RTX 3080 和交互RStudio证据分开。见[当前摘要](validation/2026-09-27-evidence-summary.zh-CN.md)。

## 模板与已知失败

使用[分阶段notebook](../examples/colab_cuda_validation.ipynb)及[范围说明](../examples/README.zh-CN.md)。模板固定 `ef729c093e162f4d6ebd797c95a9da8072ac968a`，含九个 R 文件和独立正确性、性能、G5、审计、备份阶段。静态/语法/lint 及轻量进程中断检查通过，但**未完成一次端到端 Colab 运行**。历史 `905cc79` 耗时不是新模板执行结果。

替代运行止于第 4/20 步：306 项Python通过，一项嵌套 venv 缺NumPy；后续 R/CUDA边界/G5 未执行。此前系统安装将 R 4.5.3 升级为 4.6.1 并破坏共享扩展；恢复 4.5.3 和新项目 R 库修复了安装，不代表整套验证通过。自动安装保护尚未验证；工具齐全时不加 `--install-system-packages`，重用前查看[恢复证据](validation/2026-09-27-colab-recovery/README.zh-CN.md)。

## 环境

项目要求Python3.12。首个已记录免费环境为Python3.13.15/Torch 2.11.0+cu128/R 4.6.1，应在可用时选择合适旧镜像并实查版本；[运行时供应](https://research.google.com/colaboratory/runtime-version-faq.html)会变化。免费 GPU 供应和时长无保证，不自动购买、不绕过配额、不在 CPU/CUDA比较中换 runtime。见[资源政策](https://research.google.com/colaboratory/faq.html)。

新目录检出完整 40 字符 commit。`cloud_bootstrap.py --expected-commit <sha>`仅计划，安排安装时再加`--execute`。它要求现有CUDA Torch>=2.10,<3，通过Python3.12 system-site-packages venv 复用同一 Torch 文件，再装项目/测试/pandas；不是完全隔离锁，Mac lock 不用于CUDA。

安装器通过 venv 解释器实查 Ruff，元数据存在但 binary 缺失时记录同版本本地重装。缺 ensurepip 时 uv 后备仍用同解释器/共享设置，记录版本；不主动替换 Torch/全局包。R 依赖、broom/foreign 及精确 Amelia 1.8.3 装入`.R-library`，C helper 须编译。缺 R/构建工具明确失败。apt 重试须新输出目录并事先审查 R 版本影响，仅用于 Linux VM，不在 Mac 执行。

Amelia 源码 SHA-256 固定为 `7699455ca3e9dabd60ad0ec69185ece3f24a597ef8da18033ea0b7a32356967f`，仅回退CRAN Archive 同版本。安装记录含源码哈希、commit、硬件/runtime、CPU 配额、内存、版本、命令和失败，不含序列号、主机名或全环境变量。已有输出目录拒绝覆盖。

## 执行与计时

依次完成设备探针、Python检查、九个 R 文件、下游示例和固定CUDA64/32 对照后再执行依赖任务。显式禁用 TF32，保留失败，不按结果放宽阈值。旧 notebook 的 149 项Python/五个 R 文件不覆盖后续新增检查。

为Covertype/Household/Year 准备共用 100k 完整行块状MCAR输入。下载约 232 MiB，以清单哈希/CRC 校验并保留 5 GiB磁盘余量。Household实际遮盖 2/7，不是全量或独立逐格MCAR。见[数据](datasets.zh-CN.md)和[复现](reproduce.zh-CN.md)。

按实测 CPU 配额固定预算。已记录 T4 仅两逻辑核：原生/参考 threads 2/workers 2，混合 threads 2，snow 每 worker 单BLAS线程。其他主机须记录统一预算。套件顺序执行，不改源码、不并发拟合。双核主机命令：

```python
NATIVE = "results/local/cloud/native"
HYBRID = "results/local/cloud/hybrid"
assert not pathlib.Path(NATIVE).exists(), "Choose a fresh result directory"
run(PYTHON, "scripts/run_benchmark_suite.py", "--gpu", "cuda", "--output-dir", NATIVE,
    "--rows", "100000", "--m", "5", "--warmups", "2", "--repeats", "5",
    "--threads", "2", "--workers", "2")
```

```python
assert not pathlib.Path(HYBRID).exists(), "Choose a fresh result directory"
run(PYTHON, "scripts/run_hybrid_suite.py", "--methods", "cpu64", "cpu32", "cuda64", "cuda32",
    "--csv-dir", f"{NATIVE}/inputs", "--output-dir", HYBRID,
    "--rows", "100000", "--m", "5", "--warmups", "2", "--repeats", "5", "--threads", "2")
```

上述 PYTHON、REPO 和 run()由分阶段 notebook 初始化。每配置 m5、两预热/五正式重复。原生/参考比较 R 串行/snow2与 Torch CPU/CUDA64/32；混合复用主套件 CSV。完整调用计入预处理、EM、抽样、传输和 CPU 输出，排除读文件、安装、进程启动和评分。R 混合含 reticulate 转换，不含Python→Rscript 进程/二进制交换。CPU 对照也占用已分配 GPU 会话配额。

## 审计与备份

```python
run(PYTHON, "scripts/summarize_benchmarks.py", "--input-dir", NATIVE,
    "--output-dir", "results/local/cloud/native-audit",
    "--methods", "r_serial", "r_snow2", "cpu64", "cpu32", "cuda64", "cuda32")
run(PYTHON, "scripts/summarize_hybrid.py", "--input-dir", HYBRID,
    "--output-dir", "results/local/cloud/hybrid-audit")
```

核验计划配置齐全、全部重复、收敛、观察值、有限输出和完整 heldout 评分。exit 0 不足以证明有效，比值须同机；推断门槛独立。中断后保留部分目录/日志，不覆盖重跑或合并不同 VM 为同套件。

每阶段及失败后在计时外导出完整归档并保存 notebook，本地核验哈希后才释放 VM。公开前审查原始日志/config 路径。Drive 挂载需要单独许可，并非前置条件。

可将便携 checkpoint 打印到 notebook 输出：

```python
checkpoint_text = subprocess.check_output(
    [PYTHON, "scripts/cloud_checkpoint.py", "--label", "validation-20260926"],
    cwd=REPO, text=True)
print(checkpoint_text, flush=True)
```

`cloud_checkpoint.py`纳入JSON/log/text 报告、准备数据JSON及公开清单，记录原始/便携哈希并替换项目/home 路径；排除认证、原始数据、RDS、依赖和二进制参数。输出放在收集目录外。用`--phase g5-formal`、native 或 hybrid 选择已存在直接子目录，解压上限 64 MiB；不能恢复尚未写入的结果。

本地恢复已保存 notebook 或完整 checkpoint JSON：

```sh
.venv/bin/python scripts/recover_cloud_checkpoint.py saved-notebook.ipynb \
  --label validation-20260926 --output-dir results/local/recovered-validation
```

恢复不执行 notebook 代码，核验 gzip、路径和哈希，拒绝覆盖。模板另存 12 份原生参数 NPZ 的带哈希原字节封装，并提供输入/参数下载归档。VM 在备份前丢失仍可能不可恢复，截断 stdout 不是原始JSON。
