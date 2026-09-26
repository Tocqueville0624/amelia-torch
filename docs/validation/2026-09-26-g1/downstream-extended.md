# G1：补充官方下游工作流回归

2026-09-26，本机 macOS arm64、R 4.5.3、Amelia **1.8.3**、ameliatorch
0.0.0.9000、Python 3.12.13、PyTorch 2.14.0。所有混合拟合显式使用默认
CPU float64；本记录没有 CUDA/MPS 性能或推断质量结论。

新增 [`downstream_extended.R`](../../../r-package/tests/downstream_extended.R)
已实际运行、退出码 0，无跳过分支。本轮不修改原版或项目的拟合实现。
它补充此前的 [`downstream.R`](../../../r-package/tests/downstream.R)，不是
用更多计数替代尚未完成的其他首版验收任务。随后新源码包的 `R CMD check`
也完成了该文件及其余六个 R 测试文件，最终零错误/警告/NOTE；见
[本轮打包记录](packaging.md)。新文件尚未由 hosted CI 实际运行，旧版三平台
证据不能自动外推到它。

复现命令（项目根目录）：

```sh
R_LIBS_USER="$PWD/.R-library" RETICULATE_PYTHON="$PWD/.venv/bin/python" \
  Rscript r-package/tests/downstream_extended.R
```

| 工作流 | 实际核验 |
|---|---|
| `ameliabind` | 合并两份各 m=2 的原版/混合结果，四份旧数据逐一保持；不同缺失位置与不同 `empri` 模型均返回原版明确错误；原版 bind 丢掉 backend 属性后，Python RDS 重读标记来源 unknown，而非伪造 CPU/GPU 历史 |
| `transform` 后追加 | 创建 `interaction=a*b`，比较 `missMatrix`、保存的 `transform.calls`；追加 m=1 后每份派生值正确、旧两份数据严格不变，原版与混合结果一致 |
| `with` → `mi.combine` | 两边都经 `with(fit, lm(y~a+b))`；`conf.int=FALSE/TRUE, conf.level=.90` 的全部返回列比对，包括估计、SE、df 与区间；忠实保留下面的原版特例 |
| 可选 broom | 已安装 broom 1.0.12 的分支实际通过；另以私有函数环境令依赖探测返回缺失，实际触发原版 `{broom} package required for mi.combine` 错误。没有卸载包或修改官方 namespace；这不是一个真实缺包操作系统环境测试 |
| `summary.mi` / `plot.amelia` | 汇总文本/表对照，`compare` 与 `overimpute` 两个 S3 绘图分支生成有效 PDF，检查文件魔数、大小及绘图设备清理；未把文件检查称为视觉验收 |
| `write.amelia` | 分开的 tab-delimited table 文件逐份读回；合并 DTA 使用 `orig.data=FALSE, impvar="draw_id"`，读回行数、数值、factor 标签与级别；原版/混合输出一致 |
| `moPrep` | 60 行固定例分别测试 `error.proportion`、`subset/gold.standard`、proxy formula、已有 molist 再增加另一变量；prior SD 对照原公式，旧 priors/overimp 保持；物化数据的 molist RDS 完整读回，并逐例对照原版、reference、hybrid 拟合 |
| Python/RDS/R/Python | Python 混合拟合保存官方 RDS，R 读回后变换、reference 追加和绘图，再由 Python 读回并追加；检查派生值及历史 Torch 来源。另测试无来源记录的 bind RDS |

主要合成数据为 72 行，数值列 a/b/y，另有排除的 id 与带标签的 factor。
`moPrep` 与独立进程往返用 60 行。数值拟合为小样本功能回归，不是统计等价
模拟：R `all.equal` 阈值为 theta `1e-7`、结果及下游值 `1e-6`，直接导出读回
`1e-12`、手算 prior SD `1e-14`；历史数据、类别、缺失矩阵与模型参数用严格比较。

## 明确保留的 Amelia 1.8.3 行为

- `mi.combine(conf.int=TRUE)` 使用上尾 `.95` 分位点，临界值为负，因此本次
  实际结果每项都是 `conf.low > conf.high`。测试比较了原版与混合输出并确认这个
  次序，不自行互换端点。原函数还使用带符号的 statistic 计算两倍上尾 p 值，
  负系数可产生大于 1 的值。兼容通过不代表这些值具有正确的推断解释。
- `write.amelia(format="table", sep="\t")` 若不明确给 `separate`，R 部分参数
  匹配会将 `sep` 送入 `separate`；示例使用 `separate=TRUE`。DTA 写入函数由
  原版在 caller 中求值，因此显式绑定 `write.dta <- foreign::write.dta`。
- 单独 `readRDS` 不负责注册 S3 方法。独立 R 示例先
  `requireNamespace("Amelia")`，再调用 `transform`/`plot` 等泛型。

这些是固定版本调用/公式行为，未为了让测试通过而改动拟合或下游公式。
代码来源与固定版本依据见 [THIRD_PARTY.md](../../../THIRD_PARTY.md)。

## 独立示例与依赖

[`examples/python_r_downstream.py`](../../../examples/python_r_downstream.py)
及同目录 R companion 已分别在默认 `reference` 和 `--engine torch-compat`
下运行成功，两次均生成 RDS、CSV、PDF 与可移植 JSON，再验证 Python 读回的
旧份数据和派生列。Python 文件的 Ruff 检查通过。图形文件在忽略的本地输出
目录保存，没有将机器绝对路径或原始日志写入此记录。

复现与可选依赖说明见 [`examples/README.md`](../../../examples/README.md)：
`broom` 为 `mi.combine` 的可选依赖，`rlang` 为 Amelia 正常安装的 Imports，
`foreign` 提供 DTA，Tcl/Tk 图形会话是官方 GUI 的另一个要求。没有 broom 时
本独立示例明确跳过 pooling，直接调用官方函数仍明确报错。可选分支完整 CI
验收应显式安装 broom；本次本机版本为 broom 1.0.12、foreign 0.8.91、rlang 1.2.0。

源文件哈希见 [downstream-extended.json](downstream-extended.json)。本记录仅关闭
G1 中这些有限的功能例子，不关闭其他 G2–G8 边界、GPU 质量或全产品首版验收。
