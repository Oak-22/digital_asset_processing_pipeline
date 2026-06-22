"""Stage 1 step 04: build a manifest from validated metadata artifacts."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.python.common import read_json, write_json


STAGE_NAME = "stage1_metadata_application_enrichment_query"
STAGE_PRE_IDENTITY = "stage1_pre-identity"
STAGE_POST_IDENTITY = "stage1_post-identity"
STAGE_IDENTITY_DOMAIN = "stage1_identity_domain"
STAGE_IDENTITY_DOMAIN_KEYWORDS = "stage1_identity_domain_keywords"
STAGE_ORDER = (
    STAGE_PRE_IDENTITY,
    STAGE_POST_IDENTITY,
    STAGE_IDENTITY_DOMAIN,
    STAGE_IDENTITY_DOMAIN_KEYWORDS,
)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for Stage 1 manifest generation."""
    parser = argparse.ArgumentParser(
        description="Build a Stage 1 manifest from extracted and validated artifacts."
    )
    parser.add_argument(
        "--metadata",
        default="outputs/stage1/extracted_stage1_metadata.json",
        help="Extracted Stage 1 metadata JSON produced by step 02.",
    )
    parser.add_argument(
        "--validation-report",
        default="outputs/stage1/stage1_metadata_validation_report.json",
        help="Stage 1 validation report produced by step 03.",
    )
    parser.add_argument(
        "--snapshots-dir",
        default="outputs/stage1/snapshots",
        help="Directory containing supporting Stage 1 snapshot artifacts.",
    )
    parser.add_argument(
        "--output",
        default="outputs/stage1/stage1_manifest.json",
        help="Destination Stage 1 manifest JSON.",
    )
    parser.add_argument(
        "--allow-failed-validation",
        action="store_true",
        help="Build the manifest even when the validation report status is not pass.",
    )
    return parser.parse_args()


def file_artifact(path: Path) -> dict[str, object]:
    """Return stable file metadata for a manifest artifact reference."""
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def sha256_file(path: Path) -> str:
    """Calculate a SHA-256 digest for a local artifact."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def list_snapshot_artifacts(snapshots_dir: Path) -> list[dict[str, object]]:
    """List supporting snapshot artifacts in deterministic path order."""
    if not snapshots_dir.exists():
        return []
    if not snapshots_dir.is_dir():
        raise SystemExit(f"Snapshots path is not a directory: {snapshots_dir}")
    return [
        file_artifact(path)
        for path in sorted(snapshots_dir.rglob("*"))
        if path.is_file() and not path.name.startswith(".")
    ]


def build_asset_manifest(metadata: dict[str, object]) -> list[dict[str, object]]:
    """Summarize grouped Stage 1 assets without duplicating full metadata records."""
    groups = metadata.get("snapshot_stage_groups")
    if not isinstance(groups, list):
        raise SystemExit("Extracted metadata is missing snapshot_stage_groups.")

    assets: list[dict[str, object]] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        stage = str(group.get("snapshot_stage", ""))
        stage_assets = group.get("assets", [])
        if not isinstance(stage_assets, list):
            continue
        for asset in stage_assets:
            if not isinstance(asset, dict):
                continue
            assets.append(summarize_asset(stage, asset))
    return sorted(
        assets,
        key=lambda asset: (
            stage_sort_rank(str(asset["snapshot_stage"])),
            str(asset["asset_key"]),
        ),
    )


def summarize_asset(stage: str, asset: dict[str, object]) -> dict[str, object]:
    """Build one compact asset entry for the Stage 1 manifest."""
    records = asset.get("records", [])
    if not isinstance(records, list):
        records = []

    raw_records = [
        record
        for record in records
        if isinstance(record, dict) and record.get("record_source") == "raw"
    ]
    xmp_records = [
        record
        for record in records
        if isinstance(record, dict) and record.get("record_source") == "xmp"
    ]
    return {
        "asset_key": asset.get("asset_key"),
        "snapshot_stage": stage,
        "stage_asset_position": asset.get("stage_asset_position"),
        "source_summary": asset.get("source_summary", {}),
        "raw_source_files": [
            str(record.get("source_file"))
            for record in raw_records
            if record.get("source_file")
        ],
        "xmp_source_files": [
            str(record.get("source_file"))
            for record in xmp_records
            if record.get("source_file")
        ],
        "record_count": len(records),
        "has_identity_metadata": any(
            has_any_field(
                record,
                (
                    "creator",
                    "rights",
                    "credit",
                    "authors_position",
                    "usage_terms",
                ),
            )
            for record in xmp_records
        ),
        "has_domain_metadata": any(
            has_any_field(record, ("headline", "description", "category"))
            for record in xmp_records
        ),
        "has_keyword_metadata": any(
            has_any_field(record, ("subject", "hierarchical_subject"))
            for record in xmp_records
        ),
    }


def has_any_field(record: dict[str, object], fields: tuple[str, ...]) -> bool:
    """Return true when any listed metadata field has meaningful content."""
    return any(has_value(record.get(field)) for field in fields)


def has_value(value: object) -> bool:
    """Return true when a normalized metadata field has meaningful content."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(has_value(item) for item in value)
    if isinstance(value, dict):
        return any(has_value(item) for item in value.values())
    return True


