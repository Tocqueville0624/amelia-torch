"""Run Python imputation -> official R methods -> Python RDS readback.

This small example needs the installed ameliatorch R package, Amelia 1.8.3,
amelia-torch[reference], and (for --engine torch-compat) amelia-torch[torch].
R transformations, diagnostics, pooling and the appended imputation use the
official CPU implementation. Files are written to a new output directory.
"""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from amelia_torch import amelia_reference, amelia_torch_compat, read_reference_rds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--engine", choices=("reference", "torch-compat"), default="reference")
    parser.add_argument("--rscript", default=shutil.which("Rscript"))
    parser.add_argument("--r-library", type=Path)
    args = parser.parse_args()
    if not args.rscript:
        parser.error("Rscript is required; install R and add Rscript to PATH or pass --rscript")
    # Refuse to mix a new run with old artifacts or overwrite previous evidence.
    args.output.mkdir(parents=True, exist_ok=False)
    output = args.output.resolve()
    environment = os.environ.copy()
    if args.r_library:
        environment["R_LIBS_USER"] = str(args.r_library.expanduser().resolve())
    runtime = {"rscript": args.rscript, "r_library": args.r_library}
    rng = np.random.default_rng(812)
    data = pd.DataFrame(rng.normal(size=(72, 3)), columns=["a", "b", "y"])
    data["y"] += 0.4 * data["a"] - 0.3 * data["b"]
    data.loc[::7, "a"] = np.nan
    data.loc[::9, "y"] = np.nan
    implementation = amelia_torch_compat if args.engine == "torch-compat" else amelia_reference
    fit = implementation(data, m=2, seed=813, p2s=0, **runtime)
    fit.save_rds(output / "python-imputations.rds")
    completed = subprocess.run(
        [args.rscript, "--vanilla", str(Path(__file__).with_suffix(".R")), str(output)],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError("Official R downstream step failed:\n" + completed.stdout + completed.stderr)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="")
    returned = read_reference_rds(output / "r-transformed-extended.rds", **runtime)
    assert returned.m == 3
    for draw in returned.imputations:
        np.testing.assert_allclose(draw["interaction"], draw["a"] * draw["b"], rtol=0, atol=0)
    expected = fit.imputations[0].copy()
    expected["interaction"] = expected["a"] * expected["b"]
    # Python-only index classes are not serialized into the original R object.
    pd.testing.assert_frame_equal(
        returned.imputations[0].reset_index(drop=True), expected.reset_index(drop=True)
    )
    report = {
        "first_call_engine": fit.engine,
        "returned_imputations": returned.m,
        "derived_column_checked": True,
        "old_imputation_preserved": True,
        "original_r_methods_backend": "cpu",
        "returned_metadata": returned.metadata,
    }
    (output / "roundtrip.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Verified Python -> RDS -> R transform/append/plot/export -> Python readback.")


if __name__ == "__main__":
    main()
