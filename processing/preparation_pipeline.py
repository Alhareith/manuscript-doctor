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
PREPARATION_SKIP_CROP_AREA_RATIO = 0.95


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


def _boundary_needs_automatic_crop(boundary):
    if not isinstance(boundary, dict) or not boundary.get("detected"):
        return False, "no reliable boundary was detected"

    area_ratio = float(boundary.get("area_ratio", 0.0))
    if not 0.0 < area_ratio <= 1.0:
        return False, "boundary area ratio is invalid; automatic crop was skipped"

    if area_ratio >= PREPARATION_SKIP_CROP_AREA_RATIO:
        return False, (
            "automatic crop skipped: the detected document already occupies "
            f"{area_ratio:.1%} of the image"
        )

    return True, "automatic crop is useful because the detected document leaves meaningful outer area"


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

    perspective_allowed, perspective_reason = _boundary_needs_automatic_crop(boundary)
    boundary = dict(boundary)
    boundary["automatic_crop_eligible"] = bool(perspective_allowed)
    boundary["automatic_crop_reason"] = perspective_reason

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

    if not perspective_allowed:
        result["steps"].append({
            "step": "boundary",
            "status": "accepted" if boundary_detected else "rejected",
            "reason": perspective_reason,
            "confidence": boundary.get("confidence", 0.0),
            "area_ratio": boundary.get("area_ratio", 0.0),
        })
        result["steps"].append({
            "step": "perspective",
            "status": "skipped",
            "reason": perspective_reason,
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
    crop_applied = bool(perspective_allowed and deskew_result.get("crop_applied"))
    crop_reason = deskew_result.get("crop_reason")

    if not perspective_allowed:
        crop_reason = (
            "skipped: automatic crop was unnecessary or unsafe; "
            "deskew correction kept the complete current frame"
        )

    result["deskew"] = {
        "applied": deskew_result["applied"],
        "angle": deskew_result["angle"],
        "confidence": deskew_result["confidence"],
        "reason": deskew_result["reason"],
        "safe_crop": deskew_result.get("safe_crop") if perspective_allowed else None,
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

    result["prepared"] = perspective_allowed or bool(deskew_result["applied"])
    result["image"] = current
    if result["prepared"]:
        result["reason"] = (
            "prepared: deskew-only correction completed without perspective crop"
            if not perspective_allowed and deskew_result["applied"]
            else "prepared: document preparation completed safely"
        )
    elif boundary_detected and not perspective_allowed:
        result["reason"] = (
            "stopped: the document already fills the image closely enough; "
            "the original frame was preserved instead of cropping"
        )
    else:
        result["reason"] = "stopped: no reliable boundary or confident skew correction was available"

    return result
