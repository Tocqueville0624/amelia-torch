# Intel Mac：无 Torch 的实际 wheel/reference 路线

[Run 36274875989](https://github.com/Tocqueville0624/amelia-torch/actions/runs/36274875989) 于 2026-09-26 成功完成，提交为 **`ad9bed2dfd33a7b0e0a6e4050eafc031b1726f3e`**。已独立读取运行状态及完整日志，核验实际输出，未只根据 workflow 配置判断通过。

- 实际系统为 macOS 15.7.9，`platform.machine()` 返回 **x86_64**，Python 3.12.10；R 4.5.3、Amelia 1.8.3。
- 在隔离 venv 中构建并安装 `amelia_torch-0.0.1.dev0-py3-none-any.whl[reference]`。实际导入位置位于 site-packages；`find_spec("torch") is None` 且导入包及 reference 后 `torch` 不在 `sys.modules`，两项断言均成功。
- 原版 R 依赖与本项目 R 源码包成功安装；本路线的运算始终由原版 Amelia CPU 执行。
- 实际运行 `examples/python_r_downstream.py`，完成 Python 原版插补 → RDS → R 变换、追加、headless PDF、CSV 导出 → Python 读回，并通过派生值及旧份结果保留检查。日志包含示例最后的确认行。

这关闭了“Intel Mac 安装 wheel[reference]、不装 Torch 的实际插补及下游例子”这一有限验证项。该任务没有运行整个 pytest 套件，没有测试 Intel Mac 的 hybrid/Torch、GPU 或交互式 GUI。PDF 文件检查不等于图形视觉验收。此提交也不包含稍后的 G3 frontend 修复。

工作流没有上传或打印 wheel 的 SHA-256，因此该字段如实为 null；不能用另一台机器构建的 wheel 哈希代替。公开证据仅保留便携字段及示例完成行，完整 runner 日志不复制进仓库。

[机器可读记录、job 链接及提交内源码哈希](intel-mac-reference.json)
