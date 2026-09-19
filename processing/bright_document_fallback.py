import cv2
import numpy as np


MIN_AREA_RATIO = 0.16
MAX_AREA_RATIO = 0.90
MIN_SCORE = 0.66
REVIEW_SCORE = 0.44
MIN_CLEARANCE_RATIO = 0.005


def _order(points):
    points = np.asarray(points, dtype=np.float32).reshape(4, 2)
    sums = points.sum(axis=1)
    diffs = np.diff(points, axis=1).reshape(-1)
    return np.array(
        [
            points[np.argmin(sums)],
            points[np.argmin(diffs)],
            points[np.argmax(sums)],
            points[np.argmax(diffs)],
        ],
        dtype=np.float32,
    )


def _angles(corners):
    angles = []
    for index in range(4):
        previous = corners[(index - 1) % 4] - corners[index]
        following = corners[(index + 1) % 4] - corners[index]
        denominator = np.linalg.norm(previous) * np.linalg.norm(following)
        if denominator <= 1e-6:
            return None
        cosine = np.clip(float(np.dot(previous, following) / denominator), -1.0, 1.0)
        angles.append(float(np.degrees(np.arccos(cosine))))
    return np.asarray(angles, dtype=np.float32)


def _clearance(corners, width, height):
    corners = np.asarray(corners, dtype=np.float32).reshape(4, 2)
    return max(
        0.0,
        min(
            float(np.min(corners[:, 0])) / max(width - 1, 1),
            float(width - 1 - np.max(corners[:, 0])) / max(width - 1, 1),
            float(np.min(corners[:, 1])) / max(height - 1, 1),
            float(height - 1 - np.max(corners[:, 1])) / max(height - 1, 1),
        ),
    )


def _border_contrast(gray, corners):
    height, width = gray.shape[:2]
    polygon = np.round(corners).astype(np.int32)
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillConvexPoly(mask, polygon, 255)

    band = max(5, int(round(min(height, width) * 0.012)))
    if band % 2 == 0:
        band += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (band, band))
    inner = cv2.subtract(mask, cv2.erode(mask, kernel))
    outer = cv2.subtract(cv2.dilate(mask, kernel), mask)

    if cv2.countNonZero(inner) < 100 or cv2.countNonZero(outer) < 100:
        return 0.0

    inner_mean = cv2.mean(gray, mask=inner)[0]
    outer_mean = cv2.mean(gray, mask=outer)[0]
    return float(np.clip(abs(inner_mean - outer_mean) / 55.0, 0.0, 1.0))


