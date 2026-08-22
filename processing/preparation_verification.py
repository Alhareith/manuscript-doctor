import cv2
import numpy as np

from processing.skew_detector import detect_skew


MAX_GOOD_RESIDUAL_SKEW = 0.75
MAX_CAUTION_RESIDUAL_SKEW = 2.0
MIN_GOOD_BOUNDARY_CONFIDENCE = 0.68
MIN_SAFE_RETENTION = 0.95


def _validate_preparation_result(result):
    if not isinstance(result, dict):
        raise ValueError("Preparation result must be a dictionary.")

    required = {"prepared", "image", "boundary", "perspective", "skew", "deskew", "steps", "reason"}

    if not required.issubset(result):
        raise ValueError("Preparation result is missing required fields.")

    image = result["image"]

    if image is None or not isinstance(image, np.ndarray) or image.size == 0:
        raise ValueError("Prepared image is invalid.")

    if image.dtype != np.uint8:
        raise ValueError("Prepared image must be 8-bit.")


def _verify_boundary(boundary):
    if not isinstance(boundary, dict) or not boundary.get("detected"):
        return False, "document boundary was not accepted"

    corners = boundary.get("corners", [])
    confidence = float(boundary.get("confidence", 0.0))
    area_ratio = float(boundary.get("area_ratio", 0.0))

    if len(corners) != 4:
        return False, "accepted boundary does not contain four corners"

    if confidence < MIN_GOOD_BOUNDARY_CONFIDENCE:
        return False, "boundary confidence is below the preparation safety threshold"

    if not 0.0 < area_ratio <= 1.0:
        return False, "boundary area ratio is invalid"

    return True, "boundary evidence is valid"


def _verify_perspective(perspective):
    if not isinstance(perspective, dict) or not perspective.get("applied"):
        return False, "perspective rectification was not applied"

    width = int(perspective.get("width", 0))
    height = int(perspective.get("height", 0))
    corners = perspective.get("source_corners", [])

    if width < 40 or height < 40:
        return False, "rectified dimensions are too small"

    if len(corners) != 4:
        return False, "perspective metadata does not contain four source corners"

    points = np.asarray(corners, dtype=np.float32)

    if points.shape != (4, 2) or not np.all(np.isfinite(points)):
        return False, "perspective source corners are invalid"

    if not cv2.isContourConvex(points.astype(np.int32).reshape(-1, 1, 2)):
        return False, "perspective source geometry is not convex"

    return True, "perspective geometry is valid"


def _verify_crop(deskew):
    if not isinstance(deskew, dict):
        return True, "no deskew metadata available"

    if not deskew.get("crop_applied", False):
        return True, "post-deskew crop was not applied"

    safe_crop = deskew.get("safe_crop")

    if not isinstance(safe_crop, dict):
        return False, "post-deskew crop was applied without safety metadata"

    retention = float(safe_crop.get("retention_ratio", 0.0))

    if retention < MIN_SAFE_RETENTION:
        return False, "post-deskew crop retention is below the safe threshold"

    return True, "post-deskew crop retained a safe document area"


def verify_preparation(result):
    _validate_preparation_result(result)

    if not result["prepared"]:
        return {
            "status": "reject",
            "verified": False,
            "residual_skew": None,
            "checks": [],
            "reason": "rejected: preparation pipeline did not produce an accepted result",
        }

    checks = []

    boundary_ok, boundary_reason = _verify_boundary(result["boundary"])
    checks.append({"check": "boundary", "passed": boundary_ok, "reason": boundary_reason})

    perspective_ok, perspective_reason = _verify_perspective(result["perspective"])
    checks.append({"check": "perspective", "passed": perspective_ok, "reason": perspective_reason})

    crop_ok, crop_reason = _verify_crop(result["deskew"])
    checks.append({"check": "post_deskew_crop", "passed": crop_ok, "reason": crop_reason})

    residual = detect_skew(result["image"])

    residual_angle = abs(float(residual["angle"]))
    residual_confidence = float(residual["confidence"])

    if residual_confidence == 0.0:
        skew_status = "unknown"
        skew_passed = True
        skew_reason = "residual skew could not be measured reliably"
    elif residual_angle <= MAX_GOOD_RESIDUAL_SKEW:
        skew_status = "good"
        skew_passed = True
        skew_reason = "residual skew is within the good range"
    elif residual_angle <= MAX_CAUTION_RESIDUAL_SKEW:
        skew_status = "caution"
        skew_passed = True
        skew_reason = "residual skew is small but above the preferred range"
    else:
        skew_status = "reject"
        skew_passed = False
        skew_reason = "residual skew remains too large after preparation"

    checks.append({
        "check": "residual_skew",
        "passed": skew_passed,
        "status": skew_status,
        "angle": residual["angle"],
        "confidence": residual["confidence"],
        "line_count": residual["line_count"],
        "dispersion": residual["dispersion"],
        "reason": skew_reason,
    })

    hard_failure = any(not item["passed"] for item in checks)

    if hard_failure:
        status = "reject"
        verified = False
        reason = "rejected: one or more preparation safety checks failed"
    elif skew_status in {"caution", "unknown"}:
        status = "caution"
        verified = True
        reason = "caution: preparation is usable but one verification signal is not fully reliable"
    else:
        status = "accept"
        verified = True
        reason = "accepted: preparation passed geometry, crop, and residual-skew verification"

    return {
        "status": status,
        "verified": verified,
        "residual_skew": residual,
        "checks": checks,
        "reason": reason,
    }