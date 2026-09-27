# Linux T4 正确性检查

[English](README.md) · [文档目录](../../README.zh-CN.md)

2026-09-26，新 Colab Linux VM 实际执行 `fa08a5207d197a3f82ced7913a67bc448c8ecacc`。15 步全部 exit 0：CUDA探针、161 项Python、Ruff、七个 R 文件、下游示例及原生/混合CUDA64/32 固定案例。不是旧输出恢复或 Windows 证据。

每精度三个原生案例（无先验、经验先验、cell prior）和三个混合案例（变换、类别、先验/边界，m3）通过。混合最大标准化误差约 1.43e−15/4.65e−7，离散不一致 0。33 个公共边界在这里运行 CPU64，不是CUDA；R 预处理/bootstrap/抽样/输出仍 CPU。

环境：Tesla T4、15,360 MiB、能力 7.5、驱动 580.82.07/CUDA 12.8、Python 3.12.13/Torch 2.10.0+cu128、R 4.5.3/Amelia 1.8.3/reticulate 1.47.0、双核 Xeon 2 GHz、主机内存 13,286,944 KiB，TF32关闭。缺 ensurepip 使用记录中的 uv 后备。Ruff 0.15.8 初缺 binary，venv 同版本重装后通过，Torch 未变。共享环境NumPy警告随日志保留，实际导入/拟合成功。

从带哈希 notebook checkpoint 恢复 34 文件：压缩 payload 35,892 bytes，SHA `b8ad4014836ea739d20668a065483336be6ad9ce1fda026ccad31609c67e7b94`。只替换项目/home 路径，不添加缺失结果，无认证、RDS 或安装库。后续性能用 `905cc79`，src/R 包计算源码与此版本一致，统一双线程/双 worker。小案例不证明覆盖率、完整兼容或速度。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[validation-steps.json](correctness/validation-steps.json) · [correctness](correctness/) · [bootstrap.json](correctness/bootstrap/bootstrap.json) · [correctness-checkpoint-manifest.json](correctness-checkpoint-manifest.json)
