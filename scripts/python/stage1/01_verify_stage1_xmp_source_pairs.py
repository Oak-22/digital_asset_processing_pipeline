"""Stage 1 step 01: audit preferred RAW/XMP or fallback JPEG/XMP pairing.

RAW/XMP deterministic matching rules:
1. Prefer XMP records whose `PreservedFileName` exactly matches the RAW filename.
2. If `PreservedFileName` is absent, fall back to exact stem matching.
3. Require supporting capture evidence from camera make/model and capture time.
4. Treat exact or near-exact capture-time agreement as strong support.
5. Leave RAW files unmatched when no XMP satisfies the identity rules above.

JPEG/XMP remains a weaker fallback path and still uses heuristic scoring.
"""

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
RAW_XMP_RULES = [
    "Prefer exact `PreservedFileName` -> RAW filename matches.",
    "Otherwise fall back to exact XMP stem -> RAW stem matches.",
    "Require supporting agreement from camera make/model.",
    "Treat exact capture time as strongest support; <=5s is acceptable near-match.",
    "Leave RAW files unmatched when no XMP satisfies identity rules.",
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


@dataclass
class RawXmpMatchCandidate:
    """Candidate pairing between one RAW and one XMP record."""

    raw: MetadataRecord
    xmp: MetadataRecord
    verdict: str
    rank: tuple[int, int, int, int, int]
    reasons: list[str]


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for local-folder or S3-backed inspection."""
    parser = argparse.ArgumentParser(
        description="Verify likely RAW/XMP or JPEG/XMP pairings inside a Stage 1 workspace."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default="data/live_workspace",
        help="Local mixed workspace folder to compare.",
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
    """Score every JPEG/XMP combination."""
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
        delta_seconds = abs(
            int((image_dt.replace(tzinfo=None) - xmp_dt.replace(tzinfo=None)).total_seconds())
        )
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
    """Translate JPEG/XMP score into a terminal-friendly verdict."""
    if candidate.score >= 60:
        return "MATCH"
    if candidate.score >= 35:
        return "WEAK_MATCH"
    return "CONFLICT"


def evaluate_raw_xmp_match(
    raw: MetadataRecord, xmp: MetadataRecord
) -> tuple[str, tuple[int, int, int, int, int], list[str]]:
    """Evaluate one RAW/XMP pair using deterministic identity rules."""
    reasons: list[str] = []

    raw_stem = Path(raw.file_name).stem
    xmp_stem = Path(xmp.file_name).stem
    preserved_stem = Path(xmp.preserved_file_name).stem if xmp.preserved_file_name else None
    preserved_match = bool(preserved_stem and preserved_stem == raw_stem)
    stem_match = xmp_stem == raw_stem

    if preserved_match:
        reasons.append(f"preserved raw filename={xmp.preserved_file_name}")
    elif stem_match:
        reasons.append(f"matching stem={raw_stem}")
    else:
        reasons.append(f"stem mismatch raw={raw_stem} xmp={xmp_stem}")

    make_match = bool(raw.make and xmp.make and raw.make == xmp.make)
    if raw.make and xmp.make and raw.make == xmp.make:
        reasons.append(f"make={raw.make}")
    elif raw.make and xmp.make:
        reasons.append(f"make mismatch raw={raw.make} xmp={xmp.make}")

    model_match = bool(raw.model and xmp.model and raw.model == xmp.model)
    if raw.model and xmp.model and raw.model == xmp.model:
        reasons.append(f"model={raw.model}")
    elif raw.model and xmp.model:
        reasons.append(f"model mismatch raw={raw.model} xmp={xmp.model}")

    raw_dt = parse_exif_datetime(raw.date_time_original or raw.create_date)
    xmp_dt = parse_exif_datetime(xmp.date_time_original or xmp.create_date)
    capture_exact = False
    capture_near = False
    capture_loose = False
    if raw_dt and xmp_dt:
        delta_seconds = abs(
            int((raw_dt.replace(tzinfo=None) - xmp_dt.replace(tzinfo=None)).total_seconds())
        )
        if delta_seconds == 0:
            capture_exact = True
            reasons.append("capture time exact")
        elif delta_seconds <= 5:
            capture_near = True
            reasons.append(f"capture time within {delta_seconds}s")
        elif delta_seconds <= 60:
            capture_loose = True
            reasons.append(f"capture time within {delta_seconds}s")
        else:
            reasons.append(f"capture time differs by {delta_seconds}s")
    else:
        reasons.append("capture time unavailable on one side")

    identity_match = preserved_match or stem_match
    metadata_support = make_match and model_match

    if identity_match and metadata_support and (capture_exact or capture_near):
        verdict = "MATCH"
    elif identity_match and metadata_support and capture_loose:
        verdict = "WEAK_MATCH"
    elif identity_match and (metadata_support or capture_exact or capture_near):
        verdict = "WEAK_MATCH"
    else:
        verdict = "CONFLICT"

    rank = (
        1 if preserved_match else 0,
        1 if stem_match else 0,
        1 if make_match else 0,
        1 if model_match else 0,
        2 if capture_exact else 1 if capture_near else 0,
    )
    return verdict, rank, reasons


def find_raw_xmp_candidates(
    raws: list[MetadataRecord], xmps: list[MetadataRecord]
) -> list[RawXmpMatchCandidate]:
    """Evaluate every RAW/XMP combination."""
    candidates: list[RawXmpMatchCandidate] = []
    for raw in raws:
        for xmp in xmps:
            verdict, rank, reasons = evaluate_raw_xmp_match(raw, xmp)
            candidates.append(
                RawXmpMatchCandidate(
                    raw=raw,
                    xmp=xmp,
                    verdict=verdict,
                    rank=rank,
                    reasons=reasons,
                )
            )
    return candidates


def raw_xmp_verdict_for(candidate: RawXmpMatchCandidate) -> str:
    """Return the deterministic RAW/XMP verdict."""
    return candidate.verdict


def has_identity_match(candidate: RawXmpMatchCandidate) -> bool:
    """Return whether a RAW/XMP candidate has direct filename identity evidence."""
    return any(
        reason.startswith("preserved raw filename=") or reason.startswith("matching stem=")
        for reason in candidate.reasons
    )


def sync_s3_prefix(bucket_uri: str, prefix: str, destination: Path) -> None:
    """Sync one S3 prefix into a local temporary directory."""
    source = f"{bucket_uri.rstrip('/')}/{prefix.lstrip('/')}"
    command = ["aws", "s3", "sync", source, str(destination), "--exclude", "*/"]
    subprocess.run(command, check=True, capture_output=True, text=True)


def gather_local_paths(folder: Path) -> tuple[list[Path], list[Path], list[Path], str]:
    """Collect local JPEG/XMP/RAW paths from one mixed workspace."""
    image_root = folder / "source_images"
    sidecar_root = folder / "sidecars"

    if image_root.is_dir() or sidecar_root.is_dir():
        if not image_root.is_dir():
            raise SystemExit(f"Missing source_images/ in checkpoint folder: {folder}")
        if not sidecar_root.is_dir():
            raise SystemExit(f"Missing sidecars/ in checkpoint folder: {folder}")
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
    else:
        mixed_files = [
            path
            for path in folder.iterdir()
            if path.is_file() and not path.name.startswith(".")
        ]
        image_files = mixed_files
        sidecar_files = mixed_files

    images = sorted(
        (path for path in image_files if path.suffix in IMAGE_EXTENSIONS),
        key=lambda path: path.name,
    )
    xmps = sorted(
        (path for path in sidecar_files if path.suffix.lower() == XMP_EXTENSION),
        key=lambda path: path.name,
    )
    raws = sorted(
        (path for path in image_files if path.suffix.lower() in RAW_EXTENSIONS),
        key=lambda path: path.name,
    )
    return images, xmps, raws, str(folder)


def gather_s3_paths(args: argparse.Namespace) -> tuple[list[Path], list[Path], list[Path], str]:
    """Download S3-backed checkpoint assets into a temporary local workspace."""
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
    raws = sorted(
        (path for path in raw_dir.iterdir() if path.is_file() and path.suffix.lower() in RAW_EXTENSIONS),
        key=lambda path: path.name,
    )
    source_label = (
        f"{args.bucket_uri.rstrip('/')}"
        f" [raw={args.raw_prefix}, jpeg={args.jpeg_prefix}, xmp={args.xmp_prefix}]"
    )
    return images, xmps, raws, source_label


def print_raw_xmp_report(raws: list[MetadataRecord], xmps: list[MetadataRecord]) -> None:
    """Print direct RAW/XMP verification results."""
    print("Verification mode: RAW + XMP (preferred)")
    print("Matching rules:")
    for index, rule in enumerate(RAW_XMP_RULES, start=1):
        print(f"  {index}. {rule}")
    print()

    candidates = find_raw_xmp_candidates(raws, xmps)
    best_by_raw: dict[Path, RawXmpMatchCandidate] = {}
    for candidate in candidates:
        if not has_identity_match(candidate):
            continue
        current = best_by_raw.get(candidate.raw.source_file)
        if current is None or candidate.rank > current.rank:
            best_by_raw[candidate.raw.source_file] = candidate

    matched_xmps: set[Path] = set()
    for raw in raws:
        if raw.source_file not in best_by_raw:
            continue
        candidate = best_by_raw[raw.source_file]
        matched_xmps.add(candidate.xmp.source_file)
        verdict = raw_xmp_verdict_for(candidate)
        print(f"[{verdict}] {raw.file_name}")
        print(f"  best xmp: {candidate.xmp.file_name}")
        print(f"  reasons: {'; '.join(candidate.reasons)}")
        print()

    unmatched_xmps = [xmp for xmp in xmps if xmp.source_file not in matched_xmps]
    if unmatched_xmps:
        print("Unmatched XMPs:")
        for xmp in unmatched_xmps:
            print(f"  - {xmp.file_name}")
        print()

    unmatched_raws = [raw for raw in raws if raw.source_file not in best_by_raw]
    if unmatched_raws:
        print("Unmatched RAWs:")
        for raw in unmatched_raws:
            print(f"  - {raw.file_name}")
        print()


def print_jpeg_xmp_report(images: list[MetadataRecord], xmps: list[MetadataRecord]) -> None:
    """Print fallback JPEG/XMP verification results."""
    print("Verification mode: JPEG + XMP (fallback)")
    print()

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


def print_report(
    source_label: str,
    raws: list[MetadataRecord],
    images: list[MetadataRecord],
    xmps: list[MetadataRecord],
) -> None:
    """Print a concise folder audit report."""
    print()
    print(f"Source: {source_label}")
    print(f"RAWs: {len(raws)}")
    print(f"JPEGs: {len(images)}")
    print(f"XMPs: {len(xmps)}")
    print()

    if not raws and not images and not xmps:
        print("No RAW, JPEG, or XMP assets found in this checkpoint.")
        return

    if not xmps:
        print("No XMP found.")
        if raws:
            print(
                "Interpretation: this looks like a raw-backed pre-identity "
                "checkpoint candidate (`01_pre_identity`)."
            )
            print(
                "Suggested handling: treat RAW metadata as authoritative for "
                "this stage and skip XMP pair verification."
            )
        else:
            print("Need at least one XMP to run sidecar verification.")
        return

    if raws:
        if images:
            print("JPEG companions found, but RAW + XMP takes precedence.")
            print()
        print_raw_xmp_report(raws, xmps)
        return

    if not images:
        print("Need at least one RAW or JPEG to run sidecar verification.")
        return

    print_jpeg_xmp_report(images, xmps)


def main() -> None:
    """Run pairing audit for one local or S3-backed Stage 1 workspace."""
    args = parse_args()
    if args.bucket_uri:
        image_paths, xmp_paths, raw_paths, source_label = gather_s3_paths(args)
    else:
        folder = Path(args.folder)
        if not folder.is_dir():
            raise SystemExit(f"Folder not found: {folder}")
        image_paths, xmp_paths, raw_paths, source_label = gather_local_paths(folder)

    raw_records = run_exiftool(raw_paths)
    image_records = run_exiftool(image_paths)
    xmp_records = run_exiftool(xmp_paths)
    print_report(source_label, raw_records, image_records, xmp_records)


if __name__ == "__main__":
    main()
