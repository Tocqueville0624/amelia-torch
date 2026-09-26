"""Saved-artifact comparisons must reject mismatches without fitting or torch imports."""

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


load("summarize_benchmarks")
compare = load("compare_native_parameters")


def reports():
    config = {"m": 2, "seed": 71, "repeats": 2, "warmups": 1, "threads": 2,
              "tolerance": 1e-4, "max_iterations": 300, "empri": None, "autopri": 0.05,
              "dtype": "float32", "device": "cpu"}
    fit = {"device": "cpu", "dtype": "float32", "bootstrap_attempts": 1,
           "iterations": 5, "converged": True}
    diagnostics = {"rng": compare.RNG, "seed": 71, "engine": "torch-native-continuous",
                   "reference_version": "1.8.3", "device": "cpu", "dtype": "float32",
                   "wholly_missing_rows_retained": 0, "column_order_zero_based": [1, 0],
                   "scale_mean_original_order": [2.0, 4.0], "scale_sd_original_order": [1.0, 2.0],
                   "replicates": [copy.deepcopy(fit), copy.deepcopy(fit)]}
    cpu = {"configuration": config, "input_sha256": "a" * 64, "shape": [3, 2],
           "environment": {"python": "3.12", "numpy": "2.0", "torch": "2.1",
                           "platform": "recorded-linux", "cpu_threads": 2,
                           "cuda_runtime": "12.8", "mps_cpu_fallback": "0"},
           "runs": [{"warmup": True, "seed": 100071},
                    {"warmup": False, "seed": 71, "diagnostics": diagnostics},
                    {"warmup": False, "seed": 72}]}
    gpu = copy.deepcopy(cpu)
    gpu["configuration"]["device"] = "cuda"
    gpu["runs"][1]["diagnostics"]["device"] = "cuda"
    for item in gpu["runs"][1]["diagnostics"]["replicates"]:
        item["device"] = "cuda"
    return cpu, gpu


def arrays():
    data = np.array([[1.0, np.nan], [2.0, 4.0], [3.0, 6.0]])
    mask = np.isnan(data)
    samples = np.stack([np.nan_to_num(data, nan=2.0), np.nan_to_num(data, nan=2.2)])
    parameters = {"theta": np.stack([np.eye(3), np.eye(3)], axis=-1),
                  "sample_imputations": samples}
    return data, mask, parameters


def test_same_dtype_metadata_uses_report_precision_not_npz_storage():
    cpu, gpu = reports()
    contract = compare.pairing_contract(cpu, gpu, "cuda", 2, 2)
    _, _, parameters = arrays()
    assert parameters["theta"].dtype == np.float64
    assert contract["computation_dtype"] == "float32"
    assert contract["bootstrap_attempts_per_imputation"] == [1, 1]
    assert contract["NPZ_embeds_seed_or_input_hash"] is False
    assert contract["bootstrap_indices_or_normals_archived"] is False


@pytest.mark.parametrize("change,reason", [
    ("input", "paired_input_hash_mismatch"),
    ("rng", "PCG64"),
    ("dtype", "diagnostic_backend_mismatch"),
    ("fit_dtype", "replicate_backend_mismatch"),
    ("missing_scale", "missing_or_invalid:scale_sd"),
    ("scale", "preprocessing_metadata_mismatch"),
    ("order", "preprocessing_metadata_mismatch"),
    ("missing_attempt", "missing_or_invalid_bootstrap_attempts"),
    ("attempts", "bootstrap_attempt_counts_differ"),
    ("version", "runtime_mismatch_or_missing:numpy"),
    ("seed", "measured_seed_schedule_mismatch"),
    ("duplicate_seed", "measured_seed_schedule_mismatch"),
    ("missing_first", "measured_seed_schedule_mismatch"),
])
def test_pairing_rejects_wrong_or_missing_observable_metadata(change, reason):
    cpu, gpu = reports()
    diag = gpu["runs"][1]["diagnostics"]
    if change == "input":
        gpu["input_sha256"] = "b" * 64
    elif change == "rng":
        diag["rng"] = "R L'Ecuyer-CMRG"
    elif change == "dtype":
        diag["dtype"] = "float64"
    elif change == "fit_dtype":
        diag["replicates"][0]["dtype"] = "float64"
    elif change == "missing_scale":
        del diag["scale_sd_original_order"]
    elif change == "scale":
        diag["scale_sd_original_order"][0] = 1.01
    elif change == "order":
        diag["column_order_zero_based"] = [0, 1]
    elif change == "missing_attempt":
        del diag["replicates"][0]["bootstrap_attempts"]
    elif change == "attempts":
        diag["replicates"][0]["bootstrap_attempts"] = 2
    elif change == "version":
        gpu["environment"]["numpy"] = "different"
    elif change == "seed":
        gpu["runs"][1]["seed"] = 70
    elif change == "duplicate_seed":
        gpu["runs"][2]["seed"] = 71
    else:
        gpu["runs"].pop(1)
    with pytest.raises(ValueError, match=reason):
        compare.pairing_contract(cpu, gpu, "cuda", 2, 2)


