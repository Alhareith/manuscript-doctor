import cv2
import numpy as np

from processing.auto_deskew import apply_auto_deskew
from processing.document_boundary import (
    detect_document_boundary,
    detect_preparation_boundary,
)
from processing.document_rectification import rectify_document
from processing.skew_detector import detect_skew


BOUNDARY_DETECTION_MAX_DIMENSION = 640
BOUNDARY_FALLBACK_MAX_DIMENSIONS = (512, 384)


def _validate_image(image):
    if image is None or not isinstance(image, np.ndarray):
        raise ValueError("Image must be a valid NumPy array.")

    if image.size == 0:
        raise ValueError("Image cannot be empty.")


def _make_boundary_proxy(image, max_dimension):
    if not isinstance(max_dimension, int) or isinstance(max_dimension, bool):
        raise ValueError("max boundary dimension must be a positive integer.")

    if max_dimension <= 0:
        raise ValueError("max boundary dimension must be a positive integer.")

    height, width = image.shape[:2]
    scale = min(1.0, max_dimension / max(height, width))

    if scale >= 1.0:
        return image.copy(), scale

    proxy_size = (
        max(1, int(round(width * scale))),
        max(1, int(round(height * scale))),
    )

    proxy = cv2.resize(image, proxy_size, interpolation=cv2.INTER_AREA)
    return proxy, scale


def _restore_boundary_coordinates(boundary, scale, width, height):
    if not isinstance(boundary, dict) or scale >= 1.0:
        return boundary

    restored = dict(boundary)
    corners = boundary.get("corners")

    if corners:
        restored["corners"] = [
            [
                int(np.clip(round(float(x) / scale), 0, width - 1)),
                int(np.clip(round(float(y) / scale), 0, height - 1)),
            ]
            for x, y in np.asarray(corners, dtype=np.float32).reshape(-1, 2)
        ]

    restored["detection_scale"] = round(float(scale), 6)
    restored["detection_dimensions"] = {
        "width": int(round(width * scale)),
        "height": int(round(height * scale)),
    }
    return restored


def prepare_document(
    image,
    boundary_detector=detect_document_boundary,
    boundary_max_dimension=BOUNDARY_DETECTION_MAX_DIMENSION,
):
    _validate_image(image)

    original = image.copy()
    boundary_dimensions = [boundary_max_dimension]
    if boundary_detector is detect_preparation_boundary:
        boundary_dimensions.extend(
            dimension
            for dimension in BOUNDARY_FALLBACK_MAX_DIMENSIONS
            if dimension < boundary_max_dimension
        )

    boundary = None
    boundary_scale = 1.0
    for dimension in boundary_dimensions:
        proxy, boundary_scale = _make_boundary_proxy(image, dimension)
        candidate = boundary_detector(proxy)
        boundary = _restore_boundary_coordinates(
            candidate,
            boundary_scale,
            image.shape[1],
            image.shape[0],
        )
        if boundary.get("detected") or boundary.get("status") != "reject":
            break

    result = {
        "prepared": False,
        "image": original.copy(),
        "boundary": boundary,
        "perspective": None,
        "skew": None,
        "deskew": None,
        "orientation": {
            "status": "manual_review",
            "absolute_orientation_known": False,
            "automatic_180_correction": False,
            "requires_manual_review": True,
            "reason": "لا يمكن استنتاج اتجاه 180° بأمان من هندسة الصفحة وحدها.",
        },
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
