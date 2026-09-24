# Python 调用官方 R Amelia 的兼容过渡路径

`amelia_reference` 使用**原版 R Amelia 1.8.3、CPU**。它完整保留官方预处理、bootstrap、EM、抽样、输出和 R 对象，不调用 PyTorch，也不产生任何 GPU 加速声明。它与 native 连续数据实现及实验性 Torch EM 兼容引擎明确分开；完整功能目标仍需逐项验收，不能仅因能够转发参数就宣布首版完成。

Python 安装包需要包含 `_r/reference_bridge.R`。运行环境需要可执行的 Rscript、**精确版本 Amelia 1.8.3** 和 jsonlite。pandas 是 DataFrame/factor 支持的可选依赖。已安装用户的正常 R 库会被使用；源码工作目录若包含 `.R-library/Amelia`，自动使用项目隔离库，仅作为开发便利。也可显式指定 `rscript` 和 `r_library`。不会修改用户的 R 启动文件。

```python
from amelia_torch.reference import amelia_reference

result = amelia_reference(
    data,
    m=5,
    seed=20260923,
    p2s=0,
    idvars=["respondent_id"],
    noms=["region"],
    ords=["agreement"],
    logs=["income"],
)
completed = result.imputations[0]
result.save_rds("official-amelia-result.rds")
print(result.metadata)  # engine=r-amelia-reference, cpu, gpu_used=False
```

参数使用**原版 R 名称及 1-based 行列索引**。例如 priors 的四列是行、列、均值、标准差；这里没有低层 PyTorch 的“标准化方差”替换。含点参数用字典展开：

```python
result = amelia_reference(
    data, m=2, p2s=0,
    priors=[[1, 3, 0.5, 0.05], [10, 3, 0.5, 0.05]],
    bounds=[[3, 0, 1]],
    **{"boot.type": "none", "max.resample": 100},
)
```

所有已知原版选项都通过数据编码传递，由 Amelia 自己检查组合及模型含义。未知名称会明确报错，防止把 `boot_type` 等非 R 参数静默忽略。`logs`、`sqrts`、`lgstc`、`noms`、`ords`、`priors`、`bounds`、`overimp`、`ts`、`cs`、时间 basis、lag/lead、先验与并行参数都采用官方流程；不在此桥接层重写数学。

**原版 1.8.3 的单行 priors 特例：**已通过独立 R 公共调用核验，`impfill` 中 `priors[, c(1,2)]` 对单行矩阵会掉维，导致原本的 `(row, column)` 索引变成线性向量索引，可能改动不相关的已观察值，包括字符 idvars。本桥保留原版输出，并在显式传入单行 priors 时返回 warning；不会为了让“观察值不变”测试通过而篡改官方结果。普通两个及以上先验行的接口测试独立验证观察值保留，单行行为另有回归测试。研究者应在使用该原版边界组合前检查其结果；本项目尚不将这一上游行为宣称为修复。

NumPy 二维数值输入返回 NumPy 数组。pandas DataFrame 采用逐列编码，保留缺失位置、列名、factor 类别顺序与 ordered 标记，以及 R 输出中的 numeric/integer/logical/character 类型。显式 nullable 整数、字符串即使整列缺失，也按其已知类型编码。R 官方行为可能把需要连续插补的整数列提升到 double；桥接不会强行取整。datetime/复杂 Python 对象须由用户先明确转换。超过 `2**53` 的整数不能在 R double 中精确表示，因此拒绝静默传输。列名转换为 R 字符串后必须仍然唯一；例如 `1` 与 `"1"` 并存会明确报错。

大表的数值不会逐格展开成 JSON。transport schema 2 使用显式 little-endian 的二进制列文件：double 为 IEEE754 float64（8 bytes），integer/logical/factor codes 为 int32（4 bytes），R 整数缺失哨兵为 `-2147483648`，double 缺失编码为 NaN。factor 使用 R 的 1-based codes；levels、字符及小 schema 使用 JSON。两端验证行数、字节长度、数据类型、字节序和缺失编码；数值输入/每份插补分别读写。100,000 × 90 的 double 数据每份为 72 MB 的列数据，不会因为文本浮点数展开而膨胀到数百 MB。RDS、输入和多份输出仍会占用内存及临时磁盘，调用者需为其保留空间。

同次调用及 `extend` 保留 Python 的列标签和 index。原版 RDS 保存的是 R 对象：重新读取后标签遵循 R 的字符串表示，Python 专属 MultiIndex、扩展 dtype 等并不伪装成 R 对象内已有的信息。字符、factor、ordered、逻辑和普通数值列仍能从 R 类型恢复。读取带类别的结果需要 pandas；纯数值 RDS 可指定 `return_type="numpy"`。

```python
from amelia_torch.reference import read_reference_rds, RDSValue

loaded = read_reference_rds("official-amelia-result.rds", return_type="pandas")
more = loaded.extend(m=5, seed=20260924, p2s=0)
more.save_rds("official-amelia-result-extended.rds")

# args.rds 是在 R 中 saveRDS(fit$arguments, "args.rds") 保存的原生对象。
another = amelia_reference(data, m=5, arglist=RDSValue("args.rds"), p2s=0)
```

追加调用使用原版 `amelia.amelia` 方法。该版本会复用保存的模型参数，忽略通过 `...` 传来的新模型设置，因此 Python 的 `extend` 仅允许 m、seed、p2s、frontend 等执行设置；改变模型须以原始数据重新拟合。Python 中修改 `imputations` 不会改变保存的原版 RDS，也不会影响追加调用。

