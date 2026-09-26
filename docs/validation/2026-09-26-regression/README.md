# 2026-09-26 本机完整回归

新增 Python 类型/会话边界、R 并行和统计验收工具后，完整 Python 回归 **235 passed**，Ruff 通过。该计数包含当时尚未提交的 G7 三项审计测试，逐文件哈希见 [checks.json](checks.json)，不把它冒称历史 CI 的计数。

从 R 源码重新构建 tarball，并在独立临时目录运行 `R CMD check --no-manual --no-build-vignettes`，包含全部 **9 个 R 测试文件**，结果 **0 errors / 0 warnings / 0 notes，Status: OK**。原 build/check 日志替换本机路径并去除文件末尾空行，见 [build.log](build.log)、[check.log](check.log)。并行测试需要本机 worker 通信，运行获得了必要执行权限。

此记录是 Apple Silicon 本机代码/安装回归，不是新的 GPU 性能或统计质量结论。RStudio 视觉流程和后续三平台 CI 分开记录。
