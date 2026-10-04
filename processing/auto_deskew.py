import cv2
import numpy as np


MIN_AUTO_DESKEW_CONFIDENCE = 0.70
MIN_CORRECTION_ANGLE = 0.50
MAX_CORRECTION_ANGLE = 45.0
MIN_SAFE_CROP_RETENTION = 0.95

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


def _validate_skew_result(skew_result):
    if not isinstance(skew_result, dict):
        raise ValueError("skew_result must be a dictionary.")

    required = {"angle", "confidence", "line_count", "dispersion"}

    if not required.issubset(skew_result):
        raise ValueError("skew_result is missing required fields.")

    angle = float(skew_result["angle"])
    confidence = float(skew_result["confidence"])

    if not np.isfinite(angle) or not np.isfinite(confidence):
        raise ValueError("Skew result contains invalid numeric values.")

    if confidence < 0.0 or confidence > 1.0:
        raise ValueError("Skew confidence must be between 0 and 1.")

    return angle, confidence

def _estimate_border_value(image):
    height, width = image.shape[:2]
    band = max(3, int(round(min(height, width) * 0.02)))

    if image.ndim == 2:
        samples = np.concatenate([
            image[:band, :].reshape(-1),
            image[-band:, :].reshape(-1),
            image[:, :band].reshape(-1),
            image[:, -band:].reshape(-1),
        ])

        return int(round(float(np.median(samples))))

    samples = np.concatenate([
        image[:band, :, :].reshape(-1, image.shape[2]),
        image[-band:, :, :].reshape(-1, image.shape[2]),
        image[:, :band, :].reshape(-1, image.shape[2]),
        image[:, -band:, :].reshape(-1, image.shape[2]),
    ], axis=0)

    median = np.median(samples, axis=0)

    return tuple(int(round(value)) for value in median)


