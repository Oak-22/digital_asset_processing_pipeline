"""Stage 2 step 01: extract Lightroom develop settings from XMP sidecars."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.python.common import write_json


DEFAULT_INPUT_ROOT = "data/stage2/reference_state/xmp_preconditioning"
DEFAULT_OUTPUT = "outputs/stage2/stage2_extracted_preconditioning_develop_settings.json"
INPUT_MODEL = "stage2_preconditioning_reference"
DEVELOP_FIELDS = [
    "-FileName",
    "-Directory",
    "-PreservedFileName",
    "-DocumentID",
    "-OriginalDocumentID",
    "-InstanceID",
    "-MetadataDate",
    "-CreateDate",
    "-DateTimeOriginal",
    "-Make",
    "-Model",
    "-XMP-crd:CameraProfile",
    "-XMP-crd:LookName",
    "-XMP-crs:RawFileName",
    "-XMP-crs:ProcessVersion",
    "-XMP-crs:WhiteBalance",
    "-XMP-crs:Temperature",
    "-XMP-crs:Tint",
    "-XMP-crs:Exposure2012",
    "-XMP-crs:Contrast2012",
    "-XMP-crs:Highlights2012",
    "-XMP-crs:Shadows2012",
    "-XMP-crs:Whites2012",
    "-XMP-crs:Blacks2012",
    "-XMP-crs:Texture",
    "-XMP-crs:Clarity2012",
    "-XMP-crs:Dehaze",
    "-XMP-crs:Vibrance",
    "-XMP-crs:Saturation",
    "-XMP-crs:ParametricShadows",
    "-XMP-crs:ParametricDarks",
    "-XMP-crs:ParametricLights",
    "-XMP-crs:ParametricHighlights",
    "-XMP-crs:Sharpness",
    "-XMP-crs:LuminanceSmoothing",
    "-XMP-crs:ColorNoiseReduction",
    "-XMP-crs:LensProfileEnable",
    "-XMP-crs:LensManualDistortionAmount",
    "-XMP-crs:PerspectiveUpright",
    "-XMP-crs:UprightVersion",
    "-XMP-crs:UprightCenterMode",
    "-XMP-crs:PerspectiveVertical",
    "-XMP-crs:PerspectiveHorizontal",
    "-XMP-crs:PerspectiveRotate",
    "-XMP-crs:PerspectiveScale",
    "-XMP-crs:PerspectiveAspect",
    "-XMP-crs:PerspectiveX",
    "-XMP-crs:PerspectiveY",
    "-XMP-crs:CropTop",
    "-XMP-crs:CropLeft",
    "-XMP-crs:CropBottom",
    "-XMP-crs:CropRight",
    "-XMP-crs:CropAngle",
    "-XMP-crs:CropConstrainToWarp",
    "-XMP-crs:CropConstrainToUnitSquare",
]
DEVELOP_SETTING_KEYS = [
    "camera_profile",
    "look_name",
    "process_version",
    "white_balance",
    "temperature",
    "tint",
    "exposure_2012",
    "contrast_2012",
    "highlights_2012",
    "shadows_2012",
    "whites_2012",
    "blacks_2012",
    "texture",
    "clarity_2012",
    "dehaze",
    "vibrance",
    "saturation",
    "parametric_shadows",
    "parametric_darks",
    "parametric_lights",
    "parametric_highlights",
    "sharpness",
    "luminance_smoothing",
    "color_noise_reduction",
    "lens_profile_enable",
    "lens_manual_distortion_amount",
    "perspective_upright",
    "upright_version",
    "upright_center_mode",
    "perspective_vertical",
    "perspective_horizontal",
    "perspective_rotate",
    "perspective_scale",
    "perspective_aspect",
    "perspective_x",
    "perspective_y",
    "crop_top",
    "crop_left",
    "crop_bottom",
    "crop_right",
    "crop_angle",
    "crop_constrain_to_warp",
    "crop_constrain_to_unit_square",
]
TAG_TO_KEY = {
    "XMP-crd:CameraProfile": "camera_profile",
    "XMP-crd:LookName": "look_name",
    "XMP-crs:ProcessVersion": "process_version",
    "XMP-crs:WhiteBalance": "white_balance",
    "XMP-crs:Temperature": "temperature",
    "XMP-crs:Tint": "tint",
    "XMP-crs:Exposure2012": "exposure_2012",
    "XMP-crs:Contrast2012": "contrast_2012",
    "XMP-crs:Highlights2012": "highlights_2012",
    "XMP-crs:Shadows2012": "shadows_2012",
    "XMP-crs:Whites2012": "whites_2012",
    "XMP-crs:Blacks2012": "blacks_2012",
    "XMP-crs:Texture": "texture",
    "XMP-crs:Clarity2012": "clarity_2012",
    "XMP-crs:Dehaze": "dehaze",
    "XMP-crs:Vibrance": "vibrance",
    "XMP-crs:Saturation": "saturation",
    "XMP-crs:ParametricShadows": "parametric_shadows",
    "XMP-crs:ParametricDarks": "parametric_darks",
    "XMP-crs:ParametricLights": "parametric_lights",
    "XMP-crs:ParametricHighlights": "parametric_highlights",
    "XMP-crs:Sharpness": "sharpness",
    "XMP-crs:LuminanceSmoothing": "luminance_smoothing",
    "XMP-crs:ColorNoiseReduction": "color_noise_reduction",
    "XMP-crs:LensProfileEnable": "lens_profile_enable",
    "XMP-crs:LensManualDistortionAmount": "lens_manual_distortion_amount",
    "XMP-crs:PerspectiveUpright": "perspective_upright",
    "XMP-crs:UprightVersion": "upright_version",
    "XMP-crs:UprightCenterMode": "upright_center_mode",
    "XMP-crs:PerspectiveVertical": "perspective_vertical",
    "XMP-crs:PerspectiveHorizontal": "perspective_horizontal",
    "XMP-crs:PerspectiveRotate": "perspective_rotate",
    "XMP-crs:PerspectiveScale": "perspective_scale",
    "XMP-crs:PerspectiveAspect": "perspective_aspect",
    "XMP-crs:PerspectiveX": "perspective_x",
    "XMP-crs:PerspectiveY": "perspective_y",
    "XMP-crs:CropTop": "crop_top",
    "XMP-crs:CropLeft": "crop_left",
    "XMP-crs:CropBottom": "crop_bottom",
    "XMP-crs:CropRight": "crop_right",
    "XMP-crs:CropAngle": "crop_angle",
    "XMP-crs:CropConstrainToWarp": "crop_constrain_to_warp",
    "XMP-crs:CropConstrainToUnitSquare": "crop_constrain_to_unit_square",
}


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for Stage 2 develop-setting extraction."""
    parser = argparse.ArgumentParser(
        description="Extract Lightroom develop settings from XMP sidecars."
    )
    parser.add_argument(
        "--input-root",
        default=DEFAULT_INPUT_ROOT,
        help=(
            "Directory containing XMP sidecars. Defaults to the frozen "
            "Stage 2 preconditioning checkpoint."
        ),
    )
    parser.add_argument(
        "--input-model",
        default=INPUT_MODEL,
        help="Label describing the input boundary represented by input-root.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="Destination JSON file for extracted develop settings.",
    )
    return parser.parse_args()


