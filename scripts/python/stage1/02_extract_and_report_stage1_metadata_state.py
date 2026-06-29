"""Stage 1 step 02: extract normalized metadata state from live assets."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import OrderedDict
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.python.common import write_json


RAW_EXTENSIONS = {
    ".arw",
    ".cr2",
    ".cr3",
    ".dng",
    ".nef",
    ".orf",
    ".raf",
    ".raw",
    ".rw2",
}
XMP_FIELDS = [
    "-FileName",
    "-Directory",
    "-DateTimeOriginal",
    "-CreateDate",
    "-MetadataDate",
    "-Make",
    "-Model",
    "-ImageWidth",
    "-ImageHeight",
    "-PreservedFileName",
    "-DocumentID",
    "-OriginalDocumentID",
    "-InstanceID",
    "-Creator",
    "-Rights",
    "-Subject",
    "-HierarchicalSubject",
    "-Credit",
    "-AuthorsPosition",
    "-Headline",
    "-Description",
    "-Category",
    "-Marked",
    "-UsageTerms",
    "-CreatorAddress",
    "-CreatorCity",
    "-CreatorRegion",
    "-CreatorPostalCode",
    "-CreatorCountry",
    "-CreatorWorkEmail",
    "-CreatorWorkTelephone",
    "-CreatorWorkURL",
]
RAW_FIELDS = [
    "-FileName",
    "-Directory",
    "-DateTimeOriginal",
    "-CreateDate",
    "-Make",
    "-Model",
    "-ImageWidth",
    "-ImageHeight",
]
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
IDENTITY_FIELDS = (
    "creator",
    "rights",
    "credit",
    "authors_position",
    "rights_marked",
    "usage_terms",
    "creator_address",
    "creator_city",
    "creator_region",
    "creator_postal_code",
    "creator_country",
    "creator_work_email",
    "creator_work_telephone",
    "creator_work_url",
)
DOMAIN_FIELDS = ("headline", "description", "category")
KEYWORD_FIELDS = ("subject", "hierarchical_subject")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for Stage 1 metadata-state reporting."""
    parser = argparse.ArgumentParser(
        description="Extract and report normalized Stage 1 metadata state."
    )
    parser.add_argument(
        "--input-root",
        default="data/live_workspace",
        help="Shared mixed Lightroom workspace folder observed by Stage 1.",
    )
    parser.add_argument(
        "--metadata-state",
        help=(
            "Optional metadata-state label to use when input-root is one mixed "
            "live workspace. Defaults to the folder name."
        ),
    )
    parser.add_argument(
        "--output",
        default="outputs/stage1/extracted_stage1_metadata.json",
        help="Destination JSON file for the normalized Stage 1 metadata report.",
    )
    return parser.parse_args()


def list_workspace_xmps(folder: Path) -> list[Path]:
    """List XMP sidecars from either a mixed workspace or legacy checkpoint folder."""
    sidecar_root = folder / "sidecars"
    search_root = sidecar_root if sidecar_root.is_dir() else folder
    return sorted(
        path
        for path in search_root.iterdir()
        if path.is_file() and not path.name.startswith(".") and path.suffix.lower() == ".xmp"
    )


def list_workspace_raws(folder: Path) -> list[Path]:
    """List RAW files from either a mixed workspace or legacy checkpoint folder."""
    image_root = folder / "source_images"
    search_root = image_root if image_root.is_dir() else folder
    return sorted(
        path
        for path in search_root.iterdir()
        if path.is_file()
        and not path.name.startswith(".")
        and path.suffix.lower() in RAW_EXTENSIONS
    )


def run_exiftool(paths: list[Path], fields: list[str]) -> list[dict[str, object]]:
    """Read selected metadata fields using exiftool JSON output."""
    if not paths:
        return []

    command = ["exiftool", "-json", *fields, *[str(path) for path in paths]]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def normalize_value(value: object) -> object:
    """Normalize exiftool payload values into JSON-friendly shapes."""
    if value is None:
        return None
    if isinstance(value, list):
        return [normalize_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): normalize_value(item) for key, item in value.items()}
    return value


