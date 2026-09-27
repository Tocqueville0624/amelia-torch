# R workflow prompt

[简体中文](r-user-agent-prompt.zh-CN.md) · [Documentation](README.md)

This template specifies an R imputation task for a coding assistant. It requires the data and model choices to be established before execution. Review the [compatibility matrix](amelia-compatibility.md) and retain all imputations for downstream pooling.

```text
I use R. Help me impute my data with https://github.com/Tocqueville0624/amelia-torch and return results I can use in R.

Before installing software or processing data, ask me to confirm:
- The dataset path, format and table/sheet; variables to impute, predictors, IDs/exclusions, variable types and missing-value codes.
- My downstream analysis and any categorical, transformation, bound, prior or panel/time-series requirements; ask for existing Amelia code if available.
- The number of imputations (m), seed, bootstrap method, convergence tolerance, iteration limits and regularization. Explain unfamiliar choices and suggest defaults for me to confirm.
- My OS, R/Python setup, GPU, memory/time budget, and whether installation or data upload is allowed.
- The output folder, R-readable formats and diagnostics I need.

Wait until the required details are clear. Read the repository's compatibility matrix and algorithm contract, then agree on the execution plan with me. Use native Python only when it supports my requirements; otherwise explain the reference/hybrid option. Do not drop options or change statistical assumptions to obtain a faster result. Default to CPU float64; confirm any GPU, lower-precision or trial-benchmark choice.

After agreement, create a reproducible script, run the imputations, and save every completed dataset with its row IDs and variable metadata. Preserve observed values and documented missing-row behavior; report convergence, warnings, failures and full-call elapsed time. Keep all imputations for downstream pooling. Provide R code to read and analyze them, and explain any remaining validation limits. Keep my data local unless I approve transfer.
```
