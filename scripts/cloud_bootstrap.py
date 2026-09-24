"""Prepare a Colab/Linux CUDA checkout without running fits or benchmarks.

The default is a read-only plan. --execute requires a clean checkout at the
explicit full Git commit, Python 3.12, and an existing CUDA-enabled Torch 2.10+.
The venv reuses that Torch installation; this script never installs a CUDA wheel.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import venv
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
AMELIA_VERSION = "1.8.3"
AMELIA_SHA256 = "7699455ca3e9dabd60ad0ec69185ece3f24a597ef8da18033ea0b7a32356967f"
AMELIA_URLS = (
    "https://cran.r-project.org/src/contrib/Amelia_1.8.3.tar.gz",
    "https://cran.r-project.org/src/contrib/Archive/Amelia/Amelia_1.8.3.tar.gz",
)
SYSTEM_PACKAGES = (
    "r-base", "r-base-dev", "build-essential", "gfortran", "libcurl4-openssl-dev",
    "libssl-dev", "libxml2-dev", "libpng-dev",
)
THREAD_SETTINGS = {
    "OMP_NUM_THREADS": "4", "OPENBLAS_NUM_THREADS": "4", "MKL_NUM_THREADS": "4",
    "VECLIB_MAXIMUM_THREADS": "4", "NVIDIA_TF32_OVERRIDE": "0",
    "PYTORCH_ENABLE_MPS_FALLBACK": "0",
}

TORCH_PROBE = r'''
import importlib.metadata, json, os, platform, sys
import torch
assert sys.version_info[:2] == (3, 12), "Python 3.12 is required"
assert torch.cuda.is_available(), "CUDA is unavailable; select a GPU runtime first"
report = {
    "python": platform.python_version(), "torch": str(torch.__version__),
    "cuda_runtime": torch.version.cuda, "cuda_available": torch.cuda.is_available(),
    "torch_file_internal": torch.__file__,
    "compiled_cuda_architectures": torch.cuda.get_arch_list(),
    "cpu_threads": torch.get_num_threads(), "gpu_count": torch.cuda.device_count(),
    "gpus": [{"name": torch.cuda.get_device_properties(i).name,
              "memory_bytes": torch.cuda.get_device_properties(i).total_memory,
              "compute_capability": list(torch.cuda.get_device_capability(i))}
             for i in range(torch.cuda.device_count())],
    "matmul_allow_tf32": torch.backends.cuda.matmul.allow_tf32,
    "NVIDIA_TF32_OVERRIDE": os.environ.get("NVIDIA_TF32_OVERRIDE"),
}
print(json.dumps(report))
'''

R_INSTALL = r'''
args <- commandArgs(trailingOnly = TRUE)
lib <- args[[1]]
dir.create(lib, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(lib, .libPaths()))
deps <- c("Rcpp", "RcppArmadillo", "rlang", "foreign", "jsonlite", "reticulate")
missing <- deps[!vapply(deps, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing)) install.packages(missing, repos = "https://cloud.r-project.org",
                                    lib = lib, Ncpus = 2L)
if (!all(vapply(deps, requireNamespace, logical(1), quietly = TRUE)))
  stop("One or more R dependencies failed to install")
install.packages(args[[2]], repos = NULL, type = "source", lib = lib)
stopifnot(as.character(packageVersion("Amelia")) == "1.8.3")
'''

R_REPORT = r'''
.libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))
packages <- installed.packages()
versions <- setNames(as.list(packages[, "Version"]), packages[, "Package"])
result <- list(R = as.character(getRversion()), platform = R.version$platform,
               packages = versions,
               BLAS = basename(extSoftVersion()[["BLAS"]]),
               Amelia = as.character(packageVersion("Amelia")),
               ameliatorch = as.character(packageVersion("ameliatorch")))
stopifnot(result$Amelia == "1.8.3")
cat(jsonlite::toJSON(result, auto_unbox = TRUE, null = "null"))
'''


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def capture(command: list[str], env: dict | None = None) -> str:
    return subprocess.check_output(command, cwd=ROOT, env=env, text=True).strip()


def host_resources() -> dict:
    """Only compute capacity; no hostnames, CPU serials, or full environment dump."""
    report = {"system": platform.system(), "release": platform.release(),
              "architecture": platform.machine(), "logical_cpus": os.cpu_count(),
              "cpu_affinity_count": None, "cpu_model": None, "ram_memtotal_kib": None,
              "cgroup_cpu_max": None}
    if hasattr(os, "sched_getaffinity"):
        try:
            report["cpu_affinity_count"] = len(os.sched_getaffinity(0))
        except OSError:
            pass
    for file, prefix, key in (("/proc/cpuinfo", "model name", "cpu_model"),
                              ("/proc/meminfo", "MemTotal", "ram_memtotal_kib")):
        try:
            for line in Path(file).read_text().splitlines():
                label, separator, value = line.partition(":")
                if separator and label.strip() == prefix:
                    report[key] = int(value.split()[0]) if key.endswith("_kib") else value.strip()
                    break
        except (OSError, ValueError):
            pass
    try:
        report["cgroup_cpu_max"] = Path("/sys/fs/cgroup/cpu.max").read_text().strip()
    except OSError:
        pass
    return report


def redact(value: str) -> str:
    return value.replace(str(ROOT), "<project>").replace(str(Path.home()), "<home>")


def write_report(path: Path, report: dict) -> None:
    report["updated_utc"] = datetime.now(UTC).isoformat()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def run_step(name: str, command: list[str], env: dict, output: Path, report: dict) -> None:
    """Keep every setup failure and its exit status, without shell interpolation."""
    print(f"Setup: {name}", flush=True)
    entry = {"step": name, "command": [redact(x) for x in command], "status": "running"}
    report["steps"].append(entry)
    write_report(output / "bootstrap.json", report)
    started = time.monotonic()
    with (output / f"{name}.log").open("w") as log:
        process = subprocess.Popen(
            command, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            safe_line = redact(line)
            log.write(safe_line)
            print(safe_line, end="", flush=True)
        code = process.wait()
    entry.update(exit_status=code, status="passed" if code == 0 else "failed",
                 elapsed_seconds=time.monotonic() - started)
    write_report(output / "bootstrap.json", report)
    if code:
        raise RuntimeError(f"Setup step {name} failed with exit status {code}; inspect its log")


def fetch_amelia(destination: Path) -> str:
    """Use only the exact verified upstream bytes, with an official archive fallback."""
    if destination.exists():
        if destination.is_symlink() or sha256(destination) != AMELIA_SHA256:
            raise ValueError("Existing Amelia archive fails its SHA-256 pin")
        return "existing_sha256_verified_cache"
    temporary = destination.with_suffix(".part")
    if temporary.exists() or temporary.is_symlink():
        raise FileExistsError("Partial Amelia archive exists; inspect before retrying")
    for url in AMELIA_URLS:
        try:
            with urlopen(url, timeout=90) as response, temporary.open("xb") as stream:
                size = 0
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > 20 * 1024 * 1024:
                        raise ValueError("Amelia archive exceeds the 20 MiB download limit")
                    stream.write(chunk)
        except HTTPError as error:
            if error.code == 404 and not temporary.exists():
                continue
            raise
        if sha256(temporary) != AMELIA_SHA256:
            raise ValueError("Downloaded Amelia source fails its SHA-256 pin")
        temporary.replace(destination)
        return url
    raise FileNotFoundError("Pinned Amelia source is unavailable at both official CRAN URLs")


def ensure_venv(env: dict, output: Path, report: dict) -> Path:
    target = ROOT / ".venv"
    if target.exists():
        if "include-system-site-packages = true" not in (target / "pyvenv.cfg").read_text():
            raise ValueError("Existing .venv does not share runtime packages; use a fresh checkout")
        return target
    try:
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(target)
        report["venv_creator"] = "stdlib_venv"
    except subprocess.CalledProcessError as error:
        # Some Colab/Debian Python images omit ensurepip. Retry only that case;
        # use official uv in a project cache, not a global interpreter install.
        if "ensurepip" not in error.cmd:
            raise
        report["venv_ensurepip_failure"] = redact(str(error))
        tool_dir = ROOT / ".cache/cloud-bootstrap/uv-tool"
        run_step("uv_fallback_install", [sys.executable, "-m", "pip", "--isolated",
                 "install", "--index-url", "https://pypi.org/simple", "--target", str(tool_dir),
                 "uv>=0.8,<1"], env, output, report)
        uv_env = {**env, "PYTHONPATH": str(tool_dir)}
        report["venv_creator"] = capture([sys.executable, "-m", "uv", "--version"], uv_env)
        run_step("uv_fallback_venv", [sys.executable, "-m", "uv", "--no-config", "venv",
                 "--python", sys.executable, "--system-site-packages", "--seed",
                 "--allow-existing", str(target)], uv_env, output, report)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-commit", required=True, help="Exact 40-character Git SHA")
    parser.add_argument("--execute", action="store_true", help="Install dependencies; no fitting")
    parser.add_argument("--install-system-packages", action="store_true",
                        help="Use apt-get on the cloud host; requires root")
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "results/local/cloud/bootstrap")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-fA-F]{40}", args.expected_commit):
        parser.error("Use an exact full Git commit SHA, not a branch name")
    actual_commit = capture(["git", "rev-parse", "HEAD"])
    if actual_commit != args.expected_commit.lower():
        parser.error(f"Checkout is {actual_commit}, not the requested commit")
    if capture(["git", "status", "--porcelain", "--untracked-files=no"]):
        parser.error("Tracked files differ from the pinned commit; use a clean cloud checkout")
    plan = {
        "repo_commit": actual_commit, "python": "3.12", "torch_policy":
        "Reuse the runtime's CUDA-enabled Torch >=2.10,<3 via --system-site-packages",
        "Amelia": AMELIA_VERSION, "Amelia_sha256": AMELIA_SHA256,
        "Amelia_urls": AMELIA_URLS, "system_packages": SYSTEM_PACKAGES,
        "install_system_packages": args.install_system_packages,
        "runs_imputation_or_benchmarks": False,
        "steps": ["check_cuda", "optional_apt", "create_venv", "install_python_package",
                  "download_pinned_Amelia", "install_R_dependencies_and_Amelia",
                  "install_ameliatorch", "record_environment"],
    }
    if not args.execute:
        print(json.dumps(plan, indent=2))
        return 0
    if platform.system() != "Linux" or sys.version_info[:2] != (3, 12):
        parser.error("Execute only inside the Linux cloud runtime using Python 3.12")
    if args.output_dir.exists():
        parser.error("Output directory already exists; choose a fresh directory to retain records")
    args.output_dir.mkdir(parents=True)
    output = args.output_dir.resolve()
    report = {"schema_version": 1, "scope": "Cloud dependency setup only; no fitting",
              "created_utc": datetime.now(UTC).isoformat(), "status": "running", "plan": plan,
              "steps": [], "host": host_resources(),
              "source_sha256": {name: sha256(ROOT / name) for name in
                  capture(["git", "ls-files"]).splitlines() if (ROOT / name).is_file()},
              "bootstrap_script_sha256": sha256(Path(__file__))}
    env = os.environ.copy()
    env.update(THREAD_SETTINGS)
    env["R_LIBS_USER"] = str(ROOT / ".R-library")
    env["RETICULATE_PYTHON"] = str(ROOT / ".venv/bin/python")  # Do not resolve the symlink.
    write_report(output / "bootstrap.json", report)
    try:
        base = json.loads(capture([sys.executable, "-c", TORCH_PROBE], env))
        version = tuple(map(int, re.match(r"(\d+)\.(\d+)", base["torch"]).groups()))
        if not (2, 10) <= version < (3, 0):
            raise ValueError("Runtime Torch must be >=2.10,<3; no wheel will be silently replaced")
        base_torch_file = base.pop("torch_file_internal")
        report["runtime_before_setup"] = base
        if args.install_system_packages:
            if os.geteuid() != 0:
                raise PermissionError("System package installation requires the cloud root user")
            apt_env = {**env, "DEBIAN_FRONTEND": "noninteractive"}
            run_step("apt_update", ["apt-get", "update", "-qq"], apt_env, output, report)
            run_step("apt_install", ["apt-get", "install", "-y", "--no-install-recommends",
                                     *SYSTEM_PACKAGES], apt_env, output, report)
        missing = [tool for tool in ("Rscript", "R", "make", "gcc", "g++", "gfortran")
                   if not shutil.which(tool)]
        if missing:
            raise RuntimeError("Missing system tools: " + ", ".join(missing)
                               + "; rerun with --install-system-packages and a new output-dir")
        venv_dir = ensure_venv(env, output, report)
        python = str(venv_dir / "bin/python")
        run_step("python_install", [python, "-m", "pip", "install", "-e", ".[dev,reference]"],
                 env, output, report)
        after = json.loads(capture([python, "-c", TORCH_PROBE], env))
        same_torch = after.pop("torch_file_internal") == base_torch_file
        if not same_torch or after["torch"] != base["torch"]:
            raise ValueError("The venv does not use the runtime's original Torch installation")
        report["runtime_after_setup"] = after
        report["reused_runtime_torch"] = same_torch
        cache = ROOT / ".cache/cloud-bootstrap"
        cache.mkdir(parents=True, exist_ok=True)
        archive = cache / "Amelia_1.8.3.tar.gz"
        report["Amelia_download_source"] = fetch_amelia(archive)
        install_r = cache / "install_reference.R"
        install_r.write_text(R_INSTALL)
        run_step("r_reference_install", ["Rscript", str(install_r), env["R_LIBS_USER"],
                                         str(archive)], env, output, report)
        run_step("r_setup_check", ["Rscript", "scripts/setup_r.R"], env, output, report)
        run_step("r_bridge_install", ["R", "CMD", "INSTALL", "--clean",
                                      f"--library={env['R_LIBS_USER']}", "r-package"],
                 env, output, report)
        report["r_environment"] = json.loads(capture(["Rscript", "-e", R_REPORT], env))
        packages = capture([python, "-m", "pip", "list", "--format=json"], env)
        (output / "python-packages.json").write_text(redact(packages) + "\n")
        report["nvidia_smi"] = capture([
            "nvidia-smi", "--query-gpu=name,driver_version,memory.total,compute_cap",
            "--format=csv,noheader"], env).splitlines()
        report["environment_for_subsequent_commands"] = {
            **THREAD_SETTINGS, "R_LIBS_USER": "<project>/.R-library",
            "RETICULATE_PYTHON": "<project>/.venv/bin/python",
        }
        report["status"] = "passed"
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        report.update(status="failed", error_type=type(error).__name__, error=redact(str(error)))
        print(f"Cloud setup failed: {redact(str(error))}", file=sys.stderr)
    finally:
        write_report(output / "bootstrap.json", report)
    print(f"Setup {report['status']}: {redact(str(output / 'bootstrap.json'))}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