def list_xmps(folder: Path) -> list[Path]:
    """List XMP sidecars from a flat directory or sidecar/sidecars child folder."""
    for child_name in ("sidecars", "sidecar"):
        child = folder / child_name
        if child.is_dir():
            folder = child
            break

    if not folder.is_dir():
        raise SystemExit(f"Input root not found: {folder}")

    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and not path.name.startswith(".") and path.suffix.lower() == ".xmp"
    )


def run_exiftool(paths: list[Path]) -> list[dict[str, object]]:
    """Read selected develop-setting fields using exiftool JSON output."""
    if not paths:
        return []

    command = ["exiftool", "-json", "-G1", "-a", "-s", *DEVELOP_FIELDS, *[str(path) for path in paths]]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def normalize_value(value: object) -> object:
    """Normalize exiftool payload values into JSON-friendly shapes."""
    if value == "":
        return None
    if isinstance(value, list):
        return [normalize_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): normalize_value(item) for key, item in value.items()}
    return value


def canonical_asset_key(payload: dict[str, object], source_file: Path) -> str:
    """Resolve one stable asset key from preserved RAW names or sidecar stem."""
    for key in ("PreservedFileName", "RawFileName", "FileName"):
        value = payload.get(key) or payload.get(f"XMP-xmpMM:{key}") or payload.get(f"XMP-crs:{key}") or payload.get(f"System:{key}")
        if value:
            stem = Path(str(value)).stem
            return stem.split("_", 1)[1] if "_" in stem and stem.split("_", 1)[0].isdigit() else stem
    return source_file.stem


