# R 下游检查

[English](r-downstream-validation.md) · [文档目录](../../README.zh-CN.md)

小型合成数据、CPU64、Amelia 1.8.3 的 `r-package/tests/downstream.R` 检查 API/格式/数值，不测性能或统计验收。

普通 bootstrap 下通过：print/summary 文本对照；compare.density、missmap、overimpute、tscsPlot、disperse 的临时 PDF 与数值返回对照；mi.meld 回归估计/SE 及手算 Rubin；分开/合并 CSV 读回；arglist 复用及追加保留旧份；局部moPrep对照；内部allthetas初列、上三角向量、维度及 history。disperse 仅两条短链，overimputation 和时间图各十次 draw。官方诊断/pooling 仍在 CPU，PDF 文件检查不算视觉审查。

boot.none, m2 最初发现混合第二份重复第一份 draw，而原版不同，确定性 EM 参数相符。原版 C 随机状态与 reticulate 边界交互是原因；注册 C snapshot/restore 同时保留内部状态和可见.Random.seed，不额外消耗随机数。安装包完整测试在 Inversion/Box–Muller（每份奇数正态数）下通过，核验结果、最终 seed 和随后 runif(6)/rnorm(6)。

局部moPrep还暴露 caller frame 问题：参考入口改在调用者 frame 执行原版，混合在该 frame 解析保存的数据表达式，随后原版对照通过，不改统计算法。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。
