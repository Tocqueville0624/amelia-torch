"""Repair shared-site Ruff without installing Torch or modifying a global environment."""

import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/cloud_bootstrap.py"
SPEC = importlib.util.spec_from_file_location("cloud_bootstrap_ruff", SCRIPT)
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


def setup_mocks(monkeypatch, tmp_path, *, probe_exit=1, repair_exit=0, verify_exit=0):
    venv_dir = tmp_path / ".venv"
    output = tmp_path / "logs"
    output.mkdir()
    version = "0.15.5"
    before = {
        "version": version,
        "prefix": str(venv_dir),
        "base_prefix": "/usr",
        "distribution_root": str(tmp_path / "runtime/site-packages"),
    }
    after = {**before, "distribution_root": str(venv_dir / "lib/python3.12/site-packages")}
    metadata = [before, after]
    commands = []
    report = {"steps": []}
    codes = {
        "ruff_probe": probe_exit,
        "ruff_venv_reinstall": repair_exit,
        "ruff_verify": verify_exit,
    }

    def run_step(name, command, env, destination, current, *, allow_failure=False):
        assert destination == output and current is report
        commands.append((name, command))
        code = codes[name]
        text = "RuffNotFound: Ruff binary not found\n" if code else f"ruff {version}\n"
        (output / f"{name}.log").write_text(text)
        report["steps"].append(
            {"step": name, "exit_status": code, "status": "failed" if code else "passed"}
        )
        if code and not allow_failure:
            raise RuntimeError(f"Setup step {name} failed with exit status {code}")
        return code

    def capture(command, env):
        assert command == [str(venv_dir / "bin/python"), "-c", bootstrap.RUFF_METADATA]
        return json.dumps(metadata.pop(0))

    monkeypatch.setattr(bootstrap, "run_step", run_step)
    monkeypatch.setattr(bootstrap, "capture", capture)
    return venv_dir, output, report, commands, metadata


def test_working_shared_ruff_is_verified_without_reinstall(monkeypatch, tmp_path):
    venv_dir, output, report, commands, _ = setup_mocks(monkeypatch, tmp_path, probe_exit=0)
    bootstrap.ensure_ruff(venv_dir, {}, output, report)
    assert [name for name, _ in commands] == ["ruff_probe"]
    assert report["ruff"] == {
        "status": "passed",
        "repair_attempted": False,
        "initial_probe_exit_status": 0,
        "installed_version": "0.15.5",
        "distribution_before": "shared_runtime",
        "verified_cli_version": "ruff 0.15.5",
    }


def test_missing_shared_binary_repairs_exact_version_only_inside_venv(monkeypatch, tmp_path):
    venv_dir, output, report, commands, _ = setup_mocks(monkeypatch, tmp_path)
    bootstrap.ensure_ruff(venv_dir, {"PIP_TARGET": "/global/should-not-be-used"}, output, report)
    assert [name for name, _ in commands] == ["ruff_probe", "ruff_venv_reinstall", "ruff_verify"]
    assert commands[1][1] == [
        str(venv_dir / "bin/python"),
        "-m",
        "pip",
        "--isolated",
        "install",
        "--index-url",
        "https://pypi.org/simple",
        "--ignore-installed",
        "--no-deps",
        "--prefix",
        str(venv_dir),
        "ruff==0.15.5",
    ]
    assert report["steps"][0]["status"] == "failed"  # Preserve original failure evidence.
    assert report["ruff"]["status"] == "passed"
    assert report["ruff"]["installed_version_after"] == report["ruff"]["installed_version"]
    assert report["ruff"]["distribution_after"] == "virtual_environment"
    saved = json.loads((output / "bootstrap.json").read_text())
    assert saved["ruff"] == report["ruff"]
    assert all("torch" not in argument.lower() for _, command in commands for argument in command)


@pytest.mark.parametrize("step", ["repair", "verify"])
def test_failed_repair_or_verification_cannot_be_reported_as_success(monkeypatch, tmp_path, step):
    values = {"repair_exit": 1} if step == "repair" else {"verify_exit": 1}
    venv_dir, output, report, commands, _ = setup_mocks(monkeypatch, tmp_path, **values)
    with pytest.raises(RuntimeError, match="failed with exit status"):
        bootstrap.ensure_ruff(venv_dir, {}, output, report)
    assert report["ruff"]["status"] == "failed"
    assert "verified_cli_version" not in report["ruff"]
    assert len(commands) == (2 if step == "repair" else 3)
    assert json.loads((output / "bootstrap.json").read_text())["ruff"]["status"] == "failed"


@pytest.mark.parametrize("change", ["global_interpreter", "different_venv", "invalid_version"])
def test_repair_refuses_unsafe_environment_or_unpinnable_version(monkeypatch, tmp_path, change):
    venv_dir, output, report, commands, metadata = setup_mocks(monkeypatch, tmp_path)
    if change == "global_interpreter":
        metadata[0]["base_prefix"] = metadata[0]["prefix"]
    elif change == "different_venv":
        metadata[0]["prefix"] = str(tmp_path / "other-venv")
    else:
        metadata[0]["version"] = "0.15.5 --target /global"
    with pytest.raises(ValueError):
        bootstrap.ensure_ruff(venv_dir, {}, output, report)
    assert len(commands) == 1  # No pip command may run.
    assert report["ruff"]["status"] == "failed"


@pytest.mark.parametrize("change", ["version", "global_metadata"])
def test_repair_must_load_same_version_from_venv(monkeypatch, tmp_path, change):
    venv_dir, output, report, _, metadata = setup_mocks(monkeypatch, tmp_path)
    if change == "version":
        metadata[1]["version"] = "0.16.0"
    else:
        metadata[1]["distribution_root"] = metadata[0]["distribution_root"]
    with pytest.raises(ValueError, match="pinned version from inside the venv"):
        bootstrap.ensure_ruff(venv_dir, {}, output, report)
    assert report["ruff"]["status"] == "failed"


def test_initial_cli_version_must_match_visible_package(monkeypatch, tmp_path):
    venv_dir, output, report, commands, metadata = setup_mocks(monkeypatch, tmp_path, probe_exit=0)
    metadata[0]["version"] = "0.15.4"
    with pytest.raises(ValueError, match="CLI version does not match"):
        bootstrap.ensure_ruff(venv_dir, {}, output, report)
    assert len(commands) == 1
    assert report["ruff"]["status"] == "failed"


@pytest.mark.parametrize("allow_failure", [True, False])
def test_run_step_keeps_nonzero_exit_and_log_even_for_recoverable_probe(
    monkeypatch, tmp_path, allow_failure
):
    process = SimpleNamespace(stdout=io.StringIO("RuffNotFound\n"), wait=lambda: 1)
    monkeypatch.setattr(bootstrap.subprocess, "Popen", lambda *args, **kwargs: process)
    report = {"steps": []}
    if allow_failure:
        assert (
            bootstrap.run_step("probe", ["unused"], {}, tmp_path, report, allow_failure=True) == 1
        )
    else:
        with pytest.raises(RuntimeError):
            bootstrap.run_step("probe", ["unused"], {}, tmp_path, report)
    assert report["steps"][0]["exit_status"] == 1
    assert report["steps"][0]["status"] == "failed"
    assert (tmp_path / "probe.log").read_text() == "RuffNotFound\n"
