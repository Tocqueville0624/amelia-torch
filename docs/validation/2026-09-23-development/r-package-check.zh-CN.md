# R 包检查：2026-09-23

[English](r-package-check.md) · [文档目录](../../README.zh-CN.md)

开发 R 包 ameliatorch 0.0.0.9000 在 Mac 26.6.2/Apple Silicon、R 4.5.3/Amelia 1.8.3/reticulate 1.47.0 及Python3.12 项目环境（amelia-torch 0.0.1.dev 0）安装并检查。

五个已安装包测试文件通过：bridge（环境、CPU32/64、名称/观察值/全空行/seed/形状/拒绝参数）；compatibility（原版输出/RNG、追加、类别/变换/面板/先验/边界、不初始化Python）；reference_metadata（来源，无拟合）；torch-compat（CPU64混合代表案例）；downstream（摘要、PDF、pooling、CSV、arglist/追加/moPrep/allthetas及两种正态 RNG）。

独立临时目录的源码 tarball 完整 R CMD check 也通过五文件，0 错误/0 警告/0 NOTE，Status: OK。此前修复 RNG 桥、caller frame、未限定 tail 和 Rd 多余转义；C helper 由 Appleclang 16 编译，注册及编译代码检查通过。CRAN/Bioconductor 索引网络不可用，已安装依赖检查通过；不证明远端仓库、CRAN投稿、其他系统、GPU 或交互RStudio可用。

复现先显式选择现有环境：

```sh
export R_LIBS_USER="$PWD/.R-library"
export RETICULATE_PYTHON="$PWD/.venv/bin/python"
R CMD INSTALL --library="$R_LIBS_USER" r-package
Rscript r-package/tests/bridge.R
Rscript r-package/tests/compatibility.R
Rscript r-package/tests/reference_metadata.R
Rscript r-package/tests/downstream.R
```

在独立临时目录 build/check：

```sh
R CMD build --no-manual --no-build-vignettes <project>/r-package
R CMD check --no-manual --no-build-vignettes ameliatorch_0.0.0.9000.tar.gz
```

Windows 使用 Scripts/python.exe 及对应环境变量语法。

组合 fixture 最初含一行 prior：上游矩阵掉维可能在坐标相等时 code 49，或恢复输出时选择错误单元。原版直接调用与包装结果一致。普通组合改用两行 prior，单行特例单列回归；包装器未改写上游行为。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[r-package-check.log](r-package-check.log) · [r-package-check-sources.json](r-package-check-sources.json)
