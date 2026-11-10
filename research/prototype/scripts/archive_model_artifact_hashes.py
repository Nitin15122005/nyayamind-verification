#!/usr/bin/env python3
"""Download pinned model snapshots and archive per-file SHA-256 hashes.

This records artifact identity; it does not load either model or perform inference.
Run from the repository root:
    python research/prototype/scripts/archive_model_artifact_hashes.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import platform
import re
import sys
from pathlib import Path

import yaml
from huggingface_hub import __version__ as hf_hub_version
from huggingface_hub import snapshot_download


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = REPO_ROOT / "research/prototype/config/prototype.yaml"
DEFAULT_OUTPUT = REPO_ROOT / "research/prototype/outputs/model_artifact_manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_snapshot(model_id: str, revision: str, cache_dir: str | None = None) -> dict:
    if not re.fullmatch(r"[0-9a-fA-F]{40}", revision):
        raise ValueError(f"{model_id}: revision must be a full 40-character commit SHA, got {revision!r}")

    snapshot = Path(snapshot_download(
        repo_id=model_id,
        revision=revision,
        repo_type="model",
        cache_dir=cache_dir,
    ))
    resolved_revision = snapshot.name
    if resolved_revision.lower() != revision.lower():
        raise RuntimeError(
            f"{model_id}: requested revision {revision} but snapshot resolved to {resolved_revision}"
        )

    files = []
    for path in sorted(snapshot.rglob("*")):
        if not path.is_file() or ".cache" in path.relative_to(snapshot).parts:
            continue
        files.append({
            "path": path.relative_to(snapshot).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    if not files:
        raise RuntimeError(f"{model_id}: snapshot contained no files: {snapshot}")

    return {
        "model_id": model_id,
        "requested_revision": revision.lower(),
        "resolved_revision": resolved_revision.lower(),
        "snapshot_file_count": len(files),
        "total_size_bytes": sum(item["size_bytes"] for item in files),
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache-dir", type=str, default=None)
    parser.add_argument("--model", choices=("all", "qwen", "deberta"), default="all")
    args = parser.parse_args()

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    model_configs = {
        "qwen": config["generation"],
        "deberta": config["verification"],
    }
    selected = model_configs if args.model == "all" else {args.model: model_configs[args.model]}

    manifest = {
        "manifest_schema_version": 1,
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repository_commit": None,
        "python_version": sys.version,
        "platform": platform.platform(),
        "huggingface_hub_version": hf_hub_version,
        "models": {},
    }
    for name, model_config in selected.items():
        model_id = model_config["model_id"]
        revision = model_config.get("revision")
        if not revision:
            raise ValueError(f"{name}: no immutable revision configured for {model_id}")
        print(f"Downloading/verifying {name}: {model_id}@{revision}", flush=True)
        entry = hash_snapshot(model_id, revision, args.cache_dir)
        manifest["models"][name] = entry
        print(
            f"  verified {entry['resolved_revision']}: "
            f"{entry['snapshot_file_count']} files, {entry['total_size_bytes']:,} bytes",
            flush=True,
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(f"Manifest written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
