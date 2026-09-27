# 从一次插补理解 amelia-torch

这个项目要回答两个问题：迁移计算后是否保留 Amelia 1.8.3 的统计过程，研究者实际调用时是否更快。目前仍是开发快照。[算法契约](algorithm-contract.md)固定语义；[native 入口](../src/amelia_torch/api.py)处理连续数值数据，[R 混合入口](../r-package/R/torch_compat.R)保留原版预处理、bootstrap、抽样与后处理，只替换 EM。两条路线的功能与计时不能混为一谈。

连续数据先按观察值标准化，再为每份插补抽取 bootstrap 样本。EM 根据当前均值和协方差计算缺失部分的条件矩，更新参数并检查原版收敛规则；达到迭代上限仍未收敛必须报告。随后对原始样本随机补值，恢复单位和行列顺序。bootstrap 提供参数的不确定性，条件抽样保留给定参数后的缺失值不确定性，因此多重插补不是重复填入同一个预测均值。

考虑一个手算例子，协方差矩阵的非对角项不能省略：

$$
\begin{pmatrix}X\\Y\end{pmatrix}\sim N\!\left[
\begin{pmatrix}10\\20\end{pmatrix},
\begin{pmatrix}4&3\\3&9\end{pmatrix}\right].
$$

若这一行观察到 $X=12$，而 $Y$ 缺失，则

$$
E(Y\mid X=12)=20+\frac34(12-10)=21.5,\qquad
\operatorname{Var}(Y\mid X=12)=9-\frac{3^2}{4}=6.75.
$$

EM 所需的二阶矩是 $E(Y^2\mid X)=21.5^2+6.75=469$，而非只有均值平方。丢掉 6.75 就丢掉了条件不确定性。最终补值从这个条件正态分布抽样；多维缺失时还要保留条件协方差。对应代码在 [EM 条件矩](../src/amelia_torch/em.py)与 [Cholesky 条件抽样](../src/amelia_torch/imputation.py)。这是解释公式的例子，不是新实验结果。

常规连续输入只写回缺失格，观察值从原数据恢复，避免 float32 转换改动已知数值。全空行依原版移出拟合，输出仍保留缺失；不能为了“填满”而改算法。原版单行 priors 等已知例外另按契约记录，不把异常藏进质量评分。

CPU float64 是数值参考。MPS 必须显式选 float32，CUDA 可显式选 float64 或 float32；设备不可用不能偷偷回退。精度会影响迭代与结果，因而 CPU64→GPU32 的差异同时包含精度变化。同整数 seed 也不证明 R 与 NumPy PCG64 使用相同随机流。

速度应在同一主机、同一路线、同精度下比较，包含设备传输并同步 GPU。R 用户还要测完整 R 流程及桥接成本；仅测 EM 核心不足以代表产品。已公开的 [T4 native 结果](validation/2026-09-26-colab-native/README.md)在三组各十万行的块状 MCAR 任务上显示同精度 GPU 路线更快；[Mac 结果](validation/2026-09-23-development/README.md)中 MPS 则慢于同精度 CPU。两台机器不能拼成加速比。[Mac G5 推断验证](validation/2026-09-26-g5-mps/README.md)全部拟合完成，但预设统计门槛未全部通过；收敛、低 RMSE 与有效推断是不同检查。

理解接口可从已有的 [Python→R→Python 小例子](../examples/README.md)开始。按[安装说明](setup.zh-CN.md)准备参考依赖及本项目 R 包后，在项目根目录运行：

```sh
.venv/bin/python examples/python_r_downstream.py --output results/local/walkthrough-reference --r-library .R-library
```

Windows 使用 `.venv\Scripts\python.exe`；输出目录必须是新的。例子默认走原版 R CPU：72 行数据生成两份插补，保存 RDS，在 R 中派生交互项、追加一份并导出，再由 Python 读回。先看 `roundtrip.json` 的引擎、三份结果与旧份保留检查，再对照[示例源码](../examples/python_r_downstream.py)。理解这条数据往返链，才能进一步判断换成混合计算后哪些工作仍留在 CPU。