def test_differences_describe_saved_elements_without_equivalence_threshold():
    result = compare.differences([0.0, 1.0, 4.0], [2.0, 1.0, 5.0])
    assert result["elements"] == 3
    assert result["exact_numeric_equal_elements"] == 1
    assert result["maximum_absolute"] == 2.0
    assert result["maximum_relative_where_reference_exceeds_floor"] == 0.25
    assert result["maximum_absolute_near_zero_reference"] == 2.0
    assert "passed" not in result and "equivalent" not in result


def test_empty_subset_has_no_invented_zero_error():
    result = compare.differences([], [])
    assert result["elements"] == 0
    assert result["maximum_absolute"] is None


@pytest.mark.parametrize("right", [[np.inf], [np.nan], [-1e308]])
def test_invalid_or_overflowing_differences_are_not_scored(right):
    with pytest.raises(ValueError, match="nonfinite|overflow"):
        compare.differences([1e308], right)


def test_samples_compare_observed_and_missing_cells_separately():
    data, mask, cpu = arrays()
    gpu = copy.deepcopy(cpu)
    gpu["sample_imputations"][0, 0, 1] += 0.5
    result = compare.compare_arrays(cpu, gpu, data, mask, 2, 1e-12, [1.0, 2.0], ["a", "b"])
    assert len(result) == 2
    assert result[0]["sample_observed_cells"]["elements"] == 5
    assert result[0]["sample_observed_cells"]["maximum_absolute"] == 0.0
    assert result[0]["sample_artificially_missing_cells"]["elements"] == 1
    assert result[0]["sample_artificially_missing_cells"]["maximum_absolute"] == 0.5
    assert result[1]["sample_artificially_missing_cells"]["maximum_absolute"] == 0.0
    scaled = result[0]["sample_missing_differences_in_full_truth_sd_units"]
    assert scaled["maximum_absolute"] == 0.25
    assert scaled["root_mean_squared_pair_difference"] == 0.25
    per_column = result[0]["sample_missing_differences_per_column"]
    assert per_column[0]["missing_elements"] == 0
    assert per_column[0]["maximum_absolute_original_units"] is None
    assert per_column[1]["maximum_absolute_original_units"] == 0.5
    assert per_column[1]["maximum_absolute_divided_by_full_truth_sd"] == 0.25


def test_common_observed_value_error_is_rejected_against_original_input():
    data, mask, cpu = arrays()
    gpu = copy.deepcopy(cpu)
    cpu["sample_imputations"][0, 1, 0] += 1
    gpu["sample_imputations"][0, 1, 0] += 1
    with pytest.raises(ValueError, match="changed_observed_cells"):
        compare.compare_arrays(cpu, gpu, data, mask, 2, 1e-12, [1.0, 2.0], ["a", "b"])


def test_normalized_missing_rms_uses_each_cells_own_column_scale():
    data = np.array([[np.nan, 10.0], [3.0, np.nan], [5.0, 30.0]])
    cpu = {"theta": np.eye(3)[:, :, None],
           "sample_imputations": np.array([[[1.0, 10.0], [3.0, 20.0], [5.0, 30.0]]])}
    gpu = copy.deepcopy(cpu)
    gpu["sample_imputations"][0, 0, 0] += 2.0
    gpu["sample_imputations"][0, 1, 1] += 8.0
    result = compare.compare_arrays(cpu, gpu, data, np.isnan(data), 1, 1e-12,
                                    [2.0, 4.0], ["a", "b"])[0]
    assert result["sample_artificially_missing_cells"]["maximum_absolute"] == 8.0
    normalized = result["sample_missing_differences_in_full_truth_sd_units"]
    assert normalized["elements"] == 2
    assert normalized["maximum_absolute"] == 2.0
    assert normalized["root_mean_squared_pair_difference"] == pytest.approx(np.sqrt(2.5))
    assert [column["maximum_absolute_divided_by_full_truth_sd"] for column in
            result["sample_missing_differences_per_column"]] == [1.0, 2.0]


