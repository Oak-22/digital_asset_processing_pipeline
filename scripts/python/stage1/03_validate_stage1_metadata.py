"""Stage 1 step 03: validate metadata expectations against extracted records."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.python.common import read_json, write_json


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
    "creator_country",
    "creator_work_email",
    "creator_work_url",
)
DOMAIN_FIELDS = ("headline", "description", "category")
KEYWORD_FIELDS = ("subject", "hierarchical_subject")


@dataclass
class Finding:
    """One validation finding emitted by the Stage 1 assertion gate."""

    severity: str
    code: str
    message: str
    asset_key: str | None = None
    metadata_state: str | None = None

    def as_dict(self) -> dict[str, object]:
        """Serialize the finding into a stable JSON shape."""
        payload: dict[str, object] = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.asset_key is not None:
            payload["asset_key"] = self.asset_key
        if self.metadata_state is not None:
            payload["metadata_state"] = self.metadata_state
        return payload


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for validating extracted Stage 1 metadata."""
    parser = argparse.ArgumentParser(
        description="Validate Stage 1 assertions against extracted metadata JSON."
    )
    parser.add_argument(
        "--input",
        default="outputs/stage1/extracted_stage1_metadata.json",
        help="Extracted Stage 1 metadata JSON produced by step 02.",
    )
    parser.add_argument(
        "--output",
        default="outputs/stage1/stage1_metadata_validation_report.json",
        help="Destination JSON validation report.",
    )
    return parser.parse_args()


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


def require(
    findings: list[Finding],
    condition: bool,
    code: str,
    message: str,
    *,
    asset_key: str | None = None,
    metadata_state: str | None = None,
) -> None:
    """Append an error finding when an assertion fails."""
    if condition:
        return
    findings.append(
        Finding(
            severity="error",
            code=code,
            message=message,
            asset_key=asset_key,
            metadata_state=metadata_state,
        )
    )


def validate_payload(payload: dict[str, object]) -> list[Finding]:
    """Validate top-level report structure and every Stage 1 asset bundle."""
    findings: list[Finding] = []
    groups = payload.get("metadata_state_groups")
    require(
        findings,
        isinstance(groups, list),
        "missing_stage_groups",
        "Expected metadata_state_groups to be a list.",
    )
    if not isinstance(groups, list):
        return findings

    seen_stages: list[str] = []
    total_assets = 0
    total_records = 0
    seen_source_files: set[str] = set()
    seen_stage_asset_keys: set[tuple[str, str]] = set()

    for group in groups:
        if not isinstance(group, dict):
            findings.append(
                Finding(
                    severity="error",
                    code="invalid_stage_group",
                    message="Each metadata_state_group entry must be an object.",
                )
            )
            continue

        stage = str(group.get("metadata_state", ""))
        assets = group.get("assets")
        require(
            findings,
            stage in STAGE_ORDER,
            "unknown_stage",
            f"Unknown Stage 1 metadata_state: {stage}",
            metadata_state=stage,
        )
        require(
            findings,
            isinstance(assets, list),
            "invalid_assets",
            "Stage group assets must be a list.",
            metadata_state=stage,
        )
        if stage in STAGE_ORDER:
            seen_stages.append(stage)
        if not isinstance(assets, list):
            continue

        total_assets += len(assets)
        require(
            findings,
            group.get("asset_count") == len(assets),
            "asset_count_mismatch",
            f"asset_count={group.get('asset_count')} does not match {len(assets)} assets.",
            metadata_state=stage,
        )
        for asset in assets:
            if isinstance(asset, dict):
                total_records += len(asset.get("records", []))
                validate_asset(
                    findings,
                    stage,
                    asset,
                    seen_source_files,
                    seen_stage_asset_keys,
                )
            else:
                findings.append(
                    Finding(
                        severity="error",
                        code="invalid_asset",
                        message="Each asset entry must be an object.",
                        metadata_state=stage,
                    )
                )

    expected_order = [stage for stage in STAGE_ORDER if stage in seen_stages]
    require(
        findings,
        seen_stages == expected_order,
        "stage_order_mismatch",
        f"Stage groups are ordered as {seen_stages}, expected {expected_order}.",
    )
    require(
        findings,
        payload.get("asset_count") == total_assets,
        "total_asset_count_mismatch",
        f"asset_count={payload.get('asset_count')} does not match {total_assets} grouped assets.",
    )
    require(
        findings,
        payload.get("record_count") == total_records,
        "total_record_count_mismatch",
        f"record_count={payload.get('record_count')} does not match {total_records} grouped records.",
    )
    validate_stage_counts(findings, payload, groups)
    return findings


