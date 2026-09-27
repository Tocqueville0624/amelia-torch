# Intel Mac 无 Torch 参考 wheel

[English](intel-mac-reference.md) · [文档目录](../../README.zh-CN.md)

[运行36274875989](https://github.com/Tocqueville0624/amelia-torch/actions/runs/36274875989)于 2026-09-26 在 `ad9bed2dfd33a7b0e0a6e4050eafc031b1726f3e` 通过。日志核验macOS15.7.9、实际x86_64、Python 3.12.10、R 4.5.3、Amelia 1.8.3。

隔离 venv 构建/安装 `amelia_torch-0.0.1.dev0-py3-none-any.whl[reference]`，从 site-packages 导入，断言 Torch 既未安装也未加载。原版 R 依赖和项目 R 源码包安装成功。示例完成原版拟合、RDS 交换、R 变换/追加/headless PDF/CSV、Python读回、派生值及旧份保留。

仅覆盖参考 CPU 安装及实际下游流程，不是完整 pytest、Intel hybrid/Torch、GPU 或交互 GUI；提交早于 G3 frontend 修复。未上传/打印 wheel 哈希，因此字段保持 null，不能以其他机器构建值补造。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[intel-mac-reference.json](intel-mac-reference.json)
