"""Download pinned official UCI archives with bounded storage and atomic completion.

Only archives are stored; no archive member is extracted to a filesystem path.
An interrupted transfer remains a .part file. HTTP Range resume is attempted;
if the server ignores Range, an explicit --restart is required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CHUNK = 1024 * 1024
MIB = 1024**2
GIB = 1024**3


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: dict) -> None:
    if path.is_symlink():
        raise ValueError(f"Refusing symbolic-link output: {path.name}")
    tmp = path.with_name(path.name + ".tmp")
    if tmp.is_symlink():
        raise ValueError(f"Refusing symbolic-link temporary file: {tmp.name}")
    tmp.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def verify_archive(path: Path, entry: dict, allow_unpinned: bool) -> dict:
    actual_size = path.stat().st_size
    expected_size = entry.get("download_bytes")
    if actual_size > entry["download_bytes_max"]:
        raise ValueError("Archive exceeds manifest download limit")
    if expected_size is not None and actual_size != expected_size:
        raise ValueError(f"Archive size mismatch: {actual_size} != {expected_size}")
    actual_hash = sha256_file(path)
    expected_hash = entry.get("sha256")
    if expected_hash and actual_hash != expected_hash:
        raise ValueError("SHA-256 mismatch; keep the file for inspection, do not use it")
    if not expected_hash and not allow_unpinned:
        raise ValueError("Unpinned archive requires explicit --accept-unpinned")
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        # Bound decompression before CRC testing, including hostile replacement archives.
        if sum(item.file_size for item in members) > 2 * GIB:
            raise ValueError("ZIP uncompressed members exceed the 2 GiB safety limit")
        if entry["data_member"] not in archive.namelist():
            raise ValueError("Expected data member missing from ZIP")
        bad = archive.testzip()
        if bad is not None:
            raise ValueError(f"ZIP CRC check failed: {bad}")
        member_metadata = [
            {"name": item.filename, "bytes": item.file_size, "crc32": f"{item.CRC:08x}"}
            for item in members
        ]
    return {
        "source_url": entry["source_url"],
        "download_url": entry["download_url"],
        "license": entry["license"],
        "download_bytes": actual_size,
        "sha256": actual_hash,
        "sha256_matches_pin": bool(expected_hash),
        "zip_crc_verified": True,
        "members": member_metadata,
    }


def download(entry: dict, destination: Path, args: argparse.Namespace) -> dict:
    filename = entry["filename"]
    if Path(filename).name != filename:
        raise ValueError("Manifest filename must be a basename")
    target = destination / filename
    partial = target.with_name(filename + ".part")
    metadata_path = target.with_name(filename + ".part.json")
    receipt_path = target.with_name(filename + ".download.json")
    for path in (target, partial, metadata_path, receipt_path):
        if path.is_symlink():
            raise ValueError(f"Refusing symbolic-link output: {path.name}")
    if target.exists():
        receipt = verify_archive(target, entry, args.accept_unpinned)
        write_json(receipt_path, receipt)
        print(f"Verified existing {filename}: {receipt['download_bytes']} bytes", flush=True)
        return receipt
    if args.verify_only:
        raise FileNotFoundError(f"Missing archive: {filename}")
    if not entry.get("sha256") and not args.accept_unpinned:
        raise ValueError("Manifest hash is not pinned; use --accept-unpinned only for source audit")
    if args.restart:
        partial.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {"User-Agent": "amelia-torch-dataset-audit/0.1", "Accept-Encoding": "identity"}
    if offset:
        if not metadata_path.exists():
            raise ValueError("Orphan partial file; inspect it and use --restart if appropriate")
        previous = json.loads(metadata_path.read_text(encoding="utf-8"))
        if previous["download_url"] != entry["download_url"]:
            raise ValueError("Partial-file URL differs from manifest; refusing to append")
        headers["Range"] = f"bytes={offset}-"
        validator = previous.get("etag") or previous.get("last_modified")
        if validator:
            headers["If-Range"] = validator
    upper_bound = entry.get("download_bytes") or entry["download_bytes_max"]
    if offset > upper_bound:
        raise ValueError("Partial file exceeds expected size; inspect before restarting")
    if shutil.disk_usage(destination).free < upper_bound - offset + args.reserve_gib * GIB:
        raise OSError("Insufficient free space after reserving the configured disk headroom")
    request = Request(entry["download_url"], headers=headers)
    with urlopen(request, timeout=args.timeout) as response:
        if not response.url.startswith("https://archive.ics.uci.edu/"):
            raise ValueError("Unexpected download redirect outside the official UCI host")
        if offset:
            content_range = response.headers.get("Content-Range", "")
            if response.status != 206 or not content_range.startswith(f"bytes {offset}-"):
                raise ValueError("Server cannot resume this partial; rerun with --restart")
        elif response.status != 200:
            raise ValueError(f"Unexpected HTTP status: {response.status}")
        length = response.headers.get("Content-Length")
        if length and offset + int(length) > upper_bound:
            raise ValueError("HTTP Content-Length exceeds manifest limit")
        write_json(
            metadata_path,
            {
                "download_url": entry["download_url"],
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
            },
        )
        total = offset
        next_report = total + 25 * MIB
        with partial.open("ab" if offset else "wb") as stream:
            while True:
                chunk = response.read(min(CHUNK, upper_bound - total + 1))
                if not chunk:
                    break
                if total + len(chunk) > upper_bound:
                    raise ValueError("Transfer exceeds manifest byte budget")
                if shutil.disk_usage(destination).free < len(chunk) + args.reserve_gib * GIB:
                    raise OSError("Free space fell below configured reserve; partial retained")
                stream.write(chunk)
                total += len(chunk)
                if total >= next_report:
                    print(f"{filename}: {total / MIB:.1f} MiB", flush=True)
                    next_report += 25 * MIB
            stream.flush()
            os.fsync(stream.fileno())
    receipt = verify_archive(partial, entry, args.accept_unpinned)
    os.replace(partial, target)
    metadata_path.unlink(missing_ok=True)
    write_json(receipt_path, receipt)
    print(f"Downloaded and verified {filename}: {receipt['download_bytes']} bytes", flush=True)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets", nargs="+", default=[], help="Dataset IDs, or all")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/manifest.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data/raw")
    parser.add_argument(
        "--max-download-mib",
        type=float,
        default=300,
        help="Upper bound for the selected archive set, not just new bytes",
    )
    parser.add_argument(
        "--reserve-gib",
        type=float,
        default=5,
        help="Free disk space that must remain after download",
    )
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Discard incomplete .part files; never overwrites completed archives",
    )
    parser.add_argument(
        "--accept-unpinned",
        action="store_true",
        help="Source audit only: allow a missing manifest hash, record actual SHA-256",
    )
    args = parser.parse_args()
    if args.max_download_mib <= 0 or args.reserve_gib < 0 or args.timeout <= 0:
        parser.error("Download budget and timeout must be positive; reserve cannot be negative")
    entries = json.loads(args.manifest.read_text(encoding="utf-8"))["datasets"]
    selected = list(entries) if args.datasets == ["all"] else list(dict.fromkeys(args.datasets))
    if not selected:
        for key, entry in entries.items():
            print(f"{key}: {entry['rows']:,} rows; {entry['download_bytes_max'] / MIB:.1f} MiB cap")
        print("Use --datasets all --dry-run to preview or --datasets all to download.")
        return 0
    if any(key not in entries for key in selected):
        parser.error(f"Dataset IDs must be selected from: {', '.join(entries)}; or all alone")
    budget = sum(
        entries[key].get("download_bytes") or entries[key]["download_bytes_max"] for key in selected
    )
    if budget > args.max_download_mib * MIB:
        parser.error(f"Selected archives need up to {budget / MIB:.1f} MiB; budget is too small")
    print(f"Archive budget: {budget / MIB:.1f} MiB; free-space reserve: {args.reserve_gib:g} GiB")
    if args.dry_run:
        for key in selected:
            print(f"{key}: {entries[key]['download_url']}")
        return 0
    args.output.mkdir(parents=True, exist_ok=True)
    for key in selected:
        download(entries[key], args.output, args)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"Dataset download failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
