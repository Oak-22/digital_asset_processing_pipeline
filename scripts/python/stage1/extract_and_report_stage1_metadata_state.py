"""Extract and report normalized Stage 1 metadata state from live assets."""

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
    "-Marked",
    "-UsageTerms",
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


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for Stage 1 metadata-state reporting."""
    parser = argparse.ArgumentParser(
        description="Extract and report normalized Stage 1 metadata state."
    )
    parser.add_argument(
        "--input-root",
        default="data/stage1/live_workspace",
        help="Stage 1 mixed workspace folder.",
    )
    parser.add_argument(
        "--snapshot-stage",
        help=(
            "Optional label to use when input-root is one mixed live workspace. "
            "Defaults to the folder name."
        ),
    )
    parser.add_argument(
        "--output",
        default="outputs/stage1/extracted_stage1_metadata.json",
        help="Destination JSON file for the normalized Stage 1 metadata report.",
    )
    return parser.parse_args()


def list_workspace_xmps(folder: Path) -> list[Path]:
    """List XMP sidecars from either a mixed workspace or legacy snapshot folder."""
    sidecar_root = folder / "sidecars"
    search_root = sidecar_root if sidecar_root.is_dir() else folder
    return sorted(
        path
        for path in search_root.iterdir()
        if path.is_file() and not path.name.startswith(".") and path.suffix.lower() == ".xmp"
    )


def list_workspace_raws(folder: Path) -> list[Path]:
    """List RAW files from either a mixed workspace or legacy snapshot folder."""
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
    snapshot_stage: str,
    snapshot_path: Path,
    payload: dict[str, object],
) -> dict[str, object]:
    """Normalize one raw exiftool payload into a stable Stage 1 record."""
    source_file = Path(str(payload["SourceFile"]))
    original_raw_filename = payload.get("PreservedFileName")
    asset_key = canonical_asset_key(original_raw_filename, source_file.stem)
    return {
        "snapshot_stage": snapshot_stage,
        "snapshot_path": str(snapshot_path),
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
        "rights_marked": payload.get("Marked"),
        "usage_terms": normalize_value(payload.get("UsageTerms")),
    }


def normalize_raw_record(
    snapshot_stage: str,
    snapshot_path: Path,
    payload: dict[str, object],
) -> dict[str, object]:
    """Normalize one RAW metadata payload into a stable Stage 1 record."""
    source_file = Path(str(payload["SourceFile"]))
    raw_file_name = payload.get("FileName")
    asset_key = canonical_asset_key(raw_file_name, source_file.stem)
    return {
        "snapshot_stage": snapshot_stage,
        "snapshot_path": str(snapshot_path),
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


def resolve_snapshot_inputs(
    input_root: Path, snapshot_stage: str | None
) -> list[tuple[str, Path]]:
    """Resolve one mixed workspace into a labeled Stage 1 snapshot input."""
    if not input_root.is_dir():
        raise SystemExit(f"Input root not found: {input_root}")

    snapshot_folders = sorted(
        path
        for path in input_root.iterdir()
        if path.is_dir() and path.name[:2].isdigit()
    )
    if snapshot_folders:
        return [(path.name, path) for path in snapshot_folders]

    stage_name = snapshot_stage or input_root.name
    return [(stage_name, input_root)]


def build_records(input_root: Path, snapshot_stage: str | None) -> list[dict[str, object]]:
    """Extract normalized records from one live workspace or many snapshot folders."""
    records: list[dict[str, object]] = []
    for stage_name, snapshot_path in resolve_snapshot_inputs(input_root, snapshot_stage):
        xmps = list_workspace_xmps(snapshot_path)
        raws = list_workspace_raws(snapshot_path)
        for payload in run_exiftool(raws, RAW_FIELDS):
            records.append(normalize_raw_record(stage_name, snapshot_path, payload))
        for payload in run_exiftool(xmps, XMP_FIELDS):
            records.append(normalize_record(stage_name, snapshot_path, payload))
    return sorted(records, key=record_sort_key)


def record_sort_key(record: dict[str, object]) -> tuple[str, str, int, str]:
    """Keep related RAW/XMP records adjacent for easier inspection."""
    snapshot_stage = str(record.get("snapshot_stage", ""))
    asset_key = str(record.get("asset_key") or record.get("original_raw_filename") or record.get("raw_file_name") or record.get("xmp_file_name") or "")
    source_priority = 0 if record.get("record_source") == "raw" else 1
    source_file = str(record.get("source_file", ""))
    return (snapshot_stage, asset_key, source_priority, source_file)


def print_summary(records: list[dict[str, object]]) -> None:
    """Print a concise extraction summary for the terminal."""
    print(f"Extracted metadata records: {len(records)}")
    if not records:
        return

    counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    for record in records:
        stage = str(record["snapshot_stage"])
        counts[stage] = counts.get(stage, 0) + 1
        source = str(record.get("record_source", "xmp"))
        source_counts[source] = source_counts.get(source, 0) + 1

    for stage in sorted(counts):
        print(f"  {stage}: {counts[stage]}")
    for source in sorted(source_counts):
        print(f"  source={source}: {source_counts[source]}")


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
        key = (str(record["snapshot_stage"]), str(record["asset_key"]))
        grouped.setdefault(key, []).append(record)

    assets: list[dict[str, object]] = []
    for (snapshot_stage, asset_key), asset_records in grouped.items():
        source_summary: dict[str, int] = {}
        for record in asset_records:
            source = str(record.get("record_source", "unknown"))
            source_summary[source] = source_summary.get(source, 0) + 1
        assets.append(
            {
                "snapshot_stage": snapshot_stage,
                "asset_key": asset_key,
                "source_summary": source_summary,
                "records": asset_records,
            }
        )
    return assets


def main() -> None:
    """Extract and report Stage 1 metadata state into a normalized JSON artifact."""
    args = parse_args()
    input_root = Path(args.input_root)
    output_path = Path(args.output)

    records = build_records(input_root, args.snapshot_stage)
    assets = group_assets(records)
    payload = {
        "notes": {
            "structure": "Records are grouped by snapshot stage and asset_key.",
            "record_order": "Within each asset group, RAW metadata appears before XMP metadata when both exist.",
            "record_source_values": {
                "raw": "Metadata extracted directly from the RAW master file.",
                "xmp": "Metadata extracted from the Lightroom-generated XMP sidecar.",
            },
            "asset_key_meaning": "asset_key is the normalized native raw identity stem used to keep related RAW and XMP records together.",
            "input_model": "The canonical Stage 1 input is one mixed live workspace.",
        },
        "input_root": str(input_root),
        "snapshot_stage_argument": args.snapshot_stage,
        "record_count": len(records),
        "asset_count": len(assets),
        "assets": assets,
    }
    write_payload(output_path, payload)

    print_summary(records)
    print(f"Wrote: {output_path}")


if __name__ == "__main__":
    main()
