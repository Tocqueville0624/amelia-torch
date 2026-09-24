# 免费 Colab CUDA 验证与记录

这里提供云端执行步骤，不代表以下测试已经通过。报告必须使用实际 GPU 名称；Colab 的 Linux/T4 结果不能称作 Windows 或 RTX 3080 结果。Windows 安装和 RStudio 的验收仍分别保留。

官方 Colab [过去运行时说明](https://research.google.com/colaboratory/runtime-version-faq.html)列有 Python 3.12 镜像，但默认镜像会改变。2026-09-23 实际首次分配的免费 T4 环境为 Python 3.13.15、Torch 2.11.0+cu128、R 4.6.1。该项目当前要求 Python 3.12，因此先在 Runtime → Change runtime type 选择可用的 Python 3.12 过去镜像，再实际检查。不能仅根据文档推断当前 VM 的版本。

免费资源没有供应或完整运行时长保证。失败、额度不足、断线都保留记录；不自动购买积分，不用其他账户或非官方代理绕开限制。当前运行期间不要更换 runtime；CPU 和 CUDA 必须在同一个 GPU VM 中测试。[官方资源说明](https://research.google.com/colaboratory/faq.html)

## 1. 固定源码与检查 Python

在 GPU notebook 里执行以下 Python cell。把 `REVISION` 替换为要验证的完整 Git commit；应包含本文与 bootstrap 脚本。使用一个新目录，不覆盖现有实验。

```python
import os, pathlib, re, subprocess, sys

assert sys.version_info[:2] == (3, 12), sys.version
REVISION = "REPLACE_WITH_THE_40_CHARACTER_GIT_COMMIT"
assert re.fullmatch(r"[0-9a-f]{40}", REVISION)
REPO = pathlib.Path("/content/amelia-torch")
assert not REPO.exists(), "Use a new checkout directory; retain earlier results"
subprocess.run(["git", "clone", "--filter=blob:none",
                "https://github.com/Tocqueville0624/amelia-torch.git", str(REPO)], check=True)
subprocess.run(["git", "checkout", "--detach", REVISION], cwd=REPO, check=True)
os.chdir(REPO)
os.environ.update({
    "R_LIBS_USER": str(REPO / ".R-library"),
    "RETICULATE_PYTHON": str(REPO / ".venv/bin/python"),
    "OMP_NUM_THREADS": "4", "OPENBLAS_NUM_THREADS": "4", "MKL_NUM_THREADS": "4",
    "VECLIB_MAXIMUM_THREADS": "4", "NVIDIA_TF32_OVERRIDE": "0",
    "PYTORCH_ENABLE_MPS_FALLBACK": "0", "CUDA_VISIBLE_DEVICES": "0",
})
subprocess.run([sys.executable, "scripts/cloud_bootstrap.py",
                "--expected-commit", REVISION], check=True)  # Plan only.
```

## 2. 建立隔离环境

```python
subprocess.run([sys.executable, "scripts/cloud_bootstrap.py",
                "--expected-commit", REVISION, "--execute"], check=True)
PYTHON = str(REPO / ".venv/bin/python")
```

脚本不进行拟合，也不下载或替换 Torch。它要求当前运行时的 CUDA Torch 为 `>=2.10,<3`，创建带 `--system-site-packages` 的 `.venv`，复用相同 Torch 文件，并安装项目、测试和 pandas 依赖。这是与 Colab 基础环境共享已装包的项目环境，不是完全隔离的依赖锁；具体 Python/R 包版本写入报告，后续复现应保留相同镜像和这些记录。不要拿 Mac 的 lock 文件安装 CUDA。

若该镜像缺少 `ensurepip`，脚本仅为这一失败启用 [uv 官方工具](https://docs.astral.sh/uv/getting-started/installation/)的项目缓存安装，再以同一个 Python 解释器、相同 system-site-packages 设置建立并 seed venv；记录 uv 的实际版本。不会用另一套 Python 或自动改变 CUDA wheel。

原版 Amelia 使用下列源码与 SHA-256，当前地址不可用时仅回退到 CRAN 官方 Archive 同版本，校验不符即停止：

- `https://cran.r-project.org/src/contrib/Amelia_1.8.3.tar.gz`
- `https://cran.r-project.org/src/contrib/Archive/Amelia/Amelia_1.8.3.tar.gz`
- SHA-256：`7699455ca3e9dabd60ad0ec69185ece3f24a597ef8da18033ea0b7a32356967f`

R 依赖和固定 Amelia 装入 `.R-library`，然后执行现有 `setup_r.R` 和 `R CMD INSTALL --clean r-package`。若环境缺少 R/编译器，脚本明确失败；可保留失败目录后，用新的输出目录追加 `--install-system-packages --output-dir results/local/cloud/bootstrap-2` 重试。这会通过 `apt-get` 安装系统依赖，仅适用于用户已授权的云端 VM。不要在 Mac 上执行。

`results/local/cloud/bootstrap/bootstrap.json` 记录 Git commit、所有已跟踪文件的哈希、CUDA/驱动/GPU、CPU 型号/可见核心/affinity/cgroup 配额、内存、版本、安装步骤及失败；同目录含安装日志和 Python 包版本列表。不读取机器序列号、主机名或全量环境变量。输出目录存在时拒绝覆盖。

## 3. 先过正确性检查

```python
def run(*args):
    subprocess.run(list(args), cwd=REPO, check=True)

run(PYTHON, "-m", "amelia_torch.diagnostics", "--require-device", "cuda",
    "--output", "results/local/cloud/cuda-probe.json")
run(PYTHON, "-m", "pytest", "-q")
for dtype in ("float64", "float32"):
    run(PYTHON, "scripts/validate_accelerator.py", "--device", "cuda", "--dtype", dtype,
        "--output", f"results/local/cloud/native-{dtype}-validation.json")
    run("Rscript", "scripts/validate_r_accelerator.R", "cuda", dtype,
        f"results/local/cloud/r-{dtype}-validation.json")
```

`NVIDIA_TF32_OVERRIDE=0` 显式禁用 TF32；所有拟合在新子进程里执行，不复用 notebook 已初始化的 Torch/R 状态。探针包含 CUDA float64/float32 基础算子；小型参考对照还检查 EM 和补值。任何失败都保留，不能调宽阈值后把原失败记为成功。通过这些检查不等于所有算法功能或推断质量已验收。

## 4. 三组公共数据与同机计时

```python
run(PYTHON, "scripts/download_datasets.py", "--datasets", "all", "--max-download-mib", "300")
for dataset in ("covertype", "household_power", "year_prediction_msd"):
    target = f"data/prepared/{dataset}-n100000-block_mcar-rate30-seed20260923.npz"
    run(PYTHON, "scripts/prepare_benchmark_data.py", "--dataset", dataset,
        "--rows", "100000", "--mechanism", "block_mcar", "--missing-rate", "0.3",
        "--seed", "20260923", "--output", target)
```

三个原始压缩包共约 232 MiB，下载器按 `data/manifest.json` 检查大小、哈希及 ZIP CRC，保留至少 5 GiB 磁盘余量。每组抽样 100k 完整行，采用约 30% 块状 MCAR；Household 实际为 2/7。它不是全量数据或逐格独立 MCAR。统计语境、来源和 CC BY 4.0 归属见 [datasets.zh-CN.md](datasets.zh-CN.md)。已有输入不能覆盖，重复实验复用同一组 NPZ。

下面两格分别执行并保存，勿与其他拟合并发，也不要在计时期间编辑项目源文件。主套件固定四线程/四个 snow worker，即使免费 VM 可用核心少于四个也必须记录超额线程这一局限；不能将它宣称为最优 CPU 配置。若要改变线程预算，先调整并固定全部对应方案，再新建实验，不能只改变某一个方法。

```python
NATIVE = "results/local/cloud/native"
HYBRID = "results/local/cloud/hybrid"
assert not pathlib.Path(NATIVE).exists(), "Choose a fresh result directory"
run(PYTHON, "scripts/run_benchmark_suite.py", "--gpu", "cuda", "--output-dir", NATIVE,
    "--rows", "100000", "--m", "5", "--warmups", "2", "--repeats", "5")
```

```python
assert not pathlib.Path(HYBRID).exists(), "Choose a fresh result directory"
run(PYTHON, "scripts/run_hybrid_suite.py", "--methods", "cpu64", "cpu32", "cuda64", "cuda32",
    "--csv-dir", f"{NATIVE}/inputs", "--output-dir", HYBRID,
    "--rows", "100000", "--m", "5", "--warmups", "2", "--repeats", "5", "--threads", "4")
```

主套件比较原版 R 串行、snow4、native Torch CPU64/32 与 CUDA64/32。混合套件保留 R 全流程，只替换 EM，复用主套件同一 CSV。每配置两次预热、五次正式运行、每次五份插补；CUDA 计时同步由已有实现处理。两个套件的墙钟时间不同，应保留顺序与共享云主机负载局限。

计时包含各入口的预处理、EM、随机补值及 CPU 输出；文件读取、安装、进程启动和评分在计时外。混合计时包含 R/reticulate 的转换，不包括 Python→Rscript 的启动/二进制传输开销。免费 GPU 已分配期间运行 CPU 对照也消耗这次会话配额。

## 5. 审计、保存与释放资源

报告逐配置写盘。套件途中断线时，保留现有目录和失败日志；不要直接在原目录重跑。首先单独审计已完成报告，明确整套实验是否完整。主汇总器默认为 Mac 方法，CUDA 必须显式选择：

```python
run(PYTHON, "scripts/summarize_benchmarks.py", "--input-dir", NATIVE,
    "--output-dir", "results/local/cloud/native-audit",
    "--methods", "r_serial", "r_snow4", "cpu64", "cpu32", "cuda64", "cuda32")
run(PYTHON, "scripts/summarize_hybrid.py", "--input-dir", HYBRID,
    "--output-dir", "results/local/cloud/hybrid-audit")
```

不能只凭进程 exit 0 宣称速度结果有效：检查所有请求配置齐全、收敛、观察值保留、应补值有限、heldout 无漏计及审计退出码。报告包含全部重复，不能只挑成功或最快子集。随后使用同机 CPU/CUDA 比值；Mac 耗时仅作另一台机器的独立结果。三组吞吐测试仍不能替代 Rubin pooling/覆盖率等推断质量门槛。

每完成一个主要 cell，或任何异常后，执行保存格。它只打包本次结果、准备数据及其元数据和公开来源清单，不包括 `.venv`、`.R-library`、Google 凭据或 Drive 内容。包可能几百 MiB，下载完成前不要删除 runtime。Google Drive 挂载是可选且另需用户授权，不是运行前提。

```python
import hashlib, tarfile, time
from google.colab import files

archive = pathlib.Path(f"/content/amelia-cuda-records-{int(time.time())}.tar.gz")
with tarfile.open(archive, "w:gz") as bundle:
    for item in ("results/local/cloud", "data/prepared", "data/manifest.json",
                 "THIRD_PARTY.md", "LICENSE", "docs/cloud-cuda.md"):
        path = REPO / item
        if path.exists():
            bundle.add(path, arcname=item)
digest = hashlib.sha256()
with archive.open("rb") as stream:
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
print({"artifact": archive.name, "bytes": archive.stat().st_size, "sha256": digest.hexdigest()})
files.download(str(archive))
```

将 notebook 通过 File → Download → `.ipynb` 另存，收到本机后核验下载文件哈希，再断开并删除 Colab runtime。公开 GitHub 前使用已清理的审计报告；原始 `.config.json` 和 R 日志可能含 VM 绝对路径，保留作本地记录，不直接发布。未测的内容、失败与平台范围一并写入验证说明。
