"""Audit Stage 2 develop-parameter changes across frozen checkpoints."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.python.common import read_json, write_json


DEFAULT_PRECONDITIONING_EXTRACT = (
    "outputs/stage2/stage2_extracted_preconditioning_develop_settings.json"
)
DEFAULT_POSTCONDITIONING_EXTRACT = (
    "outputs/stage2/stage2_extracted_postconditioning_develop_settings.json"
)
DEFAULT_PRECONDITIONING_MANIFEST = (
    "outputs/stage2/stage2_preconditioning_checkpoint_manifest.json"
)
DEFAULT_POSTCONDITIONING_MANIFEST = (
    "outputs/stage2/stage2_postconditioning_checkpoint_manifest.json"
)
DEFAULT_OUTPUT = "outputs/stage2/stage2_develop_parameter_comparison.json"


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the Stage 2 parameter comparison."""
    parser = argparse.ArgumentParser(
        description=(
            "Compare frozen Stage 2 preconditioning and postconditioning "
            "develop-setting extracts."
        )
    )
    parser.add_argument(
        "--preconditioning",
        default=DEFAULT_PRECONDITIONING_EXTRACT,
        help="Preconditioning develop-setting extract JSON.",
    )
    parser.add_argument(
        "--postconditioning",
        default=DEFAULT_POSTCONDITIONING_EXTRACT,
        help="Postconditioning develop-setting extract JSON.",
    )
    parser.add_argument(
        "--preconditioning-checkpoint-manifest",
        default=DEFAULT_PRECONDITIONING_MANIFEST,
        help="Hash manifest for the frozen preconditioning checkpoint.",
    )
    parser.add_argument(
        "--postconditioning-checkpoint-manifest",
        default=DEFAULT_POSTCONDITIONING_MANIFEST,
        help="Hash manifest for the frozen postconditioning checkpoint.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="Destination JSON file for the Stage 2 parameter comparison.",
    )
    return parser.parse_args()


def records_by_asset(payload: dict[str, object], path: str) -> dict[str, dict[str, object]]:
    """Index extract records by asset key and fail on duplicate keys."""
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


def setting_values(record: dict[str, object]) -> dict[str, object]:
    """Return develop settings from a normalized extraction record."""
    settings = record.get("develop_settings", {})
    if not isinstance(settings, dict):
        return {}
    return {str(key): value for key, value in settings.items()}


def compare_asset(
    asset_key: str,
    pre_record: dict[str, object],
    post_record: dict[str, object],
) -> dict[str, object]:
    """Compare one asset's pre/post develop settings."""
    pre_settings = setting_values(pre_record)
    post_settings = setting_values(post_record)
    setting_names = sorted(set(pre_settings) | set(post_settings))

    changed_settings = [
        {
            "setting": setting_name,
            "before_value": pre_settings.get(setting_name),
            "after_value": post_settings.get(setting_name),
        }
        for setting_name in setting_names
        if pre_settings.get(setting_name) != post_settings.get(setting_name)
    ]

    return {
        "asset_key": asset_key,
        "changed": bool(changed_settings),
        "changed_setting_count": len(changed_settings),
        "changed_settings": changed_settings,
        "preconditioning": {
            "source_file": pre_record.get("source_file"),
            "input_model": pre_record.get("input_model"),
            "populated_develop_setting_count": pre_record.get(
                "populated_develop_setting_count"
            ),
            "populated_develop_settings": pre_record.get(
                "populated_develop_settings", []
            ),
        },
        "postconditioning": {
            "source_file": post_record.get("source_file"),
            "input_model": post_record.get("input_model"),
            "populated_develop_setting_count": post_record.get(
                "populated_develop_setting_count"
            ),
            "populated_develop_settings": post_record.get(
                "populated_develop_settings", []
            ),
        },
    }


def summarize(records: list[dict[str, object]], missing: dict[str, list[str]]) -> dict[str, object]:
    """Build an audit summary from per-asset comparison records."""
    changed_records = [record for record in records if record["changed"]]
    changed_settings = sorted(
        {
            str(setting["setting"])
            for record in records
            for setting in record.get("changed_settings", [])
            if isinstance(setting, dict) and setting.get("setting")
        }
    )
    change_coverage = {
        setting_name: sum(
            1
            for record in records
            for setting in record.get("changed_settings", [])
            if isinstance(setting, dict) and setting.get("setting") == setting_name
        )
        for setting_name in changed_settings
    }

    return {
        "asset_count": len(records),
        "changed_asset_count": len(changed_records),
        "unchanged_asset_count": len(records) - len(changed_records),
        "missing_preconditioning_asset_count": len(missing["preconditioning"]),
        "missing_postconditioning_asset_count": len(missing["postconditioning"]),
        "changed_develop_setting_count": len(changed_settings),
        "changed_develop_settings": changed_settings,
        "changed_develop_setting_coverage": change_coverage,
    }


def build_comparison(args: argparse.Namespace) -> dict[str, object]:
    """Build the Stage 2 pre/post develop-parameter comparison payload."""
    pre_payload = read_json(args.preconditioning)
    post_payload = read_json(args.postconditioning)
    pre_records = records_by_asset(pre_payload, args.preconditioning)
    post_records = records_by_asset(post_payload, args.postconditioning)

    pre_keys = set(pre_records)
    post_keys = set(post_records)
    compared_keys = sorted(pre_keys & post_keys)
    missing = {
        "preconditioning": sorted(post_keys - pre_keys),
        "postconditioning": sorted(pre_keys - post_keys),
    }
    records = [
        compare_asset(asset_key, pre_records[asset_key], post_records[asset_key])
        for asset_key in compared_keys
    ]

    status = (
        "complete"
        if not missing["preconditioning"] and not missing["postconditioning"]
        else "complete_with_asset_mismatch"
    )
    return {
        "stage": "stage2_baseline_conditioning",
        "comparison_model": "preconditioning_vs_postconditioning_develop_settings",
        "status": status,
        "inputs": {
            "preconditioning_checkpoint_manifest": args.preconditioning_checkpoint_manifest,
            "postconditioning_checkpoint_manifest": args.postconditioning_checkpoint_manifest,
            "preconditioning": args.preconditioning,
            "postconditioning": args.postconditioning,
        },
        "notes": {
            "comparison_boundary": (
                "This artifact compares frozen preconditioning XMP settings "
                "against frozen postconditioning XMP settings after Lightroom "
                "Develop edits are applied."
            ),
            "missing_values": (
                "Null before/after values mean the develop setting was absent "
                "from that checkpoint extract."
            ),
        },
        "summary": summarize(records, missing),
        "missing_assets": missing,
        "records": records,
    }


def main() -> None:
    """Generate the Stage 2 develop-parameter comparison artifact."""
    args = parse_args()
    output = build_comparison(args)
    write_json(args.output, output)
    print(
        f"Wrote {args.output} with "
        f"{output['summary']['asset_count']} compared Stage 2 assets."
    )


if __name__ == "__main__":
    main()
