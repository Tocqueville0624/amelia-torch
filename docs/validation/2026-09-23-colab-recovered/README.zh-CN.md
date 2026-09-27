# Colab 历史输出恢复

[English](README.md) · [文档目录](../../README.zh-CN.md)

2026-09-26 从已保存 notebook 恢复，未新增执行或性能测量。原 VM 的JSON、完整日志和结果无法取回。私有 notebook 哈希为 `98df0afa88b3fc805dd3bbe39496f177f4dc9330a42f36dca98a6717b06d393b`，仅解析JSON，不执行代码。

保存 cell 声明源码 `6865b6521142338c6812ce6a9f6414349321ff25`，打印 bootstrap exit 0，环境为 Linux Tesla T4、Python 3.12.13/Torch 2.10.0+cu128/CUDA 12.8、R 4.5.3/Amelia 1.8.3、驱动 580.82.07。Torch 显存 15,637,086,208 bytes 与 nvidia-smi 15,360 MiB均按工具原值保留。

12 步中 11 步 exit 0：CUDA64/32 探针、149 项Python、五个 R 文件、每精度各三个原生和三个混合案例。Ruff 因 Ruff Not Found 失败，整格以AssertionError结束。混合最大标准化误差打印为 64 位 1.427514e−15、32 位 4.646445e−7，离散不一致 0。reticulate NumPy警告在本历史记录中未解决。

bootstrap 仅保存末 12,000 字符，各验证进程末 2,200 字符。截断探针JSON不是完整报告。脱敏代码、尾部输出、异常和恢复清单保留源哈希及脱敏计数，不含账号/cell 元数据。不由此推断后续公共边界/下游扩展通过或数据集耗时。提取的项目代码保留GPL-3.0-only 归属。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[recovered-summary.json](recovered-summary.json) · [probe.stdout.txt](probe.stdout.txt) · [bootstrap-tail.stdout.txt](bootstrap-tail.stdout.txt) · [validation-tails.stdout.txt](validation-tails.stdout.txt) · [final-error.txt](final-error.txt) · [executed-cells.sanitized.py.txt](executed-cells.sanitized.py.txt) · [LICENSE](../../../LICENSE)
