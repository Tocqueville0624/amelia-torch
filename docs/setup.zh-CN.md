# 环境与复现

以下命令从项目根目录执行。Python 环境和新增 R 包安装在项目内；不修改系统 Python 或全局 R 库。源码安装 R 包现需要 C 编译器，用于保护原版 R 随机数状态的注册 helper：macOS 用 Xcode Command Line Tools，Windows 用匹配 R 版本的 Rtools，Linux 用系统 R 开发工具链。依赖快照只复现本次 Mac 环境；版本未来可能变化，调整后重新验证并记录。

## Mac：当前环境

已使用原有 Python 3.12.13 和 R 4.5.3，安装的 Python 包见 `requirements-macos-arm64.lock`。该文件是精确版本快照，不含分发文件哈希；不是 Windows CUDA 安装清单。

首次安装/重建：

```sh
UV_CACHE_DIR="$PWD/.cache/uv" uv venv --python 3.12 .venv
UV_CACHE_DIR="$PWD/.cache/uv" uv pip install --python .venv/bin/python -r requirements-macos-arm64.lock
UV_CACHE_DIR="$PWD/.cache/uv" uv pip install --python .venv/bin/python --no-build-isolation --no-deps -e .
Rscript scripts/setup_r.R
R CMD INSTALL --library=.R-library r-package
```

R 安装脚本使用当前 CRAN 二进制包并检查安装成功，不自动覆盖已满足的依赖；本次实际版本写入验证快照。未来正式 R 实验需进一步锁定 R、Amelia、reticulate、依赖与 BLAS，不能把这个初始化脚本当完整 R 锁文件。

若 CRAN 的当前 Amelia 版本已经变化，初始化脚本会明确停止。可在项目根目录下载固定的官方 1.8.3 源码包，校验后安装到项目库；这一步需要上述 C/C++/Fortran 编译工具链。下载器只尝试 CRAN 当前目录和 Archive，并要求 SHA-256 `7699455ca3e9dabd60ad0ec69185ece3f24a597ef8da18033ea0b7a32356967f`，不会换到不同版本：

```sh
python -c "from pathlib import Path; from scripts.cloud_bootstrap import fetch_amelia; p=Path('.cache/Amelia_1.8.3.tar.gz'); p.parent.mkdir(parents=True, exist_ok=True); print(fetch_amelia(p))"
Rscript -e 'lib <- file.path(getwd(), ".R-library"); dir.create(lib, showWarnings=FALSE); .libPaths(c(lib, .libPaths())); install.packages(c("Rcpp", "RcppArmadillo", "rlang", "foreign"), repos="https://cloud.r-project.org", lib=lib); install.packages(".cache/Amelia_1.8.3.tar.gz", repos=NULL, type="source", lib=lib); stopifnot(as.character(packageVersion("Amelia")) == "1.8.3")'
Rscript scripts/setup_r.R
```

这里的 `python` 应为已激活的项目虚拟环境解释器；也可以使用 `.venv/bin/python` 或 Windows 的 `.venv\Scripts\python.exe`。这是固定 Amelia 本体的方法，不能代替其余 R 依赖版本的完整锁定。

验证：

```sh
PYTORCH_ENABLE_MPS_FALLBACK=0 .venv/bin/python -m amelia_torch.diagnostics --require-device mps --output results/local/mac_probe.json
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests scripts
Rscript scripts/smoke_amelia.R
Rscript scripts/smoke_r_bridge.R
```

若受限工具进程无法访问 GPU，在有相应权限的本机终端重试，保存两次报告；不要通过开启自动 CPU 回退掩盖问题。`--require-device` 缺失或任何可用后端的算子检查失败时，检查命令以非零状态退出。

## RStudio

打开 `Amelia_Project.Rproj`，在新的 R 会话运行：

```r
source("scripts/smoke_r_bridge.R")
source("scripts/smoke_amelia.R")
```

