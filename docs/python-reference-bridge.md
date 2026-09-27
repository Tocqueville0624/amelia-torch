# Python/R compatibility bridge

[简体中文](python-reference-bridge.zh-CN.md) · [Documentation](README.md)

`amelia_reference()` runs unmodified **R Amelia 1.8.3 on CPU**, retaining preprocessing, bootstrap, EM, draws and official output. It does not import Torch or claim GPU acceleration. Forwarding options is not complete compatibility acceptance.

## Dependencies and arguments

The wheel includes `_r/reference_bridge.R`. Runtime dependencies are Rscript, exact Amelia 1.8.3 and jsonlite; pandas optionally supports DataFrame/factor transport. Normal R libraries are used, or the project `.R-library` when present; explicit `rscript`/`r_library` override selection without editing startup files.

```python
from amelia_torch.reference import amelia_reference

result = amelia_reference(
    data,
    m=5,
    seed=20260923,
    p2s=0,
    idvars=["respondent_id"],
    noms=["region"],
    ords=["agreement"],
    logs=["income"],
)
completed = result.imputations[0]
result.save_rds("official-amelia-result.rds")
print(result.metadata)  # engine=r-amelia-reference, cpu, gpu_used=False
```

Use original R names and **1-based indices**. Public four-column priors specify row, column, mean, SD, not low-level standardized variance. Dotted names use dictionary expansion:

```python
result = amelia_reference(
    data, m=2, p2s=0,
    priors=[[1, 3, 0.5, 0.05], [10, 3, 0.5, 0.05]],
    bounds=[[3, 0, 1]],
    **{"boot.type": "none", "max.resample": 100},
)
```

Known options are encoded as data and checked by Amelia. Unknown names, including native-style `boot_type`, fail. Original transformations, categories, priors, bounds, overimputation, time structure and parallel options retain their R meaning. Single-row priors can change unrelated observed values through an upstream indexing defect; the bridge preserves the result and warns. Multi-row priors retain independent observed-value checks. The documented all-missing-character-ID/noms exception also remains. See [contract](algorithm-contract.md) and [G3](validation/2026-09-26-g3/README.md).

## Data representation

Numeric 2D NumPy input returns arrays. DataFrame transport preserves supported numeric/integer/logical/character columns, missingness, category order/ordered flags and labels. Explicit nullable types remain typed even when wholly missing. Original R may promote integer IDs to double; the bridge does not round them back. Datetime, complex, mixed object and SciPy sparse inputs are rejected. Arrow has no general support claim. Integers beyond 2^53 cannot silently pass through R double. Names must remain unique after conversion to R strings.

Schema 2 writes little-endian binary columns: IEEE 754 float64, int32 integer/logical/factor codes, R integer-NA sentinel−2147483648 and NaN double missingness. Factors use 1-based codes; levels, strings and schema use JSON. Both ends validate lengths, types, byte order and missing codes. A 100000×90 double input uses 72 MB of column bytes; RDS, temporary files and multiple outputs require additional space.

In-memory calls and `extend` preserve Python labels and duplicate indices. RDS stores an R object: rereading uses R string labels and does not invent Python MultiIndex, duplicate indices or extension dtypes. External RDS Date/custom numeric classes appear as plain strings/numbers in the Python view, while authoritative RDS bytes retain R classes/attributes. Categoricals require pandas; numeric RDS can use `return_type="numpy"`.

## RDS and extension

```python
from amelia_torch.reference import read_reference_rds, RDSValue

loaded = read_reference_rds("official-amelia-result.rds", return_type="pandas")
more = loaded.extend(m=5, seed=20260924, p2s=0)
more.save_rds("official-amelia-result-extended.rds")

# args.rds is created in R with saveRDS(fit$arguments, "args.rds").
another = amelia_reference(data, m=5, arglist=RDSValue("args.rds"), p2s=0)
```

Upstream `amelia.amelia` reuses archived model arguments; `extend` therefore permits execution settings such as m, seed, p2 s and frontend, with frontend omitted or Boolean False. Changing the model requires a new fit on original data. Editing Python imputations does not modify stored RDS or subsequent append inputs.

Metadata separates this call from historical provenance. New reference work is CPU. An external Amelia-class RDS without backend attributes has `engine="unknown"` and null GPU/Torch usage. Existing `amelia_torch_backend` or older `ameliatorch_backend` attributes are retained. Appends record historical/new counts and the current reference call separately. In-memory provenance survives `extend`; `save_rds` does not invent private attributes, so save Python metadata separately as JSON when needed.

Official diagnostics remain in R:

```r
fit <- readRDS("official-amelia-result.rds")
summary(fit)
Amelia::compare.density(fit, var = "income")
```

Connections, active clusters and GUI environments cannot cross the subprocess bridge. Python reference/hybrid/RDS/extend reject frontend=True or non-Boolean False before starting R; use interactive original R/Tcl/Tk for AmeliaView. This rejection does not validate GUI startup. Original `parallel="snow"` creates workers; choose `r_rng_kind="L'Ecuyer-CMRG"` for its parallel RNG setup. Equal seeds do not pair different RNG libraries.

Cross-process molist RDS must be self-contained. `moPrep` normally stores a data expression; materialize `prepared$data` in the original R session before saving so new Rscript sessions do not depend on local bindings.

Rscript is launched with an argument list, not interpolated shell/R code. Typed files, JSON and RDS carry values. Original errors raise `AmeliaReferenceError`; partial failures retain original RDS bytes in `partial_rds`. Original code 1 at an iteration cutoff is exposed through convergence metadata and warnings. Startup, binary exchange, RDS and reconstruction costs require separate full-call timing.

## Hybrid interface

```python
from amelia_torch import amelia_torch_compat

hybrid = amelia_torch_compat(
    data, m=5, seed=20260923, p2s=0,
    device="cpu", dtype="float64",  # default
    noms=["region"], logs=["income"],
)
hybrid.save_rds("hybrid-result.rds")
more_hybrid = hybrid.extend(m=2, seed=20260924, p2s=0)
```

The hybrid uses the same transport and an installed `ameliatorch` R package plus Torch in the caller's Python environment. Only EM moves to Torch; R retains preparation, bootstrap, random draws and output. CUDA must be available; MPS requires explicit float32. Unsupported devices/precision and multiworker scheduling fail, without automatic switching.

`RETICULATE_PYTHON` binds to the current virtual-environment interpreter without editing global configuration. Metadata records engine, device, precision, CPU work and per-fit diagnostics. In-memory `hybrid.extend()` retains the engine/device. A reread RDS defaults to reference extension; request hybrid explicitly:

```python
more_hybrid = amelia_torch_compat(
    input_rds="hybrid-result.rds", m=2, seed=20260924,
    device="cpu", dtype="float64", p2s=0,
)
```

Matched R RNG settings allow bounded hybrid/reference paired comparisons; native PCG64 does not share those streams. Registered C helpers preserve internal and visible R RNG around deterministic Python initialization/EM. Building this hybrid R package requires a C toolchain; Python reference alone does not require it.

## Validation

Current hosted CPU evidence at `ef729c0` covers 307 Python checks, nine R files and a downstream example on each of three platforms, including G3/G4. Intel Mac separately passed an isolated no-Torch reference wheel workflow. [CI records](validation/2026-09-26-ci/README.md) distinguish these from GPU, GUI and complete statistical acceptance.
