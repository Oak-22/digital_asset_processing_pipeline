"""Quick terminal audit for likely JPEG/XMP pairing in a Stage 1 snapshot."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".JPG", ".JPEG"}
XMP_EXTENSION = ".xmp"
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
EXIFTOOL_FIELDS = [
    "-FileName",
    "-DateTimeOriginal",
    "-CreateDate",
    "-Make",
    "-Model",
    "-ImageWidth",
    "-ImageHeight",
    "-Subject",
    "-Keywords",
    "-PreservedFileName",
]


@dataclass
class MetadataRecord:
    """Subset of image/XMP metadata used for pairing heuristics."""

    source_file: Path
    file_name: str
    date_time_original: str | None
    create_date: str | None
    make: str | None
    model: str | None
    image_width: int | None
    image_height: int | None
    subject: list[str]
    keywords: list[str]
    preserved_file_name: str | None


@dataclass
class MatchCandidate:
    """Candidate pairing between one JPEG and one XMP record."""

    image: MetadataRecord
    xmp: MetadataRecord
    score: int
    reasons: list[str]


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for local-folder or S3-backed inspection."""
    parser = argparse.ArgumentParser(
        description="Verify likely JPEG/XMP pairings inside a Stage 1 snapshot."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default="data/stage1/01_pre_identity",
        help="Local folder containing JPEGs and XMP sidecars to compare.",
    )
    parser.add_argument(
        "--bucket-uri",
        help="Optional S3 bucket URI, e.g. s3://jb-photo-masters.",
    )
    parser.add_argument(
        "--raw-prefix",
        default="raw/",
        help="RAW prefix inside the S3 bucket when --bucket-uri is used.",
    )
    parser.add_argument(
        "--jpeg-prefix",
        default="jpeg/",
        help="JPEG prefix inside the S3 bucket when --bucket-uri is used.",
    )
    parser.add_argument(
        "--xmp-prefix",
        default="xmp/",
        help="XMP prefix inside the S3 bucket when --bucket-uri is used.",
    )
    return parser.parse_args()


def source_images_dir(snapshot_folder: Path) -> Path:
    """Return the source-images subfolder for one local Stage 1 snapshot."""
    return snapshot_folder / "source_images"


def sidecars_dir(snapshot_folder: Path) -> Path:
    """Return the sidecars subfolder for one local Stage 1 snapshot."""
    return snapshot_folder / "sidecars"


def run_exiftool(paths: list[Path]) -> list[MetadataRecord]:
    """Read a focused metadata subset for the given paths using exiftool."""
    if not paths:
        return []

    command = ["exiftool", "-json", *EXIFTOOL_FIELDS, *[str(path) for path in paths]]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    return [build_record(item) for item in payload]


def build_record(payload: dict[str, object]) -> MetadataRecord:
    """Normalize exiftool JSON into a simpler metadata record."""
    return MetadataRecord(
        source_file=Path(str(payload["SourceFile"])),
        file_name=str(payload.get("FileName", "")),
        date_time_original=as_string(payload.get("DateTimeOriginal")),
        create_date=as_string(payload.get("CreateDate")),
        make=as_string(payload.get("Make")),
        model=as_string(payload.get("Model")),
        image_width=as_int(payload.get("ImageWidth")),
        image_height=as_int(payload.get("ImageHeight")),
        subject=as_string_list(payload.get("Subject")),
        keywords=as_string_list(payload.get("Keywords")),
        preserved_file_name=as_string(payload.get("PreservedFileName")),
    )


def as_string(value: object) -> str | None:
    """Convert a metadata field to a string when present."""
    if value is None:
        return None
    return str(value)


def as_int(value: object) -> int | None:
    """Convert a metadata field to an integer when possible."""
    if value is None:
        return None
    return int(value)


