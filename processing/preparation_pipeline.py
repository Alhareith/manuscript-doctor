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
SKEW_DETECTION_MAX_DIMENSION = 1280
PREPARATION_MIN_FRAME_CLEARANCE_RATIO = 0.005


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


def _boundary_frame_clearance_ratio(boundary, width, height):
    corners = boundary.get("corners") if isinstance(boundary, dict) else None
    if not corners:
        return 0.0

    points = np.asarray(corners, dtype=np.float32).reshape(-1, 2)
    if points.shape != (4, 2):
        return 0.0

    left = float(np.min(points[:, 0])) / max(float(width - 1), 1.0)
    right = float(width - 1 - np.max(points[:, 0])) / max(float(width - 1), 1.0)
    top = float(np.min(points[:, 1])) / max(float(height - 1), 1.0)
    bottom = float(height - 1 - np.max(points[:, 1])) / max(float(height - 1), 1.0)

    return float(max(0.0, min(left, right, top, bottom)))


def _boundary_is_safe_for_automatic_perspective(boundary, width, height):
    if not isinstance(boundary, dict) or not boundary.get("detected"):
        return False, 0.0, "no reliable boundary was detected"

    status = boundary.get("status")
    if status is not None and status != "accept_automatic":
        return False, _boundary_frame_clearance_ratio(boundary, width, height), (
            f"boundary status is {status}; automatic perspective crop requires accept_automatic"
        )

    clearance = _boundary_frame_clearance_ratio(boundary, width, height)
    if clearance < PREPARATION_MIN_FRAME_CLEARANCE_RATIO:
        return False, clearance, (
            "document boundary reaches the image frame; the page may be partially clipped"
        )

    return True, clearance, "boundary has visible background clearance on all four sides"


def _detect_skew_on_proxy(image, max_dimension=SKEW_DETECTION_MAX_DIMENSION):
    proxy, scale = _make_boundary_proxy(image, max_dimension)
    skew = dict(detect_skew(proxy))
    skew["detection_scale"] = round(float(scale), 6)
    skew["detection_dimensions"] = {
        "width": int(proxy.shape[1]),
        "height": int(proxy.shape[0]),
    }
    return skew


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

    # detect_preparation_boundary already evaluates Guided, Region and Bright
    # candidates on one score; do not run a second hidden fallback here.
    perspective_allowed, frame_clearance, perspective_reason = (
        _boundary_is_safe_for_automatic_perspective(
            boundary,
            image.shape[1],
            image.shape[0],
        )
    )
    boundary = dict(boundary)
    boundary["frame_clearance_ratio"] = round(float(frame_clearance), 6)
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

    boundary_found = bool(boundary.get("detected"))
    current = original.copy()

    if not perspective_allowed:
        result["steps"].append({
            "step": "boundary",
            "status": "review_required" if boundary_found else "rejected",
            "reason": perspective_reason,
            "confidence": boundary.get("confidence", 0.0),
            "area_ratio": boundary.get("area_ratio", 0.0),
            "frame_clearance_ratio": round(float(frame_clearance), 6),
        })
        result["steps"].append({
            "step": "perspective",
            "status": "skipped",
            "reason": (
                "skipped: automatic perspective crop requires a fully visible document "
                "with visible background on all four sides"
            ),
        })
    else:
        result["steps"].append({
            "step": "boundary",
            "status": "accepted",
            "confidence": boundary["confidence"],
            "area_ratio": boundary["area_ratio"],
            "frame_clearance_ratio": round(float(frame_clearance), 6),
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

    skew = _detect_skew_on_proxy(current)
    result["skew"] = skew

    result["steps"].append({
        "step": "skew_detection",
        "status": "measured" if skew["confidence"] > 0 else "rejected",
        "angle": skew["angle"],
        "confidence": skew["confidence"],
        "line_count": skew["line_count"],
        "dispersion": skew["dispersion"],
        "detection_scale": skew["detection_scale"],
        "detection_dimensions": skew["detection_dimensions"],
    })

    deskew_result = apply_auto_deskew(current, skew)
    crop_applied = bool(perspective_allowed and deskew_result.get("crop_applied"))
    crop_reason = deskew_result.get("crop_reason")

    if not perspective_allowed:
        crop_reason = (
            "skipped: document is not safely framed for automatic crop; "
            "deskew correction keeps the complete current frame"
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
    elif boundary_found and not perspective_allowed:
        result["reason"] = (
            "stopped: a document-like boundary was found but automatic crop was blocked "
            "because the full page is not safely visible inside the frame"
        )
    else:
        result["reason"] = "stopped: no reliable boundary or confident skew correction was available"

    return result
