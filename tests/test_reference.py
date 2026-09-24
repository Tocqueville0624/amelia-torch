"""Integration checks for the explicitly CPU-only official R compatibility path.

Do not run while collecting formal timing results. These tests use small data,
but they start R processes and exercise the actual official package.
"""

import json
import os
import shutil
import struct
import subprocess
from pathlib import Path

import numpy as np
import pytest

from amelia_torch.reference import (
    AmeliaReferenceError,
    RDSValue,
    _decode_data,
    _encode_data,
    _encode_option,
    _runtime_environment,
    amelia_reference,
    read_reference_rds,
)

ROOT = Path(__file__).resolve().parents[1]
HAS_R = shutil.which("Rscript") is not None
requires_r = pytest.mark.skipif(not HAS_R, reason="Optional reference engine requires Rscript")


def numeric_data():
    rng = np.random.default_rng(6701)
    truth = rng.normal(size=(140, 4))
    truth[:, 1] += 0.35 * truth[:, 0]
    incomplete = truth.copy()
    incomplete[::6, 0] = np.nan
    incomplete[::9, 2] = np.nan
    return incomplete


def test_option_transport_preserves_matrix_shape_missing_and_infinities(tmp_path):
    matrix = np.array([[1, 2, 0, np.inf], [2, 1, np.nan, 1.5]])
    value = _encode_option(matrix, tmp_path, [0])
    assert value["kind"] == "matrix"
    assert (value["nrow"], value["ncol"]) == (2, 4)
    assert value["values"] == [1, 2, 0, "Inf", 2, 1, None, 1.5]
    json.dumps(value, allow_nan=False)


def test_large_integer_transport_rejects_silent_rounding(tmp_path):
    with pytest.raises(ValueError, match=r"2\*\*53"):
        _encode_data(np.array([[2**53 + 1, 1], [2, 3]], dtype=np.int64), tmp_path)


def test_binary_numeric_transport_is_little_endian_and_preserves_special_values(tmp_path):
    data = np.array([[1.5, np.inf], [-2.25, -np.inf], [np.nan, 0.0]], dtype=">f8")
    payload, container, schema = _encode_data(data, tmp_path)
    first = payload["columns"][0]["storage"]
    assert first["byte_order"] == "little"
    assert (tmp_path / first["filename"]).read_bytes()[:16] == struct.pack("<dd", 1.5, -2.25)
    assert first["count"] == 3
    assert first["missing_encoding"] == "ieee754_nan"
    np.testing.assert_array_equal(_decode_data(payload, container, schema, tmp_path), data)
    assert all("values" not in column for column in payload["columns"])
    json.dumps(payload, allow_nan=False)


def test_binary_typed_nullable_columns_and_empty_typed_columns(tmp_path):
    pd = pytest.importorskip("pandas")
    frame = pd.DataFrame({
        "integer": pd.array([1, None, -3], dtype="Int64"),
        "logical": pd.array([True, None, False], dtype="boolean"),
        "factor": pd.Categorical(["high", None, "low"], categories=["low", "high"], ordered=True),
        "string": pd.array([None, None, None], dtype="string"),
        "empty_integer": pd.array([None, None, None], dtype="Int64"),
    })
    payload, container, schema = _encode_data(frame, tmp_path)
    assert [column["type"] for column in payload["columns"]] == [
        "integer", "logical", "factor", "character", "integer",
    ]
    for i, expected in [(0, [1, -(2**31), -3]), (1, [1, -(2**31), 0]), (2, [2, -(2**31), 1])]:
        storage = payload["columns"][i]["storage"]
        assert storage["missing_sentinel"] == -(2**31)
        np.testing.assert_array_equal(np.fromfile(tmp_path / storage["filename"], dtype="<i4"), expected)
    decoded = _decode_data(payload, container, schema, tmp_path)
    pd.testing.assert_frame_equal(decoded.drop(columns="string"), frame.drop(columns="string"))
    assert decoded["string"].isna().all()


@pytest.mark.parametrize("corruption", ["length", "byte_order", "sentinel", "factor_code"])
def test_binary_transport_rejects_corrupt_schema_or_file(tmp_path, corruption):
    pd = pytest.importorskip("pandas")
    frame = pd.DataFrame({"category": pd.Categorical(["a", None, "b"])})
    payload, container, schema = _encode_data(frame, tmp_path)
    storage = payload["columns"][0]["storage"]
    path = tmp_path / storage["filename"]
    if corruption == "length":
        path.write_bytes(path.read_bytes()[:-1])
    elif corruption == "byte_order":
        storage["byte_order"] = "big"
    elif corruption == "sentinel":
        storage["missing_sentinel"] = -1
    else:
        np.array([3, -(2**31), 2], dtype="<i4").tofile(path)
    with pytest.raises(AmeliaReferenceError):
        _decode_data(payload, container, schema, tmp_path)


