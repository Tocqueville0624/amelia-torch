# Amelia 1.8.3 算法契约与参考证据

审计日期：2026-09-23。兼容目标固定为 **CRAN Amelia 1.8.3 的实际行为**；数学公式、实现行为和未验证功能分开记录。本项目不是官方 Amelia。此文不代表已经完成全功能移植，也不代表 GPU 更快。

## 1. 固定参考与来源

- 官方源码：[Amelia_1.8.3.tar.gz](https://cran.r-project.org/src/contrib/Amelia_1.8.3.tar.gz)。本地审计缓存 `.cache/upstream/Amelia/`，不提交缓存。
- 下载压缩包 SHA-256：`7699455ca3e9dabd60ad0ec69185ece3f24a597ef8da18033ea0b7a32356967f`。
- 官方包许可：GPL (>= 2)。算法移植与任何源码派生必须保留来源及适用许可，不能默认宣布 MIT；最终项目许可证按用户确认落实。
- [官方参考手册](https://cran.r-project.org/web/packages/Amelia/Amelia.pdf)。手册的概括性描述不能覆盖版本源码的实际行为。
- 主要入口：`R/prep.r::{amelia_prep,amtransform,amsubset,scalecenter,amstack,unsubset,untransform}`；`R/emb.r::{bootx,startval,emarch,amelia_impute,amelia.default}`；`src/em.cpp::{emcore,sweep,ameliaImpute,resampler}`；`R/amcheck.r::amcheck`。
- 可重建证据：`Rscript scripts/export_reference_fixtures.R`。脚本调用本机未改动的 Amelia 1.8.3，导出 `tests/fixtures/reference_amelia/`。输入均为本仓库生成的合成数据。

本文“已验证”指 R 参考输出被实际执行核实；是否已被新实现复现，另见兼容矩阵和测试记录。

## 2. 不可改变的执行顺序

1. 校验输入及选项、解析列名和索引、展开 observation priors。
2. 在原始完整输入上执行指定变量变换；准备 `idvars`、名义变量虚拟列、时间结构以及 overimputation。
3. 移除分析变量全缺失的行；保留其原始位置用于最终恢复。
4. 使用每列**观察值均值和样本标准差**标准化。标准差分母为 `n_observed - 1`。这是对原始分析数据做一次，**不是每个 bootstrap 样本分别标准化**。
5. 初次列排序按缺失数从少到多；行排序按**倒序列顺序的缺失掩码**作词典序排序，观察值排在缺失值前面。相同模式形成连续块，完整行在前。
6. 每份插补独立从该预处理输入抽取 bootstrap 行；同步重映射 cell priors。bootstrap 后只重新分组排序行，不改变列顺序。
7. 在 bootstrap 样本上构造初值，运行 EM，取得参数估计。
8. 使用该参数对**原始预处理输入**抽取缺失值，而不是对 bootstrap 样本输出插补。
9. 逆转行列排列、标准化、subset/类别重构和变量变换，恢复原始格式。最终 `impfill` 一般仅写入应插补单元格，普通观察值保留；单行公共 priors 有已核验的上游索引特例，见第 8 节。

更换 EM 为均值填充、MICE、神经网络；省略条件协方差；省略 bootstrap；在 bootstrap 数据上返回输出；随意改变预处理顺序，都不是等价加速。

## 3. 输入坐标与初值

低层接口接受已变换、标准化的数值矩阵。`NaN/NA` 表示缺失，不能将零当成缺失。参数矩阵采用

\[
\Theta=\begin{bmatrix}-1&\mu^T\\\mu&\Sigma\end{bmatrix}.
\]

`startval`（`R/emb.r:161`）的实际规则：

- 给定维度正确且左上角为 -1 的矩阵时，直接采用该矩阵。
- `startvals=1`：均值零，协方差单位矩阵。
- `startvals=0`：先在初值专用副本中以 prior 均值替换对应单元格，然后提取完整行。仅当完整行数 **严格大于 p**，且完整行样本协方差所有特征值 **严格大于 `10 * .Machine$double.eps`** 时，使用完整行均值及 `cov()`；否则使用零均值、单位协方差。
- 完整行初值的 `cov()` 分母是 `n_complete-1`，不能误用 EM 的 `n`。
- PyTorch 的 CPU float64 是数值参考。MPS float32 和 CUDA float32 均须独立通过质量验证，不可把 float32 偷换成 float64 等价声明。

上游 `emcore` 将 `thetaold` 作为无复制 Armadillo view 并原地写回。**参考导出脚本必须深复制每次传入的 theta**；R 普通赋值不足以防止别名污染。脚本使用 `unserialize(serialize(..., NULL))`，使单步调用、完整调用和保存的初值互不干扰。

公共 R 混合入口须保留这项副作用：显式 **double** `startvals` 的调用者对象、`arguments$startvals` 归档与下一份插补都会看到最终 theta。注册 C helper 在保存 `allthetas` 初列后原位回写；**integer** 初值经原版 Rcpp 转换，不回写原整数对象；完整 bootstrap 样本跳过 EM，也不回写。native Python 的输入不变契约仍保留。多份插补、arglist/追加与 RNG 对照见 [2026-09-26 公共边界证据](validation/2026-09-26-g2/README.md)。

## 4. E 步及 cell priors

每个缺失模式有观察集合 O、缺失集合 M。令当前参数为 μ、Σ，条件矩为

\[
a_i=\mu_M+\Sigma_{MO}\Sigma_{OO}^{-1}(x_{iO}-\mu_O),\qquad
V=\Sigma_{MM}-\Sigma_{MO}\Sigma_{OO}^{-1}\Sigma_{OM}.
\]

先以 `a_i` 补齐第一矩，再把 V 嵌入缺失×缺失块，加入二阶矩。完整行无条件方差修正。

原版通过 `sweep` 得到条件矩。`src/em.cpp:293` 的求解先尝试 `inv_sympd`，失败时使用绝对阈值 `sqrt(double epsilon)` 的伪逆；不得增加未声明的 jitter/ridge、特征值裁剪或默认降精度。新的稳定求解形式可以不同，但需在相同输入上验证其数值结果，并记录伪逆使用情况。

公共 priors 的四列为 `[row, column, mean, standard_deviation]`；进入 `scalecenter` 后第四列变成**标准化方差**。低层 `emarch`/`amelia_impute` 因而接收 `[row, column, standardized_mean, standardized_variance]`，行列为 R 的 **1-based** 索引。进入 C++ 前又转换为 precision 和 precision-weighted mean。不能把三个坐标层混用。

有 prior 的缺失单元格形成对角精度矩阵 Λ 与精度加权均值 b，无 prior 的位置精度为 0，则

\[
W_i=(V^{-1}+\Lambda_i)^{-1},\qquad
a_i^*=W_i(V^{-1}a_i+b_i).
\]

该行同时使用 `a_i*` 和 `W_i` 更新充分统计量。不能只调整均值却仍保留 V。

公共五列 priors `[row,column,lower,upper,confidence]` 先变成均值 `(lower+upper)/2`、标准差 `(upper-lower)/(2*qnorm((1+confidence)/2))`。row=0 表示该变量所有缺失单元格；逐单元格 prior 优先于变量级 prior。这些公共预处理尚不能从低层 priors 已通过测试推断为已实现。

## 5. M 步与经验先验

令 y_i 为第一矩补齐行，C_i 为其条件协方差嵌入矩阵；`n` 是当前 bootstrap 样本行数，`p` 是展开后的分析变量数。

\[
s=\sum_i y_i,\quad Q=\sum_i(y_i y_i^T+C_i),\quad\mu'=s/n.
\]

无经验先验时

\[
\Sigma'=Q/n-\mu'\mu'^T.
\]

**一般 EM 分母是 n，不是 n−1。**

上游 C++ 把 `empri` 转为整数 e，并在迭代开始前固定 `H=e_initial I`。当当前 e>0 时

\[
\Sigma'=\frac{Q-ss^T/n+H}{n+e+p+2}.
\]

这是该版本实际实现；不能改成 `Σ + ridge I`，不能省略 `p+2`，也不能只保留非对角缩减来迎合手册的概括描述。`empri=3.75` 在 fixture 中实际使用 3。

### 完整 bootstrap 特例

如果内部 `emarch` 输入完全无缺失，就跳过 EM，返回 `mean(x)` 和样本 `cov(x)`（分母 n−1）、`iter.hist=NA`。**它忽略 empri 和提供的 theta**。尽管公共 `amelia()` 默认拒绝完全没有缺失的原始输入，bootstrap 仍可能恰好抽到完整样本，所以这个内部特例不可省略。

## 6. 停止、迭代记录和 autopri

- 每步对整个 Θ 的**上三角**计数：`cvalue = count(abs(new-old) > tolerance)`，比较是严格大于。
- 继续条件为 `(cvalue>0 OR count<emburn[1]) AND (count<emburn[2] OR emburn[2]<1)`。
- 默认 `emburn=c(0,0)` 无最大迭代数；不是默认 100、500 或 1000。研究实验可显式设预算，但各实现要一致。
- `iter.hist` 三列依次为 cvalue、nonmonotone flag、singularity flag。
- nonmonotone flag 是迭代数>20 且本轮 cvalue 比上轮大。**它不是对 log-likelihood 的检验**。
- singularity flag 是本轮协方差存在特征值≤0。
- 满足 nonmonotone、autopri>0、此前20轮 singularity flags 总和>3、当前 e<autopri*n 时，执行 `e=int(e+0.01*n)`。没有额外 cap-clamp；整数截断使 n<100 时可能无法增长。
- H 仍保持初始 `e_initial I`，不因 autopri 的 e 增长而更新。这是版本实际语义，不可未经声明“修正”。

新实现应额外报告是否因显式最大迭代数而停止；不能把仍有 cvalue 的 fit 宣称收敛。原版外层随后检查协方差最小特征值：小于 double epsilon 时返回 code=2，不输出有效插补。

`allthetas=TRUE` 的上游低层返回不是普通矩阵列表：它是按列优先顺序取 Θ 上三角、删除左上角元素后的参数向量矩阵，**第一列包含初始值**，后续每列一轮。R 兼容桥必须适配此格式；native Python 的诊断格式可以另行命名，不能伪称原版输出。

## 7. Bootstrap 与随机补值

`bootx`（`R/emb.r:71`）ordinary bootstrap 对 n 行作 n 次等概率有放回抽样。`boot.type="none"` 直接使用原始预处理矩阵。抽到任一全缺失列且该列没有 prior 时，丢弃整个 bootstrap 样本并重抽；上游没有重试上限。上游 prior 在重试循环中被重映射的版本行为应单独覆盖，不能将改良重试算法混入兼容路径。

`ameliaImpute` 用同一条件正态分布，在原始预处理输入上随机补值。对缺失组抽 n_group×p 个标准正态数，按 R/Armadillo 的**列优先**顺序排列，完整组不消耗随机数。上三角 Cholesky R 满足 `R^T R=V`，行向量噪声为 `z R`。有 cell priors 的行改用后验条件矩。

R/PyTorch 混合路径还必须保护 R RNG 的两个状态层：原版 1.8.3 的 C++ 补值调用 `Rcpp::rnorm`，却未用 RNGScope 同步 `.Random.seed`；C 内部状态可能已前进而 R 可见向量仍旧。若在无 bootstrap 的两份插补间直接进入 reticulate，其 RNGScope 会重载旧向量而重复抽样。`r-package/src/rng_state.c` 的两只注册 helper 在确定性 Python 初始化/EM 前保存可见向量并导出 C 状态；返回时先恢复 C 状态，再分别恢复原可见向量。不能仅保存 `.Random.seed`，也不能用额外 `runif()` 来“刷新”。已对照 `boot.type="none", m=2`、Inversion/Box-Muller 奇数正态数场景、结束 `.Random.seed` 和随后的 `runif/rnorm`；既保持独立补值，也保留原版外部随机调用语义。

`bounds` 作用于补值阶段；不是改变 EM 为截断正态模型。原版逐行联合拒绝抽样，最多 `max.resample` 次，之后对仍违规单元格夹到最近边界；未设边界的缺失维度仍按联合抽样更新。边界并非无穷次精确截断正态抽样。输入边界也需与分析坐标及列重排对齐。

跨 R、NumPy、PyTorch、CPU/CUDA/MPS 相同 seed 不代表相同随机输入。确定性对照必须共享明确的 bootstrap 索引和标准正态数组；统计质量对照则检验分布、Rubin pooling 和覆盖率。只看 RMSE 不能验证多重插补。

## 8. 预处理和输出边界

- `idvars` 不进入模型，原值和类型保留。`ts` 与 `cs` 被移到识别列，按选项生成额外时间/组别列。
- lag/lead 在 cs、ts 排序后按相邻观测构造，组边界置缺失；不是基于任意日历间隔自动插值。时间多项式、分段三次样条和与 cs 交互使用该版本的 basis 构造和冗余列删除顺序。
- nominal 使用观察类别首次出现顺序构造 k−1 个 dummy，恢复时把预测概率限制在 [0,1]，必要时归一化并补上基准类别概率，再随机抽类别。不能用 argmax 代替。
- ordinal 在观察到的最小/最大整数范围内，将连续预测缩放、限制到 [0,1]，再使用二项分布抽取整数；**不是简单四舍五入**。
- 全缺失分析行被移除，最后仍保持缺失；并非从无条件正态额外补齐。`edge_contract.json` 已实测确认。
- 公共默认检查拒绝非 id 列观察数≤1（code=4）、常量列（code=43）、无缺失原始输入且未设 overimp（code=39）。不能以内部 `emarch` 更宽松的输入域代替公共语义。
- 输入缺失数、数据类型、类别映射、列名、行名和顺序属于 API 契约；只有内核矩阵相同不足以声称 drop-in replacement。

### 明确记录的版本特例

`logs` 的上游正向变换是 `log(x-xmin+1)`，其中 `xmin=min(0,min(observed_x))`；逆变换实际为 `exp(z)+xmin`。2026-09-23 运行 `amtransform`→`untransform` 对 `[-2,0,2,4,7,10]` 的结果是原值+1，见 `edge_contract.json`。源码没有在 `amelia_prep` 对 xmin 另作修正。最终观察值仍通过 impfill 保留，但缺失值遵循上游这个版本行为。实现兼容模式时不能无说明地减去1；任何修正应成为用户明确知情的独立模式或上游版本变更。

同日以独立 `Amelia::amelia()` 公共调用核验：单行 `priors=matrix(c(1,3,0.5,0.05),nrow=1)` 加字符串 `idvars` 会改动第一列的第 1、3 行。原因是 `R/emb.R::impfill` 的 `is.na(x.orig)[priors[,c(1,2)]] <- TRUE` 没有 `drop=FALSE`，单行 prior 的坐标矩阵掉维成向量，变成线性索引而非 row/column 索引。因此“所有公共选项组合都不改观察值”不是 1.8.3 的事实。reference 路径保留原版结果并警告；测试单独固定此边界行为，不把它修成另一个算法版本，也不让普通多行 priors 的观察值检查绕过失败。回归入口是 `tests/test_reference.py::test_single_row_prior_preserves_documented_original_indexing_quirk`。

## 9. 可复現的校验路径

1. 导出脚本要求 Amelia 恰为1.8.3，所有数据和随机输入写入 JSON，JSON 中 null 表示缺失。
2. 同一 input、同一 initial theta：逐步比较条件均值/协方差、一次 M 步、最终 Θ、迭代历史。例子包括无 prior、fractional empri、cell prior、无完整行、最少和最多迭代、完整样本特例。
3. 对同一 final theta 注入 fixture 中明确的 `standard_normals`，比较 `amelia_impute` 完整输出；不使用跨库 seed 猜测。
4. 对 preprocess fixture 比较观察值均值、样本 SD、行列位置以及 startvals；这些确定性检查不代表公共变换已移植。
5. `adaptive_stress.json` 记录恰好共线数据在 autocorrection 附近的行为。特征值接近零的符号依赖 BLAS/舍入，**该文件是诊断案例，不是跨平台精确 history 的硬门槛**。正常条件的 fixtures 才用于严格数值一致性检查。
6. CUDA、MPS 仍须独立执行相同检验，随后执行统计等价和端到端性能方案。没有在该设备上执行就不写“已通过”。

日期固定的审计结果不能替代后续提交验证；新增功能须扩展 fixtures 和兼容矩阵，错误结果、nonconvergence 与慢于基线的结果必须保留。
