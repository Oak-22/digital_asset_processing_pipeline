"""Stage 3: extract Lightroom mask state from XMP sidecars."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.python.common import write_json


DEFAULT_INPUT_ROOT = (
    "data/stage3/spikes/proof_of_capability_mask_sidecar_parsing/postsegmentation"
)
DEFAULT_REFERENCE_ROOT = (
    "data/stage3/spikes/proof_of_capability_mask_sidecar_parsing/presegmentation"
)
DEFAULT_OUTPUT = "outputs/stage3/stage3_mask_state_spike_report.json"
DEFAULT_INPUT_MODEL = "stage3_postsegmentation_spike"
DEFAULT_REFERENCE_MODEL = "stage2_postconditioning_state_as_stage3_presegmentation"
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
CRS_NS = "http://ns.adobe.com/camera-raw-settings/1.0/"
NS = {
    "rdf": RDF_NS,
    "crs": CRS_NS,
}
CRS = f"{{{CRS_NS}}}"


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for Stage 3 mask-state extraction."""
    parser = argparse.ArgumentParser(
        description="Extract Lightroom mask group state from XMP sidecars."
    )
    parser.add_argument(
        "--input-root",
        default=DEFAULT_INPUT_ROOT,
        help="Directory containing postsegmentation Lightroom sidecars.",
    )
    parser.add_argument(
        "--reference-root",
        default=DEFAULT_REFERENCE_ROOT,
        help="Optional directory containing presegmentation XMP sidecars.",
    )
    parser.add_argument(
        "--input-model",
        default=DEFAULT_INPUT_MODEL,
        help="Label describing the input sidecar state.",
    )
    parser.add_argument(
        "--reference-model",
        default=DEFAULT_REFERENCE_MODEL,
        help="Label describing the reference sidecar state.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="Destination JSON file for extracted Stage 3 mask state.",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest for one file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def xmp_paths(folder: Path) -> list[Path]:
    """Return XMP sidecars in a flat folder."""
    if not folder.is_dir():
        raise SystemExit(f"Input root not found: {folder}")
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() == ".xmp"
    )


def strip_namespace(name: str) -> str:
    """Remove an XML namespace from an ElementTree attribute name."""
    return name.split("}", 1)[1] if name.startswith("{") else name


def crs_attrs(element: ET.Element) -> dict[str, str]:
    """Return Camera Raw settings attributes without XML namespaces."""
    return {
        strip_namespace(key): value
        for key, value in element.attrib.items()
        if key.startswith(CRS)
    }


def meaningful_local_adjustments(attrs: dict[str, str]) -> dict[str, str]:
    """Return local adjustment values that are not neutral zero values."""
    neutral_values = {"0", "0.0", "0.00", "+0", "+0.0"}
    return {
        key: value
        for key, value in attrs.items()
        if key.startswith("Local") and value not in neutral_values
    }


def child_sequence_values(element: ET.Element, child_name: str) -> list[str]:
    """Return rdf:li text values from a named CRS child sequence."""
    child = element.find(f"./crs:{child_name}", NS)
    if child is None:
        return []
    return [
        str(item.text)
        for item in child.findall(".//rdf:li", NS)
        if item.text is not None
    ]


def local_point_color_state(correction: ET.Element) -> dict[str, object]:
    """Return local point-color state persisted inside one correction group."""
    point_colors = child_sequence_values(correction, "LocalPointColors")
    color_variance = child_sequence_values(correction, "LocalColorVariance")
    source_fields = []
    if point_colors:
        source_fields.append("crs:LocalPointColors")
    if color_variance:
        source_fields.append("crs:LocalColorVariance")
    return {
        "crs_local_point_colors": point_colors,
        "crs_local_color_variance": color_variance,
        "source_fields": source_fields,
    }


def geometry_integrity_flags(mask_attrs: dict[str, str]) -> list[str]:
    """Return missing geometry identity fields for one mask entry."""
    required_fields = {
        "MaskDigest": "missing_mask_digest",
        "Origin": "missing_origin",
        "FullMaskSize": "missing_full_mask_size",
    }
    return [
        flag
        for field, flag in required_fields.items()
        if not mask_attrs.get(field)
    ]


def mask_geometry_status(mask_attrs: dict[str, str]) -> str:
    """Classify whether one mask entry has materialized geometry."""
    return "unresolved" if geometry_integrity_flags(mask_attrs) else "resolved"


