"""Build hash manifests for Stage 2 XMP checkpoint directories."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.python.common import ensure_parent_dir


DEFAULT_CHECKPOINT_ROOT = "data/stage2/reference_state/xmp_preconditioning"
DEFAULT_MUTABLE_ORIGIN_ROOT = "data/live_workspace"
DEFAULT_CHECKPOINT_LABEL = "stage2_preconditioning_reference"
DEFAULT_OUTPUT = "outputs/stage2/stage2_preconditioning_checkpoint_manifest.json"


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for Stage 2 checkpoint manifest generation."""
    parser = argparse.ArgumentParser(
        description="Build a hash manifest for a frozen Stage 2 XMP checkpoint."
    )
    parser.add_argument(
        "--checkpoint-root",
        default=DEFAULT_CHECKPOINT_ROOT,
        help="Frozen checkpoint directory containing XMP sidecars.",
    )
    parser.add_argument(
        "--mutable-origin-root",
        default=DEFAULT_MUTABLE_ORIGIN_ROOT,
        help="Mutable workspace the checkpoint was copied from.",
    )
    parser.add_argument(
        "--checkpoint-label",
        default=DEFAULT_CHECKPOINT_LABEL,
        help="Stable label describing the checkpoint boundary.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="Destination JSON file for the checkpoint manifest.",
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Allow an empty checkpoint manifest. Intended only for placeholders.",
    )
    return parser.parse_args()


def list_xmps(folder: Path) -> list[Path]:
    """Return XMP files in one checkpoint directory."""
    if not folder.is_dir():
        raise SystemExit(f"Checkpoint root not found: {folder}")
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and not path.name.startswith(".") and path.suffix.lower() == ".xmp"
    )


def sha256_file(path: Path) -> str:
    """Calculate a SHA-256 digest for one local artifact."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checkpoint_artifact(path: Path, mutable_origin_root: Path) -> dict[str, object]:
    """Build manifest evidence for one checkpointed XMP sidecar."""
    checkpoint_sha256 = sha256_file(path)
    mutable_origin_path = mutable_origin_root / path.name
    mutable_origin_exists = mutable_origin_path.is_file()
    mutable_origin_sha256 = (
        sha256_file(mutable_origin_path) if mutable_origin_exists else None
    )
    mutable_origin_size_bytes = (
        mutable_origin_path.stat().st_size if mutable_origin_exists else None
    )
    return {
        "asset_key": path.stem,
        "checkpoint_path": str(path),
        "checkpoint_size_bytes": path.stat().st_size,
        "checkpoint_sha256": checkpoint_sha256,
        "mutable_origin_path": str(mutable_origin_path),
        "mutable_origin_exists_at_manifest_time": mutable_origin_exists,
        "mutable_origin_size_bytes_at_manifest_time": mutable_origin_size_bytes,
        "mutable_origin_sha256_at_manifest_time": mutable_origin_sha256,
        "mutable_origin_matches_checkpoint_at_manifest_time": (
            mutable_origin_sha256 == checkpoint_sha256
            if mutable_origin_exists
            else False
        ),
    }


def build_manifest(
    checkpoint_root: Path,
    mutable_origin_root: Path,
    checkpoint_label: str,
    allow_empty: bool,
) -> dict[str, object]:
    """Build an ordered checkpoint manifest payload."""
    artifacts = [
        checkpoint_artifact(path, mutable_origin_root)
        for path in list_xmps(checkpoint_root)
    ]
    if not artifacts and not allow_empty:
        raise SystemExit(
            f"Checkpoint root contains no XMP sidecars: {checkpoint_root}"
        )
    matching_mutable_origin_count = sum(
        1
        for artifact in artifacts
        if artifact["mutable_origin_matches_checkpoint_at_manifest_time"]
    )
    missing_mutable_origin_count = sum(
        1
        for artifact in artifacts
        if not artifact["mutable_origin_exists_at_manifest_time"]
    )
    return {
        "stage": "stage2_baseline_conditioning",
        "checkpoint_label": checkpoint_label,
        "checkpoint_root": str(checkpoint_root),
        "mutable_origin_root": str(mutable_origin_root),
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "purpose": (
            "Preserve artifact integrity for a frozen Stage 2 XMP "
            "checkpoint copied from Lightroom's mutable live workspace."
        ),
        "summary": {
            "artifact_count": len(artifacts),
            "matching_mutable_origin_count_at_manifest_time": matching_mutable_origin_count,
            "missing_mutable_origin_count_at_manifest_time": missing_mutable_origin_count,
            "mismatched_mutable_origin_count_at_manifest_time": (
                len(artifacts)
                - matching_mutable_origin_count
                - missing_mutable_origin_count
            ),
        },
        "artifacts": artifacts,
    }


def write_ordered_json(path: str | Path, payload: dict[str, object]) -> Path:
    """Write JSON while preserving semantic insertion order."""
    target = ensure_parent_dir(path)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    return target


def main() -> None:
    """Generate a Stage 2 checkpoint manifest."""
    args = parse_args()
    manifest = build_manifest(
        checkpoint_root=Path(args.checkpoint_root),
        mutable_origin_root=Path(args.mutable_origin_root),
        checkpoint_label=args.checkpoint_label,
        allow_empty=args.allow_empty,
    )
    write_ordered_json(args.output, manifest)
    print(
        f"Wrote {args.output} with "
        f"{manifest['summary']['artifact_count']} checkpoint artifacts."
    )


if __name__ == "__main__":
    main()
