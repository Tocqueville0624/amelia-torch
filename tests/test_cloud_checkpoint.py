import base64
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/recover_cloud_checkpoint.py"
SPEC = importlib.util.spec_from_file_location("recover_checkpoint", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def make_envelope(path="results/local/cloud/example.json", text='{"value": "测量"}\n'):
    record = {"path": path, "text": text,
              "portable_sha256": hashlib.sha256(text.encode()).hexdigest()}
    bundle = {"schema_version": 1, "label": "smoke", "revision": "a" * 40,
              "files": [record]}
    packed = gzip.compress(json.dumps(bundle).encode(), mtime=0)
    return {"amelia_checkpoint": "gzip-base64-v1", "label": "smoke",
            "bytes": len(packed), "sha256": hashlib.sha256(packed).hexdigest(),
            "data": base64.b64encode(packed).decode()}


def test_recovers_exact_utf8_without_overwriting(tmp_path):
    envelope = make_envelope()
    target = tmp_path / "recovered"
    result = MODULE.recover(envelope, target)
    assert result["files"] == 1
    assert (target / "results/local/cloud/example.json").read_bytes() == '{"value": "测量"}\n'.encode()
    with pytest.raises(FileExistsError):
        MODULE.recover(envelope, target)


@pytest.mark.parametrize("path", ["../escape.json", "/tmp/escape.json",
                                  "results/local/cloud/../../escape.json",
                                  "src/amelia_torch/evil.py", "data/private/file.json",
                                  "results\\local\\cloud\\a.json"])
def test_rejects_paths_before_writing(tmp_path, path):
    target = tmp_path / "recovered"
    with pytest.raises(ValueError):
        MODULE.recover(make_envelope(path=path), target)
    assert not target.exists()


def test_corrupt_hash_rejected(tmp_path):
    envelope = make_envelope()
    envelope["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="SHA-256"):
        MODULE.recover(envelope, tmp_path / "out")


def test_recovers_notebook_stream_without_executing_source():
    envelope = make_envelope()
    notebook = {"cells": [{"source": ["raise RuntimeError()"], "outputs": [
        {"text": [json.dumps(envelope) + "\n", "CHECKPOINT_FILES 1\n"]}]}]}
    assert MODULE.envelopes(notebook) == [envelope]


def test_collector_only_includes_reports_and_redacts_paths(tmp_path):
    spec = importlib.util.spec_from_file_location("collect_checkpoint", SCRIPT.with_name("cloud_checkpoint.py"))
    collector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(collector)
    report_dir = tmp_path / "results/local/cloud"
    report_dir.mkdir(parents=True)
    (report_dir / "phase.log").write_text(str(tmp_path) + "/example")
    (report_dir / "private.rds").write_bytes(b"not a report")
    (tmp_path / "credentials.json").write_text("not included")
    envelope = collector.collect(tmp_path, "smoke", "a" * 40)
    bundle = MODULE.checked_bundle(envelope)
    assert len(bundle["files"]) == 1
    assert bundle["files"][0]["text"] == "<project>/example"


def test_phase_checkpoint_excludes_other_phases_and_rejects_escape(tmp_path):
    spec = importlib.util.spec_from_file_location("phase_checkpoint", SCRIPT.with_name("cloud_checkpoint.py"))
    collector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(collector)
    for phase in ("native", "g5-formal"):
        directory = tmp_path / "results/local/cloud" / phase
        directory.mkdir(parents=True)
        (directory / "report.json").write_text('{}')
    bundle = MODULE.checked_bundle(collector.collect(tmp_path, "g5", "a" * 40, "g5-formal"))
    assert [item["path"] for item in bundle["files"]] == ["results/local/cloud/g5-formal/report.json"]
    for invalid in ("../native", "nested/phase", "missing"):
        with pytest.raises(ValueError):
            collector.collect(tmp_path, "bad", "a" * 40, invalid)