def test_wide_numeric_transport_keeps_json_schema_small(tmp_path):
    payload, _, _ = _encode_data(np.zeros((1000, 90)), tmp_path)
    assert len(json.dumps(payload)) < 40000
    assert sum(path.stat().st_size for path in tmp_path.glob("*.bin")) == 1000 * 90 * 8


def test_column_names_cannot_collide_when_encoded_for_r(tmp_path):
    pd = pytest.importorskip("pandas")
    with pytest.raises(ValueError, match="unique"):
        _encode_data(pd.DataFrame([[1, 2]], columns=[1, "1"]), tmp_path)


def test_relative_rscript_is_resolved_before_temporary_working_directory(tmp_path, monkeypatch):
    executable = tmp_path / ("Rscript.exe" if os.name == "nt" else "Rscript")
    # This placeholder is only looked up, never executed. Windows requires a
    # recognized executable suffix for shutil.which's PATHEXT-based lookup.
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o700)
    monkeypatch.chdir(tmp_path)
    resolved, _ = _runtime_environment(f"./{executable.name}", None)
    assert resolved == str(executable.resolve())


@requires_r
def test_numeric_reference_roundtrip_and_official_rds_extension(tmp_path):
    data = numeric_data()
    fit = amelia_reference(data, m=2, seed=19, p2s=0, autopri=0)
    assert fit.engine == "r-amelia-reference"
    assert fit.metadata["compute_backend"] == "cpu"
    assert fit.metadata["reference_version"] == "1.8.3"
    assert fit.metadata["torch_used"] is False
    assert fit.metadata["gpu_used"] is False
    assert fit.m == 2
    for imputation in fit.imputations:
        assert isinstance(imputation, np.ndarray)
        assert np.isfinite(imputation).all()
        np.testing.assert_array_equal(imputation[~np.isnan(data)], data[~np.isnan(data)])
    saved = fit.save_rds(tmp_path / "official.rds")
    with pytest.raises(FileExistsError):
        fit.save_rds(saved)
    restored = read_reference_rds(saved, return_type="numpy")
    assert restored.engine == "unknown"
    assert restored.metadata["torch_used"] is None
    assert restored.metadata["gpu_used"] is None
    assert restored.metadata["call_engine"] == "rds-inspection"
    for left, right in zip(fit.imputations, restored.imputations):
        np.testing.assert_array_equal(left, right)
    extended = fit.extend(m=1, seed=27, p2s=0)
    assert extended.m == 3
    assert extended.engine == "appended-history"
    assert extended.metadata["gpu_used"] is False
    assert extended.metadata["provenance"]["historical_m"] == 2
    assert extended.metadata["provenance"]["new_m"] == 1
    np.testing.assert_array_equal(extended.imputations[0], fit.imputations[0])
    with pytest.raises(ValueError, match="reuses"):
        fit.extend(m=1, logs=[1])


@requires_r
def test_rds_backend_record_preserves_historical_gpu_provenance(tmp_path):
    fit = amelia_reference(numeric_data(), m=1, seed=20, p2s=0, autopri=0)
    saved = fit.save_rds(tmp_path / "source.rds")
    marked = tmp_path / "recorded-backend.rds"
    program = tmp_path / "mark-backend.R"
    # This synthetic record tests provenance handling only; no GPU was run.
    program.write_text(
        'args <- commandArgs(trailingOnly=TRUE)\n'
        'x <- readRDS(args[[1]])\n'
        'attr(x, "amelia_torch_backend") <- list(engine="synthetic-gpu-record", '
        'device="cuda", torch_used=TRUE, gpu_used=TRUE, test_record=TRUE)\n'
        'saveRDS(x, args[[2]])\n'
    )
    subprocess.run(["Rscript", "--vanilla", str(program), str(saved), str(marked)], check=True)
    inspected = read_reference_rds(marked, return_type="numpy")
    assert inspected.engine == "synthetic-gpu-record"
    assert inspected.metadata["gpu_used"] is True
    assert inspected.metadata["torch_used"] is True
    assert inspected.metadata["provenance"]["recorded_backend"]["test_record"] is True
    appended = amelia_reference(input_rds=marked, m=1, seed=21, p2s=0, return_type="numpy")
    assert appended.m == 2
    assert appended.metadata["gpu_used"] is True
    assert appended.metadata["torch_used"] is True
    assert appended.metadata["call_gpu_used"] is False
    assert appended.metadata["call_torch_used"] is False
    assert appended.metadata["call_engine"] == "r-amelia-reference"


