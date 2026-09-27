# Public datasets

[简体中文](datasets.zh-CN.md) · [Documentation](README.md)

The three UCI archives were downloaded and checked on 2026-09-23: SHA-256, ZIP CRC, full decompression/row traversal, field counts and natural missingness. This page documents preparation, not statistical validity. Later [Mac/T4/Windows results](validation/2026-09-27-evidence-summary.md) are separate.

| Dataset | Source rows | Selected numeric columns | Compressed bytes | Text bytes | One complete float64 matrix |
|---|---:|---:|---:|---:|---:|
| Covertype | 581,012 | 10 | 11,251,206 | 75,169,317 | 44.3 MiB |
| Household Power | 2,075,259 | 7 | 20,640,916 | 132,960,755 | 110.8 MiB |
| Year Prediction MSD | 515,345 | 90 | 211,011,981 | 448,576,698 | 353.9 MiB |

Total archives: 242,904,103 bytes, about 231.7 MiB. The downloader reserves 5 GiB free disk by default. Matrix sizes exclude bootstrap, masks, groups, bridge copies and workspace; five full Year outputs alone need about 1.73 GiB. [manifest.json](../data/manifest.json) records citations, URLs, exact sizes, compressed/uncompressed hashes, audits and column choices. Project-computed hashes are version fingerprints, not UCI signatures.

## Sources and selection

