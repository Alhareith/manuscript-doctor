import cv2
import numpy as np

from processing.deterministic_hough import hough_lines_p


MAX_ABS_SKEW = 45.0
MIN_IMAGE_SIDE = 80
MIN_LINE_COUNT = 3
MIN_LINE_LENGTH_RATIO = 0.12
ANGLE_OUTLIER_LIMIT = 6.0


def _validate_image(image):
    if image is None or not isinstance(image, np.ndarray):
        raise ValueError("Image must be a valid NumPy array.")

    if image.size == 0:
        raise ValueError("Image cannot be empty.")

    if image.dtype != np.uint8:
        raise ValueError("Only 8-bit images are supported.")

    if image.ndim == 2:
        return

    if image.ndim != 3 or image.shape[2] not in {1, 3, 4}:
        raise ValueError("Unsupported image format.")


def _to_gray(image):
    _validate_image(image)

    if image.ndim == 2:
        return image.copy()

    if image.shape[2] == 1:
        return image[:, :, 0].copy()

    if image.shape[2] == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)


def _normalize_angle(angle):
    angle = float(angle)

    while angle <= -90.0:
        angle += 180.0

    while angle > 90.0:
        angle -= 180.0

    return angle


def _collect_line_angles(gray):
    height, width = gray.shape[:2]

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(blurred)

    median_intensity = float(np.median(enhanced))
    lower = int(max(30, 0.60 * median_intensity))
    upper = int(min(255, max(lower + 30, 1.40 * median_intensity)))

    edges = cv2.Canny(enhanced, lower, upper)

    min_line_length = max(40, int(width * MIN_LINE_LENGTH_RATIO))
    max_line_gap = max(8, int(width * 0.025))

    lines = hough_lines_p(
        edges,
        rho=1,
        theta=np.pi / 360.0,
        threshold=max(35, int(width * 0.045)),
        min_line_length=min_line_length,
        max_line_gap=max_line_gap,
    )

    if lines is None:
        return []

    lines = np.asarray(lines, dtype=np.int32).reshape(-1, 4)

    measurements = []

    for x1, y1, x2, y2 in lines:
        dx = float(x2 - x1)
        dy = float(y2 - y1)
        length = float(np.hypot(dx, dy))

        if length < min_line_length:
            continue

        angle = _normalize_angle(np.degrees(np.arctan2(dy, dx)))

        if abs(angle) > MAX_ABS_SKEW:
            continue

        measurements.append({
            "angle": float(angle),
            "length": length,
        })

    return measurements


def _robust_angle_statistics(measurements):
    if len(measurements) < MIN_LINE_COUNT:
        return None

    angles = np.asarray([item["angle"] for item in measurements], dtype=np.float64)
    weights = np.asarray([item["length"] for item in measurements], dtype=np.float64)

    median_angle = float(np.median(angles))
    deviations = np.abs(angles - median_angle)

    mad = float(np.median(deviations))
    allowed_deviation = max(1.0, min(ANGLE_OUTLIER_LIMIT, 2.5 * mad if mad > 0 else 1.5))

    valid = deviations <= allowed_deviation

    filtered_angles = angles[valid]
    filtered_weights = weights[valid]

    if len(filtered_angles) < MIN_LINE_COUNT:
        return None

    detected_angle = float(np.average(filtered_angles, weights=filtered_weights))
    dispersion = float(np.sqrt(np.average((filtered_angles - detected_angle) ** 2, weights=filtered_weights)))

    return {
        "angle": detected_angle,
        "dispersion": dispersion,
        "line_count": int(len(filtered_angles)),
        "raw_line_count": int(len(measurements)),
    }


def _confidence_from_statistics(statistics):
    line_count = statistics["line_count"]
    raw_line_count = statistics["raw_line_count"]
    dispersion = statistics["dispersion"]

    count_score = float(np.clip(line_count / 16.0, 0.0, 1.0))
    agreement_ratio = float(np.clip(line_count / max(raw_line_count, 1), 0.0, 1.0))
    dispersion_score = float(np.clip(1.0 - dispersion / 5.0, 0.0, 1.0))

    confidence = 0.35 * count_score + 0.30 * agreement_ratio + 0.35 * dispersion_score

    return float(np.clip(confidence, 0.0, 1.0))


def detect_skew(image):
    gray = _to_gray(image)
    height, width = gray.shape[:2]

    if min(height, width) < MIN_IMAGE_SIDE:
        return {
            "angle": 0.0,
            "confidence": 0.0,
            "line_count": 0,
            "dispersion": 0.0,
            "reason": "rejected: image is too small for reliable skew detection",
        }

    measurements = _collect_line_angles(gray)
    statistics = _robust_angle_statistics(measurements)

    if statistics is None:
        return {
            "angle": 0.0,
            "confidence": 0.0,
            "line_count": 0,
            "dispersion": 0.0,
            "reason": "rejected: not enough consistent text-line evidence was found",
        }

    confidence = _confidence_from_statistics(statistics)

    return {
        "angle": round(statistics["angle"], 2),
        "confidence": round(confidence, 4),
        "line_count": statistics["line_count"],
        "dispersion": round(statistics["dispersion"], 4),
        "reason": "measured: skew estimated from consistent near-horizontal line evidence",
    }