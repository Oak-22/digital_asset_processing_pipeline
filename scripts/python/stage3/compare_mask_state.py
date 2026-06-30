"""Compare Stage 3 pre/post Lightroom mask-state extracts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.python.common import read_json, write_json


DEFAULT_PRESEGMENTATION_EXTRACT = (
    "outputs/stage3/stage3_extracted_presegmentation_mask_state.json"
)
DEFAULT_POSTMASKING_EXTRACT = (
    "outputs/stage3/stage3_extracted_postmasking_no_local_adjustment_mask_state.json"
)
DEFAULT_OUTPUT = (
    "outputs/stage3/stage3_mask_state_postmasking_no_local_adjustment_comparison.json"
)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the Stage 3 mask-state comparison."""
    parser = argparse.ArgumentParser(
        description="Compare Stage 3 presegmentation and postmasking mask state."
    )
    parser.add_argument(
        "--presegmentation",
        default=DEFAULT_PRESEGMENTATION_EXTRACT,
        help="Presegmentation mask-state extract JSON.",
    )
    parser.add_argument(
        "--postmasking",
        default=DEFAULT_POSTMASKING_EXTRACT,
        help="Postmasking mask-state extract JSON.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="Destination JSON file for the Stage 3 mask-state comparison.",
    )
    return parser.parse_args()


def records_by_asset(payload: dict[str, object], path: str) -> dict[str, dict[str, object]]:
    """Index mask-state records by asset key and fail on duplicate keys."""
    records = payload.get("records")
    if not isinstance(records, list):
        raise SystemExit(f"Expected a records list in {path}")

    indexed: dict[str, dict[str, object]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise SystemExit(f"Expected object records in {path}")
        asset_key = record.get("asset_key")
        if not asset_key:
            raise SystemExit(f"Missing asset_key in {path}")
        asset_key = str(asset_key)
        if asset_key in indexed:
            raise SystemExit(f"Duplicate asset_key {asset_key!r} in {path}")
        indexed[asset_key] = record
    return indexed


def mask_signature(record: dict[str, object]) -> list[dict[str, object]]:
    """Return a compact, comparable mask-state signature for one asset."""
    signature = []
    for group in record.get("mask_groups", []):
        if not isinstance(group, dict):
            continue
        signature.append(
            {
                "correction_name": group.get("correction_name"),
                "group_geometry_status": group.get("group_geometry_status"),
                "mask_names": [
                    mask.get("mask_name")
                    for mask in group.get("masks", [])
                    if isinstance(mask, dict)
                ],
                "mask_geometry_statuses": [
                    mask.get("mask_geometry_status")
                    for mask in group.get("masks", [])
                    if isinstance(mask, dict)
                ],
                "non_neutral_local_adjustments": group.get(
                    "non_neutral_local_adjustments", {}
                ),
            }
        )
    return signature


def compare_asset(
    asset_key: str,
    pre_record: dict[str, object],
    post_record: dict[str, object],
) -> dict[str, object]:
    """Compare one asset's pre/post Stage 3 mask state."""
    pre_signature = mask_signature(pre_record)
    post_signature = mask_signature(post_record)
    return {
        "asset_key": asset_key,
        "changed": pre_signature != post_signature,
        "presegmentation": {
            "xmp_path": pre_record.get("xmp_path"),
            "xmp_sha256": pre_record.get("xmp_sha256"),
            "acr_path": pre_record.get("acr_path"),
            "acr_sha256": pre_record.get("acr_sha256"),
            "mask_group_count": pre_record.get("mask_group_count"),
            "mask_entry_count": pre_record.get("mask_entry_count"),
            "mask_signature": pre_signature,
        },
        "postmasking": {
            "xmp_path": post_record.get("xmp_path"),
            "xmp_sha256": post_record.get("xmp_sha256"),
            "acr_path": post_record.get("acr_path"),
            "acr_sha256": post_record.get("acr_sha256"),
            "mask_group_count": post_record.get("mask_group_count"),
            "mask_entry_count": post_record.get("mask_entry_count"),
            "mask_signature": post_signature,
        },
    }


def build_summary(records: list[dict[str, object]], missing: dict[str, list[str]]) -> dict[str, object]:
    """Build a Stage 3 mask-state comparison summary."""
    changed_records = [record for record in records if record["changed"]]
    post_records = [record["postmasking"] for record in records]
    return {
        "asset_count": len(records),
        "changed_asset_count": len(changed_records),
        "unchanged_asset_count": len(records) - len(changed_records),
        "missing_presegmentation_asset_count": len(missing["presegmentation"]),
        "missing_postmasking_asset_count": len(missing["postmasking"]),
        "postmasking_mask_group_count": sum(
            int(record.get("mask_group_count") or 0) for record in post_records
        ),
        "postmasking_mask_entry_count": sum(
            int(record.get("mask_entry_count") or 0) for record in post_records
        ),
    }


def build_comparison(args: argparse.Namespace) -> dict[str, object]:
    """Build the Stage 3 mask-state comparison payload."""
    pre_payload = read_json(args.presegmentation)
    post_payload = read_json(args.postmasking)
    pre_records = records_by_asset(pre_payload, args.presegmentation)
    post_records = records_by_asset(post_payload, args.postmasking)

    pre_keys = set(pre_records)
    post_keys = set(post_records)
    compared_keys = sorted(pre_keys & post_keys)
    missing = {
        "presegmentation": sorted(post_keys - pre_keys),
        "postmasking": sorted(pre_keys - post_keys),
    }
    records = [
        compare_asset(asset_key, pre_records[asset_key], post_records[asset_key])
        for asset_key in compared_keys
    ]
    status = (
        "complete"
        if not missing["presegmentation"] and not missing["postmasking"]
        else "complete_with_asset_mismatch"
    )
    return {
        "stage": "stage3_semantic_local_conditioning",
        "comparison_model": "presegmentation_vs_postmasking_no_local_adjustment",
        "status": status,
        "inputs": {
            "presegmentation": args.presegmentation,
            "postmasking": args.postmasking,
        },
        "notes": {
            "comparison_boundary": (
                "This artifact compares Stage 3 presegmentation Lightroom "
                "sidecars against postmasking sidecars created before any "
                "intentional masked local Develop adjustments."
            ),
            "observability_boundary": (
                "This separates mask creation/copying persistence from later "
                "masked local adjustment parameter changes."
            ),
        },
        "summary": build_summary(records, missing),
        "missing_assets": missing,
        "records": records,
    }


def main() -> None:
    """Generate the Stage 3 mask-state comparison artifact."""
    args = parse_args()
    output = build_comparison(args)
    write_json(args.output, output)
    print(
        f"Wrote {args.output} with "
        f"{output['summary']['asset_count']} compared Stage 3 assets."
    )


if __name__ == "__main__":
    main()
