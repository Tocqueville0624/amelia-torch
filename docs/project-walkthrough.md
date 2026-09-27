# Multiple-imputation workflow

[简体中文](project-walkthrough.zh-CN.md) · [Documentation](README.md)

The project evaluates fidelity to Amelia 1.8.3 and full-call execution time. The [native API](../src/amelia_torch/api.py) handles continuous numeric data. The [hybrid R interface](../r-package/R/torch_compat.R) retains original preparation, bootstrap, draws and postprocessing, replacing only EM. Their feature sets and timings are distinct.

Observed values determine standardization. Each imputation draws a bootstrap sample, fits means and covariances by EM, then draws missing values for the original sample and restores units and order. Bootstrap represents parameter uncertainty; conditional draws represent missing-value uncertainty given those parameters. Repeating a predicted mean is not multiple imputation.

## Conditional moments

For an illustrative joint normal distribution,

$$
\begin{pmatrix}X\\Y\end{pmatrix}\sim N\left[\begin{pmatrix}10\\20\end{pmatrix},\begin{pmatrix}4&3\\3&9\end{pmatrix}\right],
$$

observing $X=12$ gives

$$
E(Y\mid X=12)=21.5,\qquad \operatorname{Var}(Y\mid X=12)=6.75.
$$

The EM second moment is $21.5^2+6.75=469$. Omitting 6.75 discards conditional uncertainty. Final imputation samples from this conditional distribution; multiple missing variables require their conditional covariance. See [EM](../src/amelia_torch/em.py) and [Cholesky draws](../src/amelia_torch/imputation.py). This is an analytic illustration, not an experiment.

## Numerical and research interpretation

Ordinary continuous inputs retain observed values exactly. Entirely missing analysis rows are excluded from fitting and remain missing, following Amelia. Documented upstream exceptions, including single-row priors, appear in the [contract](algorithm-contract.md).

CPU float64 is the reference. MPS float32 and CUDA float64/float32 require explicit choices; an unavailable device raises an error. CPU64 versus GPU32 changes both device and precision. Equal integer seeds do not pair R and NumPy PCG64 draws.

Compare timings on the same host, route and precision, including transfers and synchronization. R users need full R workflow timings. [Windows](validation/2026-09-27-windows-rtx3080/README.md) and [T4](validation/2026-09-26-colab-native/README.md) show workload-dependent CUDA gains; [Mac](validation/2026-09-23-development/README.md) shows MPS slowdowns. [Mac inference criteria](validation/2026-09-26-g5-mps/README.md) did not all pass. Convergence, prediction error and valid inference are separate outcomes.

## Reproducible example

After [installation](setup.md), run at the repository root:

```sh
.venv/bin/python examples/python_r_downstream.py --output results/local/walkthrough-reference --r-library .R-library
```

On Windows use `.venv\Scripts\python.exe`; choose a new output directory. The default original-R example uses 72 rows and two imputations, saves RDS, derives an interaction and appends another imputation in R, then reads the result back in Python. `roundtrip.json` records the engine, three results and preservation of previous imputations. [Example documentation](../examples/README.md) describes the outputs and downstream limitations.
