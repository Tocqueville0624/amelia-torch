"""Print a portable report checkpoint that a saved notebook can retain.

Run between benchmark phases, outside all timed calls. Redirecting this output
inside results/local/cloud would recursively include older checkpoint payloads;
save the envelope outside that directory or in the notebook output instead.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def collect(root: Path, label: str, revision: str, phase: str | None = None) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", label):
        raise ValueError("Use a simple checkpoint label")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("An exact Git revision is required")
    root = root.resolve()
    report_root = root / "results/local/cloud"
    if phase is not None:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", phase):
            raise ValueError("Phase must be a single report-directory name")
        report_root = report_root / phase
        if not report_root.is_dir() or report_root.is_symlink():
            raise ValueError("Phase report directory is missing or is a symlink")
    candidates = [*report_root.rglob("*"),
                  *(root / "data/prepared").glob("*.json"), root / "data/manifest.json"]
    records = []
    for path in sorted(candidates):
        if not path.is_file() or path.suffix not in {".json", ".log", ".txt"}:
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("Report paths must remain within the checkout")
        raw = path.read_bytes()
        portable = raw.decode("utf-8").replace(str(root), "<project>").replace(
            str(Path.home()), "<home>")
        records.append({"path": path.relative_to(root).as_posix(),
                        "original_sha256": hashlib.sha256(raw).hexdigest(),
                        "portable_sha256": hashlib.sha256(portable.encode()).hexdigest(),
                        "text": portable})
    payload = json.dumps({
        "schema_version": 1, "revision": revision, "label": label,
        "report_directory": report_root.relative_to(root).as_posix(),
        "created_utc": datetime.now(UTC).isoformat(),
        "scope": "JSON/log/text reports and prepared metadata only; project/home paths replaced; excludes credentials, RDS, installed libraries and raw data",
        "files": records,
    }, ensure_ascii=False).encode()
    if len(payload) > 64 * 1024 * 1024:
        raise ValueError("Reports exceed the 64 MiB portable recovery limit")
    packed = gzip.compress(payload, mtime=0)
    return {"amelia_checkpoint": "gzip-base64-v1", "label": label,
            "bytes": len(packed), "sha256": hashlib.sha256(packed).hexdigest(),
            "data": base64.b64encode(packed).decode()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True)
    parser.add_argument("--phase", help="Back up one subdirectory of results/local/cloud to keep phases bounded")
    args = parser.parse_args()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    print(json.dumps(collect(ROOT, args.label, revision, args.phase)), flush=True)


if __name__ == "__main__":
    main()