def group_geometry_status(masks: list[dict[str, object]]) -> str:
    """Classify whether a correction group's child masks materialized."""
    statuses = {
        str(mask.get("mask_geometry_status"))
        for mask in masks
        if mask.get("mask_geometry_status")
    }
    if not statuses:
        return "unresolved"
    if statuses == {"resolved"}:
        return "resolved"
    if statuses == {"unresolved"}:
        return "unresolved"
    return "partial"


def extract_mask_groups(xmp_path: Path) -> list[dict[str, object]]:
    """Extract Lightroom mask correction groups from one XMP file."""
    root = ET.parse(xmp_path).getroot()
    corrections = root.findall(
        ".//crs:MaskGroupBasedCorrections/rdf:Seq/rdf:li/rdf:Description",
        NS,
    )
    groups = []
    for index, correction in enumerate(corrections, start=1):
        correction_attrs = crs_attrs(correction)
        masks = []
        for mask in correction.findall("./crs:CorrectionMasks/rdf:Seq/rdf:li", NS):
            mask_attrs = crs_attrs(mask)
            integrity_flags = geometry_integrity_flags(mask_attrs)
            masks.append(
                {
                    "mask_name": mask_attrs.get("MaskName"),
                    "mask_active": mask_attrs.get("MaskActive"),
                    "mask_inverted": mask_attrs.get("MaskInverted"),
                    "mask_geometry_status": (
                        "unresolved" if integrity_flags else "resolved"
                    ),
                    "geometry_integrity_flags": integrity_flags,
                    "mask_sync_id": mask_attrs.get("MaskSyncID"),
                    "mask_digest": mask_attrs.get("MaskDigest"),
                    "mask_subcategory_id": mask_attrs.get("MaskSubCategoryID"),
                    "reference_point": mask_attrs.get("ReferencePoint"),
                    "origin": mask_attrs.get("Origin"),
                    "full_mask_size": mask_attrs.get("FullMaskSize"),
                    "model_version": mask_attrs.get("ModelVersion"),
                    "input_digest": mask_attrs.get("InputDigest"),
                    "local_input_digest": mask_attrs.get("LocalInputDigest"),
                }
            )

        groups.append(
            {
                "correction_index": index,
                "correction_name": correction_attrs.get("CorrectionName"),
                "correction_active": correction_attrs.get("CorrectionActive"),
                "correction_sync_id": correction_attrs.get("CorrectionSyncID"),
                "group_geometry_status": group_geometry_status(masks),
                "local_adjustments": {
                    key: value
                    for key, value in correction_attrs.items()
                    if key.startswith("Local")
                },
                "local_point_color_state": local_point_color_state(correction),
                "non_neutral_local_adjustments": meaningful_local_adjustments(
                    correction_attrs
                ),
                "mask_count": len(masks),
                "masks": masks,
            }
        )
    return groups


def build_record(
    xmp_path: Path,
    input_root: Path,
    input_model: str,
    reference_root: Path | None,
    reference_model: str,
) -> dict[str, object]:
    """Build one Stage 3 mask-state record from an XMP sidecar."""
    asset_key = xmp_path.stem
    acr_path = xmp_path.with_suffix(".acr")
    reference_xmp_path = reference_root / xmp_path.name if reference_root else None
    reference_groups = (
        extract_mask_groups(reference_xmp_path)
        if reference_xmp_path and reference_xmp_path.exists()
        else []
    )
    mask_groups = extract_mask_groups(xmp_path)
    mask_names = [
        str(mask["mask_name"])
        for group in mask_groups
        for mask in group["masks"]
        if mask.get("mask_name")
    ]

    return {
        "asset_key": asset_key,
        "input_model": input_model,
        "input_root": str(input_root),
        "xmp_path": str(xmp_path),
        "xmp_sha256": sha256_file(xmp_path),
        "acr_path": str(acr_path) if acr_path.exists() else None,
        "acr_sha256": sha256_file(acr_path) if acr_path.exists() else None,
        "reference": {
            "reference_model": reference_model,
            "reference_xmp_path": (
                str(reference_xmp_path)
                if reference_xmp_path and reference_xmp_path.exists()
                else None
            ),
            "reference_xmp_sha256": (
                sha256_file(reference_xmp_path)
                if reference_xmp_path and reference_xmp_path.exists()
                else None
            ),
            "reference_mask_group_count": len(reference_groups),
            "reference_mask_entry_count": sum(
                int(group["mask_count"]) for group in reference_groups
            ),
        },
        "mask_group_count": len(mask_groups),
        "mask_entry_count": sum(int(group["mask_count"]) for group in mask_groups),
        "mask_names": mask_names,
        "mask_groups": mask_groups,
    }


