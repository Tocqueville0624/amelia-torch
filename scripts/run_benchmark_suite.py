"""Run the same public-data task through CPU, GPU and pinned R Amelia.

Runs implementations sequentially in seeded randomized order for each dataset.
The suite is a platform-local measurement, not a cross-machine speedup claim.
"""

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/local/benchmarks/main")
    parser.add_argument("--rows", type=int, default=100000)
    parser.add_argument("--m", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--gpu", choices=["mps", "cuda", "none"], default="none")
    parser.add_argument("--max-iterations", type=int, default=300)
    parser.add_argument("--threads", type=int, default=4,
                        help="BLAS/Torch threads for serial methods and GPU host work")
    parser.add_argument("--workers", type=int, choices=[2, 4], default=4,
                        help="R snow processes; each worker uses one BLAS thread")
    args = parser.parse_args()
    if args.threads < 1:
        parser.error("threads must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_dir = args.output_dir / "inputs"
    csv_dir.mkdir(exist_ok=True)
    sources = sorted((ROOT / "src/amelia_torch").glob("*.py")) + [
        ROOT / "scripts/benchmark.py",
        ROOT / "scripts/benchmark_reference.R",
    ]
    source_hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sources
    }
    suite = {
        "created_utc": datetime.now(UTC).isoformat(),
        "source_sha256": source_hashes,
        "description": "100k uniform public-data samples; block MCAR ~30%; methods randomized by dataset; failures retained",
        "seeds": list(range(20260923, 20260923 + args.repeats)),
        "cpu_budget": {"serial_threads": args.threads, "snow_workers": args.workers,
                       "snow_worker_blas_threads": 1},
        "execution": [],
    }
    generator = random.Random(20260923)
    for dataset in ("covertype", "household_power", "year_prediction_msd"):
        source = (
            ROOT / "data/prepared" / f"{dataset}-n{args.rows}-block_mcar-rate30-seed20260923.npz"
        )
        input_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        with np.load(source, allow_pickle=False) as archive:
            header = ",".join(archive["column_names"])
            paths = {}
            for field, name in (
                ("data", "input"),
                ("truth", "truth"),
                ("artificial_missing_mask", "mask"),
            ):
                path = csv_dir / f"{dataset}-{name}.csv"
                np.savetxt(
                    path,
                    archive[field],
                    delimiter=",",
                    header=header,
                    comments="",
                    fmt="%d" if name == "mask" else "%.17g",
                )
                paths[name] = str(path)
        snow_method = f"r_snow{args.workers}"
        methods = ["cpu64", "cpu32", "r_serial", snow_method]
        if args.gpu != "none":
            methods.append(f"{args.gpu}32")
        if args.gpu == "cuda":
            methods.append("cuda64")
        generator.shuffle(methods)
        for method in methods:
            output = args.output_dir / f"{dataset}-{method}.json"
            environment = os.environ.copy()
            environment["PYTORCH_ENABLE_MPS_FALLBACK"] = "0"
            if method.startswith("r_"):
                config = {
                    "input_csv": paths["input"],
                    "truth_csv": paths["truth"],
                    "mask_csv": paths["mask"],
                    "output_json": str(output),
                    "m": args.m,
                    "seeds": suite["seeds"],
                    "warmups": args.warmups,
                    "warmup_seeds": list(range(20360923, 20360923 + args.warmups)),
                    "parallel": "snow" if method == snow_method else "no",
                    "ncpus": args.workers if method == snow_method else 1,
                    "autopri": 0.05,
                    "tolerance": 1e-4,
                    "emburn": [0, args.max_iterations],
                }
                config_path = args.output_dir / f"{dataset}-{method}.config.json"
                config_path.write_text(json.dumps(config, indent=2))
                command = ["Rscript", "scripts/benchmark_reference.R", str(config_path)]
                # A process/thread budget: parallel workers each get one BLAS thread.
                threads = "1" if method == snow_method else str(args.threads)
                environment.update(
                    {
                        key: threads
                        for key in (
                            "OMP_NUM_THREADS",
                            "OPENBLAS_NUM_THREADS",
                            "MKL_NUM_THREADS",
                            "VECLIB_MAXIMUM_THREADS",
                        )
                    }
                )
            else:
                device = "cpu" if method.startswith("cpu") else args.gpu
                dtype = "float64" if method.endswith("64") else "float32"
                command = [
                    sys.executable,
                    "scripts/benchmark.py",
                    str(source),
                    "--output",
                    str(output),
                    "--device",
                    device,
                    "--dtype",
                    dtype,
                    "--m",
                    str(args.m),
                    "--repeats",
                    str(args.repeats),
                    "--warmups",
                    str(args.warmups),
                    "--threads",
                    str(args.threads),
                    "--max-iterations",
                    str(args.max_iterations),
                ]
                environment.update(
                    {
                        key: str(args.threads)
                        for key in (
                            "OMP_NUM_THREADS",
                            "OPENBLAS_NUM_THREADS",
                            "MKL_NUM_THREADS",
                            "VECLIB_MAXIMUM_THREADS",
                        )
                    }
                )
            print(f"Starting {dataset} / {method}", flush=True)
            result = subprocess.run(command, cwd=ROOT, env=environment, check=False)
            suite["execution"].append(
                {
                    "dataset": dataset,
                    "method": method,
                    "input_sha256": input_hash,
                    "result": output.name,
                    "exit_status": result.returncode,
                }
            )
            (args.output_dir / "suite.json").write_text(json.dumps(suite, indent=2))
    suite["completed_utc"] = datetime.now(UTC).isoformat()
    (args.output_dir / "suite.json").write_text(json.dumps(suite, indent=2))
    return int(any(item["exit_status"] != 0 for item in suite["execution"]))


if __name__ == "__main__":
    raise SystemExit(main())
