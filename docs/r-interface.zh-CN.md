# R 接口

[English](r-interface.md) · [文档目录](README.zh-CN.md)

`ameliatorch` 提供原版参考、混合和原生接口。当前为 GPL-3.0-only 开发包，不是官方 Amelia 或 CRAN 版本。[兼容表](amelia-compatibility.zh-CN.md)和[发布标准](release-gates.zh-CN.md)说明当前范围。

## 安装

原生/混合调用需要 Python 3.12 项目及兼容 Torch。参考调用要求精确 R Amelia 1.8.3，不初始化 Python。包不会自动安装 Python、Torch 或 CUDA。源码安装需要 R 兼容 C 工具链：Mac 命令行工具、Windows 匹配版本 Rtools、Linux R 开发工具链。

```r
.libPaths(c(file.path(getwd(), ".R-library"), .libPaths()))
install.packages("r-package", repos = NULL, type = "source", lib = ".R-library")
library(ameliatorch)
use_amelia_python(venv = ".venv")
check_environment(device = "cpu", dtype = "float64")
```

加载包不初始化 Python。也可在初始化前设置 `python="/path/to/environment/bin/python"`，Windows 为 `C:/path/to/environment/Scripts/python.exe`，或设置 `RETICULATE_PYTHON`。保留解释器符号链接；已初始化后更换解释器须重启 R。遵循 [reticulate 环境选择](https://rstudio.github.io/reticulate/reference/use_python.html)，不调用自动创建环境的 `py_require()`。

## 原版与混合接口

`amelia_compat(x, ..., engine="reference")` 调用原版 S3 公共入口，不改变预处理或 R RNG。保留官方类和字段，附 `amelia_torch_backend` 标明 CPU 参考计算。追加操作记录历史/当前来源及份数，未知历史仍为未知。

`amelia_torch_compat(x, ..., device="cpu", dtype="float64")` 保留 R 预处理、bootstrap、抽样和输出，通过私有查找环境替换 EM，不改 Amelia namespace。副本串行调度。已有 CPU64 变换、名义/有序类别、先验、边界、overimputation、面板和下游方法代表案例。原版诊断仍在 CPU 执行。

两者均使用原版 R 参数名，如 `boot.type`、`max.resample`；缺依赖或版本不符明确报错。注册 C helper 保留 R 内部 RNG 和可见 `.Random.seed`，仅赋值 seed 不足以复现；同时保留原版显式 double 初值回写。混合源码检查仍需已安装的 helper；C 代码变化后用 `R CMD INSTALL --clean --library=.R-library r-package` 重装。

官方 `mi.combine` 需要可选 broom；rlang 为 Amelia import，foreign 提供 DTA 导出。原版区间端点倒序和带符号上尾 p 值行为见 [G1](validation/2026-09-26-g1/downstream-extended.zh-CN.md)，不静默修正。AmeliaView 是独立的交互 R/Tcl/Tk GUI。

## 原生接口

```r
fit <- amelia_torch(
  x,
  m = 5L,
  device = "cpu",
  dtype = "float64",
  seed = 2026,
  boot.type = "ordinary"
)
fit$imputations[[1L]]
fit$diagnostics
```

接口调用 `amelia_torch.amelia()`，执行观察值标准化、bootstrap、条件矩 EM、随机补值和单位恢复。Python 字典含 `imputations` 二维 NumPy 数组列表及 `diagnostics`，其他参数直接传递；R 返回 `ameliatorch_result`，不伪装官方 `amelia` 对象。

接受普通数值矩阵/数据框，保留容器、名称、顺序和观察值；输出数据框列为 numeric。factor、带额外类的数值列、非数值列及不支持的模型参数明确拒绝。全空行仍缺失并保留 NA/NaN；其他分析行输出须有限。观察值改变或排除全空行被填入会报错。

R `boot.type`/`max.resample` 映射到原生 Python `boot_type`/`max_resample`，重复别名报错；别名不代表新增了原本不支持的功能。m 为正整数值标量；seed 支持小于 2^53 的精确非负整数，诊断转换不截断为 32 位。同种子不配对 R/Python 随机流。

## 设备与证据

默认 CPU64。CUDA 精度及 MPS32 须显式选择；设备缺失、精度不支持、算子失败或 MPS 自动 CPU fallback 开启均报错，不静默回退或降精度。

`ef729c0` 三平台 CPU CI 各通过 307 项 Python、九个 R 文件及下游示例。Windows RTX 3080 和 Linux T4 有独立固定 CUDA 与性能记录。Mac RStudio 已安装包会话完成 reference/hybrid CPU64、读回、Data Viewer 和可见图形。这些证据不覆盖所有 GUI/设备/模型组合，也不完成统计验收。见[证据摘要](validation/2026-09-27-evidence-summary.zh-CN.md)。

## 开发检查

原生源码加载方式：

```r
.libPaths(c(file.path(getwd(), ".R-library"), .libPaths()))
source("r-package/R/environment.R")
source("r-package/R/amelia.R")
use_amelia_python(venv = ".venv")
check_environment("cpu", "float64")
```

`r-package/tests/bridge.R` 的实际桥接检查要求显式 `RETICULATE_PYTHON`，缺配置记为跳过。`AMELIATORCH_R_SOURCE=r-package` 选择源码函数，不替代包安装/check。当前文档整理阶段不启动新测试。
