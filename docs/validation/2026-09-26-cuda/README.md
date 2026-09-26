# Colab T4：重新执行的 CUDA 正确性记录

2026-09-26 在新分配的免费 Google Colab Linux VM 实际运行，源码固定为 `fa08a5207d197a3f82ced7913a67bc448c8ecacc`。这不是 Windows 或 RTX 3080 结果，也不是从旧笔记本推算的结果。

## 当前已完成的部分

全部 **15 个步骤退出 0**：CUDA 算子探针、161 项 Python 测试、Ruff、七个 R 测试文件、Python/R 下游示例，以及 native/hybrid 各自的 CUDA float64/float32 固定案例。

- Native 的无先验、经验先验、cell prior 三例，在两个精度下均通过预先存在的门槛。
- R 混合路径的变换、类别、先验/边界三例，每例 m=3，两个精度下全部通过；观察值保留、原版类、收敛、GPU 使用及 theta 对照均通过。最大的标准化连续输出误差约为 float64 `1.43e-15`、float32 `4.65e-7`，离散值分歧均为 0。
- 新的 33 个 public edge 案例在此处仍执行 CPU64；不能把它们记成新增 GPU 边界测试。
- 原版 R 1.8.3 仍负责 hybrid 的准备、bootstrap、draw、恢复和下游方法；GPU 用于 EM，不能称为全流程纯 GPU。

完整步骤与耗时在 [validation-steps.json](correctness/validation-steps.json)，各步骤完整日志及原始结构化报告位于 [correctness](correctness/)。测试耗时不是插补性能基准。

## 实际环境和恢复行为

| 项目 | 实测值 |
|---|---|
| GPU | Tesla T4，15,360 MiB，compute capability 7.5 |
| 驱动 / CUDA | 580.82.07 / 12.8 |
| Python / Torch | 3.12.13 / 2.10.0+cu128 |
| R / Amelia / reticulate | 4.5.3 / 1.8.3 / 1.47.0 |
| 主机 CPU | Intel Xeon @ 2.00 GHz，2 个逻辑核、affinity 2 |
| 主机内存 | MemTotal 13,286,944 KiB |
| TF32 | 显式关闭 |

[bootstrap.json](correctness/bootstrap/bootstrap.json) 保存版本、编译安装步骤、来源哈希和硬件记录。缺少 ensurepip 时用项目缓存内的官方 uv 建立 venv；全局 Ruff 0.15.8 的包装器最初确实缺少二进制，原失败日志保留，然后只在 venv 内重装同版本，复验通过。原有 CUDA Torch 文件和版本没有被替换。

reticulate 仍会对共享系统包环境发出 numpy 依赖探测警告；原警告保留，实际 NumPy 导入及所有拟合对照成功。该警告不能被当作静默忽略计算错误的理由。

## 记录的完整性与范围

运行后将本次 JSON/log/text 报告压缩为 gzip+base64，打印进保存的 notebook，再通过可见页面复制保存到本机。解码前后均核验 SHA-256；这一批压缩记录共 35,892 字节，哈希 `b8ad4014836ea739d20668a065483336be6ad9ce1fda026ccad31609c67e7b94`。共恢复 34 个文件，包含报告与公共数据来源清单。

[checkpoint manifest](correctness-checkpoint-manifest.json) 保留云端原始内容哈希与可公开文本哈希。文本仅把本次项目目录和 home 路径替换成占位符；没有把失败改写为成功，也没有添加缺失结果。原数据包、RDS、已安装库、Google 账号信息和凭据不在此备份内；公共数据清单仍由仓库 `data/manifest.json` 管理。

这批小型正确性检查不能替代大数据性能、Rubin pooling/覆盖率或所有参数组合的验收。正式速度比较另固定到 `905cc79ce20e65fe5b673039d4e411db73cd7544`：只增加可设的线程/worker 预算与其测试，已核实 `src/`、`r-package/` 源码与本次正确性版本完全相同。由于实际只有两个 CPU 核，速度比较统一为两个主机线程、两个 snow worker，每个 worker 一个 BLAS 线程。Mac 的旧四线程记录不改写。
