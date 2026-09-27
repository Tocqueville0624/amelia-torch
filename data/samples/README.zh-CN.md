# 带归属的数据小样本

[English](README.md) · [文档目录](../../docs/README.zh-CN.md)

每个 NPZ 含从固定 UCI 归档均匀抽取的 256 个完整数值行，再施加人工块状MCAR掩码。对应JSON记录来源引用、CC BY 4.0 链接、源/输出 SHA-256、行 ID 规则、列、种子及变换。数据与软件许可独立，详见[数据说明](../../docs/datasets.zh-CN.md)。

这些样本用于接口示例，不是大数据吞吐或区间覆盖率证据。`data`是插补输入；`truth`仅供保留评估，不得传给插补器。

下载固定来源归档后，从仓库根目录重建：

```sh
python scripts/prepare_benchmark_data.py --dataset covertype --rows 256 --output data/samples/covertype.npz
python scripts/prepare_benchmark_data.py --dataset household_power --rows 256 --output data/samples/household_power.npz
python scripts/prepare_benchmark_data.py --dataset year_prediction_msd --rows 256 --output data/samples/year_prediction_msd.npz
```

准备脚本拒绝覆盖已有文件。复核时写入其他目录，再比较数组或记录的哈希。用 `numpy.load(..., allow_pickle=False)` 读取 NPZ。