`metadata` 区分**这次调用**与**历史结果来源**。新拟合明确记录 R CPU；外部 RDS 仅有 `amelia` 类不能证明其原始引擎，因此无 backend 属性时 `engine="unknown"`、`torch_used/gpu_used=null`。有 `amelia_torch_backend`（兼容旧 `ameliatorch_backend`）属性时保留其记录。追加使用 `engine="appended-history"`，同时保留旧来源、旧/新份数及本次 `call_engine="r-amelia-reference"`、`call_gpu_used=False`。历史结果来自 GPU 时，不能把整个追加结果称为纯 CPU。Python 对象直接 `extend` 会携带内存中的 provenance；`save_rds` 不给官方对象添加私有属性，故无原始 backend 属性的 RDS 重新读取后来源仍为 unknown。需要保留 Python 调用来源记录时，应把 `metadata` 另存为 JSON。

原版诊断继续在 R/RStudio 使用，不声称已经把每个 R 诊断函数移植到 Python：

```r
fit <- readRDS("official-amelia-result.rds")
summary(fit)
Amelia::compare.density(fit, var = "income")
```

R 中的活跃连接、PSOCK cluster、GUI 环境不能作为 Python 对象跨子进程传输；使用原版 R 工作流处理这些对象。常规 `parallel="snow", ncpus=...` 由官方 Amelia 创建 worker。若需要可复现的 R 并行流，显式设 `r_rng_kind="L'Ecuyer-CMRG"`；相同 seed 不表示 R/PyTorch 数值抽样逐一相同。

跨进程 RDS 必须自包含。例如原版 `moPrep` 的 molist `$data` 保存的是调用表达式，可能引用创建时 R 会话中的局部变量。保存给 Python 前应在原 R 会话把 `prepared$data` 设为实际数据再 `saveRDS(prepared, ...)`；否则新的 Rscript 会话无法恢复那些外部绑定。直接在 R 中使用原版或本包接口时无需为跨进程传输做这一步。

桥接使用参数列表启动 Rscript，配置、矩阵、类别和对象路径都通过临时 JSON/二进制列/RDS 传递，没有把用户字符串拼接成 shell 或可执行 R 代码。完整官方 RDS 可以保存给后续诊断。官方错误携带原始错误码抛出 `AmeliaReferenceError`；若官方返回部分失败结果，异常的 `partial_rds` 保留其原始 RDS 字节，避免将部分结果伪装成成功。达到迭代上限却由原版报告 code=1 的情况，在 metadata 的 `converged_by_tolerance` 和 warnings 中明确展示。

schema 序列化、二进制 I/O、子进程启动、完整 RDS 及输入输出转换都会产生开销。这条兼容路径的耗时必须单独测量，不能用 native Python 基准替代，也不能把任何 CPU 兼容结果称为 GPU 加速。

开发状态：Mac 上的数值、类别、变换、先验、边界、二进制传输、RDS 重读与追加、历史来源标注已运行集成测试；这不构成全部原版 API 的验收。跨 Windows/Linux 的安装和调用仍需独立验证。

## Python 调用实验性 R/PyTorch 混合引擎

`amelia_torch_compat` 使用同一个 typed binary/RDS 通道，调用已安装 R 包的 `ameliatorch::amelia_torch_compat`。原版 Amelia 1.8.3 负责预处理、bootstrap、R 随机流、条件补值、类别抽样和后处理；**仅 EM 交给 PyTorch**。需要同时安装 `ameliatorch` R 包以及当前 Python 环境的 PyTorch。reference 入口仍无需安装或导入 PyTorch。

```python
from amelia_torch import amelia_torch_compat

hybrid = amelia_torch_compat(
    data, m=5, seed=20260923, p2s=0,
    device="cpu", dtype="float64",  # 默认设置
    noms=["region"], logs=["income"],
)
hybrid.save_rds("hybrid-result.rds")
more_hybrid = hybrid.extend(m=2, seed=20260924, p2s=0)
```

`device="cuda"` 必须在本机可用；`device="mps"` 必须同时显式选择 `dtype="float32"`。设备不可用会报错，不自动切换。当前只支持原版串行副本调度；`parallel="snow", ncpus>1` 等组合明确拒绝。本入口不承诺速度优势，运行时仍有 R CPU 计算、子进程、二进制传输和 RDS 开销。

桥接在子进程环境中将 `RETICULATE_PYTHON` 绑定到**当前运行的 Python 解释器**，保留虚拟环境路径，不修改用户环境或启动文件。`metadata` 包含本次引擎、device、dtype、`torch_used/gpu_used`、R CPU 工作范围以及每份 EM 的诊断。`hybrid.extend()` 保留所选混合引擎和设备。若只从磁盘读取 RDS，历史引擎记录依然保留，但 `read_reference_rds(...).extend()` 默认执行原版 R reference；重新选择混合引擎应显式使用：

```python
more_hybrid = amelia_torch_compat(
    input_rds="hybrid-result.rds", m=2, seed=20260924,
    device="cpu", dtype="float64", p2s=0,
)
```

在 Mac CPU float64 下对照的是**同一 R 随机实现**和公共调用流程，因此可以核验相同 seed 的结果及迭代数；这不同于 native NumPy/PyTorch 随机抽样，不能把这个对照推广成跨随机库逐值相等保证。

混合 R 包包含两个无外部依赖的注册 C helper，用于分别保存/恢复 R 内部随机状态与 R 可见 `.Random.seed`。原版 1.8.3 补值函数可能只推进内部状态；如果只保存 `.Random.seed`，无 bootstrap 的多份结果会在进入 reticulate 时意外重复随机数。该同步保护覆盖 Python 初始化和每次确定性 EM，保留原版结束时的可见状态及后续 R 随机调用语义。源码安装 R 包需要对应平台的 R C 编译工具链；纯 Python→原版 reference 入口不需要这个项目 R 包。
