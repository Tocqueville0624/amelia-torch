"""Create an explicit, shared benchmark input from pinned UCI archives.

Streams ZIP/gzip data without extracting full CSVs. Saves source row IDs, original
observations, natural missingness, artificial missingness, and masked input. This
prepares input only; it does not run imputation or claim inferential validity.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import os
import shutil
from contextlib import contextmanager
from pathlib import Path

import numpy as np
from download_datasets import GIB, ROOT, sha256_file, verify_archive, write_json


@contextmanager
def source_rows(archive_path: Path, entry: dict):
    import zipfile

    with zipfile.ZipFile(archive_path) as archive, archive.open(entry["data_member"]) as member:
        binary = gzip.GzipFile(fileobj=member) if entry["inner_compression"] == "gzip" else member
        with io.TextIOWrapper(binary, encoding="utf-8", newline="") as text:
            rows = csv.reader(text, delimiter=entry["delimiter"])
            if entry["has_header"]:
                next(rows)
            yield rows


def numeric_columns(entry: dict) -> tuple[list[int], list[str]]:
    indices = entry["numeric_indices_zero_based"]
    if isinstance(indices, str):
        start, stop = map(int, indices.split(":"))
        return list(range(start, stop)), (
            [f"timbre_average_{i:02d}" for i in range(1, 13)]
            + [f"timbre_covariance_{i:02d}" for i in range(1, 79)]
        )
    return indices, entry["numeric_columns"]


def row_state(row: list[str], entry: dict, columns: list[int]) -> tuple[list[str], bool]:
    if len(row) != entry["raw_columns"]:
        raise ValueError(f"Source row has {len(row)} fields, expected {entry['raw_columns']}")
    values = [row[index].strip() for index in columns]
    incomplete = any(value in entry["missing_tokens"] for value in values)
    return values, incomplete


def load_sample(
    archive_path: Path, entry: dict, n: int, seed: int, sampling: str, natural_policy: str
) -> tuple[np.ndarray, np.ndarray, dict]:
    columns, _ = numeric_columns(entry)
    eligible_count = 0
    natural_incomplete_count = 0
    source_count = 0
    # Count eligible rows before uniform sampling; complete-case restriction is explicit.
    with source_rows(archive_path, entry) as rows:
        for row in rows:
            _, incomplete = row_state(row, entry, columns)
            source_count += 1
            natural_incomplete_count += incomplete
            eligible_count += natural_policy == "preserve" or not incomplete
    if source_count != entry["rows"]:
        raise ValueError(f"Source has {source_count} data rows, expected {entry['rows']}")
    if n > eligible_count:
        raise ValueError(f"Requested {n} rows, but only {eligible_count} are eligible")
    if sampling == "random":
        selected = np.sort(np.random.default_rng(seed).choice(eligible_count, n, replace=False))
    else:
        selected = np.arange(n)
    data = np.empty((n, len(columns)), dtype=np.float64)
    row_ids = np.empty(n, dtype=np.int64)
    eligible_index = 0
    output_index = 0
    with source_rows(archive_path, entry) as rows:
        for source_index, row in enumerate(rows):
            values, incomplete = row_state(row, entry, columns)
            if natural_policy == "complete-cases" and incomplete:
                continue
            if eligible_index == selected[output_index]:
                data[output_index] = [
                    np.nan if value in entry["missing_tokens"] else float(value) for value in values
                ]
                row_ids[output_index] = source_index
                output_index += 1
                if output_index == n:
                    break
            eligible_index += 1
    if np.isinf(data).any():
        raise ValueError("Source contains infinite numeric values")
    return (
        data,
        row_ids,
        {
            "source_rows_verified": source_count,
            "natural_incomplete_source_rows": natural_incomplete_count,
            "eligible_rows": eligible_count,
            "excluded_source_rows": source_count - eligible_count,
        },
    )


def artificial_mask(
    data: np.ndarray, mechanism: str, rate: float, seed: int, patterns: int
) -> tuple[np.ndarray, dict]:
    rng = np.random.default_rng(seed)
    n, p = data.shape
    observed = ~np.isnan(data)
    details: dict = {}
    if mechanism == "mcar":
        mask = rng.random((n, p)) < rate
    elif mechanism == "block_mcar":
        missing_columns = min(p - 1, max(1, round(p * rate)))
        pattern_bank = np.zeros((patterns, p), dtype=bool)
        for index in range(patterns):
            start = index * p // patterns
            pattern_bank[index, (start + np.arange(missing_columns)) % p] = True
        mask = pattern_bank[rng.integers(0, patterns, n)]
        details = {
            "pattern_bank": pattern_bank.astype(int).tolist(),
            "missing_columns_per_pattern": missing_columns,
            "note": "Pattern sampled independently of values; not independent cell masking.",
        }
    else:
        if np.isnan(data[:, 0]).any():
            raise ValueError("MAR anchor column must be fully observed; use complete-cases")
        anchor_std = data[:, 0].std()
        if anchor_std == 0:
            raise ValueError("MAR anchor column is constant")
        anchor = (data[:, 0] - data[:, 0].mean()) / anchor_std
        counts = observed[:, 1:].sum(axis=1)
        target = rate * observed.sum() / counts.sum()
        if target >= 1:
            raise ValueError("MAR rate too high while keeping anchor observed")
        low, high = -40.0, 40.0
        for _ in range(80):
            midpoint = (low + high) / 2
            probabilities = 1 / (1 + np.exp(-np.clip(midpoint + anchor, -40, 40)))
            if np.average(probabilities, weights=counts) < target:
                low = midpoint
            else:
                high = midpoint
        mask = np.zeros((n, p), dtype=bool)
        mask[:, 1:] = rng.random((n, p - 1)) < probabilities[:, None]
        details = {
            "always_observed_anchor_column_zero_based": 0,
            "logistic_slope": 1.0,
            "logistic_intercept": midpoint,
        }
    # Natural missing cells are never included in the artificial truth/scoring mask.
    mask &= observed
    return mask, details


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--rows", type=int, default=10000)
    parser.add_argument("--sampling", choices=["random", "prefix"], default="random")
    parser.add_argument(
        "--natural-missing", choices=["complete-cases", "preserve"], default="complete-cases"
    )
    parser.add_argument("--mechanism", choices=["block_mcar", "mcar", "mar"], default="block_mcar")
    parser.add_argument("--missing-rate", type=float, default=0.1)
    parser.add_argument("--patterns", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260923)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/manifest.json")
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/raw")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--max-working-mib",
        type=float,
        default=2048,
        help="Conservative preparation array budget; not an imputation budget",
    )
    parser.add_argument("--reserve-gib", type=float, default=5)
    args = parser.parse_args()
    if args.rows < 1 or not 0 < args.missing_rate < 1 or args.patterns < 1:
        parser.error("Rows/patterns must be positive and missing rate strictly between 0 and 1")
    if args.max_working_mib <= 0 or args.reserve_gib < 0:
        parser.error("Working budget must be positive; disk reserve cannot be negative")
    entries = json.loads(args.manifest.read_text(encoding="utf-8"))["datasets"]
    if args.dataset not in entries:
        parser.error(f"Unknown dataset; choose: {', '.join(entries)}")
    entry = entries[args.dataset]
    columns, names = numeric_columns(entry)
    # Truth, input, temporary RNG draws, masks, packed patterns, output compression buffers.
    estimated_bytes = args.rows * len(columns) * 64 + args.rows * 32
    if estimated_bytes > args.max_working_mib * 1024**2:
        parser.error(f"Preparation estimate {estimated_bytes / 1024**2:.1f} MiB exceeds budget")
    if args.output.suffix != ".npz":
        parser.error("Output must end in .npz")
    sidecar = args.output.with_suffix(".json")
    temporary = args.output.with_name(args.output.name + ".tmp")
    if any(path.exists() or path.is_symlink() for path in (args.output, sidecar, temporary)):
        parser.error("Output or temporary file already exists; select a new output name")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(args.output.parent).free < estimated_bytes + args.reserve_gib * GIB:
        parser.error("Insufficient free disk space after the configured reserve")
    source = args.raw_dir / entry["filename"]
    verify_archive(source, entry, allow_unpinned=False)
    truth, row_ids, counts = load_sample(
        source, entry, args.rows, args.seed, args.sampling, args.natural_missing
    )
    natural = np.isnan(truth)
    mask, mechanism_details = artificial_mask(
        truth, args.mechanism, args.missing_rate, args.seed + 1, args.patterns
    )
    masked = truth.copy()
    masked[mask] = np.nan
    pattern_count = len(np.unique(np.packbits(np.isnan(masked), axis=1), axis=0))
    metadata = {
        "dataset": args.dataset,
        "citation": entry["citation"],
        "source_url": entry["source_url"],
        "license": entry["license"],
        "license_url": entry["license_url"],
        "source_archive_sha256": entry["sha256"],
        "transformations": "Selected numeric columns and sampled source rows; added artificial mask.",
        "shape": list(truth.shape),
        "columns": names,
        "source_row_index_base": 0,
        "sampling": args.sampling,
        "row_seed": args.seed,
        "mask_seed": args.seed + 1,
        "natural_missing_policy": args.natural_missing,
        **counts,
        "mechanism": args.mechanism,
        "mechanism_details": mechanism_details,
        "requested_missing_rate": args.missing_rate,
        "artificial_missing_cells": int(mask.sum()),
        "artificial_rate_among_observed": float(mask.sum() / (~natural).sum()),
        "natural_missing_cells_in_sample": int(natural.sum()),
        "all_missing_rows_after_mask": int(np.isnan(masked).all(axis=1).sum()),
        "distinct_missingness_patterns": pattern_count,
        "preparation_estimated_working_bytes": estimated_bytes,
        "benchmark_executed": False,
        "quality_warning": "Real-data masks support held-out observed-cell error only; coverage needs simulations with known estimands.",
    }
    with temporary.open("xb") as stream:
        np.savez_compressed(
            stream,
            truth=truth,
            data=masked,
            artificial_missing_mask=mask,
            natural_missing_mask=natural,
            source_row_ids=row_ids,
            column_names=np.asarray(names),
        )
    os.replace(temporary, args.output)
    metadata["npz_sha256"] = sha256_file(args.output)
    write_json(sidecar, metadata)
    print(
        json.dumps(
            {
                "dataset": args.dataset,
                "shape": list(truth.shape),
                "K": pattern_count,
                "npz_sha256": metadata["npz_sha256"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
