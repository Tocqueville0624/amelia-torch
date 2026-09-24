# 初始化验证记录

日期：2026-09-23；机器：Apple M4 iMac，16 GB 统一内存，macOS 26.6.2。

## 通过的检查

- `mac-native.json`：Python 3.12.13 / PyTorch 2.14.0；CPU float64、CPU float32、MPS float32 的 6 类基础算子检查全部通过；MPS CPU 自动回退关闭。确定性矩阵测试仅为 2×2，随机数检查仅验证形状/有限性相关执行，不代表统计分布检验。
- `r-bridge.json`：从 R 4.5.3，经 reticulate 1.47.0 进入项目 Python，并实际执行 CPU/MPS 探针，全部通过。
- `r-reference.json`：Amelia 1.8.3 在 200×3 的合成连续数据上生成 2 份结果，无残余缺失且已观测值保持不变；不包含全缺失行。
- Python 测试：`tests/test_backends.py` 的 4 个测试通过，覆盖 CPU 双精度基准、MPS 禁止静默降精度、不可用 CUDA/MPS 禁止静默回退。
- 代码检查和格式检查通过；README/docs 相对链接检查通过。
- Mac 上要求不可用的 CUDA 时，诊断命令按预期返回退出状态 1。

## 实测边界

此处所有 JSON 是环境/算子或原版 smoke 结果，**不是本项目插补结果，更不是加速结果**。当前源码没有 EM 插补器。CUDA、完整模型数值稳定性、多重插补质量、性能和可发布 R 包仍待后续阶段。

R 桥接以本机 `Rscript` 执行；RStudio 应用已存在，已提供 `.Rproj` 和运行入口，但本次没有在 RStudio 图形界面另行执行演示。

受限进程曾报告 MPS 不可用；取得本机 GPU 访问权限后通过验证。该中间结果保留在忽略版本管理的 `results/local/mac_probe.json`，勿误判为硬件不支持。

初始化时发现并修复了两个脚本问题：全缺失行不适合作为“原版应补满”的默认断言；解析 `.venv/bin/python` 符号链接会使 reticulate 丢失项目环境。二者已在路线图与 Agent 指南中记录。

本地 Git 已初始化为 `main`；没有创建提交、配置远程或发布。快照不包含机器序列号和私人解释器路径。完整 R session 信息仅保留在 `results/local/r_session.txt`。