def validate_stage_counts(
    findings: list[Finding],
    payload: dict[str, object],
    groups: list[object],
) -> None:
    """Validate metadata_state_counts against the grouped asset counts."""
    counts = payload.get("metadata_state_counts")
    require(
        findings,
        isinstance(counts, dict),
        "invalid_stage_counts",
        "metadata_state_counts must be an object.",
    )
    if not isinstance(counts, dict):
        return

    grouped_counts = {
        str(group.get("metadata_state")): len(group.get("assets", []))
        for group in groups
        if isinstance(group, dict) and isinstance(group.get("assets"), list)
    }
    for stage in STAGE_ORDER:
        require(
            findings,
            counts.get(stage, 0) == grouped_counts.get(stage, 0),
            "stage_count_mismatch",
            (
                f"metadata_state_counts[{stage}]={counts.get(stage, 0)} "
                f"does not match {grouped_counts.get(stage, 0)} grouped assets."
            ),
            metadata_state=stage,
        )


def validate_asset(
    findings: list[Finding],
    stage: str,
    asset: dict[str, object],
    seen_source_files: set[str],
    seen_stage_asset_keys: set[tuple[str, str]],
) -> None:
    """Validate one grouped Stage 1 asset bundle."""
    asset_key = str(asset.get("asset_key", ""))
    records = asset.get("records")
    source_summary = asset.get("source_summary")

    require(
        findings,
        bool(asset_key),
        "missing_asset_key",
        "Asset is missing asset_key.",
        metadata_state=stage,
    )
    if asset_key:
        key = (stage, asset_key)
        require(
            findings,
            key not in seen_stage_asset_keys,
            "duplicate_stage_asset",
            f"Asset key {asset_key} appears more than once in {stage}.",
            asset_key=asset_key,
            metadata_state=stage,
        )
        seen_stage_asset_keys.add(key)

    require(
        findings,
        isinstance(records, list) and bool(records),
        "missing_records",
        "Asset must contain at least one record.",
        asset_key=asset_key,
        metadata_state=stage,
    )
    require(
        findings,
        isinstance(source_summary, dict),
        "invalid_source_summary",
        "Asset source_summary must be an object.",
        asset_key=asset_key,
        metadata_state=stage,
    )
    if not isinstance(records, list):
        return

    raw_records = records_by_source(records, "raw")
    xmp_records = records_by_source(records, "xmp")
    validate_source_summary(findings, stage, asset_key, source_summary, raw_records, xmp_records)

    require(
        findings,
        len(raw_records) == 1,
        "raw_record_count",
        f"Expected exactly one RAW record, found {len(raw_records)}.",
        asset_key=asset_key,
        metadata_state=stage,
    )
    if stage == STAGE_PRE_IDENTITY:
        require(
            findings,
            len(xmp_records) == 0,
            "pre_identity_has_xmp",
            "Pre-identity assets should not have XMP sidecars.",
            asset_key=asset_key,
            metadata_state=stage,
        )
    else:
        require(
            findings,
            len(xmp_records) == 1,
            "xmp_record_count",
            f"Expected exactly one XMP record, found {len(xmp_records)}.",
            asset_key=asset_key,
            metadata_state=stage,
        )

    for record in records:
        if not isinstance(record, dict):
            findings.append(
                Finding(
                    severity="error",
                    code="invalid_record",
                    message="Each record must be an object.",
                    asset_key=asset_key,
                    metadata_state=stage,
                )
            )
            continue
        validate_record_identity(findings, stage, asset_key, record, seen_source_files)

    if raw_records and xmp_records:
        validate_raw_xmp_consistency(findings, stage, asset_key, raw_records[0], xmp_records[0])
    for xmp_record in xmp_records:
        validate_stage_metadata(findings, stage, asset_key, xmp_record)


