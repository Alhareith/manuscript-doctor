import numpy as np

from processing.auto_deskew import apply_auto_deskew
from processing.document_boundary import (
    detect_document_boundary,
    detect_preparation_boundary,
)
from processing.document_rectification import rectify_document
from processing.skew_detector import detect_skew


def _validate_image(image):
    if image is None or not isinstance(image, np.ndarray):
        raise ValueError("Image must be a valid NumPy array.")

    if image.size == 0:
        raise ValueError("Image cannot be empty.")


def prepare_document(image, boundary_detector=detect_document_boundary):
    _validate_image(image)

    original = image.copy()
    boundary = boundary_detector(image)

    result = {
        "prepared": False,
        "image": original.copy(),
        "boundary": boundary,
        "perspective": None,
        "skew": None,
        "deskew": None,
        "steps": [],
        "reason": "",
    }

    boundary_detected = bool(boundary.get("detected"))
    current = original.copy()

    if not boundary_detected:
        result["steps"].append({
            "step": "boundary",
            "status": "rejected",
            "reason": boundary.get("reason", "boundary was not reliable enough"),
        })
        result["steps"].append({
            "step": "perspective",
            "status": "skipped",
            "reason": "skipped: no reliable boundary; deskew-only fallback will use the original frame",
        })
    else:
        result["steps"].append({
            "step": "boundary",
            "status": "accepted",
            "confidence": boundary["confidence"],
            "area_ratio": boundary["area_ratio"],
        })

        rectified = rectify_document(image, boundary["corners"])

        result["perspective"] = {
            "applied": True,
            "width": rectified["width"],
            "height": rectified["height"],
            "source_corners": rectified["source_corners"],
        }

        result["steps"].append({
            "step": "perspective",
            "status": "applied",
            "width": rectified["width"],
            "height": rectified["height"],
        })

        current = rectified["image"]

    skew = detect_skew(current)
    result["skew"] = skew

    result["steps"].append({
        "step": "skew_detection",
        "status": "measured" if skew["confidence"] > 0 else "rejected",
        "angle": skew["angle"],
        "confidence": skew["confidence"],
        "line_count": skew["line_count"],
        "dispersion": skew["dispersion"],
    })

    deskew_result = apply_auto_deskew(current, skew)
    crop_applied = bool(boundary_detected and deskew_result.get("crop_applied"))
    crop_reason = deskew_result.get("crop_reason")

    if not boundary_detected:
        crop_reason = "skipped: no reliable document boundary; deskew correction kept the original frame without crop"

    result["deskew"] = {
        "applied": deskew_result["applied"],
        "angle": deskew_result["angle"],
        "confidence": deskew_result["confidence"],
        "reason": deskew_result["reason"],
        "safe_crop": deskew_result.get("safe_crop") if boundary_detected else None,
        "crop_applied": crop_applied,
        "crop_reason": crop_reason,
    }

    if deskew_result["applied"]:
        current = deskew_result["final_image"] if crop_applied else deskew_result["image"]
        result["steps"].append({
            "step": "auto_deskew",
            "status": "applied",
            "angle": deskew_result["angle"],
            "crop_applied": crop_applied,
        })
    else:
        result["steps"].append({
            "step": "auto_deskew",
            "status": "skipped",
            "angle": deskew_result["angle"],
            "reason": deskew_result["reason"],
        })

    if not np.array_equal(image, original):
        raise RuntimeError("Preparation pipeline modified the original input image.")

    result["prepared"] = boundary_detected or bool(deskew_result["applied"])
    result["image"] = current
    if result["prepared"]:
        result["reason"] = (
            "prepared: deskew-only correction completed without perspective crop"
            if not boundary_detected and deskew_result["applied"]
            else "prepared: document preparation completed safely"
        )
    else:
        result["reason"] = "stopped: no reliable boundary or confident skew correction was available"

    return result
