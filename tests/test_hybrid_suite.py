"""Offline checks of R-user benchmark input/provenance orchestration; no fitting."""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

SPEC = importlib.util.spec_from_file_location(
    "run_hybrid_suite", Path(__file__).resolve().parents[1] / "scripts/run_hybrid_suite.py"
)
suite = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(suite)


@pytest.mark.parametrize("content", [b"a,b\n1,2\n3,4\n", b"a,b\r\n1,2\r\n3,4"])
def test_csv_dimension_check_accepts_native_line_endings(tmp_path, content):
    path = tmp_path / "input.csv"
    path.write_bytes(content)
    result = suite.inspect_csv(path, 2, ["a", "b"])
    assert result["rows"] == 2
    assert result["columns"] == 2
    assert result["sha256"] == suite.file_hash(path)


def test_reused_csv_with_wrong_task_size_is_rejected(tmp_path):
    path = tmp_path / "input.csv"
    path.write_text("a,b\n1,2\n3,4\n")
    with pytest.raises(ValueError, match="row count"):
        suite.inspect_csv(path, 100000, ["a", "b"])
    with pytest.raises(ValueError, match="columns"):
        suite.inspect_csv(path, 2, ["b", "a"])


def test_generated_csvs_preserve_input_truth_and_mask(tmp_path):
    source = tmp_path / "prepared.npz"
    truth = np.array([[0.1, 5.0], [2.0, 1 / 3]])
    data = truth.copy()
    data[0, 1] = np.nan
    np.savez(
        source,
        data=data,
        truth=truth,
        artificial_missing_mask=np.isnan(data),
        column_names=np.array(["a", "b"]),
    )
    destination = tmp_path / "csv"
    suite.generate_csvs(source, "example", destination)
    for name, expected in (("input", data), ("truth", truth), ("mask", np.isnan(data))):
        restored = np.loadtxt(destination / f"example-{name}.csv", delimiter=",", skiprows=1)
        np.testing.assert_array_equal(restored, expected)
    with pytest.raises(FileExistsError):
        suite.generate_csvs(source, "example", destination)


def test_plan_only_never_launches_r_or_writes_results(tmp_path, monkeypatch, capsys):
    output = tmp_path / "untouched"
    monkeypatch.setattr(
        suite.sys,
        "argv",
        [
            "run_hybrid_suite.py",
            "--plan-only",
            "--methods",
            "cpu64",
            "cpu32",
            "--output-dir",
            str(output),
        ],
    )
    monkeypatch.setattr(
        suite.subprocess, "run", lambda *a, **kw: pytest.fail("No R launch expected")
    )
    assert suite.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert len(report["tasks"]) == 6
    assert report["parallel"] == "no"
    assert not output.exists()