def test_normalization_uses_complete_full_truth_and_sample_sd_not_prefix_or_observed(tmp_path):
    truth = np.column_stack([np.arange(1002, dtype=float), np.arange(1002, dtype=float) * 3])
    truth[-1, 1] = 1000000.0
    data = truth.copy()
    data[-1, 1] = np.nan  # Largest value remains part of the truth SD.
    path = tmp_path / "prepared.npz"
    np.savez(path, data=data, truth=truth, artificial_missing_mask=np.isnan(data),
             column_names=np.array(["a", "b"]))
    _, _, _, scale = compare.load_input(path, compare.sha256(path), truth.shape)
    np.testing.assert_array_equal(scale, np.nanstd(truth, axis=0, ddof=1))
    assert scale[1] != np.std(truth[:1000, 1], ddof=1)
    assert scale[1] != np.nanstd(data[:, 1], ddof=1)
    assert scale[1] != np.std(truth[:, 1], ddof=0)


@pytest.mark.parametrize("scale", [[0.0, 1.0], [np.nan, 1.0], [1.0]])
def test_invalid_truth_scale_cannot_produce_normalized_differences(scale):
    data, mask, cpu = arrays()
    with pytest.raises(ValueError, match="invalid_full_truth_sd"):
        compare.compare_arrays(cpu, cpu, data, mask, 2, 1e-12, scale, ["a", "b"])


@pytest.mark.parametrize("change", ["theta_shape", "sample_shape", "nonfinite", "object", "extra"])
def test_bad_parameter_npz_is_rejected_without_pickle(tmp_path, change):
    _, _, parameters = arrays()
    if change == "theta_shape":
        parameters["theta"] = np.eye(2)
    elif change == "sample_shape":
        parameters["sample_imputations"] = parameters["sample_imputations"][:, :2]
    elif change == "nonfinite":
        parameters["theta"][0, 0, 0] = np.inf
    elif change == "object":
        parameters["theta"] = parameters["theta"].astype(object)
    else:
        parameters["unexpected"] = np.array([1])
    path = tmp_path / "parameters.npz"
    np.savez(path, **parameters)
    with pytest.raises(ValueError):
        compare.load_parameters(path, 2, 2, 3)


@pytest.mark.parametrize("change", ["mask", "observed", "truth", "hash"])
def test_prepared_truth_and_mask_contract_is_enforced(tmp_path, change):
    data, mask, parameters = arrays()
    truth = parameters["sample_imputations"][0].copy()
    if change == "mask":
        mask[0, 1] = False
    elif change == "observed":
        truth[1, 0] += 1
    elif change == "truth":
        truth[0, 1] = np.nan
    path = tmp_path / "prepared.npz"
    np.savez(path, data=data, truth=truth, artificial_missing_mask=mask,
             column_names=np.array(["a", "b"]))
    digest = "f" * 64 if change == "hash" else compare.sha256(path)
    with pytest.raises(ValueError):
        compare.load_input(path, digest, (3, 2))


def test_incomplete_suite_really_calls_existing_auditor_with_full_cuda_plan(tmp_path, monkeypatch):
    (tmp_path / "suite.json").write_text(json.dumps({
        "completed_utc": "fixture", "execution": [], "seeds": [1],
        "source_sha256": {"src/fixture.py": "a" * 64},
    }))
    original = compare.audit_suite
    calls = []

    def spy(suite, reports, expected, **kwargs):
        calls.append((expected, kwargs))
        return original(suite, reports, expected, **kwargs)

    monkeypatch.setattr(compare, "audit_suite", spy)
    with pytest.raises(ValueError, match="independent_complete_suite_audit_failed"):
        compare.load_native_suite(tmp_path, "cuda", 2)
    assert len(calls[0][0]) == 18
    assert {method for _, method in calls[0][0]} == {
        "cpu64", "cpu32", "cuda64", "cuda32", "r_serial", "r_snow2"}
    assert calls[0][1] == {"expected_rows": 100000}


def stub_audited_suite():
    reports = {}
    for dataset, p in compare.COLUMNS.items():
        for method in ("cpu64", "cpu32", "cuda64", "cuda32"):
            reports[(dataset, method)] = {
                "parameter_file": f"{dataset}-{method}.parameters.npz",
                "shape": [100000, p], "configuration": {"m": 1},
            }
    return {"source_sha256": {}}, reports, {}, {"all_passed": True}


def test_exact_parameter_file_set_is_required(tmp_path, monkeypatch):
    monkeypatch.setattr(compare, "load_native_suite", lambda *args: stub_audited_suite())
    (tmp_path / "unrelated.npz").write_bytes(b"preserved")
    with pytest.raises(ValueError, match="parameter_file_set_not_exactly_expected"):
        compare.analyze(tmp_path, tmp_path, "cuda", 2, 1e-12)
    assert (tmp_path / "unrelated.npz").read_bytes() == b"preserved"


