# 示例

[English](README.md) · [文档目录](../docs/README.zh-CN.md)

## Python/R 往返

完成[安装](../docs/setup.zh-CN.md)后，从仓库根目录运行：

```sh
R_LIBS_USER="$PWD/.R-library" .venv/bin/python examples/python_r_downstream.py \
  --output results/local/downstream-example --r-library .R-library
```

输出目录须为新目录。Windows 使用 `.venv\Scripts\python.exe`、`--r-library .R-library`，Rscript 需在PATH或由`--rscript`指定。首次拟合默认原版 R；`--engine torch-compat`将首次拟合改为混合 CPU64，后续 R 变换、原版追加、建模、绘图和导出仍由原版 CPU 执行。

示例保存真实 Amelia RDS，在 R 派生交互项、追加一份且保留旧 draw，生成 PDF/合并 CSV，再由Python读取权威 RDS。检查派生值与旧份数据，并在 roundtrip.json 记录来源。

安装Python `[reference]`、Amelia 1.8.3 和 ameliatorch，混合另需 Torch。可选 R broom 启用 mi.combine：

```r
install.packages("broom", lib = ".R-library")
```

缺 broom 时示例明确跳过 pooling；直接调用原版 mi.combine 会报错。rlang 为 Amelia import，foreign 提供 Stata 导出。AmeliaView是独立交互 Tcl/Tk GUI，本示例不启动。

Amelia 1.8.3 mi.combine 的区间端点倒序，带符号上尾 p 值对负系数可能大于 1。示例关闭区间输出并保留原版结果；兼容不代表认可 p 值。解释前参阅[G1](../docs/validation/2026-09-26-g1/downstream-extended.zh-CN.md)。

## Colab CUDA模板

[colab_cuda_validation.ipynb](colab_cuda_validation.ipynb)含中文说明 cell，无账号元数据；[云端流程](../docs/cloud-cuda.zh-CN.md)提供对应中英文使用指南。阶段覆盖安装、Python和九个 R 文件、固定CUDA、数据、原生/混合基准、冻结 G5、审计与恢复。代码 cell 无保存输出/执行计数。静态结构/语法/lint 和本地睡眠子进程中断检查通过，但**尚无该模板完整端到端 Colab 通过记录**。

部分阶段尝试暴露 R 意外升级/共享扩展冲突及嵌套 venv 缺NumPy。安装修复后止于Python306 通过/一项失败，后续 R/CUDA/G5 未执行。Colab 保持暂停，安装器保护不是已验证修复，重用前阅读[恢复记录](../docs/validation/2026-09-27-colab-recovery/README.zh-CN.md)。

模板固定 `ef729c093e162f4d6ebd797c95a9da8072ac968a`，不同于 905cc79 历史计时。使用Python3.12、新 checkout 及明确双核预算。主要阶段默认关闭，不使用 Run all、不并发基准、不自动付费、不改阈值。失败阻止依赖计算；中断先终止进程组、确认退出再备份，清理不确定则保留活动标记并阻止后续工作。不监控其他 notebook 或脱离组的进程。完整 G5 报告可通过记录审计而统计标准仍失败。

JSON/log checkpoint 不含二进制参数和准备数组。模板另备份 12 个原生参数 NPZ 的原字节/哈希封装，并提供有界下载归档。释放 VM 前保存 notebook 并核验下载/哈希；备份在计时外，不能恢复尚未写入结果。

[旧恢复输出](../docs/validation/2026-09-23-colab-recovered/README.zh-CN.md)、[后续T4原生结果](../docs/validation/2026-09-26-colab-native/README.zh-CN.md)、[Mac结果](../docs/validation/2026-09-23-development/README.zh-CN.md)均为独立证据，不是此模板的执行结果。
