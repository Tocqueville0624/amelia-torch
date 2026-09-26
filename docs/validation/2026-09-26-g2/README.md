# G2 公共混合入口：CPU64 边界回归

2026-09-26，本机 Apple silicon / R 4.5.3 / Python 3.12.13 / PyTorch 2.14.0，参考固定为未修改的 Amelia 1.8.3。新增 [public-edge-cases.R](../../../r-package/tests/public-edge-cases.R) 的 **33 个案例通过**，全部 **7 个 R 测试文件通过**，相关 **26 个 Python reference/public/hybrid 集成测试通过**。这些是小型正确性回归，不是 GPU 验收或性能测量。

机器可读记录：[逐案例输出](public-edge-cases.json)、[全部 R 文件及源码哈希](r-tests.json)、[环境、命令和关键源码哈希](summary.json)。R 测试日志也在本目录；其中耗时仅用于记录测试执行，不用于速度结论。没有记录主机名、用户目录或完整环境变量。

## 修复的真实语义差异

原版 `R/emb.r:168–170` 的 `startval()` 直接返回合法显式初值；`src/em.cpp:13,34` 用 `Rcpp::NumericMatrix` 与不复制的 Armadillo view 读取该矩阵，`:207` 执行 `thetaold = thetanew`。因此普通 **double** 初值的底层 R 对象会被修改：调用者变量、归档的 `arguments$startvals`、下一份插补的初始参数都能看到最终 theta。R 的普通赋值并不能隔离这些别名。

此前混合入口返回了新的 Python theta，却没有回写原 R 对象。单份输出几乎相同，但多份插补的后续初值和历史不同，存档也没有反映原版副作用。现在使用注册的内部 C helper 原位回写 double 矩阵，并保留两项必要例外：

- **integer** 初值在原版 Rcpp 入口被转换为独立 double buffer，调用者和存档保持 integer 且不改变；混合入口同样不回写。
- 完整 bootstrap 样本走原版样本协方差 shortcut，既忽略初值也不修改初值；混合入口跳过回写。

该 helper 不生成随机数，不改 EM 公式，不改 R RNG helper。`allthetas` 的初始参数列在回写前保存。所有符号仍显式注册，动态查找关闭。公开 R 对象的这一有意副作用只用于兼容原版；native Python EM 的输入不变契约没有改变。

固定 80×3 合成数据、seed 77、`tolerance=1e-6`、`autopri=0` 的代表结果：

| 初值 / bootstrap | 原版与修复后混合迭代数 | 初值与归档 |
|---|---|---|
| double 显式 theta / none，m=2 | 10、1 | 变成最终 theta |
| integer 单位 theta / none，m=2 | 10、10 | 保持原值与 integer 类型 |
| double 显式 theta / ordinary，m=2 | 10、9 | 变成最终 theta |
| integer 单位 theta / ordinary，m=2 | 9、11 | 保持原值与 integer 类型 |

另测默认初值和 `startvals=1` 的两种 bootstrap、多份输出、调用者/归档别名、存档 `arglist` 重用和已有对象追加、`allthetas` 初列。检查结束时 R 可见 `.Random.seed`，并紧接检查 `runif(6)` 和 `rnorm(6)`，均与原版一致；已有 `downstream.R` 的 Inversion/Box–Muller 奇数正态缓存回归也通过。

## 其余已实际触发的边界

- `emburn` 最少 35 轮和最多 2 轮均对齐原版 history。最大轮数用尽时，原版仍返回 code 1 和 “Normal EM convergence.”；混合对象保留原版字段，同时明确记录 `converged=FALSE` 并发出 Python `RuntimeWarning`，不能只凭原版 code 判断收敛。
- 固定 24×2 输入中，seed 1 的 ordinary bootstrap 确实一次抽成完整样本；协方差对照 `stats::cov()`，history 为 NA，显式初值和存档保持不变。seed 5 的另一个输入第一次抽样确实令一列全缺失，第二次抽样才接受。
- bootstrap 证据来自原版函数的私有副本：仅记录实际 `runif` 返回的行索引，不额外抽数。原版 namespace 未修改；记录版输出与未插桩的公共调用完全相同，原版/混合的抽样索引相同。完整索引和观察值计数见 JSON。
- 全缺失分析行最终仍全为 NA，其余缺失被补齐；无缺失输入分别检查默认错误及 `incheck=FALSE` 的完整样本行为；全缺失列、常量列、样本量不足分别匹配原版错误码 4、43、34。
- 远离数据的窄 bounds `[100,100.001]`、`max.resample=1` 实际令 9 个缺失值最终等于下边界；`max.resample=0` 匹配原版错误码 52，未把该非法值伪装成零次拒绝抽样。
- `incheck=FALSE`、`collect=TRUE`、`p2s=1/2` 各自与原版统计结果对照。混合进度文字仍明确标记 PyTorch，不声称与原版逐字符相同。原版输入检查可消耗 RNG，因此不假设开启/关闭 `incheck` 后的抽样逐值相同。

## 复现与未覆盖部分

先安装当前 R 包（新注册 helper 需要重新编译安装），再运行：

```sh
R_LIBS_USER="$PWD/.R-library" R CMD INSTALL --clean --library=.R-library r-package
R_LIBS_USER="$PWD/.R-library" RETICULATE_PYTHON="$PWD/.venv/bin/python" \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  Rscript r-package/tests/public-edge-cases.R
.venv/bin/python -m pytest -q tests/test_hybrid_reference.py tests/test_reference.py tests/test_public_reference.py
```

若需重建逐案例 JSON，R 中 `source("r-package/tests/public-edge-cases.R")` 后使用 `jsonlite::write_json(edge_report, ..., auto_unbox=TRUE, pretty=TRUE)`。测试保留 `edge_report`，不自行向源码树写文件。

本记录没有覆盖 public `autopri` 实际更新/固定初始 hold 的病态触发，也没有覆盖 GPU 精度下这些新增案例。已有低层诊断不能自动替代这些验收，因此 G2 仍有这两项后续工作，不能据此宣布完整首版。

历史记录说明：`r-tests.json` 中 `downstream_extended.R` 的源码哈希对应该次直接运行版本；之后为 R CMD check 子进程隔离 `R_TESTS` 启动变量所作的测试修订，已由 [G1 最终包检查](../2026-09-26-g1/packaging.md) 和其源码哈希覆盖。这里保留原次执行的哈希，不将历史记录改写为新版本。
