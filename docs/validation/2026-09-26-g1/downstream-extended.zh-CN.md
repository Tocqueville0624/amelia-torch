# G1 下游方法

[English](downstream-extended.md) · [文档目录](../../README.zh-CN.md)

2026-09-26，Mac arm64、R 4.5.3/Amelia 1.8.3/ameliatorch 0.0.0.9000、Python 3.12.13/Torch 2.14.0、hybrid CPU64 运行 downstream_extended.R，无跳过分支。新增小型 API 检查，未改拟合代码；随后七文件 R 包 check 通过，后续提交的 hosted 结果另记。

覆盖：两份 m2 结果 ameliabind、四份旧 draw 保留、缺失位置/empri 不同的原版错误；交互项 transform 后 m1 追加及调用归档；with/lm→mi.combine 两种区间设置(.90)；summary/compare/overimpute PDF；分开 tab 表及带 factor 标签、自定义 draw_id、orig.data=FALSE的合并 DTA；四个 60 行moPrep分支（error.proportion、subset/gold.standard、proxy、已有 molist 增补）；实际Python/RDS/R/Python读回。原版 bind 丢失后端时来源保持 unknown。

主合成输入 72 行含 a/b/y、ID 和 factor。theta 容差 1e−7、结果/下游 1e−6、导出读回 1e−12、手算 prior SD 1e−14；旧数据/类别/掩码/参数严格比较。broom 1.0.12 通过；私有依赖探测环境触发原版缺 broom 错误，未卸载包，是故障注入而非干净缺包系统。

保留上游行为：mi.combine 区间倒序，带符号上尾 p 值可大于 1；兼容不证明推断解释正确。table 传 sep 须显式 separate=TRUE，DTA 在 caller 绑定 foreign:: write.dta，readRDS后 S3 泛型前加载 Amelia namespace。原版/混合示例均完成 RDS/CSV/PDF/JSON往返。PDF 结构检查不是 GUI 视觉验收，本项不完成 GPU/推断质量。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[downstream_extended.R](../../../r-package/tests/downstream_extended.R) · [downstream.R](../../../r-package/tests/downstream.R) · [python_r_downstream.py](../../../examples/python_r_downstream.py) · [downstream-extended.json](downstream-extended.json)

```sh
R_LIBS_USER="$PWD/.R-library" RETICULATE_PYTHON="$PWD/.venv/bin/python" \
  Rscript r-package/tests/downstream_extended.R
```