def test_archive_hash_mismatch_retains_actual_file_fingerprint(tmp_path, monkeypatch):
    fixture = stub_audited_suite()
    monkeypatch.setattr(compare, "load_native_suite", lambda *args: fixture)
    hashes = {}
    for report in fixture[1].values():
        path = tmp_path / report["parameter_file"]
        path.write_bytes(b"unused binary payload; hash checked before NPZ loading")
        hashes[path.name] = "f" * 64
    evidence = {}
    with pytest.raises(ValueError, match="archived_parameter_sha256_mismatch"):
        compare.analyze(tmp_path, tmp_path, "cuda", 2, 1e-12, hashes, evidence)
    name = "covertype-cpu64.parameters.npz"
    assert evidence["parameter_files"][name]["sha256"] == compare.sha256(tmp_path / name)
    assert evidence["parameter_files"][name]["archived_sha256_verified"] is False


def test_new_output_and_checksum_are_exact_and_cannot_be_overwritten(tmp_path):
    path = tmp_path / "comparison.json"
    compare.write_new_report(path, {"comparison": "descriptive only"})
    original = path.read_bytes()
    checksum = json.loads((tmp_path / "comparison.json.sha256.json").read_text())
    assert checksum["sha256"] == hashlib.sha256(original).hexdigest()
    assert checksum["bytes"] == len(original)
    with pytest.raises(ValueError, match="output_already_exists"):
        compare.write_new_report(path, {"changed": True})
    assert path.read_bytes() == original


def test_failed_analysis_writes_explicit_nonpassing_report_and_raw_suite_hash(tmp_path, monkeypatch):
    (tmp_path / "suite.json").write_text('{}\n')
    output = tmp_path / "failed.json"
    monkeypatch.setattr(sys, "argv", ["compare_native_parameters.py", "--input-dir", str(tmp_path),
                                     "--prepared-dir", str(tmp_path), "--output", str(output)])
    assert compare.main() == 1
    result = json.loads(output.read_text())
    assert result["all_pairing_contracts_verified"] is False
    assert result["comparisons"] == []
    assert result["fitting_performed"] is False
    assert result["available_input_evidence"]["suite_sha256"] == compare.sha256(tmp_path / "suite.json")


def test_truncated_npz_is_recorded_as_failure_with_its_actual_hash(tmp_path, monkeypatch):
    fixture = stub_audited_suite()
    monkeypatch.setattr(compare, "load_native_suite", lambda *args: fixture)
    for report in fixture[1].values():
        p = report["shape"][1]
        np.savez_compressed(tmp_path / report["parameter_file"], theta=np.zeros((p + 1, p + 1, 1)),
                            sample_imputations=np.zeros((1, 1000, p)))
    broken = tmp_path / "covertype-cpu64.parameters.npz"
    broken.write_bytes(broken.read_bytes()[:-20])
    output = tmp_path / "failed-truncated.json"
    monkeypatch.setattr(sys, "argv", ["compare_native_parameters.py", "--input-dir", str(tmp_path),
                                     "--prepared-dir", str(tmp_path), "--output", str(output)])
    assert compare.main() == 1
    result = json.loads(output.read_text())
    assert result["error_type"] == "BadZipFile"
    assert result["all_pairing_contracts_verified"] is False
    assert result["comparisons"] == []
    evidence = result["available_input_evidence"]["parameter_files"][broken.name]
    assert evidence["sha256"] == compare.sha256(broken)


@pytest.mark.parametrize("payload,reason", [
    ([], "suite_not_an_object"),
    ({"execution": {}}, "execution_not_a_list"),
    ({"execution": [1]}, "execution_member_not_an_object"),
])
def test_malformed_suite_structure_is_recorded_without_traceback(tmp_path, monkeypatch, payload, reason):
    (tmp_path / "suite.json").write_text(json.dumps(payload))
    output = tmp_path / "bad-structure.json"
    monkeypatch.setattr(sys, "argv", ["compare_native_parameters.py", "--input-dir", str(tmp_path),
                                     "--prepared-dir", str(tmp_path), "--output", str(output)])
    assert compare.main() == 1
    result = json.loads(output.read_text())
    assert result["all_pairing_contracts_verified"] is False
    assert result["error"] == reason
    assert "traceback" not in result


def test_unexpected_parser_exception_is_portable_and_cannot_pass(tmp_path, monkeypatch):
    def parser_failure(*args):
        raise RuntimeError("private path /Users/person/private/input.npz")
    monkeypatch.setattr(compare, "analyze", parser_failure)
    output = tmp_path / "parser-failure.json"
    monkeypatch.setattr(sys, "argv", ["compare_native_parameters.py", "--input-dir", str(tmp_path),
                                     "--prepared-dir", str(tmp_path), "--output", str(output)])
    assert compare.main() == 1
    result = json.loads(output.read_text())
    assert result["error_type"] == "RuntimeError"
    assert result["error"] == "input_read_or_schema_failure"
    assert "/Users/" not in output.read_text()