def detect_bright_document_boundary(image):
    """Conservative fallback for bright paper on a contrasting background.

    This detector is intentionally supplementary. It is used only by the
    preparation pipeline to recover cases where the primary Guided/Region
    detector returns a frame-like region instead of the actual sheet.
    """
    if image is None or not isinstance(image, np.ndarray) or image.size == 0:
        raise ValueError("Image must be a valid NumPy array.")

    if image.ndim == 2:
        bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.ndim == 3 and image.shape[2] == 1:
        bgr = cv2.cvtColor(image[:, :, 0], cv2.COLOR_GRAY2BGR)
    elif image.ndim == 3 and image.shape[2] == 4:
        bgr = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    elif image.ndim == 3 and image.shape[2] == 3:
        bgr = image
    else:
        raise ValueError("Unsupported image format.")

    height, width = bgr.shape[:2]
    image_area = float(height * width)
    if min(height, width) < 80:
        return {
            "detected": False,
            "status": "reject",
            "corners": [],
            "confidence": 0.0,
            "area_ratio": 0.0,
            "reason": "rejected: image is too small for bright-paper fallback",
        }

    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    luminance = lab[:, :, 0]
    saturation = hsv[:, :, 1]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    saturation_limit = min(185, max(90, int(np.percentile(saturation, 70))))
    luminance_thresholds = sorted(
        set(
            max(150, min(235, int(np.percentile(luminance, percentile))))
            for percentile in (68, 75, 82, 88)
        )
    )

    candidates = []

    for threshold in luminance_thresholds:
        mask = np.where(
            (luminance >= threshold) & (saturation <= saturation_limit),
            255,
            0,
        ).astype(np.uint8)

        kernel_size = max(5, int(round(min(height, width) * 0.014)))
        if kernel_size % 2 == 0:
            kernel_size += 1
        close_kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
        )
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_kernel, iterations=2)
        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)),
            iterations=1,
        )

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
            contour_area = float(cv2.contourArea(contour))
            if contour_area < image_area * 0.14:
                continue

            hull = cv2.convexHull(contour)
            perimeter = float(cv2.arcLength(hull, True))
            if perimeter <= 0:
                continue

            quadrilateral = None
            for epsilon_ratio in (0.012, 0.018, 0.025, 0.035, 0.05, 0.07):
                approximation = cv2.approxPolyDP(
                    hull, epsilon_ratio * perimeter, True
                )
                if len(approximation) == 4 and cv2.isContourConvex(approximation):
                    quadrilateral = approximation.reshape(4, 2)
                    break

            if quadrilateral is None:
                continue

            corners = _order(quadrilateral)
            polygon_area = abs(float(cv2.contourArea(corners)))
            area_ratio = polygon_area / image_area
            if area_ratio < MIN_AREA_RATIO or area_ratio > MAX_AREA_RATIO:
                continue

            angles = _angles(corners)
            if angles is None or np.min(angles) < 35.0 or np.max(angles) > 145.0:
                continue

            sides = np.asarray(
                [
                    np.linalg.norm(corners[(index + 1) % 4] - corners[index])
                    for index in range(4)
                ],
                dtype=np.float32,
            )
            if np.min(sides) < np.hypot(width, height) * 0.08:
                continue

            angle_error = float(np.mean(np.abs(angles - 90.0)))
            geometry_score = float(
                np.clip(1.0 - angle_error / 60.0, 0.0, 1.0)
            )
            balance_score = float(
                np.sqrt(
                    (min(sides[0], sides[2]) / max(sides[0], sides[2]))
                    * (min(sides[1], sides[3]) / max(sides[1], sides[3]))
                )
            )
            fill_score = float(
                np.clip(contour_area / max(polygon_area, 1.0), 0.0, 1.0)
            )
            contrast_score = _border_contrast(gray, corners)
            clearance = _clearance(corners, width, height)
            clearance_score = float(np.clip(clearance / 0.08, 0.0, 1.0))

            score = (
                0.33 * geometry_score
                + 0.20 * balance_score
                + 0.20 * fill_score
                + 0.22 * contrast_score
                + 0.05 * clearance_score
            )

            candidates.append(
                {
                    "corners": corners,
                    "confidence": float(score),
                    "area_ratio": float(area_ratio),
                    "clearance": float(clearance),
                }
            )

    safe_candidates = [
        candidate
        for candidate in candidates
        if candidate["clearance"] >= MIN_CLEARANCE_RATIO
    ]
    ranked = safe_candidates if safe_candidates else candidates
    ranked.sort(key=lambda item: item["confidence"], reverse=True)

    if not ranked:
        return {
            "detected": False,
            "status": "reject",
            "method_used": "bright",
            "corners": [],
            "confidence": 0.0,
            "area_ratio": 0.0,
            "reason": "rejected: bright-paper detector found no document-like quadrilateral",
        }

    best = ranked[0]
    safe = best["clearance"] >= MIN_CLEARANCE_RATIO
    confidence = float(best["confidence"])

    if safe and confidence >= MIN_SCORE:
        status = "accept_automatic"
        detected = True
        reason = "accepted: bright-paper detector found a fully visible document"
    elif safe and confidence >= REVIEW_SCORE:
        status = "review_required"
        detected = True
        reason = "review required: bright-paper detector found a usable medium-confidence document"
    else:
        status = "reject"
        detected = False
        reason = "rejected: bright-paper detector did not find a safe reviewable document boundary"

    return {
        "detected": detected,
        "status": status,
        "method_used": "bright",
        "corners": [
            [int(round(x)), int(round(y))] for x, y in best["corners"]
        ],
        "confidence": round(confidence, 4),
        "final_score": round(confidence, 4),
        "area_ratio": round(best["area_ratio"], 4),
        "clearance": round(best["clearance"], 6),
        "edge_support": 0.0,
        "reason": reason,
    }
