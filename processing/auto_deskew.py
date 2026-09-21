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

def _calculate_safe_crop(image_shape, transform, rotated_shape):
    source_height, source_width = image_shape[:2]
    rotated_height, rotated_width = rotated_shape[:2]

    source_corners = np.array([
        [0.0, 0.0],
        [source_width - 1.0, 0.0],
        [source_width - 1.0, source_height - 1.0],
        [0.0, source_height - 1.0],
    ], dtype=np.float32).reshape(-1, 1, 2)

    transformed_corners = cv2.transform(source_corners, transform).reshape(4, 2)

    mask = np.zeros((rotated_height, rotated_width), dtype=np.uint8)
    cv2.fillConvexPoly(mask, np.round(transformed_corners).astype(np.int32), 255)

    valid_area = int(cv2.countNonZero(mask))

    if valid_area <= 0:
        return None

    distance = cv2.distanceTransform(mask, cv2.DIST_L2, 5)

    best = None
    step = max(1, int(round(min(rotated_height, rotated_width) * 0.002)))

    for top in range(0, rotated_height // 2, step):
        if not np.any(mask[top, :]):
            continue

        bottom = rotated_height - 1 - top

        if bottom <= top:
            break

        row_top = np.where(mask[top, :] > 0)[0]
        row_bottom = np.where(mask[bottom, :] > 0)[0]

        if row_top.size == 0 or row_bottom.size == 0:
            continue

        left = int(max(row_top[0], row_bottom[0]))
        right = int(min(row_top[-1], row_bottom[-1]))

        if right <= left:
            continue

        rectangle_mask = mask[top:bottom + 1, left:right + 1]

        if rectangle_mask.size == 0 or np.any(rectangle_mask == 0):
            continue

        crop_area = int((right - left + 1) * (bottom - top + 1))
        retention_ratio = float(crop_area / valid_area)

        if best is None or crop_area > best["area"]:
            best = {
                "x": left,
                "y": top,
                "width": right - left + 1,
                "height": bottom - top + 1,
                "area": crop_area,
                "retention_ratio": retention_ratio,
            }

    return best


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
    safe_crop = _calculate_safe_crop(image.shape, transform, corrected.shape)
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