def _rotate_without_clipping(image, angle):
    height, width = image.shape[:2]
    center = (width / 2.0, height / 2.0)

    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

    cosine = abs(matrix[0, 0])
    sine = abs(matrix[0, 1])

    new_width = int(np.ceil(height * sine + width * cosine))
    new_height = int(np.ceil(height * cosine + width * sine))

    matrix[0, 2] += new_width / 2.0 - center[0]
    matrix[1, 2] += new_height / 2.0 - center[1]

    border_value = _estimate_border_value(image)

    rotated = cv2.warpAffine(
        image,
        matrix,
        (new_width, new_height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border_value
    )

    if rotated is None or rotated.size == 0:
        raise RuntimeError("Auto deskew produced an empty image.")

    return rotated, matrix

def _largest_axis_aligned_rect(width, height, angle_degrees):
    """Return the largest axis-aligned rectangle inside a rotated rectangle.

    This is an O(1) geometric calculation. It replaces the previous row-by-row
    mask scan while preserving the conservative retention check.
    """
    width = float(width)
    height = float(height)

    if width <= 0 or height <= 0:
        return None

    angle = abs(float(angle_degrees)) % 180.0
    if angle > 90.0:
        angle = 180.0 - angle

    radians = np.deg2rad(angle)
    sine = abs(float(np.sin(radians)))
    cosine = abs(float(np.cos(radians)))

    if sine < 1e-9:
        return width, height

    width_is_longer = width >= height
    side_long = max(width, height)
    side_short = min(width, height)

    if (
        side_short <= 2.0 * sine * cosine * side_long
        or abs(sine - cosine) < 1e-9
    ):
        half_short = 0.5 * side_short
        if width_is_longer:
            rect_width = half_short / max(sine, 1e-9)
            rect_height = half_short / max(cosine, 1e-9)
        else:
            rect_width = half_short / max(cosine, 1e-9)
            rect_height = half_short / max(sine, 1e-9)
    else:
        cos_2a = (cosine * cosine) - (sine * sine)
        if abs(cos_2a) < 1e-9:
            return None

        rect_width = (
            (width * cosine) - (height * sine)
        ) / cos_2a
        rect_height = (
            (height * cosine) - (width * sine)
        ) / cos_2a

    rect_width = float(max(1.0, min(rect_width, width / max(cosine, 1e-9))))
    rect_height = float(max(1.0, min(rect_height, height / max(cosine, 1e-9))))

    if not np.isfinite(rect_width) or not np.isfinite(rect_height):
        return None

    return rect_width, rect_height


def _calculate_safe_crop(image_shape, transform, rotated_shape, angle=None):
    source_height, source_width = image_shape[:2]
    rotated_height, rotated_width = rotated_shape[:2]

    if angle is None:
        rotation_cos = float(transform[0, 0])
        rotation_sin = float(transform[0, 1])
        angle = np.degrees(np.arctan2(rotation_sin, rotation_cos))

    rectangle = _largest_axis_aligned_rect(
        source_width,
        source_height,
        angle,
    )
    if rectangle is None:
        return None

    crop_width, crop_height = rectangle
    crop_width = int(max(1, min(round(crop_width), rotated_width)))
    crop_height = int(max(1, min(round(crop_height), rotated_height)))

    left = int(round((rotated_width - crop_width) / 2.0))
    top = int(round((rotated_height - crop_height) / 2.0))

    left = int(np.clip(left, 0, max(rotated_width - crop_width, 0)))
    top = int(np.clip(top, 0, max(rotated_height - crop_height, 0)))

    valid_area = float(max(source_width * source_height, 1))
    crop_area = int(crop_width * crop_height)
    retention_ratio = float(crop_area / valid_area)

    return {
        "x": left,
        "y": top,
        "width": crop_width,
        "height": crop_height,
        "area": crop_area,
        "retention_ratio": retention_ratio,
        "method": "direct_geometry",
    }

def _apply_safe_crop(image, safe_crop):
    if safe_crop is None:
        return image.copy(), False, "skipped: no geometrically valid post-deskew crop was found"

    if safe_crop["retention_ratio"] < MIN_SAFE_CROP_RETENTION:
        return image.copy(), False, "skipped: post-deskew crop would remove too much valid document area"

    x = safe_crop["x"]
    y = safe_crop["y"]
    width = safe_crop["width"]
    height = safe_crop["height"]

    cropped = image[y:y + height, x:x + width].copy()

    if cropped.size == 0:
        raise RuntimeError("Post-deskew crop produced an empty image.")

    return cropped, True, "applied: post-deskew framing retained a safe amount of document area"

def apply_auto_deskew(image, skew_result):
    _validate_image(image)

    angle, confidence = _validate_skew_result(skew_result)

    if confidence < MIN_AUTO_DESKEW_CONFIDENCE:
        return {
            "applied": False,
            "image": image.copy(),
            "angle": angle,
            "confidence": confidence,
            "reason": "skipped: skew confidence is below the automatic correction threshold",
            "transform": None,
        }

    if abs(angle) < MIN_CORRECTION_ANGLE:
        return {
            "applied": False,
            "image": image.copy(),
            "angle": angle,
            "confidence": confidence,
            "reason": "skipped: detected skew is too small to require correction",
            "transform": None,
        }

    if abs(angle) > MAX_CORRECTION_ANGLE:
        return {
            "applied": False,
            "image": image.copy(),
            "angle": angle,
            "confidence": confidence,
            "reason": "skipped: detected skew exceeds the safe automatic correction range",
            "transform": None,
        }

    corrected, transform = _rotate_without_clipping(image, angle)
    safe_crop = _calculate_safe_crop(image.shape, transform, corrected.shape, angle=angle)
    final_image, crop_applied, crop_reason = _apply_safe_crop(corrected, safe_crop)

    return {
        "applied": True,
        "image": corrected,
        "angle": angle,
        "confidence": confidence,
        "reason": "applied: automatic deskew correction passed confidence and angle safety checks",
        "transform": transform.copy(),
        "safe_crop": safe_crop,
        "final_image": final_image,
        "crop_applied": crop_applied,
        "crop_reason": crop_reason,
    }