def canonical_asset_key(file_name: object, fallback_stem: str) -> str:
    """Normalize local renamed files and preserved raw names to one asset stem."""
    if file_name:
        stem = Path(str(file_name)).stem
    else:
        stem = fallback_stem
    parts = stem.split("_", 1)
    if len(parts) == 2 and parts[0].isdigit():
        return parts[1]
    return stem


def normalize_record(
    metadata_state: str,
    metadata_source_path: Path,
    payload: dict[str, object],
) -> dict[str, object]:
    """Normalize one raw exiftool payload into a stable Stage 1 record."""
    source_file = Path(str(payload["SourceFile"]))
    original_raw_filename = payload.get("PreservedFileName")
    asset_key = canonical_asset_key(original_raw_filename, source_file.stem)
    return {
        "metadata_state": metadata_state,
        "metadata_source_path": str(metadata_source_path),
        "record_source": "xmp",
        "source_file": str(source_file),
        "xmp_file_name": payload.get("FileName"),
        "xmp_directory": payload.get("Directory"),
        "capture_time": payload.get("DateTimeOriginal"),
        "create_time": payload.get("CreateDate"),
        "metadata_time": payload.get("MetadataDate"),
        "camera_make": payload.get("Make"),
        "camera_model": payload.get("Model"),
        "image_width": payload.get("ImageWidth"),
        "image_height": payload.get("ImageHeight"),
        "original_raw_filename": original_raw_filename,
        "asset_key": asset_key,
        "document_id": payload.get("DocumentID"),
        "original_document_id": payload.get("OriginalDocumentID"),
        "instance_id": payload.get("InstanceID"),
        "creator": normalize_value(payload.get("Creator")),
        "rights": normalize_value(payload.get("Rights")),
        "subject": normalize_value(payload.get("Subject")),
        "hierarchical_subject": normalize_value(payload.get("HierarchicalSubject")),
        "credit": payload.get("Credit"),
        "authors_position": payload.get("AuthorsPosition"),
        "headline": payload.get("Headline"),
        "description": payload.get("Description"),
        "category": payload.get("Category"),
        "rights_marked": payload.get("Marked"),
        "usage_terms": normalize_value(payload.get("UsageTerms")),
        "creator_address": payload.get("CreatorAddress"),
        "creator_city": payload.get("CreatorCity"),
        "creator_region": payload.get("CreatorRegion"),
        "creator_postal_code": payload.get("CreatorPostalCode"),
        "creator_country": payload.get("CreatorCountry"),
        "creator_work_email": payload.get("CreatorWorkEmail"),
        "creator_work_telephone": payload.get("CreatorWorkTelephone"),
        "creator_work_url": payload.get("CreatorWorkURL"),
    }


def normalize_raw_record(
    metadata_state: str,
    metadata_source_path: Path,
    payload: dict[str, object],
) -> dict[str, object]:
    """Normalize one RAW metadata payload into a stable Stage 1 record."""
    source_file = Path(str(payload["SourceFile"]))
    raw_file_name = payload.get("FileName")
    asset_key = canonical_asset_key(raw_file_name, source_file.stem)
    return {
        "metadata_state": metadata_state,
        "metadata_source_path": str(metadata_source_path),
        "record_source": "raw",
        "source_file": str(source_file),
        "raw_file_name": raw_file_name,
        "raw_directory": payload.get("Directory"),
        "asset_key": asset_key,
        "capture_time": payload.get("DateTimeOriginal"),
        "create_time": payload.get("CreateDate"),
        "camera_make": payload.get("Make"),
        "camera_model": payload.get("Model"),
        "image_width": payload.get("ImageWidth"),
        "image_height": payload.get("ImageHeight"),
    }


def resolve_metadata_inputs(
    input_root: Path, metadata_state: str | None
) -> list[tuple[str, Path]]:
    """Resolve one mixed workspace or legacy checkpoint folders into inputs."""
    if not input_root.is_dir():
        raise SystemExit(f"Input root not found: {input_root}")

    checkpoint_folders = sorted(
        path
        for path in input_root.iterdir()
        if path.is_dir() and path.name[:2].isdigit()
    )
    if checkpoint_folders:
        return [(path.name, path) for path in checkpoint_folders]

    stage_name = metadata_state or input_root.name
    return [(stage_name, input_root)]


