"""Adversarial measurement records must not become successful benchmark claims."""

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


native = load("summarize_benchmarks")
hybrid = load("summarize_hybrid")


def r_report():
    config = {
        "n": 100000,
        "p": 10,
        "m": 2,
        "warmups": 1,
        "seeds": [10, 11],
        "warmup_seeds": [100010],
        "completely_missing_input_rows": 0,
        "missing_cells": 300000,
        "heldout_cells": 300000,
        "parallel": "no",
        "ncpus": 1,
        "tolerance": 1e-4,
        "autopri": 0.05,
        "empri": None,
        "emburn": [0, 300],
        "startvals": 0,
        "boot.type": "ordinary",
    }
    runs = []
    for phase, seed, elapsed in (
        ("warmup", 100010, 4.0),
        ("measured", 10, 1.0),
        ("measured", 11, 3.0),
    ):
        runs.append(
            {
                "phase": phase,
                "seed": seed,
                "wall_seconds": elapsed,
                "error": None,
                "code": 1,
                "converged_by_tolerance": [True, True],
                "quality_status": "computed",
                "observed_values_unchanged": [True, True],
                "remaining_missing_cells": [0, 0],
                "nonfinite_cells": [0, 0],
                "normalized_heldout_rmse": [0.2, 0.3],
            }
        )
    return {"config": config, "runs": runs, "summary": {"median_seconds": 999}}


def native_fixture():
    reference = r_report()
    report = {
        "configuration": {
            "m": 2,
            "warmups": 1,
            "repeats": 2,
            "seed": 10,
            "device": "cpu",
            "dtype": "float64",
            "tolerance": 1e-4,
            "empri": None,
            "autopri": 0.05,
            "max_iterations": 300,
        },
        "shape": [100000, 10],
        "input_sha256": "b" * 64,
        "runs": [],
    }
    for phase, seed, elapsed in ((True, 100010, 4.0), (False, 10, 1.0), (False, 11, 3.0)):
        report["runs"].append(
            {
                "warmup": phase,
                "seed": seed,
                "wall_seconds": elapsed,
                "status": "ok",
                "diagnostics": {
                    "converged": True,
                    "device": "cpu",
                    "dtype": "float64",
                    "wholly_missing_rows_retained": 0,
                    "replicates": [
                        {"converged": True, "device": "cpu", "dtype": "float64"} for _ in range(2)
                    ],
                },
                "quality": {
                    "observed_values_preserved": True,
                    "remaining_missing_cells": [0, 0],
                    "unscored_heldout_cells_per_imputation": [0, 0],
                    "normalized_rmse_per_imputation": [0.2, 0.3],
                },
            }
        )
    reports = {("covertype", "r_serial"): reference, ("covertype", "cpu64"): report}
    suite = {
        "completed_utc": "2026-09-24T00:00:00Z",
        "seeds": [10, 11],
        "source_sha256": {"source.py": "a" * 64},
        "execution": [
            {
                "dataset": key[0],
                "method": key[1],
                "result": f"{key[0]}-{key[1]}.json",
                "exit_status": 0,
                "input_sha256": "b" * 64,
            }
            for key in reports
        ],
    }
    return suite, reports, list(reports)


