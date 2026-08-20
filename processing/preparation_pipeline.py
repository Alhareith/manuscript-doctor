import numpy as np

from processing.auto_deskew import apply_auto_deskew
from processing.document_boundary import detect_document_boundary
from processing.document_rectification import rectify_document
from processing.skew_detector import detect_skew


def _validate_image(image):
    if image is None or not isinstance(image, np.ndarray):
        raise ValueError("Image must be a valid NumPy array.")

    if image.size == 0:
        raise ValueError("Image cannot be empty.")


def prepare_document(image):
    _validate_image(image)

    original = image.copy()
    boundary = detect_document_boundary(image)

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

    if not boundary["detected"]:
        result["steps"].append({
            "step": "boundary",
            "status": "rejected",
            "reason": boundary["reason"],
        })

        result["reason"] = "stopped: document boundary was not reliable enough"
        return result

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

    deskew = apply_auto_deskew(current, skew)

    result["deskew"] = {
        "applied": deskew["applied"],
        "angle": deskew["angle"],
        "confidence": deskew["confidence"],
        "reason": deskew["reason"],
        "safe_crop": deskew.get("safe_crop"),
        "crop_applied": deskew.get("crop_applied", False),
        "crop_reason": deskew.get("crop_reason"),
    }

    if deskew["applied"]:
        current = deskew["image"]

        result["steps"].append({
            "step": "auto_deskew",
            "status": "applied",
            "angle": deskew["angle"],
            "crop_applied": deskew.get("crop_applied", False),
        })
    else:
        result["steps"].append({
            "step": "auto_deskew",
            "status": "skipped",
            "angle": deskew["angle"],
            "reason": deskew["reason"],
        })

    if not np.array_equal(image, original):
        raise RuntimeError("Preparation pipeline modified the original input image.")

    result["prepared"] = True
    result["image"] = current
    result["reason"] = "prepared: document preparation completed safely"

    return result