脚本自动添加项目 `.R-library`，显式绑定 `.venv`。如当前会话已绑定别的 Python，先重启 R 会话；reticulate 不能在已初始化的解释器之间任意切换。R 包已通过本机安装和 `R CMD check`（0 ERROR/0 WARNING/0 NOTE）；运行 `R CMD INSTALL --library=.R-library r-package` 后可 `library(ameliatorch)`。见 [R 接口说明](r-interface.md)。实际 RStudio GUI 会话及其他机器仍需独立核验。

## Windows CUDA：可选到机复现

用户已授权用云端 CUDA 测试替代本地 RTX 3080；以下保留为其他研究者的可选 Windows CUDA 复现步骤。前提：Windows 10/11 64 位、NVIDIA 驱动、Python 3.12、R、RStudio、uv；这些是待核验/准备清单，不是已在用户 Windows 电脑完成的状态。机器需要能联网安装依赖；支持具体版本以到机时官方信息为准。

1. 把项目源文件复制或通过 Git 同步过去，不复制 `.venv`、`.R-library`、`.cache`。
2. 运行 `nvidia-smi`，记录 GPU 型号、显存、驱动；其显示的 CUDA 版本是驱动支持信息，不等于已安装的 PyTorch runtime。
3. 在 PowerShell 创建环境：

```powershell
uv venv --python 3.12 .venv
```

4. 在 [PyTorch 官方安装选择器](https://pytorch.org/get-started/locally/)选择 Windows / Pip / CUDA，选择兼容 RTX 3080 与驱动的稳定 wheel。将其命令的 `pip install` 替换为 `uv pip install --python .venv\Scripts\python.exe`。本项目只需要 `torch`；保留官方 CUDA index 参数。尽量匹配 Mac 的 torch 2.14.0；不能匹配时记录差异，不能把差异隐去。预编译 wheel 为首选；只有后续编译自定义扩展时再核验 CUDA Toolkit/编译器需求。
5. 安装其余项目依赖并验证：

```powershell
uv pip install --python .venv\Scripts\python.exe -e ".[dev,reference]"
.venv\Scripts\python.exe -m amelia_torch.diagnostics --require-device cuda --output results/local/windows_probe.json
Rscript scripts/setup_r.R
R CMD INSTALL --library=.R-library r-package
.venv\Scripts\python.exe -m pytest -q
Rscript scripts/smoke_amelia.R
Rscript scripts/smoke_r_bridge.R
```

如果 `Rscript` 不在 PATH，可在 RStudio 项目中 `source()` 对应脚本。探针必须显示 CUDA 可用、正确 GPU、实际显存和算子检查成功；仅 `nvidia-smi` 成功不足以证明 PyTorch 能调用 GPU。安装后核对 torch 版本与 CUDA 信息，防止依赖解析替换了刚安装的 wheel。

Windows 初始化成功后再按[基准计划](benchmark-plan.zh-CN.md)运行真正插补实验。本次没有访问或更改 Windows 机器。

## 无 PyTorch 的兼容安装与 Intel Mac

PyTorch 官方已[停止为 2.3 及以后版本提供 macOS x86_64 二进制包](https://dev-discuss.pytorch.org/t/pytorch-macos-x86-builds-deprecation-starting-january-2024/1690)。因此不能把“所有 Mac 都安装最新 torch”作为产品前提。

项目将 PyTorch 设为可选依赖：`pip install '.[reference]'` 安装 Python 的原版 R 兼容入口及数据框支持；其运行仍需 R、Amelia 1.8.3 和 jsonlite。`pip install '.[torch,reference]'` 适用于有受支持 PyTorch wheel 的环境。Windows CUDA/CPU wheel 仍按官方安装选择器先明确选择，不能通过安装选项名称推断驱动可用。

Python 包的顶层导入不应加载 PyTorch；参考路径在没有 torch 的环境中必须单独测试。2026-09-26 已在实际 macOS x86_64 hosted runner 上构建并安装 wheel[reference]，核验未安装/加载 Torch，并完成插补与 Python/RDS/R 下游往返，见 [Intel Mac 实测](validation/2026-09-26-ci/intel-mac-reference.md)。该证据仅覆盖原版 R CPU 路线，不宣称 Intel Mac 的 PyTorch/MPS 支持或交互式 GUI 已测试。
