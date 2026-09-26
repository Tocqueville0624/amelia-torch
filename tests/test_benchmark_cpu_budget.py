"""Check process/thread budgeting without fitting or invoking external tools."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np


def test_two_core_suite_budgets_each_method(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[1] / "scripts/run_benchmark_suite.py"
    spec = importlib.util.spec_from_file_location("budget_suite", path)
    suite = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(suite)
    monkeypatch.setattr(suite, "ROOT", tmp_path)
    (tmp_path / "src/amelia_torch").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    for name in ("benchmark.py", "benchmark_reference.R"):
        (tmp_path / "scripts" / name).write_text("fixture")
    prepared = tmp_path / "data/prepared"
    prepared.mkdir(parents=True)
    for dataset in ("covertype", "household_power", "year_prediction_msd"):
        np.savez(prepared / f"{dataset}-n3-block_mcar-rate30-seed20260923.npz",
                 data=np.ones((3, 2)), truth=np.ones((3, 2)),
                 artificial_missing_mask=np.zeros((3, 2), dtype=bool),
                 column_names=np.array(["a", "b"]))
    calls = []

    def fake_run(command, *, cwd, env, check):
        if command[0] == "Rscript":
            config = json.loads(Path(command[-1]).read_text())
            assert config["ncpus"] == (2 if config["parallel"] == "snow" else 1)
            expected_threads = "1" if config["parallel"] == "snow" else "2"
        else:
            assert command[command.index("--threads") + 1] == "2"
            expected_threads = "2"
        for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                    "VECLIB_MAXIMUM_THREADS"):
            assert env[key] == expected_threads
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(suite.subprocess, "run", fake_run)
    output = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", [str(path), "--rows", "3", "--gpu", "cuda",
                        "--threads", "2", "--workers", "2", "--output-dir", str(output)])
    assert suite.main() == 0
    report = json.loads((output / "suite.json").read_text())
    assert len(calls) == 18
    assert report["cpu_budget"] == {"serial_threads": 2, "snow_workers": 2,
                                    "snow_worker_blas_threads": 1}
    assert {x["method"] for x in report["execution"]} == {
        "cpu64", "cpu32", "r_serial", "r_snow2", "cuda64", "cuda32"}