def hybrid_fixture():
    report = r_report()
    task = {"dataset": "covertype", "method": "cpu64", "device": "cpu", "dtype": "float64"}
    settings = {
        **report["config"],
        "rows": 100000,
        "repeats": 2,
        "threads": 4,
        "RNGkind": "L'Ecuyer-CMRG",
    }
    evidence = {
        "shape": [100000, 10],
        "npz_sha256": "b" * 64,
        "source_archive_sha256": "c" * 64,
        "csv": {
            field: {"sha256": "d" * 64, "rows": 100000, "columns": 10}
            for field in ("input", "truth", "mask")
        },
    }
    source = {"source.py": "a" * 64}
    report.update(
        {
            "engine": hybrid.ENGINE,
            "reference_version": "1.8.3",
            "requested_em_backend": {"device": "cpu", "dtype": "float64"},
            "provenance": {
                "source_sha256": copy.deepcopy(source),
                "input": copy.deepcopy(evidence),
            },
            "environment": {
                "requested_python_matches_active": True,
                "torch_threads": 4,
                "RNGkind": ["L'Ecuyer-CMRG", "Inversion", "Rejection"],
            },
        }
    )
    report["config"].update({"device": "cpu", "em_dtype": "float64", "torch_threads": 4})
    for run in report["runs"]:
        run.update(
            {
                "status": "ok",
                "quality_passed": True,
                "backend_contract_passed": True,
                "unscored_heldout_cells_per_imputation": [0, 0],
                "unexpected_nonfinite_cells": [0, 0],
                "wholly_missing_rows_preserved": [True, True],
                "backend": {
                    "engine": hybrid.CALL_ENGINE,
                    "call_engine": hybrid.CALL_ENGINE,
                    "reference_version": "1.8.3",
                    "device": "cpu",
                    "dtype": "float64",
                    "converged": True,
                    "fits": [
                        {"converged": True, "device": "cpu", "dtype": "float64", "iterations": 4}
                        for _ in range(2)
                    ],
                },
            }
        )
    suite = {
        "completed_utc": "2026-09-24T00:00:00Z",
        "settings": settings,
        "planned_order": [task],
        "seeds": [10, 11],
        "warmup_seeds": [100010],
        "source_sha256": source,
        "inputs": {"covertype": evidence},
        "execution": [
            {
                **task,
                "status": "completed",
                "exit_status": 0,
                "source_unchanged_during_process": True,
                "report_exists": True,
                "report_sha256": "f" * 64,
                "result": "covertype-cpu64.json",
            }
        ],
    }
    return suite, {("covertype", "cpu64"): report}, {("covertype", "cpu64"): "f" * 64}


def test_native_audit_reads_m_and_warmups_and_recomputes_timing():
    suite, reports, plan = native_fixture()
    result = native.audit_suite(suite, reports, plan)
    assert result["all_passed"]
    assert all(row["m"] == 2 and row["requested_warmups"] == 1 for row in result["measurements"])
    assert result["measurements"][0]["median_seconds"] == 2.0
    assert result["measurements"][0]["iqr_seconds"] == [1.5, 2.5]


@pytest.mark.parametrize(
    "change", ["missing", "duplicate", "nonzero_exit", "false_exit", "missing_report"]
)
def test_native_missing_or_failed_tasks_cannot_vacuously_pass(change):
    suite, reports, plan = native_fixture()
    if change == "missing":
        suite["execution"].pop()
    elif change == "duplicate":
        suite["execution"].append(copy.deepcopy(suite["execution"][0]))
    elif change == "missing_report":
        reports.pop(plan[0])
    else:
        suite["execution"][0]["exit_status"] = False if change == "false_exit" else 1
    assert not native.audit_suite(suite, reports, plan)["all_passed"]


@pytest.mark.parametrize("elapsed", [0, -1, float("inf"), float("nan"), True])
def test_nonpositive_or_nonfinite_times_never_receive_success_summary(elapsed):
    suite, reports, plan = native_fixture()
    reports[plan[0]]["runs"][1]["wall_seconds"] = elapsed
    result = native.audit_suite(suite, reports, plan)
    assert not result["all_passed"]
    assert result["measurements"][0]["median_seconds"] is None


def test_native_top_level_converged_does_not_hide_failed_individual_fit():
    suite, reports, plan = native_fixture()
    reports[("covertype", "cpu64")]["runs"][1]["diagnostics"]["replicates"][0]["converged"] = False
    assert not native.audit_suite(suite, reports, plan)["all_passed"]


def test_duplicate_measured_seed_fails_even_when_counts_are_correct():
    suite, reports, plan = native_fixture()
    reports[plan[0]]["runs"][-1]["seed"] = 10
    assert not native.audit_suite(suite, reports, plan)["all_passed"]


