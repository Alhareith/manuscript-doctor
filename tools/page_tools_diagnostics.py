from pathlib import Path
import json
import cv2

from processing.document_boundary import detect_preparation_boundary
from processing.bright_document_fallback import detect_bright_document_boundary
from processing.preparation_pipeline import prepare_document
from processing.preparation_verification import verify_preparation
from processing.skew_detector import detect_skew

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "evaluation" / "input"

CASES = [
    "b01.jpg",
    "b02.jpg",
    "check/c04.jpg",
    "check/c05.jpg",
    "check/c06.jpg",
    "check/c08.jpg",
]

def compact_boundary(value):
    if not isinstance(value, dict):
        return value
    keys = (
        "detected", "status", "method_used", "confidence", "final_score",
        "area_ratio", "edge_support", "corners", "frame_clearance_ratio",
        "automatic_crop_eligible", "automatic_crop_reason", "reason",
        "fallback_used",
    )
    return {key: value.get(key) for key in keys if key in value}

for name in CASES:
    image = cv2.imread(str(INPUT / name), cv2.IMREAD_COLOR)
    if image is None:
        print(name, "MISSING")
        continue

    prep_boundary = detect_preparation_boundary(image)
    bright = detect_bright_document_boundary(image)
    skew = detect_skew(image)
    result = prepare_document(image, boundary_detector=detect_preparation_boundary)
    verification = verify_preparation(result)

    payload = {
        "case": name,
        "shape": list(image.shape),
        "prep_boundary_direct": compact_boundary(prep_boundary),
        "bright_fallback_direct": compact_boundary(bright),
        "skew_direct": skew,
        "result": {
            "prepared": result.get("prepared"),
            "boundary": compact_boundary(result.get("boundary")),
            "perspective": result.get("perspective"),
            "skew": result.get("skew"),
            "deskew": result.get("deskew"),
            "reason": result.get("reason"),
        },
        "verification": {
            "status": verification.get("status"),
            "verified": verification.get("verified"),
            "reason": verification.get("reason"),
            "checks": verification.get("checks"),
            "residual_skew": verification.get("residual_skew"),
        },
    }
    print("PAGE_TOOL_DIAGNOSTIC=" + json.dumps(payload, ensure_ascii=False, default=str))
