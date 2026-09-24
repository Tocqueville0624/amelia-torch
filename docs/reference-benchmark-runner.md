# R Amelia benchmark runner

Run from the repository root:

```sh
Rscript scripts/benchmark_reference.R results/local/example-config.json
```

Example configuration (paths are relative to the current working directory):

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

All three CSVs require a header and no row-name column. Input and truth contain
numeric values; missing values may be empty, `NA`, or `NaN`. The heldout mask must
contain numeric 0/1 values and have the same shape; every marked cell must be
missing in the input and finite in truth. Pre-existing unscored missing cells may
remain in input and truth. `parallel` accepts `no` and `snow` to keep the reference
configuration usable on Windows. `warmup_seed` is incremented per warmup and does
not reuse the measured seeds by default.

The script requires Amelia 1.8.3 and sets `R_LIBS_USER` **only in the runner
process**, allowing PSOCK children to find the project's isolated R library. It
uses and records `RNGkind("L'Ecuyer-CMRG")`, which activates the upstream worker RNG
stream initialization. It does not pre-create a cluster. Each timed public call
includes the original package's cluster startup/teardown when `snow` is selected.
Restricted execution environments may deny localhost server sockets: those calls
are recorded as failures rather than silently replaced by serial execution.

Timing starts with the numeric matrix already in memory and stops after the full
Amelia result returns. CSV loading, quality summaries and JSON output are outside
the timed interval. Cold process/package startup and peak RAM are not measured;
the latter is `null`, never a fabricated zero. Timing a process-launch wrapper in
another program measures a different quantity and should be labeled separately.

The JSON has `schema_version`, `implementation`, `version`, `config`,
`timing_contract`, `quality_contract`, `environment`, and `runs`. Each run contains:

- `phase` (`warmup` or `measured`), `repeat_index`, `seed`, `wall_seconds`;
- official `code`, per-imputation `iterations` and `converged_by_tolerance`;
- `warnings`, `error`, `peak_ram_bytes`;
- `quality_status`, per-imputation `observed_values_unchanged`,
  `remaining_missing_cells`, `remaining_missing_rows`, `nonfinite_cells`, and
  `normalized_heldout_rmse` when a valid output exists;
- pooled column means, within/between/total variances for column means, and the
  average completed-data covariance matrix.

JSON serialization may use a scalar for a one-element vector; a consuming driver
should normalize these fields to lists when `m=1`. Missing/error metrics are
`null` or absent as indicated by `quality_status`, not zero. The report is updated
after every completed call, so a failed run is not dropped from the record.

Normalized heldout RMSE divides each error by that truth column's sample SD and
then takes the root mean square across all heldout cells. **If any heldout
prediction is nonfinite, the score is null**, with the missing/nonfinite counts
still reported. Thus a method cannot improve its RMSE by failing on hard cells.
Other runners must use the same policy for comparisons. The mean pooling summaries
are descriptive checks; one dataset and one run do not estimate interval coverage.

On 2026-09-23, an integration smoke with 300 rows, 4 columns, `m=2`, one warmup and
two measured calls succeeded in both serial and two-worker PSOCK modes. Every call
returned code 1, preserved all observed values and produced finite heldout RMSE.
These tiny runs establish the runner works, not a performance result or GPU gain.
