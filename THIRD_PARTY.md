# 来源、归属与许可证状态

## Amelia 参考实现

本项目依据 James Honaker、Gary King、Matthew Blackwell 的 Amelia 方法及官方源代码核对统计语义；不把 EMB 算法归为本项目原创。

- 参考版本：Amelia 1.8.3。
- 官方来源：https://cran.r-project.org/src/contrib/Amelia_1.8.3.tar.gz
- 归档 SHA-256：`7699455ca3e9dabd60ad0ec69185ece3f24a597ef8da18033ea0b7a32356967f`。
- 原包声明许可证：GPL (>= 2)。
- 本地审计参考包括 `R/emb.r`、`R/prep.r`、`R/amcheck.r`、`src/em.cpp`，详细语义和特例见 `docs/algorithm-contract.md`。
- 原包存放在忽略的 `.cache/upstream/`；参考 fixture 由本项目合成数据通过原版导出，生成代码及出处位于 `scripts/export_reference_fixtures.R` 和 `tests/fixtures/reference_amelia/README.md`。

当前 Python 代码根据已审计流程编写。应以 GPL 兼容方式处理该移植工作；所有者已于 2026-09-23 选择 GPL-3.0；项目按 GPL-3.0-only 分发，完整许可文本见根目录 LICENSE。原版来源及作者归属继续保留，不因移植而替换。

## 数据集

Covertype、Individual Household Electric Power Consumption、YearPredictionMSD 的 UCI 官方页面标明 CC BY 4.0。来源、作者归属、DOI、下载地址、哈希和样本说明集中记录于 `data/manifest.json`、`data/samples/README.md` 和 `docs/datasets.zh-CN.md`。数据许可与软件许可分别适用；公开分发时保留归属信息。

## 依赖

PyTorch、NumPy、SciPy、reticulate 及其他依赖保持各自许可。项目不将第三方虚拟环境、R 库或下载缓存打包提交。