@requires_r
def test_public_categorical_transform_prior_and_bounds_interfaces(tmp_path):
    pd = pytest.importorskip("pandas")
    rng = np.random.default_rng(610)
    n = 180
    group = pd.Categorical(
        np.tile(["south", "north", "east"], n // 3),
        categories=["east", "north", "south"], ordered=False,
    )
    ordinal = pd.Categorical(
        rng.choice(["low", "medium", "high"], n),
        categories=["low", "medium", "high"], ordered=True,
    )
    data = pd.DataFrame({
        "id": [f"person-{i}" for i in range(n)],
        "income": np.exp(rng.normal(2, 0.4, n)),
        "score": rng.normal(0.5, 0.1, n),
        "group": group,
        "rank": ordinal,
        "flag": np.tile([True, False], n // 2),
    }, index=pd.Index([f"row-{i}" for i in range(n)], name="subject"))
    data.loc[data.index[::8], "income"] = np.nan
    data.loc[data.index[::9], "score"] = np.nan
    data.loc[data.index[::10], "group"] = np.nan
    data.loc[data.index[::11], "rank"] = np.nan
    fit = amelia_reference(
        data, m=2, seed=114, p2s=0, idvars=["id"], logs=["income"],
        noms=["group"], ords=["rank"],
        priors=[[1, 3, 0.5, 0.05], [10, 3, 0.5, 0.05]], bounds=[[3, 0.0, 1.0]],
        **{"max.resample": 50},
    )
    for imputation in fit.imputations:
        assert isinstance(imputation, pd.DataFrame)
        pd.testing.assert_index_equal(imputation.index, data.index)
        pd.testing.assert_index_equal(imputation.columns, data.columns)
        assert list(imputation["group"].cat.categories) == ["east", "north", "south"]
        assert not imputation["group"].cat.ordered
        assert list(imputation["rank"].cat.categories) == ["low", "medium", "high"]
        assert imputation["rank"].cat.ordered
        assert imputation["flag"].dtype == bool
        assert imputation["score"].between(0, 1).all()
        assert not imputation.isna().any().any()
        for name in data.columns:
            observed = data[name].notna()
            pd.testing.assert_series_equal(imputation.loc[observed, name], data.loc[observed, name],
                                            check_dtype=False)
    saved = fit.save_rds(tmp_path / "categorical.rds")
    reloaded = read_reference_rds(saved, return_type="pandas")
    assert reloaded.imputations[0]["rank"].cat.ordered
    assert list(reloaded.imputations[0]["group"].cat.categories) == ["east", "north", "south"]


@requires_r
def test_single_row_prior_preserves_documented_original_indexing_quirk():
    pd = pytest.importorskip("pandas")
    values = numeric_data()
    data = pd.DataFrame(values[:, :3], columns=["a", "b", "c"])
    data.insert(0, "id", [f"person-{i}" for i in range(len(data))])
    result = amelia_reference(
        data, m=1, seed=617, p2s=0, idvars=["id"],
        priors=[[1, 2, 0.5, 0.05]], autopri=0, **{"boot.type": "none"},
    )
    # Original impfill drops the single prior's (row, column) matrix dimension:
    # the resulting vector indexes rows 1 and 2 of the first column. This bridge
    # must expose the authoritative R result, not silently repair that version.
    changed = np.flatnonzero(result.imputations[0]["id"].to_numpy() != data["id"].to_numpy())
    np.testing.assert_array_equal(changed, [0, 1])
    assert any("single-row priors" in message for message in result.warnings)


@requires_r
def test_original_error_codes_and_unknown_option_are_explicit():
    data = numeric_data()
    data[:, 1] = 1
    with pytest.raises(AmeliaReferenceError) as failure:
        amelia_reference(data, m=1, p2s=0)
    assert failure.value.code == 43
    with pytest.raises(AmeliaReferenceError, match="boot_type"):
        amelia_reference(numeric_data(), m=1, p2s=0, boot_type="none")


@requires_r
def test_saved_arglist_is_forwarded_as_an_actual_r_object(tmp_path):
    fit = amelia_reference(numeric_data(), m=1, p2s=0, seed=99, empri=3)
    rds = fit.save_rds(tmp_path / "fit.rds")
    arglist = tmp_path / "args.rds"
    # Fixed code only; paths are positional arguments, never interpolated into R.
    program = tmp_path / "extract.R"
    program.write_text(
        'args <- commandArgs(trailingOnly=TRUE)\n'
        'saveRDS(readRDS(args[[1]])$arguments, args[[2]])\n'
    )
    subprocess.run(["Rscript", "--vanilla", str(program), str(rds), str(arglist)], check=True)
    result = amelia_reference(numeric_data(), m=1, p2s=0, seed=99, arglist=RDSValue(arglist))
    assert result.m == 1
    assert result.metadata["reference_version"] == "1.8.3"
    assert np.isfinite(result.imputations[0]).all()