def stage_sort_rank(snapshot_stage: str) -> int:
    """Return the intended Stage 1 sequence rank for manifest ordering."""
    try:
        return STAGE_ORDER.index(snapshot_stage)
    except ValueError:
        return len(STAGE_ORDER)


def build_manifest(
    metadata_path: Path,
    validation_path: Path,
    snapshots_dir: Path,
    metadata: dict[str, object],
    validation_report: dict[str, object],
) -> dict[str, object]:
    """Build the stable Stage 1 manifest payload."""
    snapshot_artifacts = list_snapshot_artifacts(snapshots_dir)
    return {
        "stage": STAGE_NAME,
        "status": manifest_status(validation_report),
        "pipeline_step": "04_build_stage1_manifest",
        "inputs": {
            "metadata": file_artifact(metadata_path),
            "validation_report": file_artifact(validation_path),
            "snapshot_artifacts": snapshot_artifacts,
        },
        "validation": {
            "status": validation_report.get("status"),
            "error_count": validation_report.get("error_count"),
            "warning_count": validation_report.get("warning_count"),
        },
        "summary": {
            "input_root": metadata.get("input_root"),
            "asset_count": metadata.get("asset_count"),
            "record_count": metadata.get("record_count"),
            "snapshot_stage_counts": metadata.get("snapshot_stage_counts", {}),
            "snapshot_artifact_count": len(snapshot_artifacts),
        },
        "assets": build_asset_manifest(metadata),
    }


def manifest_status(validation_report: dict[str, object]) -> str:
    """Return manifest status based on the upstream validation report."""
    if validation_report.get("status") == "pass":
        return "validated"
    return "validation_failed"


def print_summary(manifest: dict[str, object], output_path: Path) -> None:
    """Print a concise manifest summary for terminal use."""
    summary = manifest["summary"]
    validation = manifest["validation"]
    print(f"Stage 1 manifest status: {manifest['status']}")
    print(f"Assets: {summary['asset_count']}")
    print(f"Records: {summary['record_count']}")
    print(f"Validation: {validation['status']}")
    print(f"Wrote: {output_path}")


def main() -> None:
    """Build a Stage 1 manifest from validated extraction artifacts."""
    args = parse_args()
    metadata_path = Path(args.metadata)
    validation_path = Path(args.validation_report)
    snapshots_dir = Path(args.snapshots_dir)
    output_path = Path(args.output)

    metadata = read_json(metadata_path)
    validation_report = read_json(validation_path)
    if not isinstance(metadata, dict):
        raise SystemExit(f"Expected metadata JSON object: {metadata_path}")
    if not isinstance(validation_report, dict):
        raise SystemExit(f"Expected validation report JSON object: {validation_path}")
    if validation_report.get("status") != "pass" and not args.allow_failed_validation:
        raise SystemExit(
            "Validation report is not pass; rerun with --allow-failed-validation "
            "to build a manifest anyway."
        )

    manifest = build_manifest(
        metadata_path,
        validation_path,
        snapshots_dir,
        metadata,
        validation_report,
    )
    write_json(output_path, manifest)
    print_summary(manifest, output_path)


if __name__ == "__main__":
    main()