@pytest.mark.parametrize(
    "change", ["boolean_code", "absent_input_hash", "source_changed", "heldout"]
)
def test_native_success_requires_typed_and_complete_evidence(change):
    suite, reports, plan = native_fixture()
    if change == "boolean_code":
        reports[plan[0]]["runs"][1]["code"] = True
    elif change == "absent_input_hash":
        suite["execution"][1].pop("input_sha256")
        reports[plan[1]].pop("input_sha256")
    elif change == "source_changed":
        suite["execution"][0]["source_unchanged_during_process"] = False
    else:
        reports[plan[0]]["config"]["heldout_cells"] -= 1
    assert not native.audit_suite(suite, reports, plan)["all_passed"]


def test_hybrid_independent_audit_passes_complete_evidence():
    suite, reports, hashes = hybrid_fixture()
    result = hybrid.audit_hybrid_suite(suite, reports, hashes)
    assert result["all_passed"]
    assert result["measurements"][0]["median_seconds"] == 2.0


def test_actual_r_api_metadata_uses_call_engine_not_report_title():
    fixture = json.loads(
        (Path(__file__).parent / "fixtures/hybrid_backend_metadata.json").read_text()
    )
    backend = fixture["backend"]
    assert backend["engine"] == "r-amelia-torch-em"
    assert backend["call_engine"] == "r-amelia-torch-em"
    assert hybrid.ENGINE == "R-Amelia-pipeline-with-PyTorch-EM"
    assert hybrid.audit_backend(backend, "cpu", "float64", m=1) == []
    assert backend["torch_used"] is True and backend["current_call_torch_used"] is True
    assert backend["gpu_used"] is False and backend["current_call_gpu_used"] is False
    assert backend["historical_m"] == 0 and backend["new_m"] == backend["total_m"] == 1
    assert backend["fits"][0]["explicit_cpu_work"] == ["initialization", "missingness_grouping"]


def test_single_imputation_scalar_r_fields_with_actual_backend_schema():
    """Synthetic success record tests m1 serialization; no old pilot status is changed."""
    suite, reports, hashes = hybrid_fixture()
    report = reports[("covertype", "cpu64")]
    suite["settings"].update({"m": 1, "warmups": 0, "repeats": 1})
    suite.update({"seeds": [10], "warmup_seeds": []})
    report["config"].update({"m": 1, "warmups": 0, "seeds": 10, "warmup_seeds": []})
    run = report["runs"][1]
    for field in (
        "converged_by_tolerance",
        "observed_values_unchanged",
        "remaining_missing_cells",
        "nonfinite_cells",
        "normalized_heldout_rmse",
        "unscored_heldout_cells_per_imputation",
        "unexpected_nonfinite_cells",
        "wholly_missing_rows_preserved",
    ):
        run[field] = run[field][0]
    run["backend"] = json.loads(
        (Path(__file__).parent / "fixtures/hybrid_backend_metadata.json").read_text()
    )["backend"]
    report["runs"] = [run]
    result = hybrid.audit_hybrid_suite(suite, reports, hashes)
    assert result["all_passed"]
    assert result["measurements"][0]["m"] == 1


@pytest.mark.parametrize("field", ["engine", "call_engine", "reference_version"])
def test_incorrect_backend_contract_names_fail_even_if_summary_claims_success(field):
    suite, reports, hashes = hybrid_fixture()
    reports[("covertype", "cpu64")]["runs"][1]["backend"][field] = hybrid.ENGINE
    assert not hybrid.audit_hybrid_suite(suite, reports, hashes)["all_passed"]


