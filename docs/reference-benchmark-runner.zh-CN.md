# R Amelia 基准执行器

[English](reference-benchmark-runner.md) · [文档目录](README.zh-CN.md)

在仓库根目录运行：

```sh
Rscript scripts/benchmark_reference.R results/local/example-config.json
```

配置示例，路径相对当前目录：

```json
{
  "input_csv": "data/benchmark/input.csv",
  "truth_csv": "data/benchmark/truth.csv",
  "mask_csv": "data/benchmark/heldout_mask.csv",
  "m": 5,
  "seeds": [20260923, 20260924, 20260925, 20260926, 20260927],
  "warmups": 2,
  "warmup_seed": 20360923,
  "ncpus": 2,
  "parallel": "snow",
  "empri": 0,
  "autopri": 0,
  "tolerance": 0.0001,
  "emburn": [0, 500],
  "startvals": 0,
  "boot.type": "ordinary",
  "output_json": "results/local/amelia-snow.json"
}
```

三份 CSV 均须有表头、无行名列。输入和 truth 为数值，缺失可为空、NA 或NaN。heldout 掩码为同形状 0/1 矩阵；标记格必须在输入缺失、在 truth 有限。原有未评分缺失可保留。`parallel` 接受 no/snow，兼容 Windows。预热种子逐次递增，默认不重复正式种子。

执行器要求 Amelia 1.8.3，仅在自身进程设置 R_LIBS_USER 供 PSOCK 子进程查找项目 R 库。使用并记录 `RNGkind("L'Ecuyer-CMRG")`，不预建 cluster。snow 公共调用计入 worker 创建/销毁；受限环境禁止 localhost socket 时记录失败，不改为串行。

计时从内存数值矩阵开始，到完整 Amelia 结果返回。CSV 读取、评分和JSON写出在计时外；不测进程冷启动/首次包导入或峰值 RAM，未测内存为 null。另一个程序包裹进程启动的耗时是不同指标。

报告含 schema_version、implementation、version、config、timing_contract、quality_contract、environment、runs。每次记录阶段、序号、seed、wall_seconds、原版 code、逐份 iterations/converged_by_tolerance、警告/错误/内存、quality_status、观察值保留、剩余缺失、非有限数及归一化 heldout RMSE，并提供列均值、Rubin 均值方差和平均完成数据协方差。

m=1 时JSON可能用标量表示单元素向量，读取方需规范为列表。错误/缺失指标为 null 或缺省，不填 0。每次调用后更新报告，失败不删除。

归一化RMSE以真值列样本 SD 缩放误差，再对全部 heldout 求均方根。任一 heldout 预测非有限时，完整评分为 null，同时保留缺失/非有限计数，不能仅评分容易的子集。均值合并摘要不能从单个数据集估计区间覆盖率。

2026-09-23 的 300×4、m2、一次预热/两次正式集成检查在串行和 snow2 均成功：code 1、观察值保留、heldout RMSE有限。这只验证执行器，不构成性能收益。