def build_records(input_root: Path, metadata_state: str | None) -> list[dict[str, object]]:
    """Extract normalized records from one live workspace or checkpoint folders."""
    records: list[dict[str, object]] = []
    for stage_name, metadata_source_path in resolve_metadata_inputs(input_root, metadata_state):
        xmps = list_workspace_xmps(metadata_source_path)
        raws = list_workspace_raws(metadata_source_path)
        for payload in run_exiftool(raws, RAW_FIELDS):
            records.append(normalize_raw_record(stage_name, metadata_source_path, payload))
        for payload in run_exiftool(xmps, XMP_FIELDS):
            records.append(normalize_record(stage_name, metadata_source_path, payload))
    return sorted(records, key=record_sort_key)


def record_sort_key(record: dict[str, object]) -> tuple[str, str, int, str]:
    """Keep related RAW/XMP records adjacent for easier inspection."""
    metadata_state = str(record.get("metadata_state", ""))
    asset_key = str(record.get("asset_key") or record.get("original_raw_filename") or record.get("raw_file_name") or record.get("xmp_file_name") or "")
    source_priority = 0 if record.get("record_source") == "raw" else 1
    source_file = str(record.get("source_file", ""))
    return (metadata_state, asset_key, source_priority, source_file)


def stage_sort_rank(metadata_state: str) -> int:
    """Return the intended Stage 1 sequence rank for report ordering."""
    try:
        return STAGE_ORDER.index(metadata_state)
    except ValueError:
        return len(STAGE_ORDER)


def print_summary(records: list[dict[str, object]]) -> None:
    """Print a concise extraction summary for the terminal."""
    print(f"Extracted metadata records: {len(records)}")
    if not records:
        return

    counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    for record in records:
        stage = str(record["metadata_state"])
        counts[stage] = counts.get(stage, 0) + 1
        source = str(record.get("record_source", "xmp"))
        source_counts[source] = source_counts.get(source, 0) + 1

    for stage in sorted(counts, key=lambda name: (stage_sort_rank(name), name)):
        print(f"  {stage}: {counts[stage]}")
    for source in sorted(source_counts):
        print(f"  source={source}: {source_counts[source]}")