**Covertype.** [UCI](https://archive.ics.uci.edu/dataset/31/covertype) contains 581,012 records, 54 features and a label, with no missing values. This workload retains the first 10 measurements, excluding 4 wilderness dummies, 40 soil dummies and the target. Aspect is circular and some measurements are integer-recorded; treating them numerically is a throughput/model-misspecification exercise, not validation of Gaussian assumptions or categorical compatibility. Citation: Blackard, J.(1998), DOI [10.24432/C50K5N](https://doi.org/10.24432/C50K5N).

**Household Power.** [UCI](https://archive.ics.uci.edu/dataset/235/individual+household+electric+power+consumption) contains nearly four years of minute observations from one household. Retain 7 measurements, excluding Date/Time; source row IDs locate observations. Full traversal found 25,979 entirely missing numeric rows (181,853 cells), leaving 2,049,280 complete rows. Parse both `?` and empty strings. Natural missing values lack truth, so controlled benchmarks select complete rows before masking; this selection boundary is explicit. `--natural-missing preserve` is a separate all-missing-row compatibility stress route. Time dependence, zeros, skew and measurement relationships remain; numeric throughput does not validate time-series imputation. Citation: Hebrail, G.&Berard, A.(2006), DOI [10.24432/C58K54](https://doi.org/10.24432/C58K54).

**Year Prediction MSD.** [UCI](https://archive.ics.uci.edu/dataset/203/yearpredictionmsd) has 515,345 songs and 90 timbre features (12 means, 78 covariance descriptors). Exclude release year from 91 source columns; no natural missingness was found. Official prediction uses 463,715 training and 51,630 test rows to limit artist leakage. Random imputation samples are not song-year prediction scores; any prediction study must respect that split. Independent-cell missingness in 90 dimensions can create nearly one pattern per row; retain such difficult outcomes. Citation: Bertin-Mahieux, T.(2011), DOI [10.24432/C50K61](https://doi.org/10.24432/C50K61).

These datasets vary width, row count and distribution but are not representative social-science samples. Fidelity relies on original-reference tests and known-generating-model simulations. UCI HIGGS is only a possible later workload, not downloaded or required as a third dataset.

## Licensing and downloads

All three UCI pages identify **CC BY 4.0**. Preserve authors, title, DOI, [license](https://creativecommons.org/licenses/by/4.0/) and modification descriptions with redistribution; do not imply endorsement. Software licensing is separate. Git contains manifests, scripts and attributed samples. `data/raw/` and `data/prepared/` are ignored; full data use pinned official downloads. No Release data attachments have been uploaded. Year's archive exceeds the ordinary Git 100 MiB limit; any later hosting must retain attribution and checksums.

```sh
.venv/bin/python scripts/download_datasets.py --datasets all --dry-run
.venv/bin/python scripts/download_datasets.py --datasets all --max-download-mib 300
.venv/bin/python scripts/download_datasets.py --datasets all --verify-only
```

Use `.venv\Scripts\python.exe` on Windows. Select individual dataset IDs if needed. Downloads stream to `.part`, enforce byte/free-space budgets, and rename only after hash/CRC checks; completed files are not overwritten. ZIP members are read without extracting archive paths. HTTP Range requires a matching 206 response. The observed UCI endpoint returned 200 and lacked HEAD length, so resumption was not guaranteed; retain partial files and use `--restart` only to restart an incomplete download. `--accept-unpinned` is for initial source audits, not normal reproduction. Investigate changed upstream content instead of silently accepting it.

## Prepared inputs

```sh
.venv/bin/python scripts/prepare_benchmark_data.py --dataset covertype --rows 10000 --output data/prepared/covertype-n10000-block_mcar.npz
.venv/bin/python scripts/prepare_benchmark_data.py --dataset household_power --rows 10000 --output data/prepared/household_power-n10000-block_mcar.npz
.venv/bin/python scripts/prepare_benchmark_data.py --dataset year_prediction_msd --rows 10000 --output data/prepared/year_prediction_msd-n10000-block_mcar.npz
```

The recorded 10k-row preliminary inputs had 8/7/8 patterns. Seven Household columns cause duplicate requested patterns; integer mask widths determine the actual rate. Later inputs use `--missing-rate 0.3 --seed 20260923`; m belongs to the imputer, not preparation.

| Dataset | Rows | Mechanism | Actual missingness | Patterns K | Entirely missing rows |
|---|---:|---|---:|---:|---:|
| covertype |100,000|block_mcar|30.000%|8|0|
| household_power |100,000|block_mcar|28.571%|7|0|
| year_prediction_msd |100,000|block_mcar|30.000%|8|0|
| covertype |5,000|mcar|29.752%|779|0|
| household_power |5,000|mcar|29.706%|125|2|
| year_prediction_msd |5,000|mcar|30.017%|5,000|0|

Paths follow `data/prepared/{dataset}-n{rows}-{mechanism}-rate30-seed20260923.npz`, with JSON metadata. Checks confirmed finite truth, exact artificial masks, unchanged unmasked values and no empty columns. Preserve Household's two all-missing rows and Year's5,000 patterns; dropping difficult rows changes the experiment.

The parser traverses the full source, verifies rows/fields, uniformly samples eligible rows without replacement, and restores source order. Optional prefix sampling must be labeled. Only compressed source archives are retained. Default preparation array budget is 2,048 MiB, separate from fitting memory.

NPZ fields: `data` is the shared imputer input; `truth` is heldout evaluation information, never an imputer/tuning input; `artificial_missing_mask` and `natural_missing_mask` separate mechanisms; `source_row_ids` are 0-based original rows; `column_names` fixes column order. JSON records provenance, hashes, shape, seeds, sampling, natural-missing handling, realized rates and K. R uses the same arrays/masks.

`block_mcar` assigns a finite predefined pattern independently of values. `mcar` masks observed cells independently and may create empty rows/many patterns. `mar` retains the first selected variable and masks others using a calibrated logistic function of that observed anchor; naturally missing anchors are rejected. Seeds reproduce the current NumPy environment; long-term replication also needs saved arrays, row IDs, hashes and versions.

## Preparation evidence and limits

All three archives passed complete read/CRC/hash audits with no infinities. Prepared records include three 10k preliminary, three 100k block-MCAR, three 5k independent-MCAR inputs and three 256-row attributed samples. Twelve offline preparation tests covered corrupt/unpinned rejection, existing-file verification, ignored Range, provenance, masks, MAR anchors and samples. Formal block-MCAR benchmarks subsequently ran on Mac/T4/Windows. Broader independent-cell, scaling and total RAM/VRAM studies remain incomplete. Masked-data RMSE does not establish Rubin coverage; follow the [benchmark plan](benchmark-plan.md).
