"""Data provenance and preparation checks; all fixtures are synthetic and offline."""

from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from argparse import Namespace
from pathlib import Path

import numpy as np
import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


download = load_script("download_datasets")
prepare = load_script("prepare_benchmark_data")


@pytest.fixture
def archive_fixture(tmp_path):
    path = tmp_path / "example.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("data.csv", "1,2\n3,?\n5,6\n7,8\n")
    entry = {
        "filename": path.name,
        "download_url": "https://archive.ics.uci.edu/example.zip",
        "source_url": "https://archive.ics.uci.edu/dataset/example",
        "license": "CC-BY-4.0",
        "download_bytes": path.stat().st_size,
        "download_bytes_max": 100000,
        "sha256": download.sha256_file(path),
        "data_member": "data.csv",
        "inner_compression": None,
        "delimiter": ",",
        "has_header": False,
        "raw_columns": 2,
        "rows": 4,
        "numeric_indices_zero_based": [0, 1],
        "numeric_columns": ["a", "b"],
        "missing_tokens": ["", "?"],
    }
    return path, entry


def test_corrupt_download_never_passes_pinned_hash(archive_fixture):
    path, entry = archive_fixture
    corrupted = bytearray(path.read_bytes())
    corrupted[-1] ^= 1
    path.write_bytes(corrupted)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        download.verify_archive(path, entry, False)


def test_archive_crc_and_members_are_recorded(archive_fixture):
    path, entry = archive_fixture
    receipt = download.verify_archive(path, entry, False)
    assert receipt["sha256_matches_pin"]
    assert receipt["zip_crc_verified"]
    assert receipt["members"][0]["name"] == "data.csv"


def test_unpinned_download_rejected(archive_fixture):
    path, entry = archive_fixture
    entry["sha256"] = None
    with pytest.raises(ValueError, match="Unpinned"):
        download.verify_archive(path, entry, False)


def test_existing_archive_is_verified_offline(archive_fixture, monkeypatch):
    path, entry = archive_fixture
    monkeypatch.setattr(download, "urlopen", lambda *a, **kw: pytest.fail("No network expected"))
    receipt = download.download(entry, path.parent, Namespace(accept_unpinned=False))
    assert receipt["sha256"] == entry["sha256"]


def test_ignored_http_range_does_not_truncate_partial(tmp_path, monkeypatch):
    entry = {
        "filename": "data.zip",
        "download_url": "https://archive.ics.uci.edu/data.zip",
        "sha256": "a" * 64,
        "download_bytes": 100,
        "download_bytes_max": 100,
    }
    partial = tmp_path / "data.zip.part"
    partial.write_bytes(b"first bytes")
    (tmp_path / "data.zip.part.json").write_text(
        json.dumps({"download_url": entry["download_url"]})
    )

    class Response:
        status = 200
        url = entry["download_url"]

        def __init__(self):
            self.headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(download, "urlopen", lambda *a, **kw: Response())
    args = Namespace(
        accept_unpinned=False, verify_only=False, restart=False, reserve_gib=0, timeout=1
    )
    with pytest.raises(ValueError, match="cannot resume"):
        download.download(entry, tmp_path, args)
    assert partial.read_bytes() == b"first bytes"


def test_complete_case_subset_keeps_source_row_ids(archive_fixture):
    path, entry = archive_fixture
    data, indices, counts = prepare.load_sample(path, entry, 3, 4, "prefix", "complete-cases")
    np.testing.assert_array_equal(data, [[1, 2], [5, 6], [7, 8]])
    np.testing.assert_array_equal(indices, [0, 2, 3])
    assert counts["excluded_source_rows"] == 1


def test_preserve_natural_missing_is_separate_from_artificial(archive_fixture):
    path, entry = archive_fixture
    data, _, counts = prepare.load_sample(path, entry, 4, 4, "prefix", "preserve")
    mask, _ = prepare.artificial_mask(data, "mcar", 0.9, 5, 2)
    assert np.isnan(data[1, 1])
    assert not mask[1, 1]
    assert counts["excluded_source_rows"] == 0


def test_mar_only_conditions_on_unmasked_anchor():
    data = np.random.default_rng(4).normal(size=(10000, 7))
    mask, details = prepare.artificial_mask(data, "mar", 0.3, 6, 8)
    assert not mask[:, 0].any()
    assert abs(mask.mean() - 0.3) < 0.01
    assert mask[data[:, 0] > 1].mean() > mask[data[:, 0] < -1].mean()
    assert details["always_observed_anchor_column_zero_based"] == 0


def test_block_mcar_does_not_mislabel_independent_cell_masking():
    data = np.ones((1000, 90))
    mask, details = prepare.artificial_mask(data, "block_mcar", 0.1, 7, 8)
    assert len(np.unique(mask, axis=0)) == 8
    np.testing.assert_array_equal(mask.sum(axis=1), np.full(1000, 9))
    assert "not independent" in details["note"]


@pytest.mark.parametrize("dataset", ["covertype", "household_power", "year_prediction_msd"])
def test_committed_sample_provenance_and_truth_separation(dataset):
    root = SCRIPTS.parent
    path = root / "data/samples" / f"{dataset}.npz"
    metadata = json.loads(path.with_suffix(".json").read_text())
    manifest = json.loads((root / "data/manifest.json").read_text())["datasets"][dataset]
    assert download.sha256_file(path) == metadata["npz_sha256"]
    assert metadata["source_archive_sha256"] == manifest["sha256"]
    assert metadata["citation"] == manifest["citation"]
    with np.load(path, allow_pickle=False) as sample:
        data, truth = sample["data"], sample["truth"]
        mask = sample["artificial_missing_mask"]
        assert list(data.shape) == metadata["shape"]
        assert not sample["natural_missing_mask"].any()
        assert np.isfinite(truth).all()
        np.testing.assert_array_equal(np.isnan(data), mask)
        np.testing.assert_array_equal(data[~mask], truth[~mask])
        assert np.all(np.diff(sample["source_row_ids"]) > 0)
        assert 0 <= sample["source_row_ids"][0] < sample["source_row_ids"][-1] < manifest["rows"]