def as_string_list(value: object) -> list[str]:
    """Normalize keyword-like metadata into a flat string list."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def parse_exif_datetime(value: str | None) -> datetime | None:
    """Parse common exiftool datetime formats with optional timezone."""
    if not value:
        return None

    normalized = value[:19]
    for pattern in ("%Y:%m:%d %H:%M:%S",):
        try:
            return datetime.strptime(normalized, pattern)
        except ValueError:
            continue
    return None


def find_candidates(
    images: list[MetadataRecord], xmps: list[MetadataRecord]
) -> list[MatchCandidate]:
    """Score every image/XMP combination."""
    candidates: list[MatchCandidate] = []
    for image in images:
        for xmp in xmps:
            score, reasons = score_match(image, xmp)
            candidates.append(
                MatchCandidate(image=image, xmp=xmp, score=score, reasons=reasons)
            )
    return candidates


def score_match(image: MetadataRecord, xmp: MetadataRecord) -> tuple[int, list[str]]:
    """Assign a rough confidence score to one JPEG/XMP pair."""
    score = 0
    reasons: list[str] = []

    image_dt = parse_exif_datetime(image.date_time_original or image.create_date)
    xmp_dt = parse_exif_datetime(xmp.date_time_original or xmp.create_date)

    if image.make and xmp.make and image.make == xmp.make:
        score += 10
        reasons.append(f"make={image.make}")

    if image.model and xmp.model and image.model == xmp.model:
        score += 10
        reasons.append(f"model={image.model}")

    if image_dt and xmp_dt:
        delta_seconds = abs(int((image_dt.replace(tzinfo=None) - xmp_dt.replace(tzinfo=None)).total_seconds()))
        if delta_seconds == 0:
            score += 50
            reasons.append("capture time exact")
        elif delta_seconds <= 5:
            score += 40
            reasons.append(f"capture time within {delta_seconds}s")
        elif delta_seconds <= 60:
            score += 30
            reasons.append(f"capture time within {delta_seconds}s")
        elif delta_seconds <= 180:
            score += 20
            reasons.append(f"capture time within {delta_seconds}s")
        else:
            reasons.append(f"capture time differs by {delta_seconds}s")
    else:
        reasons.append("capture time unavailable on one side")

    overlapping_terms = sorted(
        set(term.lower() for term in image.subject + image.keywords)
        & set(term.lower() for term in xmp.subject + xmp.keywords)
    )
    if overlapping_terms:
        overlap_score = min(20, 5 * len(overlapping_terms))
        score += overlap_score
        reasons.append(f"keyword overlap={', '.join(overlapping_terms[:4])}")

    if image.image_width and image.image_height and xmp.image_width and xmp.image_height:
        image_orientation = "portrait" if image.image_height > image.image_width else "landscape"
        xmp_orientation = "portrait" if xmp.image_height > xmp.image_width else "landscape"
        if image_orientation == xmp_orientation:
            score += 5
            reasons.append(f"orientation={image_orientation}")

    return score, reasons


def verdict_for(candidate: MatchCandidate) -> str:
    """Translate numeric score into a terminal-friendly verdict."""
    if candidate.score >= 60:
        return "MATCH"
    if candidate.score >= 35:
        return "WEAK_MATCH"
    return "CONFLICT"


def sync_s3_prefix(bucket_uri: str, prefix: str, destination: Path) -> None:
    """Sync one S3 prefix into a local temporary directory."""
    source = f"{bucket_uri.rstrip('/')}/{prefix.lstrip('/')}"
    command = ["aws", "s3", "sync", source, str(destination), "--exclude", "*/"]
    subprocess.run(command, check=True, capture_output=True, text=True)


def gather_local_paths(folder: Path) -> tuple[list[Path], list[Path], int, str]:
    """Collect local JPEG/XMP/RAW paths from one Stage 1 snapshot folder."""
    image_root = source_images_dir(folder)
    sidecar_root = sidecars_dir(folder)

    if not image_root.is_dir():
        raise SystemExit(f"Missing source_images/ in snapshot folder: {folder}")
    if not sidecar_root.is_dir():
        raise SystemExit(f"Missing sidecars/ in snapshot folder: {folder}")

    image_files = [
        path
        for path in image_root.iterdir()
        if path.is_file() and not path.name.startswith(".")
    ]
    sidecar_files = [
        path
        for path in sidecar_root.iterdir()
        if path.is_file() and not path.name.startswith(".")
    ]
    images = sorted(
        (path for path in image_files if path.suffix in IMAGE_EXTENSIONS),
        key=lambda path: path.name,
    )
    xmps = sorted(
        (path for path in sidecar_files if path.suffix.lower() == XMP_EXTENSION),
        key=lambda path: path.name,
    )
    raw_count = sum(1 for path in image_files if path.suffix.lower() in RAW_EXTENSIONS)
    return images, xmps, raw_count, str(folder)


def gather_s3_paths(args: argparse.Namespace) -> tuple[list[Path], list[Path], int, str]:
    """Download S3-backed snapshot assets into a temporary local workspace."""
    if not args.bucket_uri:
        raise SystemExit("Missing required --bucket-uri for S3-backed verification.")

    temp_root = Path(tempfile.mkdtemp(prefix="stage1_verify_"))
    raw_dir = temp_root / "raw"
    jpeg_dir = temp_root / "jpeg"
    xmp_dir = temp_root / "xmp"
    raw_dir.mkdir(parents=True, exist_ok=True)
    jpeg_dir.mkdir(parents=True, exist_ok=True)
    xmp_dir.mkdir(parents=True, exist_ok=True)

    sync_s3_prefix(args.bucket_uri, args.raw_prefix, raw_dir)
    sync_s3_prefix(args.bucket_uri, args.jpeg_prefix, jpeg_dir)
    sync_s3_prefix(args.bucket_uri, args.xmp_prefix, xmp_dir)

    images = sorted(
        (path for path in jpeg_dir.iterdir() if path.is_file() and path.suffix in IMAGE_EXTENSIONS),
        key=lambda path: path.name,
    )
    xmps = sorted(
        (path for path in xmp_dir.iterdir() if path.is_file() and path.suffix == XMP_EXTENSION),
        key=lambda path: path.name,
    )
    raw_count = sum(
        1
        for path in raw_dir.iterdir()
        if path.is_file() and path.suffix.lower() in RAW_EXTENSIONS
    )
    source_label = (
        f"{args.bucket_uri.rstrip('/')}"
        f" [raw={args.raw_prefix}, jpeg={args.jpeg_prefix}, xmp={args.xmp_prefix}]"
    )
    return images, xmps, raw_count, source_label


def print_report(
    source_label: str,
    images: list[MetadataRecord],
    xmps: list[MetadataRecord],
    raw_count: int,
) -> None:
    """Print a concise folder audit report."""
    print()
    print(f"Source: {source_label}")
    print(f"RAWs: {raw_count}")
    print(f"JPEGs: {len(images)}")
    print(f"XMPs: {len(xmps)}")
    print()

    if not images and not xmps:
        print("No JPEG or XMP assets found in this snapshot.")
        return

    if not xmps:
        print("No XMP found.")
        if raw_count:
            print(
                "Interpretation: this looks like a raw-backed pre-identity "
                "snapshot candidate (`01_pre_identity`)."
            )
            print(
                "Suggested handling: treat RAW metadata as authoritative for "
                "this stage and skip XMP pair verification."
            )
        else:
            print("Need at least one XMP to run sidecar verification.")
        return

    if not images:
        if raw_count:
            print("JPEG companions not found.")
            print(
                "Interpretation: this snapshot may still be valid for "
                "preferred RAW+XMP verification once that path is implemented."
            )
        else:
            print("Need at least one JPEG to run JPEG/XMP pair verification.")
        return

    candidates = find_candidates(images, xmps)
    best_by_image: dict[Path, MatchCandidate] = {}
    for candidate in candidates:
        current = best_by_image.get(candidate.image.source_file)
        if current is None or candidate.score > current.score:
            best_by_image[candidate.image.source_file] = candidate

    matched_xmps: set[Path] = set()
    for image in images:
        candidate = best_by_image[image.source_file]
        matched_xmps.add(candidate.xmp.source_file)
        verdict = verdict_for(candidate)
        print(f"[{verdict}] {image.file_name}")
        print(f"  best xmp: {candidate.xmp.file_name}")
        print(f"  score: {candidate.score}")
        print(f"  reasons: {'; '.join(candidate.reasons)}")
        if candidate.xmp.preserved_file_name:
            print(
                "  xmp original raw filename: "
                f"{candidate.xmp.preserved_file_name}"
            )
        print()

    unmatched_xmps = [xmp for xmp in xmps if xmp.source_file not in matched_xmps]
    if unmatched_xmps:
        print("Unmatched XMPs:")
        for xmp in unmatched_xmps:
            print(f"  - {xmp.file_name}")


def main() -> None:
    """Run pairing audit for one local or S3-backed Stage 1 snapshot."""
    args = parse_args()
    if args.bucket_uri:
        images, xmps, raw_count, source_label = gather_s3_paths(args)
    else:
        folder = Path(args.folder)
        if not folder.is_dir():
            raise SystemExit(f"Folder not found: {folder}")
        images, xmps, raw_count, source_label = gather_local_paths(folder)

    image_records = run_exiftool(images)
    xmp_records = run_exiftool(xmps)
    print_report(source_label, image_records, xmp_records, raw_count)


if __name__ == "__main__":
    main()
