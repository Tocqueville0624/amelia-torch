# G7 Python调用成本与MCAR压力

[English](README.md) · [文档目录](../../README.zh-CN.md)

九次预定公共调用、每次 m5，于 2026-09-26 UTC 22:07:03–22:09:03 完成。M4/Mac arm64、Python 3.12.13/NumPy 2.5.3/Torch 2.14.0/R 4.5.3/Amelia 1.8.3。计划在拟合前固定输入哈希、16 源码、顺序和质量规则。工作区含未提交修改，以指纹/源码 ZIP 而非背景 commit 标签标识测量代码。

统一 seed 20260926、L'Ecuyer-CMRG/Inversion/Rejection、ordinary、startvals 0、tolerance 1e−4、emburn 0/300、autopri=0.05、empri NULL、串行副本。线程变量请求 4，不代表实测每个BLAS池。CPU64、显式 MPS32/fallback 0 且保留 CPU 特征值检查。

Python完整计时从内存数组，经二进制传输、新 Rscript、R 加载、混合Python/Torch 初始化、插补、CPU 结果/RDS 字节回传，到子进程退出/临时清理。父进程导入、NPZ 读取、评分、哈希和随后 save_rds 不计。每次新 R 进程，首次/后续只指父调用顺序，不是冷 OS 或持续 R。后台负载未完全隔离，旧 R 内存计时不配对，不能相减为桥接成本。

| Covertype 100k×10，块状MCAR30%，8 模式 | 首次 | 后续 1 | 后续 2 | 后续中位数 |
|---|---:|---:|---:|---:|
| Reference |12.144 s|12.114 s|11.804 s|11.959 s|
| Hybrid CPU64 |11.966 s|12.047 s|12.210 s|12.128 s|

六次均通过收敛、观察值和 300,000 heldout 完整评分，轮数 52/41/43/72/59。每引擎三次 RDS 哈希内部相同，不要求两引擎相同。输出数组 40,000,000 bytes，RDS 18,627,244/18,628,077 bytes，是结果体积非峰值内存；两次后续不足以确定 1%差距稳定。

| Household 5000×7，独立MCAR | 完整调用 | 每份未评分 heldout | 状态 |
|---|---:|---:|---|
| Reference |.561 s|14|heldout_incomplete|
| Hybrid CPU64 |2.812 s|14|heldout_incomplete|
| Hybrid MPS32 |24.271 s|14|heldout_incomplete|

遮盖 29.7057%、125 模式、10,397 heldout，含两条全空行。按原版仍 NA，不为评分修补掩码/行。全部拟合收敛(18/14/15/16/12)、观察值精确保留、其余补值有限。完整RMSE为 null；混合拟合模式 124/124/122/124/124，无伪逆/校正/警告/OOM。各路线仅一次且精度不同，不构成质量成功加速或模式数因果曲线。

45 份均返回/收敛，source/input guard 通过。driver exit 1 保留压力评分不完整；独立审计通过记录完整性，但 all_runs_valid_for_speed_comparison=false。总 RAM/VRAM为 null，无CUDA或推断等价声明。新运行须新计划/目录，预期压力失败也须审计。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[plan.json](plan.json) · [measured-source.zip](measured-source.zip) · [source-snapshot.json](source-snapshot.json) · [manifest.json](../../../data/manifest.json) · [results.json](results.json) · [audit.json](audit.json) · [validate_product_costs.py](../../../scripts/validate_product_costs.py) · [test_product_costs.py](../../../tests/test_product_costs.py)

```sh
.venv/bin/python scripts/prepare_benchmark_data.py --dataset covertype --rows 100000 --mechanism block_mcar --missing-rate 0.3 --seed 20260923 --output data/prepared/covertype-n100000-block_mcar-rate30-seed20260923.npz
.venv/bin/python scripts/prepare_benchmark_data.py --dataset household_power --rows 5000 --mechanism mcar --missing-rate 0.3 --seed 20260923 --output data/prepared/household_power-n5000-mcar-rate30-seed20260923.npz
.venv/bin/python scripts/validate_product_costs.py --write-plan results/local/g7-new/plan.json
.venv/bin/python scripts/validate_product_costs.py --execute results/local/g7-new/plan.json --output results/local/g7-new/results.json
# Expected exit 1 for unscored entirely missing rows; retain the audit.
.venv/bin/python scripts/summarize_product_costs.py results/local/g7-new/plan.json results/local/g7-new/results.json --output results/local/g7-new/audit.json
```
