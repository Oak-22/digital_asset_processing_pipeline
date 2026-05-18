"""Extract normalized Stage 1 XMP metadata records from snapshot folders."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.python.common import write_json


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


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for Stage 1 XMP extraction."""
    parser = argparse.ArgumentParser(
        description="Extract normalized Stage 1 XMP metadata from snapshot folders."
    )
    parser.add_argument(
        "--input-root",
        default="data/stage1",
        help="Root folder containing ordered Stage 1 snapshot folders.",
    )
    parser.add_argument(
        "--output",
        default="outputs/stage1/extracted_xmp_metadata.json",
        help="Destination JSON file for normalized metadata records.",
    )
    return parser.parse_args()


def list_snapshot_folders(input_root: Path) -> list[Path]:
    """Return Stage 1 snapshot folders in pipeline order."""
    if not input_root.is_dir():
        raise SystemExit(f"Input root not found: {input_root}")

    return sorted(
        path
        for path in input_root.iterdir()
        if path.is_dir() and path.name[:2].isdigit()
    )


def list_xmps(folder: Path) -> list[Path]:
    """List XMP sidecars inside one snapshot folder."""
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() == ".xmp"
    )


def run_exiftool(paths: list[Path]) -> list[dict[str, object]]:
    """Read selected XMP fields using exiftool JSON output."""
    if not paths:
        return []

    command = ["exiftool", "-json", *XMP_FIELDS, *[str(path) for path in paths]]
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


def normalize_record(snapshot_folder: Path, payload: dict[str, object]) -> dict[str, object]:
    """Normalize one raw exiftool payload into a stable Stage 1 record."""
    source_file = Path(str(payload["SourceFile"]))
    return {
        "snapshot_stage": snapshot_folder.name,
        "snapshot_path": str(snapshot_folder),
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
        "original_raw_filename": payload.get("PreservedFileName"),
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


def build_records(input_root: Path) -> list[dict[str, object]]:
    """Extract normalized records from every Stage 1 snapshot folder."""
    records: list[dict[str, object]] = []
    for snapshot_folder in list_snapshot_folders(input_root):
        xmps = list_xmps(snapshot_folder)
        for payload in run_exiftool(xmps):
            records.append(normalize_record(snapshot_folder, payload))
    return records


def print_summary(records: list[dict[str, object]]) -> None:
    """Print a concise extraction summary for the terminal."""
    print(f"Extracted XMP records: {len(records)}")
    if not records:
        return

    counts: dict[str, int] = {}
    for record in records:
        stage = str(record["snapshot_stage"])
        counts[stage] = counts.get(stage, 0) + 1

    for stage in sorted(counts):
        print(f"  {stage}: {counts[stage]}")


def main() -> None:
    """Extract Stage 1 XMP metadata into a normalized JSON artifact."""
    args = parse_args()
    input_root = Path(args.input_root)
    output_path = Path(args.output)

    records = build_records(input_root)
    payload = {
        "input_root": str(input_root),
        "record_count": len(records),
        "records": records,
    }
    write_json(output_path, payload)

    print_summary(records)
    print(f"Wrote: {output_path}")


if __name__ == "__main__":
    main()