def records_by_source(records: list[object], source: str) -> list[dict[str, object]]:
    """Return object records that match a given record_source value."""
    return [
        record
        for record in records
        if isinstance(record, dict) and record.get("record_source") == source
    ]


def validate_source_summary(
    findings: list[Finding],
    stage: str,
    asset_key: str,
    source_summary: object,
    raw_records: list[dict[str, object]],
    xmp_records: list[dict[str, object]],
) -> None:
    """Validate source_summary counts against records."""
    if not isinstance(source_summary, dict):
        return
    expected = {"raw": len(raw_records)}
    if xmp_records:
        expected["xmp"] = len(xmp_records)
    require(
        findings,
        source_summary == expected,
        "source_summary_mismatch",
        f"source_summary={source_summary} does not match records={expected}.",
        asset_key=asset_key,
        metadata_state=stage,
    )


def validate_record_identity(
    findings: list[Finding],
    stage: str,
    asset_key: str,
    record: dict[str, object],
    seen_source_files: set[str],
) -> None:
    """Validate record-level identity fields shared by RAW and XMP records."""
    record_source = record.get("record_source")
    source_file = str(record.get("source_file", ""))
    require(
        findings,
        record_source in {"raw", "xmp"},
        "unknown_record_source",
        f"Unknown record_source: {record_source}",
        asset_key=asset_key,
        metadata_state=stage,
    )
    require(
        findings,
        record.get("metadata_state") == stage,
        "record_stage_mismatch",
        f"Record metadata_state={record.get('metadata_state')} does not match group {stage}.",
        asset_key=asset_key,
        metadata_state=stage,
    )
    require(
        findings,
        record.get("asset_key") == asset_key,
        "record_asset_key_mismatch",
        f"Record asset_key={record.get('asset_key')} does not match asset {asset_key}.",
        asset_key=asset_key,
        metadata_state=stage,
    )
    require(
        findings,
        bool(source_file),
        "missing_source_file",
        "Record is missing source_file.",
        asset_key=asset_key,
        metadata_state=stage,
    )
    if source_file:
        require(
            findings,
            source_file not in seen_source_files,
            "duplicate_source_file",
            f"source_file appears more than once: {source_file}",
            asset_key=asset_key,
            metadata_state=stage,
        )
        seen_source_files.add(source_file)


def validate_raw_xmp_consistency(
    findings: list[Finding],
    stage: str,
    asset_key: str,
    raw_record: dict[str, object],
    xmp_record: dict[str, object],
) -> None:
    """Validate RAW/XMP fields that should agree after pair verification."""
    raw_file_name = str(raw_record.get("raw_file_name", ""))
    original_raw_filename = str(xmp_record.get("original_raw_filename", ""))
    require(
        findings,
        Path(original_raw_filename).stem == asset_key,
        "xmp_preserved_filename_mismatch",
        (
            f"original_raw_filename={original_raw_filename} does not preserve "
            f"asset_key={asset_key}."
        ),
        asset_key=asset_key,
        metadata_state=stage,
    )
    require(
        findings,
        not raw_file_name or Path(raw_file_name).stem == asset_key,
        "raw_filename_mismatch",
        f"raw_file_name={raw_file_name} does not match asset_key={asset_key}.",
        asset_key=asset_key,
        metadata_state=stage,
    )
    for raw_field, xmp_field in (
        ("camera_make", "camera_make"),
        ("camera_model", "camera_model"),
    ):
        require(
            findings,
            raw_record.get(raw_field) == xmp_record.get(xmp_field),
            "raw_xmp_metadata_mismatch",
            (
                f"RAW {raw_field}={raw_record.get(raw_field)} does not match "
                f"XMP {xmp_field}={xmp_record.get(xmp_field)}."
            ),
            asset_key=asset_key,
            metadata_state=stage,
        )
    require(
        findings,
        comparable_capture_time(raw_record.get("capture_time"))
        == comparable_capture_time(xmp_record.get("capture_time")),
        "raw_xmp_metadata_mismatch",
        (
            f"RAW capture_time={raw_record.get('capture_time')} does not match "
            f"XMP capture_time={xmp_record.get('capture_time')}."
        ),
        asset_key=asset_key,
        metadata_state=stage,
    )


