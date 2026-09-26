"""Recover reports from a visible Colab JSON checkpoint or saved notebook.

Only report text is recovered, never executable environment state. Every packed
payload and portable file is checked before a fresh output directory is created.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import zlib
from pathlib import Path, PurePosixPath

MAX_BYTES = 64 * 1024 * 1024


def envelopes(document: dict) -> list[dict]:
    if document.get("amelia_checkpoint") == "gzip-base64-v1":
        return [document]
    found = []
    for cell in document.get("cells", []):
        for output in cell.get("outputs", []):
            text = output.get("text", [])
            text = "".join(text) if isinstance(text, list) else text
            for line in text.splitlines():
                if line.startswith('{"amelia_checkpoint"'):
                    found.append(json.loads(line))
    return found


def checked_bundle(envelope: dict) -> dict:
    if envelope.get("amelia_checkpoint") != "gzip-base64-v1":
        raise ValueError("Unsupported checkpoint format")
    packed = base64.b64decode(envelope["data"], validate=True)
    if (len(packed) > MAX_BYTES or len(packed) != envelope["bytes"]
            or hashlib.sha256(packed).hexdigest() != envelope["sha256"]):
        raise ValueError("Compressed checkpoint size or SHA-256 mismatch")
    inflater = zlib.decompressobj(16 + zlib.MAX_WBITS)
    payload = inflater.decompress(packed, MAX_BYTES + 1)
    if len(payload) > MAX_BYTES or not inflater.eof or inflater.unused_data:
        raise ValueError("Checkpoint exceeds size limit or has an invalid gzip stream")
    bundle = json.loads(payload)
    if bundle.get("schema_version") != 1 or bundle.get("label") != envelope.get("label"):
        raise ValueError("Checkpoint schema or label mismatch")
    if not re.fullmatch(r"[0-9a-f]{40}", bundle.get("revision", "")):
        raise ValueError("Checkpoint must record an exact Git revision")
    seen = set()
    for item in bundle["files"]:
        path = PurePosixPath(item["path"])
        if (path.is_absolute() or ".." in path.parts or "\\" in item["path"]
                or str(path) != item["path"] or path.suffix not in {".json", ".log", ".txt"}):
            raise ValueError("Unsafe checkpoint path")
        allowed = (path.parts[:3] == ("results", "local", "cloud")
                   or path.parts[:2] == ("data", "prepared")
                   or str(path) == "data/manifest.json")
        if not allowed or str(path) in seen:
            raise ValueError("Unexpected or duplicate checkpoint path")
        seen.add(str(path))
        if hashlib.sha256(item["text"].encode()).hexdigest() != item["portable_sha256"]:
            raise ValueError("Portable report SHA-256 mismatch")
    return bundle


def recover(envelope: dict, destination: Path) -> dict:
    bundle = checked_bundle(envelope)
    # exist_ok=False prevents overwriting an earlier attempt or following an
    # existing output-directory symlink. Files have already been fully checked.
    destination.mkdir(parents=True, exist_ok=False)
    for item in bundle["files"]:
        path = destination / item["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="") as stream:
            stream.write(item["text"])
    manifest = {**bundle, "files": [{k: v for k, v in item.items() if k != "text"}
                                   for item in bundle["files"]]}
    (destination / "checkpoint-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"label": bundle["label"], "revision": bundle["revision"],
            "files": len(bundle["files"]), "packed_sha256": envelope["sha256"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Saved checkpoint JSON or .ipynb")
    parser.add_argument("--label", help="Required when a notebook contains multiple checkpoints")
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if args.source.stat().st_size > MAX_BYTES:
        parser.error("Input file exceeds the 64 MiB recovery limit")
    candidates = envelopes(json.loads(args.source.read_text(encoding="utf-8")))
    if args.label:
        candidates = [item for item in candidates if item.get("label") == args.label]
    if len(candidates) != 1:
        parser.error("Select exactly one available checkpoint with --label")
    print(json.dumps(recover(candidates[0], args.output_dir), indent=2))


if __name__ == "__main__":
    main()