def normalize_record(
    payload: dict[str, object],
    input_root: Path,
    input_model: str,
) -> dict[str, object]:
    """Normalize one XMP exiftool payload into a Stage 2 develop-setting record."""
    source_file = Path(str(payload["SourceFile"]))
    settings = {
        output_key: normalize_value(payload.get(tag))
        for tag, output_key in TAG_TO_KEY.items()
    }
    populated_settings = sorted(
        key for key, value in settings.items() if has_setting_value(value)
    )
    return {
        "asset_key": canonical_asset_key(payload, source_file),
        "input_model": input_model,
        "input_root": str(input_root),
        "source_file": str(source_file),
        "xmp_file_name": payload.get("System:FileName"),
        "xmp_directory": payload.get("System:Directory"),
        "original_raw_filename": payload.get("XMP-xmpMM:PreservedFileName") or payload.get("XMP-crs:RawFileName"),
        "capture_time": payload.get("XMP-exif:DateTimeOriginal"),
        "create_time": payload.get("XMP-xmp:CreateDate"),
        "metadata_time": payload.get("XMP-xmp:MetadataDate"),
        "camera_make": payload.get("XMP-tiff:Make"),
        "camera_model": payload.get("XMP-tiff:Model"),
        "document_id": payload.get("XMP-xmpMM:DocumentID"),
        "original_document_id": payload.get("XMP-xmpMM:OriginalDocumentID"),
        "instance_id": payload.get("XMP-xmpMM:InstanceID"),
        "populated_develop_setting_count": len(populated_settings),
        "populated_develop_settings": populated_settings,
        "develop_settings": settings,
    }


def has_setting_value(value: object) -> bool:
    """Return whether a develop setting is meaningfully present."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def build_summary(records: list[dict[str, object]]) -> dict[str, object]:
    """Summarize develop-setting coverage across extracted records."""
    coverage = {
        key: sum(
            1
            for record in records
            if has_setting_value(
                dict(record.get("develop_settings", {})).get(key)
            )
        )
        for key in DEVELOP_SETTING_KEYS
    }
    return {
        "asset_count": len(records),
        "develop_setting_coverage": coverage,
        "fully_absent_develop_settings": [
            key for key, count in coverage.items() if count == 0
        ],
        "populated_develop_settings": [
            key for key, count in coverage.items() if count > 0
        ],
    }


def main() -> None:
    """Extract Stage 2 develop-setting evidence from XMP sidecars."""
    args = parse_args()
    input_root = Path(args.input_root)
    xmp_paths = list_xmps(input_root)
    payloads = run_exiftool(xmp_paths)
    records = [
        normalize_record(payload, input_root, args.input_model)
        for payload in payloads
    ]
    records.sort(key=lambda record: str(record["asset_key"]))

    output = {
        "stage": "stage2_baseline_conditioning",
        "input_model": args.input_model,
        "input_root": str(input_root),
        "notes": {
            "input_boundary": (
                "The extractor can run against any explicit XMP sidecar set. "
                "The default input references the frozen Stage 2 "
                "preconditioning checkpoint. The input_model label records "
                "how the extracted values should be interpreted."
            ),
            "missing_values": (
                "Lightroom/Camera Raw develop settings absent from source XMPs "
                "are represented as null; coverage is summarized so each input "
                "boundary can be evaluated on its own terms."
            ),
        },
        "summary": build_summary(records),
        "records": records,
    }
    write_json(args.output, output)
    print(f"Wrote {args.output} with {len(records)} Stage 2 develop-setting records.")


if __name__ == "__main__":
    main()