def comparable_capture_time(value: object) -> str | None:
    """Normalize exiftool capture times for RAW/XMP comparison."""
    if not value:
        return None
    return str(value)[:19]


def validate_stage_metadata(
    findings: list[Finding],
    stage: str,
    asset_key: str,
    xmp_record: dict[str, object],
) -> None:
    """Validate Stage 1 metadata-field expectations for one XMP record."""
    if stage in {
        STAGE_POST_IDENTITY,
        STAGE_IDENTITY_DOMAIN,
        STAGE_IDENTITY_DOMAIN_KEYWORDS,
    }:
        require_fields(findings, stage, asset_key, xmp_record, IDENTITY_FIELDS)

    if stage == STAGE_POST_IDENTITY:
        forbid_fields(findings, stage, asset_key, xmp_record, DOMAIN_FIELDS + KEYWORD_FIELDS)
    elif stage == STAGE_IDENTITY_DOMAIN:
        require_fields(findings, stage, asset_key, xmp_record, DOMAIN_FIELDS)
        forbid_fields(findings, stage, asset_key, xmp_record, KEYWORD_FIELDS)
    elif stage == STAGE_IDENTITY_DOMAIN_KEYWORDS:
        require_fields(findings, stage, asset_key, xmp_record, DOMAIN_FIELDS + KEYWORD_FIELDS)


def require_fields(
    findings: list[Finding],
    stage: str,
    asset_key: str,
    record: dict[str, object],
    fields: tuple[str, ...],
) -> None:
    """Require every listed metadata field to contain a meaningful value."""
    for field in fields:
        require(
            findings,
            has_value(record.get(field)),
            "missing_required_metadata",
            f"Required metadata field is empty: {field}",
            asset_key=asset_key,
            metadata_state=stage,
        )


def forbid_fields(
    findings: list[Finding],
    stage: str,
    asset_key: str,
    record: dict[str, object],
    fields: tuple[str, ...],
) -> None:
    """Require every listed metadata field to be absent or empty."""
    for field in fields:
        require(
            findings,
            not has_value(record.get(field)),
            "unexpected_metadata",
            f"Metadata field should not be populated at this stage: {field}",
            asset_key=asset_key,
            metadata_state=stage,
        )


def build_report(input_path: Path, findings: list[Finding]) -> dict[str, object]:
    """Build the JSON validation report."""
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]
    return {
        "input": str(input_path),
        "status": "pass" if not errors else "fail",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "findings": [finding.as_dict() for finding in findings],
    }


def print_summary(report: dict[str, object], output_path: Path) -> None:
    """Print a concise terminal validation summary."""
    print(f"Stage 1 metadata validation: {str(report['status']).upper()}")
    print(f"Errors: {report['error_count']}")
    print(f"Warnings: {report['warning_count']}")
    print(f"Wrote: {output_path}")


def main() -> None:
    """Run Stage 1 validation assertions against the extracted JSON artifact."""
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    payload = read_json(input_path)
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected top-level JSON object: {input_path}")

    findings = validate_payload(payload)
    report = build_report(input_path, findings)
    write_json(output_path, report)
    print_summary(report, output_path)
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