def build_summary(records: list[dict[str, object]]) -> dict[str, object]:
    """Summarize extracted Stage 3 mask-state records."""
    mask_names = sorted(
        {
            str(mask_name)
            for record in records
            for mask_name in record.get("mask_names", [])
        }
    )
    mask_entries = [
        mask
        for record in records
        for group in record.get("mask_groups", [])
        for mask in group.get("masks", [])
        if isinstance(mask, dict)
    ]
    mask_groups = [
        group
        for record in records
        for group in record.get("mask_groups", [])
        if isinstance(group, dict)
    ]
    local_point_color_group_count = sum(
        1
        for group in mask_groups
        if dict(group.get("local_point_color_state", {})).get(
            "crs_local_point_colors"
        )
        or dict(group.get("local_point_color_state", {})).get(
            "crs_local_color_variance"
        )
    )
    mask_geometry_status_counts = {
        status: sum(
            1 for mask in mask_entries if mask.get("mask_geometry_status") == status
        )
        for status in ("resolved", "unresolved")
    }
    group_geometry_status_counts = {
        status: sum(
            1
            for group in mask_groups
            if group.get("group_geometry_status") == status
        )
        for status in ("resolved", "partial", "unresolved")
    }
    geometry_integrity_flag_counts = {
        flag: sum(
            1
            for mask in mask_entries
            for mask_flag in mask.get("geometry_integrity_flags", [])
            if mask_flag == flag
        )
        for flag in sorted(
            {
                str(flag)
                for mask in mask_entries
                for flag in mask.get("geometry_integrity_flags", [])
            }
        )
    }
    return {
        "asset_count": len(records),
        "assets_with_mask_groups": sum(
            1 for record in records if int(record["mask_group_count"]) > 0
        ),
        "mask_group_count": sum(int(record["mask_group_count"]) for record in records),
        "mask_entry_count": sum(int(record["mask_entry_count"]) for record in records),
        "acr_sidecar_count": sum(1 for record in records if record["acr_path"]),
        "mask_geometry_status_counts": mask_geometry_status_counts,
        "group_geometry_status_counts": group_geometry_status_counts,
        "geometry_integrity_flag_counts": geometry_integrity_flag_counts,
        "local_point_color_group_count": local_point_color_group_count,
        "mask_names": mask_names,
    }


def main() -> None:
    """Extract Stage 3 Lightroom mask-state evidence."""
    args = parse_args()
    input_root = Path(args.input_root)
    reference_root = Path(args.reference_root) if args.reference_root else None
    records = [
        build_record(
            xmp_path,
            input_root,
            args.input_model,
            reference_root,
            args.reference_model,
        )
        for xmp_path in xmp_paths(input_root)
    ]
    output = {
        "stage": "stage3_semantic_local_conditioning",
        "spike_name": "proof_of_capability_mask_sidecar_parsing",
        "status": "complete",
        "input_model": args.input_model,
        "input_root": str(input_root),
        "reference_model": args.reference_model,
        "reference_root": str(reference_root) if reference_root else None,
        "notes": {
            "scope": (
                "One-image proof-of-capability spike for parsing Lightroom "
                "mask group state after GUI-assisted AI segmentation."
            ),
            "sidecar_boundary": (
                "The XMP records mask group metadata, semantic mask names, "
                "local adjustment values, digests, and model versions. The "
                "ACR sidecar is preserved as heavier binary Lightroom mask "
                "state referenced by the XMP."
            ),
            "mask_geometry_status": (
                "A resolved mask entry has mask digest, origin, and "
                "full-mask-size metadata. An unresolved mask keeps the "
                "semantic mask entry but lacks one or more geometry/payload "
                "identity fields. A partially resolved group has mixed "
                "resolved and unresolved child masks."
            ),
            "local_point_color_state": (
                "Local point-color state records CRS LocalPointColors and "
                "LocalColorVariance child sequences attached to a mask "
                "correction group."
            ),
        },
        "summary": build_summary(records),
        "records": records,
    }
    write_json(args.output, output)
    print(
        f"Wrote {args.output} with "
        f"{output['summary']['mask_group_count']} mask groups and "
        f"{output['summary']['mask_entry_count']} mask entries."
    )


if __name__ == "__main__":
    main()