@pytest.mark.parametrize(
    "change",
    [
        "missing_task",
        "exit",
        "source",
        "hash",
        "unscored",
        "nonfinite",
        "observed",
        "fit",
        "warmup",
        "seed",
        "settings",
        "provenance",
        "runtime",
    ],
)
def test_hybrid_success_labels_do_not_override_failed_evidence(change):
    suite, reports, hashes = hybrid_fixture()
    report = reports[("covertype", "cpu64")]
    run = report["runs"][1]
    if change == "missing_task":
        suite["execution"] = []
    elif change == "exit":
        suite["execution"][0]["exit_status"] = 1
    elif change == "source":
        suite["execution"][0]["source_unchanged_during_process"] = False
    elif change == "hash":
        hashes[("covertype", "cpu64")] = "e" * 64
    elif change == "unscored":
        run["unscored_heldout_cells_per_imputation"][0] = 1
    elif change == "nonfinite":
        run["unexpected_nonfinite_cells"][0] = 1
    elif change == "observed":
        run["observed_values_unchanged"][0] = False
    elif change == "fit":
        run["backend"]["fits"][0]["converged"] = False
    elif change == "warmup":
        report["runs"].pop(0)
    elif change == "seed":
        run["seed"] = 11
    elif change == "settings":
        report["config"]["m"] = 5
    elif change == "provenance":
        report["provenance"]["source_sha256"]["source.py"] = "e" * 64
    else:
        report["environment"]["requested_python_matches_active"] = False
    result = hybrid.audit_hybrid_suite(suite, reports, hashes)
    assert not result["all_passed"]


def test_empty_hybrid_plan_never_passes():
    suite, reports, hashes = hybrid_fixture()
    suite["planned_order"], suite["execution"] = [], []
    assert not hybrid.audit_hybrid_suite(suite, reports, hashes)["all_passed"]


@pytest.mark.parametrize(
    "private",
    ["/Users/person/file", "/home/person/file", "C:\\Users\\person\\file", "C:/Users/person/file"],
)
def test_portable_export_refuses_private_paths(tmp_path, private):
    path = tmp_path / "report.json"
    path.write_text(json.dumps({"error": private}))
    with pytest.raises(ValueError, match="Private path"):
        native.portable_bytes(path)


def test_export_refuses_to_overwrite_existing_measurements(tmp_path):
    path = tmp_path / "report.json"
    path.write_bytes(b"original")
    with pytest.raises(FileExistsError):
        native.export_files([(path, b"modified")])
    assert path.read_bytes() == b"original"


@pytest.mark.parametrize(
    "name", ["../report.json", "report.config.json", "folder/report.json", "folder\\report.json"]
)
def test_configs_and_external_paths_are_never_exported_as_reports(tmp_path, name):
    with pytest.raises(ValueError):
        native.report_path(tmp_path, name)


def test_hybrid_cli_exports_exact_raw_portable_reports_without_configs(tmp_path):
    suite, reports, _ = hybrid_fixture()
    source, output = tmp_path / "input", tmp_path / "output"
    source.mkdir()
    raw = (json.dumps(reports[("covertype", "cpu64")], indent=2) + "\n").encode()
    (source / "covertype-cpu64.json").write_bytes(raw)
    (source / "covertype-cpu64.config.json").write_text('{"input": "/Users/private/local.csv"}')
    suite["execution"][0]["report_sha256"] = hashlib.sha256(raw).hexdigest()
    suite_raw = (json.dumps(suite, indent=2) + "\n").encode()
    (source / "suite.json").write_bytes(suite_raw)
    command = [
        sys.executable,
        str(SCRIPTS / "summarize_hybrid.py"),
        "--input-dir",
        str(source),
        "--output-dir",
        str(output),
    ]
    first = subprocess.run(command, capture_output=True, text=True, check=False)
    assert first.returncode == 0, first.stderr
    assert (output / "hybrid-reports/covertype-cpu64.json").read_bytes() == raw
    assert (output / "hybrid-reports/suite.json").read_bytes() == suite_raw
    assert not list(output.rglob("*.config.json"))
    summary = json.loads((output / "hybrid-summary.json").read_text())
    assert summary["all_passed"]
    assert summary["measurements"][0]["result_sha256"] == hashlib.sha256(raw).hexdigest()
    assert subprocess.run(command, capture_output=True, check=False).returncode == 0
