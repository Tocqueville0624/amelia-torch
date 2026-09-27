# G1 打包

[English](packaging.md) · [文档目录](../../README.zh-CN.md)

2026-09-26 的打包检查中，下游测试与Python/R 示例已加入三平台 CPU 工作流，显式要求 broom/foreign（DESCRIPTION Suggests），避免 pooling 静默跳过。工作流配置本身不证明后续 hosted 执行。

wheel 成功构建并安装临时目标，实际从 wheel 导入，内嵌 reference_bridge.R 与源码逐字节一致，两个公共 R 入口导入不加载 Torch。元数据正常依赖NumPy/SciPy，reference 额外依赖 pandas，torch 额外依赖 Torch。

独立Python3.12.13 venv 仅安装 wheel[reference]及NumPy2.5.3/SciPy 1.18.1/pandas 3.0.6/dateutil 2.9.0.post 0/six 1.17.0，无 Torch。复用本机 R 安装完成原版插补、RDS、R 变换/原版追加、PDF/CSV/pooling 和Python读回，旧值与派生列通过。独立示例属于仓库，不承诺包含在 wheel；此非新 R 安装、Intel Mac、hosted CI、GPU 或PyPI/CRAN发布。

显式初值修复安装后，新源码 tarball 在独立临时目录完整 R CMD check，七个 R 文件全部通过，0 错误/警告/NOTE、Status: OK，C helper 编译及 Suggests 检查通过。首轮发现 R_TESTS 被嵌套 Rscript 继承为失效路径，测试在子进程前后仅清除/恢复该变量，最小复现后重新 build/check 通过，未改数值实现。远端CRAN/Bioconductor 索引不可用，已安装依赖通过；不验证远端供应。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[python_r_downstream.py](../../../examples/python_r_downstream.py) · [r-package-check.log](r-package-check.log) · [r-package-source-hashes.json](r-package-source-hashes.json) · [packaging.json](packaging.json)
