# G6 Mac RStudio流程

[English](README.md) · [文档目录](../../README.zh-CN.md)

2026-09-26，Mac arm64的实际RStudio 2026.1.1.403 会话完成已安装 reference/hybrid CPU64 插补、解释器选择、保存读回、Data Viewer 和图形视觉检查。只覆盖一个有限交互流程，不代表AmeliaView、其他平台或 GPU/推断验收。

R 4.5.3/Amelia 1.8.3/ameliatorch 0.0.0.9000/Python 3.12/Torch 2.14.0 使用精确项目 venv 解释器，不解析到环境外。合成 120×4 含 ID 和三个连续变量，每路线 m3、R seed 871。两者 code 1、预设 all.equal 1e−6 内一致，观察值精确保留、应补值有限；混合 7/9/6 轮、伪逆 0。

RDS 读回 identical，首份 CSV 在 1e−12 内一致。Data Viewer 显示 12×4，compare.density 在RStudioGD/Plots 绘制，Plot Zoom 可见完整标题、坐标、红蓝曲线和图例。现有会话工作保留。session.json 生成早于视觉检查，Pending 原样保留；后续检查见 independent-visual-review.json。

![RStudio Plot Zoom](rstudio-plot-ui.jpg)

未修改的 2400×1800 JPEG 哈希为 `d97916eed48ec1449295268737d90d2a7a017c4df5aad2b7db51450453f7f371`。diagnostic.png 为导出图，不替代 GUI 证据。公开 CSV 均合成数据；RDS 可能含表达式/环境路径，留在本地。

实际脚本副本哈希 `1e66f712a651c8c5e4c48a3cd5aa2e5806337de6847552993c3444b1a40f15e7`。后续清理顺序收紧为先恢复 Torch 线程再恢复两层 RNG，只做语法检查、未重跑 GUI，源码身份分开。首轮 utils:: View 请求缺失 X11，改为RStudio的 View 后完整流程通过；这是 helper 集成失败，不是插补或RStudio图形缺陷。

复现须在实际RStudio会话执行，替换 checkout 占位路径。results/local/g6-rstudio 下六个同名输出已存在时拒绝覆盖：

```r
local({
  project_root <- normalizePath("path/to/amelia-torch", mustWork = TRUE)
  e <- new.env(parent = globalenv())
  sys.source(file.path(project_root, "scripts", "rstudio_smoke.R"), envir = e)
  e$run_rstudio_smoke(project_root)
})
```

## AmeliaView边界

原版AmeliaView为 R/Tcl/Tk CPU GUI，启动/载入/关闭均未验收。XQuartz依赖缺失，官方 2.8.6 安装包已下载并核验签名/哈希/公证，但未确认安装完成。没有成功 GUI 启动或就绪认证窗口记录。先决条件及未成功安装尝试保留在 xquartz-prerequisite.json，不算 GUI 通过；上述普通RStudio Data Viewer 和图形不需XQuartz。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[session.json](session.json) · [independent-visual-review.json](independent-visual-review.json) · [review.json](review.json) · [rstudio-plot-ui.jpg](rstudio-plot-ui.jpg) · [diagnostic.png](diagnostic.png) · [input.csv](input.csv) · [completed.csv](completed.csv) · [executed-rstudio-smoke.R](executed-rstudio-smoke.R) · [rstudio_smoke.R](../../../scripts/rstudio_smoke.R) · [SHA256SUMS.json](SHA256SUMS.json) · [xquartz-prerequisite.json](xquartz-prerequisite.json)