def has_metadata_value(value: object) -> bool:
    """Return true when a normalized metadata field has meaningful content."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(has_metadata_value(item) for item in value)
    if isinstance(value, dict):
        return any(has_metadata_value(item) for item in value.values())
    return True


def infer_asset_stage(asset_records: list[dict[str, object]]) -> str:
    """Infer the Stage 1 metadata state from paired RAW/XMP records."""
    xmp_records = [
        record for record in asset_records if record.get("record_source") == "xmp"
    ]
    if not xmp_records:
        return STAGE_PRE_IDENTITY

    has_keywords = any(
        has_metadata_value(record.get(field))
        for record in xmp_records
        for field in KEYWORD_FIELDS
    )
    if has_keywords:
        return STAGE_IDENTITY_DOMAIN_KEYWORDS

    has_domain = any(
        has_metadata_value(record.get(field))
        for record in xmp_records
        for field in DOMAIN_FIELDS
    )
    if has_domain:
        return STAGE_IDENTITY_DOMAIN

    has_identity = any(
        has_metadata_value(record.get(field))
        for record in xmp_records
        for field in IDENTITY_FIELDS
    )
    if has_identity:
        return STAGE_POST_IDENTITY

    return STAGE_POST_IDENTITY


def write_payload(path: Path, payload: dict[str, object]) -> Path:
    """Write extractor output without alphabetizing keys."""
    target = write_json(path, {})
    with target.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    return target


def group_assets(records: list[dict[str, object]]) -> list[dict[str, object]]:
    """Nest related records under one asset bundle for easier inspection."""
    grouped: OrderedDict[tuple[str, str], list[dict[str, object]]] = OrderedDict()
    for record in records:
        key = (str(record["metadata_source_path"]), str(record["asset_key"]))
        grouped.setdefault(key, []).append(record)

    assets: list[dict[str, object]] = []
    for (_metadata_source_path, asset_key), asset_records in grouped.items():
        metadata_state = infer_asset_stage(asset_records)
        source_summary: dict[str, int] = {}
        for record in asset_records:
            record["metadata_state"] = metadata_state
            source = str(record.get("record_source", "unknown"))
            source_summary[source] = source_summary.get(source, 0) + 1
        assets.append(
            {
                "metadata_state": metadata_state,
                "asset_key": asset_key,
                "source_summary": source_summary,
                "records": asset_records,
            }
        )
    return sorted(
        assets,
        key=lambda asset: (
            stage_sort_rank(str(asset["metadata_state"])),
            str(asset["asset_key"]),
        ),
    )


def count_assets_by_stage(assets: list[dict[str, object]]) -> dict[str, int]:
    """Count asset bundles assigned to each known Stage 1 metadata stage."""
    counts = {stage: 0 for stage in STAGE_ORDER}
    for asset in assets:
        stage = str(asset["metadata_state"])
        counts[stage] = counts.get(stage, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (stage_sort_rank(item[0]), item[0])))


def group_assets_by_stage(assets: list[dict[str, object]]) -> list[dict[str, object]]:
    """Group asset bundles under one header per inferred metadata stage."""
    grouped = {stage: [] for stage in STAGE_ORDER}
    for asset in assets:
        asset_copy = dict(asset)
        stage = str(asset_copy.pop("metadata_state"))
        grouped.setdefault(stage, []).append(asset_copy)

    stage_groups: list[dict[str, object]] = []
    for stage, stage_assets in sorted(
        grouped.items(), key=lambda item: (stage_sort_rank(item[0]), item[0])
    ):
        if not stage_assets:
            continue
        stage_asset_count = len(stage_assets)
        positioned_assets: list[dict[str, object]] = []
        for index, asset in enumerate(stage_assets, start=1):
            positioned_assets.append(
                {
                    "asset_key": asset["asset_key"],
                    "source_summary": asset["source_summary"],
                    "stage_asset_position": f"{index}/{stage_asset_count}",
                    "records": asset["records"],
                }
            )
        stage_groups.append(
            {
                "metadata_state": stage,
                "asset_count": stage_asset_count,
                "assets": positioned_assets,
            }
        )
    return stage_groups


def main() -> None:
    """Extract and report Stage 1 metadata state into a normalized JSON artifact."""
    args = parse_args()
    input_root = Path(args.input_root)
    output_path = Path(args.output)

    records = build_records(input_root, args.metadata_state)
    assets = group_assets(records)
    payload = {
        "notes": {
            "structure": "Assets are grouped under one header per inferred metadata_state; records remain grouped by input location and asset_key.",
            "record_order": "Within each asset group, RAW metadata appears before XMP metadata when both exist.",
            "record_source_values": {
                "raw": "Metadata extracted directly from the RAW master file.",
                "xmp": "Metadata extracted from the Lightroom-generated XMP sidecar.",
            },
            "asset_key_meaning": "asset_key is the normalized native raw identity stem used to keep related RAW and XMP records together.",
            "metadata_state_meaning": "metadata_state is inferred from each asset pair: no XMP, identity XMP, identity+domain XMP, or identity+domain+keywording XMP.",
            "metadata_state_values": {
                STAGE_PRE_IDENTITY: "RAW has no matching XMP sidecar.",
                STAGE_POST_IDENTITY: "XMP contains identity/contact/copyright metadata but no content-domain fields.",
                STAGE_IDENTITY_DOMAIN: "XMP contains identity metadata plus content-domain fields such as headline, description, or category.",
                STAGE_IDENTITY_DOMAIN_KEYWORDS: "XMP contains identity and domain metadata plus keyword fields such as subject or hierarchical subject.",
            },
            "input_model": "The canonical Stage 1 input is one mixed live workspace.",
        },
        "input_root": str(input_root),
        "metadata_state_argument": args.metadata_state,
        "record_count": len(records),
        "asset_count": len(assets),
        "metadata_state_counts": count_assets_by_stage(assets),
        "metadata_state_groups": group_assets_by_stage(assets),
    }
    write_payload(output_path, payload)

    print_summary(records)
    print(f"Wrote: {output_path}")


if __name__ == "__main__":
    main()
