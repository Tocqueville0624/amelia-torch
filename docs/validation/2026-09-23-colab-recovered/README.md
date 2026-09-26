# 旧 Colab 验证输出恢复记录

**恢复日期为 2026-09-26；这不是一次新的云端运行，也不是 CUDA 性能基准。** 本目录从本地保存的 `amelia-torch-cuda-validation-20260923.ipynb` 提取必要代码和 stdout。原 Colab VM 已断开，原 VM 中的 bootstrap/validation JSON、完整日志及拟合产物未能取回。

原文件 SHA-256 为 `98df0afa88b3fc805dd3bbe39496f177f4dc9330a42f36dca98a6717b06d393b`。原始 notebook 不公开，以免包含 Google 账户、notebook/单元格标识或输出元数据。提取过程只解析 JSON，不执行任何 notebook 代码。

## 可以确认的历史输出

保存的 cell 声明固定源码 commit `6865b6521142338c6812ce6a9f6414349321ff25`，其 bootstrap 尾部打印 `Setup passed` 和 `BOOTSTRAP_EXIT 0`。这支持旧 cell 所记录的执行，不等于重新核验已经消失的 VM 源码或完整环境。

| 项目 | 保存输出中的信息 |
|---|---|
| 平台 | Linux，Tesla T4；不是 Windows 或 RTX 3080 |
| Python / Torch | Python 3.12.13；Torch 2.10.0+cu128；CUDA runtime 12.8 |
| R | Rscript 4.5.3；安装输出显示 Amelia 1.8.3 |
| GPU / 驱动 | Torch 报告 15,637,086,208 字节显存；nvidia-smi 报告 15,360 MiB、驱动 580.82.07；保留两个工具的原值 |
| 基础 CUDA 探针 | exit 0；保存尾部包含 CUDA float64/float32 算子检查，设备为 cuda:0，TF32 标记为 false |
| Python 测试 | exit 0，`149 passed` |
| R 测试 | 5 个文件 exit 0：bridge、compatibility、torch-compat、reference_metadata、downstream |
| native CUDA 对照 | float64 和 float32 各 3 个固定案例，输出均为 passed，两个进程均 exit 0 |
| R hybrid CUDA 对照 | float64 和 float32 各 3 个固定案例，输出均为 TRUE，两个进程均 exit 0 |
| Ruff | exit 1：Python 包装器抛出 `RuffNotFound`，未找到可执行文件；已装 Ruff 版本未出现在保存片段中 |
| 完整验证格 | **失败**：12 个步骤中 11 个 exit 0，1 个 exit 1；最后抛出 `AssertionError` |

R hybrid 的 transformed、categorical、prior_bounds 三个可见案例中，float64 打印的最大标准化连续误差最高为 `1.427514e-15`，float32 最高为 `4.646445e-7`，离散不一致计数均为 0。这些只是打印精度下的小型固定案例结果，不是全部 Amelia 功能、推断覆盖率或完整输出等价的证明。

多个成功的 R 子进程仍打印了 reticulate 的 NumPy requirement 警告。本目录保留该警告，不能凭 exit 0 就把它写成“已解决”。

## 证据文件及截断限制

- [可审计恢复摘要](recovered-summary.json)：原文件哈希、声明的源码版本、12 个步骤的退出码及 stdout 行号、提取文件哈希和脱敏计数。
- [初始探针 stdout](probe.stdout.txt)：Python/Torch/GPU 基础信息、float64 Cholesky、nvidia-smi 与 Rscript 版本。
- [bootstrap stdout 尾部](bootstrap-tail.stdout.txt)：旧 cell 原本只打印安装输出的最后 12,000 字符。
- [验证 stdout 尾部](validation-tails.stdout.txt)：旧 cell 对每个子进程原本只打印最后 2,200 字符。CUDA 探针在此处是被截断的 JSON 尾部，不能当作完整 `cuda-probe.json`。
- [最终异常](final-error.txt)：原断言失败的异常类型与信息。
- [执行 cell 的脱敏代码文本](executed-cells.sanitized.py.txt)：用于核对命令、返回码收集和截断逻辑；含路径占位符，不是直接重放脚本。

未导出 notebook、cell 或 output 的 metadata，也未导出异常 traceback 中的 notebook 标识。保留工具版本、公开仓库 commit、GPU 型号等必要复现信息；本机/临时路径改为占位符，邮箱、Google 链接、IP 和 GPU UUID 经过脱敏规则检查。摘要保留选中文本脱敏前后的哈希，原始敏感文件仍只在本地。

## 后续验证范围

Ruff 的旧失败没有被改写为通过。当前 bootstrap 已新增实际 Ruff CLI 检查及虚拟环境内同版本恢复，但修复是否在新 VM 上通过，需要独立的新运行记录。

旧 notebook 未运行新增的 public-edge-cases、downstream_extended 两个 R 文件，也未运行新增 Python→RDS→R 下游示例或对 examples 的 Ruff 检查。当前重跑清单见[云端验证指南](../../cloud-cuda.md)。新代码、G1/G2 回归及完整 CUDA 性能/统计验收不能由这份旧记录替代。该 notebook 没有三组公开数据的 CUDA 耗时结果，因此没有据此建立任何 GPU 加速结论。

提取的项目 cell 代码适用仓库的 [GPL-3.0-only 许可](../../../LICENSE)。Amelia、PyTorch、R 和其他第三方工具的来源与归属见 [THIRD_PARTY.md](../../../THIRD_PARTY.md)；本目录不把第三方软件输出声明为本项目独立算法成果。
