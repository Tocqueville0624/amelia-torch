"""Exercise interruption/recording failures with mocked fits and child processes only."""

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
DATASETS = ("covertype", "household_power", "year_prediction_msd")


def load_script(name):
    spec = importlib.util.spec_from_file_location(f"interruption_{name}", SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("name", ["benchmark", "run_benchmark_suite", "run_hybrid_suite"])
@pytest.mark.parametrize("failure_stage", ["partial_write", "replace"])
def test_atomic_snapshot_keeps_previous_json_on_interruption(
    tmp_path, monkeypatch, name, failure_stage
):
    module = load_script(name)
    save = module.save_report if name == "benchmark" else module.save_suite
    destination = tmp_path / "report.json"
    previous = {"runs": [{"seed": 123, "status": "ok"}]}
    save(destination, previous)
    previous_bytes = destination.read_bytes()
    write_text = Path.write_text

    def interrupted_write(path, value, *args, **kwargs):
        if path.name.endswith(".tmp"):
            write_text(path, '{"runs": [')
            raise KeyboardInterrupt
        return write_text(path, value, *args, **kwargs)

    if failure_stage == "partial_write":
        monkeypatch.setattr(Path, "write_text", interrupted_write)
    else:
        def interrupted_replace(*args):
            raise KeyboardInterrupt
        monkeypatch.setattr(module.os, "replace", interrupted_replace)
    with pytest.raises(KeyboardInterrupt):
        save(destination, {"runs": previous["runs"] + [{"seed": 124}]})
    assert destination.read_bytes() == previous_bytes
    assert json.loads(destination.read_text()) == previous


def make_input(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    truth = np.array([[1.0, 2.0], [3.0, 5.0], [5.0, 8.0]])
    data = truth.copy()
    data[0, 1] = np.nan
    np.savez(path, data=data, truth=truth, artificial_missing_mask=np.isnan(data),
             column_names=np.array(["a", "b"]))
    return truth


def prepare_native(tmp_path, monkeypatch, *, warmups=1, repeats=2):
    module = load_script("benchmark")
    source = tmp_path / "input.npz"
    truth = make_input(source)
    output = tmp_path / "native.json"
    monkeypatch.setattr(sys, "argv", ["benchmark.py", str(source), "--output", str(output),
                                     "--warmups", str(warmups), "--repeats", str(repeats), "--m", "1"])
    monkeypatch.setattr(module, "git_revision", lambda: {"commit": "fixture", "dirty": False})
    monkeypatch.setattr(module, "resolve_backend", lambda *args: (SimpleNamespace(type="cpu"), None))
    monkeypatch.setattr(module, "synchronize", lambda *args: None)
    monkeypatch.setattr(module.torch, "set_num_threads", lambda *args: None)
    result = {"diagnostics": {"converged": True}, "imputations": [truth], "theta": np.eye(3)}
    return module, output, result


@pytest.mark.parametrize("error_type,expected_exit", [(KeyboardInterrupt, 130), (RuntimeError, 1)])
def test_native_keeps_completed_repeat_and_records_abort(
    tmp_path, monkeypatch, error_type, expected_exit
):
    module, output, result = prepare_native(tmp_path, monkeypatch)
    seeds = []
    prior_run = None

    def fake_fit(data, **kwargs):
        nonlocal prior_run
        snapshot = json.loads(output.read_text())
        assert snapshot["status"] == "running"
        seeds.append(kwargs["seed"])
        if len(seeds) == 1:
            assert snapshot["runs"] == []  # Initial report exists before fitting starts.
            return result
        prior_run = snapshot["runs"][0]
        raise error_type("injected interruption or failure")

    monkeypatch.setattr(module, "amelia", fake_fit)
    assert module.main() == expected_exit
    report = json.loads(output.read_text())
    assert seeds == [20360923, 20260923]
    assert report["runs"][0] == prior_run
    if error_type is KeyboardInterrupt:
        assert len(report["runs"]) == 1
        assert report["status"] == "interrupted"
        assert report["unfinished_run"] == {
            "run": 1, "warmup": False, "seed": 20260923,
            "status": "interrupted_before_record_commit",
        }
        assert "completed_utc" not in report
        assert "summary" not in report
    else:
        assert len(report["runs"]) == 2
        assert report["runs"][1]["status"] == "error"
        assert report["runs"][1]["error_type"] == "RuntimeError"
        assert report["status"] == "failed"
        assert report["summary"]["all_requested_runs_succeeded"] is False


def test_native_failed_warmup_cannot_claim_all_requested_runs_succeeded(tmp_path, monkeypatch):
    module, output, result = prepare_native(tmp_path, monkeypatch, warmups=1, repeats=1)

    def fake_fit(data, **kwargs):
        return {**result, "diagnostics": {"converged": kwargs["seed"] == 20260923}}

    monkeypatch.setattr(module, "amelia", fake_fit)
    assert module.main() == 1
    report = json.loads(output.read_text())
    assert [run["status"] for run in report["runs"]] == ["not_converged", "ok"]
    assert report["summary"]["all_requested_runs_succeeded"] is False
    assert report["status"] == "failed"


def test_native_nonfinite_quality_description_is_saved_as_recording_failure(tmp_path, monkeypatch):
    module, output, result = prepare_native(tmp_path, monkeypatch)
    prior_run = None

    def fake_fit(data, **kwargs):
        nonlocal prior_run
        if kwargs["seed"] == 20360923:
            return result
        prior_run = json.loads(output.read_text())["runs"][0]
        invalid = result["imputations"][0].copy()
        invalid[0, 1] = np.inf  # Held-out cell: pooled_column_means is not strict JSON.
        return {**result, "imputations": [invalid]}

    monkeypatch.setattr(module, "amelia", fake_fit)
    assert module.main() == 1
    report = json.loads(output.read_text())
    assert report["runs"][0] == prior_run
    assert len(report["runs"]) == 2
    failure = report["runs"][1]
    assert failure["seed"] == 20260923
    assert failure["warmup"] is False
    assert failure["status"] == "error"
    assert failure["stage"] == "record_serialization"
    assert failure["original_status"] == "quality_failed"
    assert failure["error_type"] == "ValueError"
    assert report["status"] == "failed"
    assert report["summary"]["all_requested_runs_succeeded"] is False
    json.dumps(report, allow_nan=False)


def test_native_refuses_to_overwrite_prior_report_without_fitting(tmp_path, monkeypatch):
    module, output, _ = prepare_native(tmp_path, monkeypatch)
    original = b'{"runs": [{"seed": 123}]}\n'
    output.write_bytes(original)
    monkeypatch.setattr(module, "amelia", lambda *a, **kw: pytest.fail("No fit authorized"))
    with pytest.raises(SystemExit, match="2"):
        module.main()
    assert output.read_bytes() == original


def prepare_suite(tmp_path, monkeypatch, name):
    module = load_script(name)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    (tmp_path / "scripts").mkdir()
    for filename in ("benchmark.py", "benchmark_reference.R", "benchmark_hybrid.R", f"{name}.py"):
        (tmp_path / "scripts" / filename).write_text("source fixture\n")
    monkeypatch.setattr(module, "__file__", str(tmp_path / "scripts" / f"{name}.py"))
    (tmp_path / "r-package").mkdir()
    for filename in ("DESCRIPTION", "NAMESPACE"):
        (tmp_path / "r-package" / filename).write_text("source fixture\n")
    for dataset in DATASETS:
        path = tmp_path / "data/prepared" / f"{dataset}-n3-block_mcar-rate30-seed20260923.npz"
        make_input(path)
        path.with_suffix(".json").write_text(json.dumps({
            "npz_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "shape": [3, 2], "columns": ["a", "b"], "source_archive_sha256": "a" * 64,
        }))
    output = tmp_path / "output"
    options = (["--gpu", "none"] if name == "run_benchmark_suite" else
               ["--methods", "cpu64", "cpu32", "--generate-inputs"])
    monkeypatch.setattr(sys, "argv", [f"{name}.py", "--output-dir", str(output), "--rows", "3",
                                     *options])
    return module, output


def child_output(command):
    if "--output" in command:
        return Path(command[command.index("--output") + 1])
    return Path(json.loads(Path(command[-1]).read_text())["output_json"])


@pytest.mark.parametrize("name", ["run_benchmark_suite", "run_hybrid_suite"])
def test_suite_commits_full_plan_and_running_state_before_launch_and_keeps_partial(
    tmp_path, monkeypatch, name
):
    module, output = prepare_suite(tmp_path, monkeypatch, name)
    expected_tasks = 12 if name == "run_benchmark_suite" else 6
    snapshots = []
    partial = b'{"runs": [{"phase": "warmup", "seed": 20360923}], "status": "running"}\n'
    partial_path = None

    def fake_run(command, **kwargs):
        nonlocal partial_path
        snapshot = json.loads((output / "suite.json").read_text())
        snapshots.append(snapshot)
        assert len(snapshot["planned_order"]) == expected_tasks
        assert snapshot["execution"][-1]["status"] == "running"
        assert snapshot["execution"][-1]["exit_status"] is None
        destination = child_output(command)
        if len(snapshots) == 1:
            destination.write_text('{"summary":{"all_requested_runs_succeeded":true}}')
            return subprocess.CompletedProcess(command, 0)
        partial_path = destination
        destination.write_bytes(partial)
        raise KeyboardInterrupt

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    assert module.main() == 130
    suite = json.loads((output / "suite.json").read_text())
    assert len(snapshots) == 2
    assert suite["execution"][0] == snapshots[1]["execution"][0]
    assert suite["execution"][0]["status"] == "completed"
    assert suite["execution"][0]["exit_status"] == 0
    assert suite["execution"][1]["status"] == "interrupted"
    assert suite["execution"][1]["exit_status"] is None
    assert suite["status"] == "interrupted"
    assert suite["aborted_reason"] == "keyboard_interrupt"
    assert "completed_utc" not in suite
    assert len(suite["planned_order"]) == expected_tasks
    assert partial_path.read_bytes() == partial
    if name == "run_hybrid_suite":
        assert suite["all_requested_tasks_succeeded"] is False


def test_main_suite_launch_failure_keeps_previous_tasks_and_unfinished_plan(tmp_path, monkeypatch):
    module, output = prepare_suite(tmp_path, monkeypatch, "run_benchmark_suite")
    calls = 0

    def fake_run(command, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return subprocess.CompletedProcess(command, 0)
        raise FileNotFoundError("injected missing executable")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    assert module.main() == 1
    suite = json.loads((output / "suite.json").read_text())
    assert len(suite["planned_order"]) == 12
    assert len(suite["execution"]) == 2
    assert suite["execution"][0]["exit_status"] == 0
    assert suite["execution"][1]["exit_status"] is None
    assert suite["execution"][1]["status"] == "failed"
    assert suite["execution"][1]["error_type"] == "FileNotFoundError"
    assert suite["status"] == "failed"
    assert "completed_utc" not in suite


def test_main_suite_existing_directory_is_untouched_without_launch(tmp_path, monkeypatch):
    module, output = prepare_suite(tmp_path, monkeypatch, "run_benchmark_suite")
    output.mkdir()
    prior = output / "old.json"
    prior.write_text('{"previous_run": true}\n')
    before = prior.read_bytes()
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **kw: pytest.fail("No launch expected"))
    with pytest.raises(SystemExit, match="2"):
        module.main()
    assert prior.read_bytes() == before
    assert list(output.iterdir()) == [prior]


def test_main_suite_plan_preserves_original_default_shuffle():
    module = load_script("run_benchmark_suite")
    expected = {
        "covertype": ["cpu64", "mps32", "r_snow4", "cpu32", "r_serial"],
        "household_power": ["r_serial", "cpu64", "mps32", "r_snow4", "cpu32"],
        "year_prediction_msd": ["cpu32", "r_snow4", "r_serial", "mps32", "cpu64"],
    }
    assert module.planned_order("mps", 4) == [
        {"dataset": dataset, "method": method}
        for dataset, methods in expected.items() for method in methods
    ]


def test_hybrid_malformed_child_report_does_not_erase_prior_completion(tmp_path, monkeypatch):
    module, output = prepare_suite(tmp_path, monkeypatch, "run_hybrid_suite")
    calls = 0
    malformed = None

    def fake_run(command, **kwargs):
        nonlocal calls, malformed
        calls += 1
        destination = child_output(command)
        if calls == 1:
            destination.write_text('{"summary":{"all_requested_runs_succeeded":true}}')
        else:
            malformed = destination
            destination.write_text('{"runs":[')
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    assert module.main() == 1
    suite = json.loads((output / "suite.json").read_text())
    assert calls == 2
    assert suite["execution"][0]["status"] == "completed"
    assert suite["execution"][1]["status"] == "failed"
    assert suite["execution"][1]["exit_status"] == 0  # Known process result retained.
    assert suite["execution"][1]["error_type"] == "JSONDecodeError"
    assert suite["status"] == "failed"
    assert suite["all_requested_tasks_succeeded"] is False
    assert "completed_utc" not in suite
    assert malformed.read_text() == '{"runs":['
