# Small attributed data samples

Each `.npz` contains 256 uniformly sampled complete numeric rows from one pinned
UCI archive, with an additional artificial block-MCAR mask. Each matching `.json`
records the source citation, CC BY 4.0 license URL, exact source/output SHA-256,
source row IDs convention, columns, seeds, and transformations. Data licenses
are independent of the software license. See [dataset documentation](../../docs/datasets.zh-CN.md).

These are interface examples, not evidence of large-dataset throughput or valid
coverage. The `data` array is the imputation input. The `truth` array is withheld
evaluation information and must not be supplied to the imputer.

Recreate from the project root, after downloading pinned source archives:

```sh
python scripts/prepare_benchmark_data.py --dataset covertype --rows 256 --output data/samples/covertype.npz
python scripts/prepare_benchmark_data.py --dataset household_power --rows 256 --output data/samples/household_power.npz
python scripts/prepare_benchmark_data.py --dataset year_prediction_msd --rows 256 --output data/samples/year_prediction_msd.npz
```

The preparation script intentionally refuses to overwrite existing files. To
verify reproducibility, write to a different directory and compare the recorded
hashes or arrays. NumPy `.npz` files can be read with `numpy.load(..., allow_pickle=False)`.
