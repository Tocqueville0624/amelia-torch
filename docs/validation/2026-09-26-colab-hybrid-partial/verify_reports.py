"""Verify this eleven-report collection offline, without inventing a suite or fitting.

Run from this repository. Optionally pass an extracted reports directory to prove
archive round-trip reproduction. Successful checks cover recovered reports only.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from summarize_benchmarks import audit_report  # noqa: E402
from summarize_hybrid import audit_backend  # noqa: E402

DATASETS = {"covertype": 10, "household_power": 7, "year_prediction_msd": 90}
METHODS = ("cpu64", "cpu32", "cuda64", "cuda32")
EXPECTED = {(d, m) for d in DATASETS for m in METHODS} - {("year_prediction_msd", "cuda32")}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def archive_files(path, digest):
    require(sha(path.read_bytes()) == digest, f"Archive SHA mismatch: {path.name}")
    result = {}
    with tarfile.open(path, "r:gz") as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            require(member.isfile() and not name.is_absolute() and ".." not in name.parts,
                    "Non-file or unsafe archive member")
            require(member.name not in result, "Duplicate archive member")
            result[member.name] = archive.extractfile(member).read()
    return result


def verify(reports_dir=None):
    manifest = json.loads((HERE / "collection-manifest.json").read_text())
    if reports_dir is None:
        raw_reports = archive_files(HERE / manifest["archive"]["filename"],
                                    manifest["archive"]["sha256"])
    else:
        raw_reports = {"reports/" + p.name: p.read_bytes() for p in reports_dir.glob("*.json")}
    require(set(raw_reports) == {item["archive_path"] for item in manifest["files"]},
            "Report collection differs from the eleven-file manifest")
    native_info = manifest["native_baseline_archive"]
    native = archive_files(HERE / native_info["path"], native_info["sha256"])

    def original(dataset, method):
        return json.loads(native[f"results/local/cloud/native/{dataset}-{method}.json"])

    rows, totals, common_inputs = [], Counter(), {}
    common_bridge = None
    for entry in manifest["files"]:
        name = entry["archive_path"]
        raw = raw_reports[name]
        require(len(raw) == entry["bytes"] and sha(raw) == entry["sha256"], name + " hash/size")
        report = json.loads(raw)
        dataset, method = Path(name).stem.rsplit("-", 1)
        require((dataset, method) in EXPECTED, "Unexpected configuration")
        device, dtype = ("cuda" if method.startswith("cuda") else "cpu"), "float" + method[-2:]
        config, env, provenance = report["config"], report["environment"], report["provenance"]
        audit = audit_report(report, "r_hybrid", list(range(20260923, 20260928)), 100000, DATASETS[dataset])
        require(audit["independent_quality_audit_passed"] and not audit["audit_errors"], name + " quality")
        require(report["engine"] == "R-Amelia-pipeline-with-PyTorch-EM" and report["reference_version"] == "1.8.3", name + " engine")
        require(report["requested_em_backend"] == {"device": device, "dtype": dtype}, name + " requested backend")
        require(config["device"] == device and config["em_dtype"] == dtype and config["torch_threads"] == env["torch_threads"] == 2, name + " actual backend/threads")
        require(config["parallel"] == "no" and config["ncpus"] == 1 and config["m"] == 5, name + " scheduling")
        require(config["seeds"] == list(range(20260923, 20260928)) and config["warmup_seeds"] == [20360923, 20360924], name + " seeds")
        require(config["tolerance"] == 1e-4 and config["emburn"] == [0, 300] and config["autopri"] == .05 and config["empri"] is None and config["startvals"] == 0 and config["boot.type"] == "ordinary", name + " settings")
        require(all(env["thread_environment"][key] == "2" for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")), name + " thread caps")
        require(env["requested_python_matches_active"] and env["RNGkind"] == ["L'Ecuyer-CMRG", "Inversion", "Rejection"], name + " Python/RNG")
        require(device != "cuda" or env["cuda_tf32_allowed"] is False, name + " TF32")
        require(provenance["source_sha256"] == manifest["source_sha256_matching_pinned_git"], name + " source fingerprint")
        if common_bridge is None:
            common_bridge = env["installed_bridge_files_md5"]
        require(env["installed_bridge_files_md5"] == common_bridge, name + " installed bridge")
        metadata = json.loads(native[f"data/prepared/{dataset}-n100000-block_mcar-rate30-seed20260923.json"])
        input_meta = provenance["input"]
        require(input_meta["npz_sha256"] == metadata["npz_sha256"] == original(dataset, "cpu64")["input_sha256"], name + " input NPZ")
        require(input_meta["source_archive_sha256"] == metadata["source_archive_sha256"] and input_meta["shape"] == metadata["shape"] == [100000, DATASETS[dataset]], name + " source/shape")
        require(config["heldout_cells"] == config["missing_cells"] == metadata["artificial_missing_cells"] and config["completely_missing_input_rows"] == 0, name + " heldout")
        common_inputs.setdefault(dataset, input_meta)
        require(common_inputs[dataset] == input_meta, name + " CSV provenance")
        reference, snow = original(dataset, "r_serial"), original(dataset, "r_snow2")
        require(reference["environment"]["RNGkind"] == env["RNGkind"], name + " reference RNGkind")
        fits, peaks, measured, rmse_deltas = [], [], [], []
        equal_iterations = 0
        require(len(report["runs"]) == len(reference["runs"]) == 7, name + " call count")
        for index, run in enumerate(report["runs"]):
            require(not audit_backend(run["backend"], device, dtype, 5), name + " fit backend")
            require(run["status"] == "ok" and run["code"] == 1 and run["quality_passed"] and run["backend_contract_passed"] and run["error"] is None and run["warnings"] == [], name + " status")
            require(run["backend"]["current_call_torch_used"] and run["backend"]["current_call_gpu_used"] == (device == "cuda"), name + " device use")
            require(all(run["wholly_missing_rows_preserved"]) and run["peak_ram_bytes"] is None, name + " missing rows/RAM")
            for fit in run["backend"]["fits"]:
                require(fit["patterns"] == metadata["distinct_missingness_patterns"] and fit["pseudoinverse_uses"] == 0 and fit["empri_initial"] == fit["empri_final"] == 0 and fit["eigenvalue_check_device"] == device, name + " diagnostic")
                fits.append(fit)
            peak = run["peak_cuda_allocated_bytes"]
            require((isinstance(peak, int) and peak > 0) if device == "cuda" else peak is None, name + " CUDA allocation")
            if peak is not None:
                peaks.append(peak)
            totals["calls"] += 1
            totals["fits"] += 5
            totals[run["phase"] + "_calls"] += 1
            totals[run["phase"] + "_fits"] += 5
            if run["phase"] == "measured":
                measured.append(run["wall_seconds"])
            ref_run = reference["runs"][index]
            require((run["seed"], run["phase"]) == (ref_run["seed"], ref_run["phase"]), name + " paired phase/seed")
            equal_iterations += sum(a == b for a, b in zip(run["iterations"], ref_run["iterations"]))
            rmse_deltas.extend(abs(a-b) for a, b in zip(run["normalized_heldout_rmse"], ref_run["normalized_heldout_rmse"]))
        require(len(fits) == 35 and len(measured) == 5, name + " fit/repeat count")
        ordered = sorted(measured)
        require(report["summary"]["median_seconds"] == ordered[2] and report["summary"]["iqr_seconds"] == [ordered[1], ordered[3]], name + " median/IQR")
        rows.append({"dataset": dataset, "method": method, "report_sha256": sha(raw),
                     "recovered_report_checks_passed": True, "process_exit_status": None,
                     "source_unchanged_during_process": None, "calls": 7, "fits": 35,
                     "median_seconds": ordered[2], "iqr_seconds": [ordered[1], ordered[3]],
                     "all_seven_wall_seconds": [r["wall_seconds"] for r in report["runs"]],
                     "iteration_range": [min(f["iterations"] for f in fits), max(f["iterations"] for f in fits)],
                     "same_seed_iterations_equal_R_serial_count": equal_iterations,
                     "max_abs_paired_R_serial_normalized_rmse_difference": max(rmse_deltas),
                     "mean_measured_normalized_heldout_rmse": audit["mean_normalized_heldout_rmse"],
                     "max_torch_cuda_allocated_bytes": max(peaks) if peaks else None,
                     "peak_ram_bytes": None, "total_process_GPU_peak_bytes": None,
                     "R_serial_median_seconds": reference["summary"]["median_seconds"],
                     "R_snow2_median_seconds": snow["summary"]["median_seconds"]})
    require({(r["dataset"], r["method"]) for r in rows} == EXPECTED and len(rows) == 11, "Configuration count")
    require(totals == {"calls": 77, "fits": 385, "warmup_calls": 22, "warmup_fits": 110, "measured_calls": 55, "measured_fits": 275}, "Total counts")
    ratios = []
    for dataset in DATASETS:
        for precision in ("64", "32"):
            paired = {r["method"]: r for r in rows if r["dataset"] == dataset}
            if "cuda" + precision not in paired:
                continue
            cpu, gpu = paired["cpu" + precision], paired["cuda" + precision]
            ratios.append({"dataset": dataset, "dtype": "float" + precision,
                           "cpu_median_seconds": cpu["median_seconds"], "cuda_median_seconds": gpu["median_seconds"],
                           "CPU_median_divided_by_CUDA_median": cpu["median_seconds"] / gpu["median_seconds"]})
    return {"schema_version": 1, "kind": "limited_recovered_report_audit_not_suite_audit",
            "recovered_report_checks_passed": True, "complete_planned_suite_verified": False,
            "planned_configuration_count_from_root_task": 12, "recovered_configuration_count": 11,
            "missing_configuration": manifest["missing_configuration"], "counts": dict(totals),
            "measurement_revision": manifest["measurement_revision"],
            "per_process_exit_and_source_before_after": "Unavailable; not synthesized from report success.",
            "recorded_quality": {"converged_fits": 385, "observed_values_preserved": True,
                                 "missing_nonfinite_unscored_cells": 0, "warnings": 0, "errors": 0,
                                 "pseudoinverse_uses": 0, "positive_final_empri_fits": 0},
            "configurations": rows, "same_dtype_hybrid_pairs": ratios,
            "source_map_matches_collection_manifest": True, "same_installed_bridge_fingerprints": True,
            "input_provenance_matches_native_preparation_metadata": True,
            "auditor_source_sha256": {p.name: sha(p.read_bytes()) for p in
                                      (Path(__file__), ROOT / "scripts/summarize_benchmarks.py", ROOT / "scripts/summarize_hybrid.py")},
            "limitations": ["This audits only eleven recovered reports. The last configuration and final suite are unavailable after runtime loss.",
                            "No complete-suite status, process exit codes or source-before/after evidence is invented.",
                            "Matching R RNGkind and phase/seed pairs support descriptive comparisons only; full RNG states, draws and completed matrices were not saved.",
                            "Same original host is root-attested; native/reference and hybrid ran in different wall-clock batches.",
                            "Read-only file previews occurred during Year CPU64 timing; background load was not isolated.",
                            "The five ratios pair CPU/CUDA of the same precision and route; they are ratios of medians, not causal GPU attribution or confidence intervals.",
                            "CUDA allocated is active Torch tensor memory, not total VRAM or host RAM; unmeasured fields remain null.",
                            "100k low-pattern block-MCAR tasks do not establish G5 statistical equivalence, full-data scaling, Windows performance or release completion."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.reports_dir)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print("11 recovered reports verified; complete suite NOT verified; 77 calls / 385 fits.")


if __name__ == "__main__":
    main()
