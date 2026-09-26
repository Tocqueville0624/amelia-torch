# 复现实验入口

这些命令从项目根目录运行，先按 [setup.zh-CN.md](setup.zh-CN.md) 建立环境。源码开发版仍有未完成功能；不要用它替换未经兼容性验证的现有研究流程。

## 数据与确定性参考

```sh
.venv/bin/python scripts/download_datasets.py --datasets all --max-download-mib 300
Rscript scripts/export_reference_fixtures.R
.venv/bin/python -m pytest -q
```

为三组数据各生成 100,000 行、约 30% 块状 MCAR 的统一输入：

```sh
.venv/bin/python scripts/prepare_benchmark_data.py --dataset covertype --rows 100000 --mechanism block_mcar --missing-rate 0.3 --seed 20260923 --output data/prepared/covertype-n100000-block_mcar-rate30-seed20260923.npz
.venv/bin/python scripts/prepare_benchmark_data.py --dataset household_power --rows 100000 --mechanism block_mcar --missing-rate 0.3 --seed 20260923 --output data/prepared/household_power-n100000-block_mcar-rate30-seed20260923.npz
.venv/bin/python scripts/prepare_benchmark_data.py --dataset year_prediction_msd --rows 100000 --mechanism block_mcar --missing-rate 0.3 --seed 20260923 --output data/prepared/year_prediction_msd-n100000-block_mcar-rate30-seed20260923.npz
```

Household 只含 7 列，实际遮盖率为 2/7；所有方法共用该输入。默认仅从完整源行抽样，天然全缺失行的剔除和选择偏差见[数据文档](datasets.zh-CN.md)。不是全量原始行的基准，也不是独立逐格缺失。

## 同机端到端基准

Mac MPS：

```sh
PYTORCH_ENABLE_MPS_FALLBACK=0 .venv/bin/python scripts/run_benchmark_suite.py --gpu mps
.venv/bin/python scripts/summarize_benchmarks.py --output-dir results/local/native-audit
```

CPU-only 机器使用 `--gpu none`，汇总时显式指定 `--methods cpu64 cpu32 r_serial r_snow4`；审计器不会把漏跑的 GPU 项目默认为成功。Windows PowerShell 上用 `.venv\Scripts\python.exe`，确认 `Rscript` 在 PATH、CUDA 探针通过后运行：

```powershell
.venv\Scripts\python.exe scripts/run_benchmark_suite.py --gpu cuda
.venv\Scripts\python.exe scripts/summarize_benchmarks.py --methods cpu64 cpu32 cuda64 cuda32 r_serial r_snow4 --output-dir results/local/native-audit
```

每个数据集按固定随机顺序依次执行原版 R 串行、R snow 4 进程、PyTorch CPU float64/float32，以及选定 GPU；CUDA 额外测 float64。每种配置 2 次预热、5 次正式计时，每次生成 5 份插补。GPU 必须同步；默认最多 300 EM 轮，超过上限是未收敛而非成功。原版 R 使用 1.8.3。

原始报告位于 `results/local/benchmarks/main/`。汇总器逐条检查质量与收敛，并把不含私人路径的报告复制到验证文档目录。不要只根据进程正常退出判断全部成功；不要发布含本地绝对路径的 `.config.json`。重复实验请用新 `--output-dir` 保存，避免覆盖旧证据；汇总器指定对应 `--input-dir` 和 `--output-dir`。

计时含预处理、bootstrap、EM、随机补值、设备传输和 CPU 输出；不含文件读取、进程冷启动、质量评分。R snow 的 worker 创建/销毁在计时内。本套件不含 R→Python 桥接成本，尚不能当作 R 用户的完整端到端提速结论。

## 推断质量

```sh
.venv/bin/python scripts/validate_inference.py --output results/local/inference_validation.json
```

默认每种缺失机制生成 200 个独立的 300 行合成数据集，每次 5 份插补。检查 MCAR 与依赖已观测 y 的 MAR 下，OLS 系数的偏差、蒙特卡洛误差与 Rubin pooled 95% 区间覆盖率。该实验仅覆盖指定联合正态模型；不是所有数据的有效性证明，也不是 R/Python 分布等价检验。

完整功能兼容、真实 Windows/Linux 安装、CUDA 及 RTX 3080 的测试仍须后续补齐。

## R 用户混合路线

先安装 `ameliatorch` 并通过兼容测试。已有主基准 CSV 时复用相同输入；尚未生成时加 `--generate-inputs`，从相同准备 NPZ 另写 CSV：

```sh
PYTORCH_ENABLE_MPS_FALLBACK=0 .venv/bin/python scripts/run_hybrid_suite.py --methods cpu64 cpu32 mps32
.venv/bin/python scripts/summarize_hybrid.py --input-dir results/local/benchmarks/hybrid --output-dir results/local/hybrid-audit
.venv/bin/python scripts/compare_hybrid_reference.py --output results/local/hybrid-audit/hybrid-reference-comparison.json
Rscript scripts/plot_benchmarks.R --native results/local/native-audit/benchmark-summary.json --hybrid results/local/hybrid-audit/hybrid-summary.json --output-prefix results/local/figures/timings
```

其中 native 审计目录由前一节生成。Windows CUDA 将 hybrid methods 改为 `cpu64 cpu32 cuda64 cuda32`，配对比较器另加 `--reference-methods cpu64 cpu32 cuda64 cuda32 r_serial r_snow4`；Python 路径使用 `.venv\Scripts\python.exe`。混合路线固定保留 R 预处理、抽样与后处理，只替换 EM，计时包括 R/reticulate 转换；初次 Python 导入和文件读取在计时外。运行期间不要改动被指纹记录的 Python/R 源码，也不要同时做 CPU/GPU 拟合。

配对比较必须等两套实验完整结束且通过独立审计后运行。它按 `phase + seed` 对齐全部预热和正式调用，要求匹配的 R RNG、参数与输入来源，比较已保存的均值、协方差、迭代数和 RMSE；这些汇总不能证明完整插补矩阵逐格等价。新实验使用不同目录时同时指定 `--reference-dir` 和 `--hybrid-dir`。默认要求复用主基准 CSV；`--generate-inputs` 的新 CSV 不自动获得相同历史输入的配对证据。

绘图脚本实际检测图形设备并核验输出文件，生成 PNG 和矢量 PDF；Cairo 可用时另生成 SVG。本机不依赖 XQuartz，PNG 使用 macOS Quartz。已有文件不会被覆盖，重新出图需选择新的 `--output-prefix`。

固定小型 GPU 正确性对照与正式性能测量分开运行：

```sh
PYTORCH_ENABLE_MPS_FALLBACK=0 .venv/bin/python scripts/validate_accelerator.py --device mps --dtype float32 --output results/local/mps-validation.json
PYTORCH_ENABLE_MPS_FALLBACK=0 RETICULATE_PYTHON="$PWD/.venv/bin/python" Rscript scripts/validate_r_accelerator.R mps float32 results/local/r-mps-validation.json
```

R 混合计时不等于 Python→Rscript 混合入口计时，后者还包含进程和二进制文件传输。完整启动成本应另测并标注。
