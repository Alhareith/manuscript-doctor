from email.mime import image

import cv2
import numpy as np

from processing.bright_document_fallback import detect_bright_document_boundary
from processing.deterministic_hough import hough_lines_p

MIN_AREA_RATIO = 0.18
MAX_AREA_RATIO = 0.98
MIN_CONFIDENCE = 0.68
MAX_CANDIDATES = 12
APPROX_EPSILON_RATIOS = (0.015, 0.02, 0.025, 0.03)
PREPARATION_REVIEW_MIN_CONFIDENCE = 0.45
PREPARATION_ALLOWED_METHODS = ("guided", "region", "bright")


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


def _order_corners(points):
    points = np.asarray(points, dtype=np.float32).reshape(4, 2)
    ordered = np.zeros((4, 2), dtype=np.float32)

    sums = points.sum(axis=1)
    diffs = np.diff(points, axis=1).reshape(-1)

    ordered[0] = points[np.argmin(sums)]
    ordered[2] = points[np.argmax(sums)]
    ordered[1] = points[np.argmin(diffs)]
    ordered[3] = points[np.argmax(diffs)]

    return ordered


def _corners_inside_image(corners, width, height):
    x = corners[:, 0]
    y = corners[:, 1]

    return bool(
        np.all(x >= 0)
        and np.all(x <= width - 1)
        and np.all(y >= 0)
        and np.all(y <= height - 1)
    )


def _side_lengths(corners):
    return np.array(
        [
            np.linalg.norm(corners[1] - corners[0]),
            np.linalg.norm(corners[2] - corners[1]),
            np.linalg.norm(corners[3] - corners[2]),
            np.linalg.norm(corners[0] - corners[3]),
        ],
        dtype=np.float32,
    )


def _interior_angles(corners):
    angles = []

    for index in range(4):
        previous_point = corners[(index - 1) % 4]
        current_point = corners[index]
        next_point = corners[(index + 1) % 4]

        vector_a = previous_point - current_point
        vector_b = next_point - current_point

        norm_product = np.linalg.norm(vector_a) * np.linalg.norm(vector_b)

        if norm_product <= 1e-6:
            return None

        cosine = float(np.dot(vector_a, vector_b) / norm_product)
        cosine = float(np.clip(cosine, -1.0, 1.0))
        angles.append(float(np.degrees(np.arccos(cosine))))

    return np.array(angles, dtype=np.float32)


def _geometry_scores(corners, image_width, image_height):
    side_lengths = _side_lengths(corners)
    image_diagonal = float(np.hypot(image_width, image_height))

    if np.min(side_lengths) < image_diagonal * 0.08:
        return None, "rejected: one or more document sides are too short"

    angles = _interior_angles(corners)

    if angles is None:
        return None, "rejected: degenerate quadrilateral geometry"

    if np.min(angles) < 25.0 or np.max(angles) > 155.0:
        return None, "rejected: quadrilateral angles are not plausible for a document"

    angle_error = float(np.mean(np.abs(angles - 90.0)))
    angle_score = float(np.clip(1.0 - angle_error / 65.0, 0.0, 1.0))

    top, right, bottom, left = side_lengths

    horizontal_balance = min(top, bottom) / max(top, bottom)
    vertical_balance = min(left, right) / max(left, right)

    side_balance_score = float(np.sqrt(horizontal_balance * vertical_balance))

    return {
        "angle_score": angle_score,
        "side_balance_score": side_balance_score,
    }, None


def _area_score(area_ratio):
    if area_ratio < MIN_AREA_RATIO or area_ratio > MAX_AREA_RATIO:
        return 0.0

    target = 0.70

    if area_ratio <= target:
        return float(
            np.clip((area_ratio - MIN_AREA_RATIO) / (target - MIN_AREA_RATIO), 0.0, 1.0)
        )

    return float(
        np.clip((MAX_AREA_RATIO - area_ratio) / (MAX_AREA_RATIO - target), 0.0, 1.0)
    )


def _candidate_from_contour(contour, image_width, image_height, image_area):
    contour_area = float(cv2.contourArea(contour))

    if contour_area <= 0:
        return None, ("rejected: contour has no measurable area")

    perimeter = float(cv2.arcLength(contour, True))

    if perimeter <= 0:
        return None, ("rejected: contour has no measurable perimeter")

    best_rejection = "rejected: contour could not be " "approximated to four corners"

    for epsilon_ratio in APPROX_EPSILON_RATIOS:
        approximation = cv2.approxPolyDP(contour, epsilon_ratio * perimeter, True)

        if len(approximation) != 4:
            continue

        if not cv2.isContourConvex(approximation):
            best_rejection = "rejected: four-point contour " "is not convex"
            continue

        corners = _order_corners(approximation.reshape(4, 2))

        if not _corners_inside_image(corners, image_width, image_height):
            best_rejection = "rejected: one or more corners " "are outside the image"
            continue

        polygon_area = abs(float(cv2.contourArea(corners.astype(np.float32))))

        area_ratio = polygon_area / image_area

        if area_ratio < MIN_AREA_RATIO:
            return None, ("rejected: candidate occupies " "too little of the image")

        if area_ratio > MAX_AREA_RATIO:
            return None, ("rejected: candidate is too close " "to the full image frame")

        geometry, geometry_rejection = _geometry_scores(
            corners, image_width, image_height
        )

        if geometry is None:
            best_rejection = geometry_rejection
            continue

        contour_fit_score = float(
            np.clip(
                min(contour_area, polygon_area) / max(contour_area, polygon_area),
                0.0,
                1.0,
            )
        )

        area_score = _area_score(area_ratio)

        confidence = (
            0.35 * area_score
            + 0.30 * geometry["angle_score"]
            + 0.20 * contour_fit_score
            + 0.15 * geometry["side_balance_score"]
        )

        return {
            "corners": corners,
            "confidence": float(np.clip(confidence, 0.0, 1.0)),
            "area_ratio": float(area_ratio),
        }, None

    return None, best_rejection


def _extract_cluttered_background_contours(gray):
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)

    edges = cv2.Canny(blurred, 30, 110)

    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))

    connected = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, close_kernel, iterations=2)

    connected = cv2.dilate(
        connected, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)), iterations=1
    )

    contours, _ = cv2.findContours(
        connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    expanded_candidates = []

    for contour in contours:
        if cv2.contourArea(contour) <= 0:
            continue

        hull = cv2.convexHull(contour)

        perimeter = cv2.arcLength(hull, True)

        if perimeter <= 0:
            continue

        for epsilon_ratio in (0.02, 0.03, 0.04, 0.05, 0.06):
            approximation = cv2.approxPolyDP(hull, epsilon_ratio * perimeter, True)

            if len(approximation) == 4:
                expanded_candidates.append(approximation)
                break

    return expanded_candidates


def _border_contrast_score(image, corners):
    height, width = image.shape[:2]

    polygon = np.asarray(corners, dtype=np.int32).reshape(-1, 1, 2)

    mask = np.zeros((height, width), dtype=np.uint8)

    cv2.fillConvexPoly(mask, polygon, 255)

    band_size = max(5, int(round(min(height, width) * 0.012)))

    if band_size % 2 == 0:
        band_size += 1

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (band_size, band_size))

    eroded = cv2.erode(mask, kernel, iterations=1)

    dilated = cv2.dilate(mask, kernel, iterations=1)

    inner_ring = cv2.subtract(mask, eroded)

    outer_ring = cv2.subtract(dilated, mask)

    inner_count = cv2.countNonZero(inner_ring)

    outer_count = cv2.countNonZero(outer_ring)

    if inner_count < 100 or outer_count < 100:
        return 0.0

    if image.ndim == 2:
        channels = [image]

    elif image.ndim == 3 and image.shape[2] == 1:
        channels = [image[:, :, 0]]

    elif image.ndim == 3 and image.shape[2] >= 3:
        channels = [
            image[:, :, 0],
            image[:, :, 1],
            image[:, :, 2],
        ]

    else:
        return 0.0

    scores = []

    for channel in channels:
        inner_hist = cv2.calcHist([channel], [0], inner_ring, [32], [0, 256])

        outer_hist = cv2.calcHist([channel], [0], outer_ring, [32], [0, 256])

        cv2.normalize(inner_hist, inner_hist, 1.0, 0.0, cv2.NORM_L1)

        cv2.normalize(outer_hist, outer_hist, 1.0, 0.0, cv2.NORM_L1)

        distance = cv2.compareHist(inner_hist, outer_hist, cv2.HISTCMP_CHISQR_ALT)

        score = float(np.clip(distance / 2.0, 0.0, 1.0))

        scores.append(score)

    if not scores:
        return 0.0

    return float(np.mean(scores))


def _rank_boundary_candidate(image, candidate):
    contrast_score = _border_contrast_score(image, candidate["corners"])

    geometry_score = float(candidate["confidence"])

    final_score = 0.62 * geometry_score + 0.38 * contrast_score

    if candidate.get("touches_frame", False):
        final_score *= 0.78

    candidate["contrast_score"] = contrast_score
    candidate["final_score"] = float(np.clip(final_score, 0.0, 1.0))

    return candidate


def _angle_distance(angle_a, angle_b):
    diff = abs(angle_a - angle_b) % 180.0
    return min(diff, 180.0 - diff)


def _line_from_segment(x1, y1, x2, y2):
    a = float(y1 - y2)
    b = float(x2 - x1)
    c = float(x1 * y2 - x2 * y1)

    norm = float(np.hypot(a, b))

    if norm <= 1e-6:
        return None

    a /= norm
    b /= norm
    c /= norm

    if a < 0 or (abs(a) <= 1e-6 and b < 0):
        a = -a
        b = -b
        c = -c

    return np.array([a, b, c], dtype=np.float64)


def _intersection_of_lines(line_a, line_b):
    a1, b1, c1 = line_a
    a2, b2, c2 = line_b

    determinant = a1 * b2 - a2 * b1

    if abs(determinant) < 1e-6:
        return None

    x = (b1 * c2 - b2 * c1) / determinant
    y = (c1 * a2 - c2 * a1) / determinant

    if not np.isfinite(x) or not np.isfinite(y):
        return None

    return np.array([x, y], dtype=np.float32)


def _unique_extreme_lines(lines, center, diagonal, count=4):
    prepared = []

    for item in lines:
        line = item["line"]

        distance = float(line[0] * center[0] + line[1] * center[1] + line[2])

        prepared.append(
            {
                **item,
                "offset": distance,
            }
        )

    prepared.sort(key=lambda item: item["offset"])

    tolerance = diagonal * 0.015

    unique = []

    for item in prepared:
        if all(
            abs(item["offset"] - existing["offset"]) > tolerance for existing in unique
        ):
            unique.append(item)

    if len(unique) < 2:
        return [], []

    low = unique[:count]
    high = unique[-count:]

    return low, high


def _frame_contact_count(corners, width, height, margin_ratio=0.04):
    corners = np.asarray(corners, dtype=np.float32).reshape(4, 2)

    margin_x = width * margin_ratio
    margin_y = height * margin_ratio

    touches_left = bool(np.min(corners[:, 0]) <= margin_x)
    touches_right = bool(np.max(corners[:, 0]) >= width - 1 - margin_x)
    touches_top = bool(np.min(corners[:, 1]) <= margin_y)
    touches_bottom = bool(np.max(corners[:, 1]) >= height - 1 - margin_y)

    return sum(
        [
            touches_left,
            touches_right,
            touches_top,
            touches_bottom,
        ]
    )


def _extract_hough_document_candidate(image, gray):
    height, width = gray.shape[:2]

    image_area = float(width * height)
    diagonal = float(np.hypot(width, height))

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    enhanced = clahe.apply(blurred)

    median_value = float(np.median(enhanced))

    lower = int(max(20, 0.55 * median_value))

    upper = int(min(255, max(lower + 30, 1.45 * median_value)))

    edges = cv2.Canny(enhanced, lower, upper)

    edges = cv2.morphologyEx(
        edges,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)),
        iterations=1,
    )

    minimum_line_length = max(40, int(diagonal * 0.14))

    maximum_line_gap = max(10, int(diagonal * 0.035))

    lines = hough_lines_p(
        edges,
        rho=1,
        theta=np.pi / 180.0,
        threshold=max(40, int(min(height, width) * 0.06)),
        min_line_length=minimum_line_length,
        max_line_gap=maximum_line_gap,
    )

    if lines is None:
        return None

    segments = []

    angle_histogram = np.zeros(36, dtype=np.float64)

    lines = np.asarray(lines, dtype=np.int32).reshape(-1, 4)

    for raw_line in lines:
        x1, y1, x2, y2 = [int(value) for value in raw_line]

        dx = float(x2 - x1)
        dy = float(y2 - y1)

        length = float(np.hypot(dx, dy))

        if length < minimum_line_length:
            continue

        angle = float(np.degrees(np.arctan2(dy, dx)) % 180.0)

        equation = _line_from_segment(x1, y1, x2, y2)

        if equation is None:
            continue

        segment = {
            "line": equation,
            "length": length,
            "angle": angle,
        }

        segments.append(segment)

        histogram_index = int(angle // 5.0) % 36

        angle_histogram[histogram_index] += length

    if len(segments) < 4:
        return None

    primary_bin = int(np.argmax(angle_histogram))

    primary_angle = primary_bin * 5.0 + 2.5

    secondary_angle = (primary_angle + 90.0) % 180.0

    angle_tolerance = 20.0

    family_a = [
        segment
        for segment in segments
        if _angle_distance(segment["angle"], primary_angle) <= angle_tolerance
    ]

    family_b = [
        segment
        for segment in segments
        if _angle_distance(segment["angle"], secondary_angle) <= angle_tolerance
    ]

    if len(family_a) < 2 or len(family_b) < 2:
        return None

    center = np.array([width / 2.0, height / 2.0], dtype=np.float64)

    a_low, a_high = _unique_extreme_lines(family_a, center, diagonal)

    b_low, b_high = _unique_extreme_lines(family_b, center, diagonal)

    if not a_low or not a_high or not b_low or not b_high:
        return None

    best_candidate = None

    for side_a1 in a_low:
        for side_a2 in a_high:
            if side_a1 is side_a2:
                continue

            for side_b1 in b_low:
                for side_b2 in b_high:
                    if side_b1 is side_b2:
                        continue

                    p1 = _intersection_of_lines(side_a1["line"], side_b1["line"])

                    p2 = _intersection_of_lines(side_a1["line"], side_b2["line"])

                    p3 = _intersection_of_lines(side_a2["line"], side_b2["line"])

                    p4 = _intersection_of_lines(side_a2["line"], side_b1["line"])

                    if any(point is None for point in (p1, p2, p3, p4)):
                        continue

                    corners = _order_corners(
                        np.array([p1, p2, p3, p4], dtype=np.float32)
                    )

                    if not _corners_inside_image(corners, width, height):
                        continue
                    frame_contacts = _frame_contact_count(corners, width, height)

                    if frame_contacts >= 3:
                        continue

                    polygon = corners.astype(np.float32)

                    if not cv2.isContourConvex(polygon.astype(np.int32)):
                        continue

                    polygon_area = abs(float(cv2.contourArea(polygon)))

                    area_ratio = polygon_area / image_area

                    if area_ratio < MIN_AREA_RATIO or area_ratio > MAX_AREA_RATIO:
                        continue

                    geometry, _ = _geometry_scores(corners, width, height)

                    if geometry is None:
                        continue

                    area_score = _area_score(area_ratio)

                    line_support = float(
                        np.clip(
                            np.mean(
                                [
                                    side_a1["length"],
                                    side_a2["length"],
                                    side_b1["length"],
                                    side_b2["length"],
                                ]
                            )
                            / diagonal,
                            0.0,
                            1.0,
                        )
                    )

                    confidence = (
                        0.30 * area_score
                        + 0.35 * geometry["angle_score"]
                        + 0.20 * geometry["side_balance_score"]
                        + 0.15 * line_support
                    )

                    margin_x = width * 0.025
                    margin_y = height * 0.025

                    touches_frame = frame_contacts > 0

                    candidate = {
                        "corners": corners,
                        "confidence": float(np.clip(confidence, 0.0, 1.0)),
                        "area_ratio": float(area_ratio),
                        "touches_frame": touches_frame,
                    }

                    candidate = _rank_boundary_candidate(image, candidate)

                    if (
                        best_candidate is None
                        or candidate["final_score"] > best_candidate["final_score"]
                    ):
                        best_candidate = candidate

    return best_candidate


def _extract_region_document_candidates(image, gray):
    height, width = gray.shape[:2]
    image_area = float(width * height)

    if image.ndim == 2:
        working = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.ndim == 3 and image.shape[2] == 1:
        working = cv2.cvtColor(image[:, :, 0], cv2.COLOR_GRAY2BGR)
    elif image.ndim == 3 and image.shape[2] == 4:
        working = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    else:
        working = image.copy()

    working = cv2.GaussianBlur(working, (5, 5), 0)

    margin_x = max(5, int(width * 0.04))

    margin_y = max(5, int(height * 0.04))

    mask = np.full((height, width), cv2.GC_PR_BGD, dtype=np.uint8)

    mask[:margin_y, :] = cv2.GC_BGD
    mask[height - margin_y :, :] = cv2.GC_BGD
    mask[:, :margin_x] = cv2.GC_BGD
    mask[:, width - margin_x :] = cv2.GC_BGD

    center_x1 = int(width * 0.18)
    center_x2 = int(width * 0.82)
    center_y1 = int(height * 0.12)
    center_y2 = int(height * 0.88)

    mask[center_y1:center_y2, center_x1:center_x2] = cv2.GC_PR_FGD

    background_model = np.zeros((1, 65), dtype=np.float64)

    foreground_model = np.zeros((1, 65), dtype=np.float64)

    try:
        cv2.grabCut(
            working,
            mask,
            None,
            background_model,
            foreground_model,
            5,
            cv2.GC_INIT_WITH_MASK,
        )
    except cv2.error:
        return []

    foreground = np.where(
        (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0
    ).astype(np.uint8)

    close_size = max(5, int(round(min(width, height) * 0.025)))

    if close_size % 2 == 0:
        close_size += 1

    foreground = cv2.morphologyEx(
        foreground,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_size, close_size)),
        iterations=2,
    )

    foreground = cv2.morphologyEx(
        foreground,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)),
        iterations=1,
    )

    contours, _ = cv2.findContours(
        foreground, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:8]

    candidates = []

    for contour in contours:
        contour_area = float(cv2.contourArea(contour))

        contour_ratio = contour_area / image_area

        if contour_ratio < MIN_AREA_RATIO * 0.70:
            continue

        hull = cv2.convexHull(contour)

        perimeter = float(cv2.arcLength(hull, True))

        if perimeter <= 0:
            continue

        quadrilateral = None

        for epsilon_ratio in (0.015, 0.02, 0.025, 0.03, 0.04, 0.05):
            approximation = cv2.approxPolyDP(hull, epsilon_ratio * perimeter, True)

            if len(approximation) == 4:
                quadrilateral = approximation
                break

        if quadrilateral is None:
            rectangle = cv2.minAreaRect(hull)

            quadrilateral = cv2.boxPoints(rectangle).reshape(-1, 1, 2)

        corners = _order_corners(
            np.asarray(quadrilateral, dtype=np.float32).reshape(4, 2)
        )

        if not _corners_inside_image(corners, width, height):
            continue

        if not cv2.isContourConvex(corners.astype(np.int32)):
            continue

        polygon_area = abs(float(cv2.contourArea(corners.astype(np.float32))))

        area_ratio = polygon_area / image_area

        if area_ratio < MIN_AREA_RATIO or area_ratio > MAX_AREA_RATIO:
            continue

        geometry, _ = _geometry_scores(corners, width, height)

        if geometry is None:
            continue

        frame_contacts = _frame_contact_count(corners, width, height)

        if frame_contacts >= 3:
            continue

        foreground_fit = float(np.clip(contour_area / max(polygon_area, 1.0), 0.0, 1.0))

        confidence = (
            0.25 * _area_score(area_ratio)
            + 0.30 * geometry["angle_score"]
            + 0.20 * geometry["side_balance_score"]
            + 0.25 * foreground_fit
        )

        candidate = {
            "corners": corners,
            "confidence": float(np.clip(confidence, 0.0, 1.0)),
            "area_ratio": float(area_ratio),
            "touches_frame": (frame_contacts > 0),
        }

        candidate = _rank_boundary_candidate(image, candidate)

        candidates.append(candidate)

    candidates.sort(key=lambda item: item["final_score"], reverse=True)

    return candidates

def _extract_guided_region_candidate(image, guide_candidate):
    if guide_candidate is None:
        return None

    height, width = image.shape[:2]
    image_area = float(width * height)

    corners = np.asarray(guide_candidate["corners"], dtype=np.float32).reshape(4, 2)
    center = np.mean(corners, axis=0)

    expanded = center + (corners - center) * 1.18
    expanded[:, 0] = np.clip(expanded[:, 0], 0, width - 1)
    expanded[:, 1] = np.clip(expanded[:, 1], 0, height - 1)

    inner = center + (corners - center) * 0.72
    inner[:, 0] = np.clip(inner[:, 0], 0, width - 1)
    inner[:, 1] = np.clip(inner[:, 1], 0, height - 1)

    mask = np.full((height, width), cv2.GC_PR_BGD, dtype=np.uint8)

    border_x = max(5, int(width * 0.025))
    border_y = max(5, int(height * 0.025))

    mask[:border_y, :] = cv2.GC_BGD
    mask[-border_y:, :] = cv2.GC_BGD
    mask[:, :border_x] = cv2.GC_BGD
    mask[:, -border_x:] = cv2.GC_BGD

    cv2.fillConvexPoly(mask, np.round(expanded).astype(np.int32), cv2.GC_PR_FGD)
    cv2.fillConvexPoly(mask, np.round(inner).astype(np.int32), cv2.GC_FGD)

    bg_model = np.zeros((1, 65), dtype=np.float64)
    fg_model = np.zeros((1, 65), dtype=np.float64)

    try:
        cv2.grabCut(image, mask, None, bg_model, fg_model, 7, cv2.GC_INIT_WITH_MASK)
    except cv2.error:
        return None

    foreground = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)

    kernel_size = max(5, int(round(min(height, width) * 0.015)))

    if kernel_size % 2 == 0:
        kernel_size += 1

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))

    foreground = cv2.morphologyEx(foreground, cv2.MORPH_CLOSE, kernel, iterations=2)
    foreground = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)), iterations=1)

    contours, _ = cv2.findContours(foreground, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    candidates = []

    for contour in contours:
        contour_area = float(cv2.contourArea(contour))

        if contour_area / image_area < MIN_AREA_RATIO:
            continue

        hull = cv2.convexHull(contour)
        perimeter = float(cv2.arcLength(hull, True))

        if perimeter <= 0:
            continue

        quadrilateral = None

        for epsilon_ratio in (0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05):
            approximation = cv2.approxPolyDP(hull, epsilon_ratio * perimeter, True)

            if len(approximation) == 4:
                quadrilateral = approximation.reshape(4, 2).astype(np.float32)
                break

        if quadrilateral is None:
            continue

        candidate, _ = _candidate_from_contour(quadrilateral.reshape(-1, 1, 2), width, height, image_area)

        if candidate is None:
            continue

        candidate["touches_frame"] = False
        candidate = _rank_boundary_candidate(image, candidate)
        candidates.append(candidate)

    if not candidates:
        return None

    candidates.sort(key=lambda item: item["final_score"], reverse=True)

    return candidates[0]


def detect_document_boundary(image):
    gray = _to_gray(image)

    height, width = gray.shape[:2]
    image_area = float(width * height)

    if width < 80 or height < 80:
        return {
            "detected": False,
            "corners": [],
            "confidence": 0.0,
            "area_ratio": 0.0,
            "reason": "rejected: image is too small for reliable boundary detection",
        }

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    median_intensity = float(np.median(blurred))

    lower = int(max(20, 0.66 * median_intensity))

    upper = int(min(255, max(lower + 20, 1.33 * median_intensity)))

    edges = cv2.Canny(blurred, lower, upper)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

    connected_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(
        connected_edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
    )

    candidates = []

    best_rejection = "rejected: no reliable " "document quadrilateral was found"

    contours = sorted(contours, key=cv2.contourArea, reverse=True)[: MAX_CANDIDATES * 4]

    for contour in contours:
        contour_area_ratio = float(cv2.contourArea(contour)) / image_area

        if contour_area_ratio < MIN_AREA_RATIO * 0.60:
            continue

        candidate, rejection = _candidate_from_contour(
            contour, width, height, image_area
        )

        if candidate is None:
            if rejection:
                best_rejection = rejection

            continue

        corners = candidate["corners"]

        margin_x = width * 0.025

        margin_y = height * 0.025

        candidate["touches_frame"] = bool(
            np.any(corners[:, 0] <= margin_x)
            or np.any(corners[:, 0] >= width - 1 - margin_x)
            or np.any(corners[:, 1] <= margin_y)
            or np.any(corners[:, 1] >= height - 1 - margin_y)
        )

        candidates.append(candidate)

    fallback_contours = _extract_cluttered_background_contours(gray)

    for contour in fallback_contours:
        candidate, rejection = _candidate_from_contour(
            contour, width, height, image_area
        )

        if candidate is None:
            if rejection:
                best_rejection = rejection

            continue

        candidate["touches_frame"] = False

        candidates.append(candidate)

    ranked_candidates = []

    for candidate in candidates:
        ranked_candidates.append(_rank_boundary_candidate(image, candidate))

    ranked_candidates.sort(key=lambda item: item["final_score"], reverse=True)

    best_candidate = ranked_candidates[0] if ranked_candidates else None

    if (best_candidate is None or best_candidate["final_score"] < MIN_CONFIDENCE):
        region_candidates = _extract_region_document_candidates(image,gray )

        if region_candidates:
            region_candidate = region_candidates[0]

            if (
                best_candidate is None
                or region_candidate["final_score"] > best_candidate["final_score"]):
                best_candidate = region_candidate

    if best_candidate is None or best_candidate["final_score"] < MIN_CONFIDENCE:
        hough_candidate = _extract_hough_document_candidate(image, gray)
        guided_candidate = _extract_guided_region_candidate(image, hough_candidate)

        if guided_candidate is not None:
            if best_candidate is None or guided_candidate["final_score"] > best_candidate["final_score"]:
                best_candidate = guided_candidate
                if hough_candidate is not None and (
                    best_candidate is None
                    or hough_candidate["final_score"] > best_candidate["final_score"]
                ):
                    best_candidate = hough_candidate

    if best_candidate is None:
        return {
            "detected": False,
            "corners": [],
            "confidence": 0.0,
            "area_ratio": 0.0,
            "reason": (
                "rejected: contour and Hough detectors "
                "could not find a reliable document boundary"
            ),
        }

    confidence = float(best_candidate["final_score"])

    area_ratio = float(best_candidate["area_ratio"])

    if confidence < MIN_CONFIDENCE:
        diagnostic_corners = [
            [int(round(x)), int(round(y))] for x, y in best_candidate["corners"]
        ]

        return {
            "detected": False,
            "corners": diagnostic_corners,
            "confidence": round(confidence, 4),
            "area_ratio": round(area_ratio, 4),
            "reason": (
                "rejected: document-like boundary was found, "
                "but geometry and inside/outside contrast were "
                "not reliable enough"
            ),
        }

    corners = [[int(round(x)), int(round(y))] for x, y in best_candidate["corners"]]

    return {
        "detected": True,
        "corners": corners,
        "confidence": round(confidence, 4),
        "area_ratio": round(area_ratio, 4),
        "reason": (
            "accepted: document boundary passed "
            "geometry and inside/outside "
            "contrast ranking"
        ),
    }

def _edge_support_for_corners(image, corners):
    gray = _to_gray(image)
    height, width = gray.shape[:2]
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    median_value = float(np.median(blurred))
    lower = int(max(18, 0.55 * median_value))
    upper = int(min(255, max(lower + 25, 1.45 * median_value)))
    edges = cv2.Canny(blurred, lower, upper)
    edges = cv2.dilate(
        edges,
        cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)),
        iterations=1,
    )

    ordered = _order_corners(corners)
    thickness = max(2, int(round(min(height, width) * 0.006)))
    supports = []

    for index in range(4):
        mask = np.zeros((height, width), dtype=np.uint8)
        a = tuple(np.round(ordered[index]).astype(np.int32))
        b = tuple(np.round(ordered[(index + 1) % 4]).astype(np.int32))
        cv2.line(mask, a, b, 255, thickness=thickness, lineType=cv2.LINE_AA)
        total = cv2.countNonZero(mask)
        if total <= 0:
            supports.append(0.0)
            continue
        overlap = cv2.bitwise_and(edges, mask)
        supports.append(float(cv2.countNonZero(overlap)) / float(total))

    mean_support = float(np.mean(supports)) if supports else 0.0
    minimum_support = float(np.min(supports)) if supports else 0.0
    combined = float(np.clip((0.68 * mean_support) + (0.32 * minimum_support), 0.0, 1.0))
    return combined, supports


def _downscale_support_stability(image, corners):
    height, width = image.shape[:2]
    longest = max(height, width)
    if longest <= 420:
        return 1.0

    scale = 420.0 / float(longest)
    proxy = cv2.resize(
        image,
        (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
        interpolation=cv2.INTER_AREA,
    )
    scaled_corners = _order_corners(corners) * scale
    original_support, _ = _edge_support_for_corners(image, corners)
    proxy_support, _ = _edge_support_for_corners(proxy, scaled_corners)

    if original_support <= 1e-6:
        return 0.0

    ratio = min(original_support, proxy_support) / max(original_support, proxy_support, 1e-6)
    absolute = float(np.clip(proxy_support / 0.34, 0.0, 1.0))
    return float(np.clip((0.65 * ratio) + (0.35 * absolute), 0.0, 1.0))


def _preparation_area_score(area_ratio):
    if area_ratio < MIN_AREA_RATIO or area_ratio > MAX_AREA_RATIO:
        return 0.0

    low = float(np.clip((area_ratio - MIN_AREA_RATIO) / 0.16, 0.0, 1.0))
    high = float(np.clip((MAX_AREA_RATIO - area_ratio) / 0.10, 0.0, 1.0))
    return min(low, high)


def _preparation_candidate_payload(image, method, candidate):
    empty = {
        "method_used": method,
        "status": "reject",
        "detected": False,
        "corners": [],
        "confidence": 0.0,
        "final_score": 0.0,
        "area_ratio": 0.0,
        "edge_support": 0.0,
        "contrast_score": 0.0,
        "angle_score": 0.0,
        "stability_score": 0.0,
        "frame_contact_count": 0,
    }

    if candidate is None or not candidate.get("corners"):
        return {
            **empty,
            "reason": f"rejected: {method} did not produce a valid quadrilateral",
        }

    height, width = image.shape[:2]
    image_area = float(width * height)
    corners = _order_corners(
        np.asarray(candidate["corners"], dtype=np.float32).reshape(4, 2)
    )

    if not _corners_inside_image(corners, width, height):
        return {
            **empty,
            "reason": f"rejected: {method} produced corners outside the image",
        }

    if not cv2.isContourConvex(corners.astype(np.int32)):
        return {
            **empty,
            "reason": f"rejected: {method} produced a non-convex quadrilateral",
        }

    polygon_area = abs(float(cv2.contourArea(corners.astype(np.float32))))
    area_ratio = polygon_area / max(image_area, 1.0)
    geometry, geometry_rejection = _geometry_scores(corners, width, height)

    if geometry is None or not (MIN_AREA_RATIO <= area_ratio <= MAX_AREA_RATIO):
        return {
            **empty,
            "corners": [[int(round(x)), int(round(y))] for x, y in corners],
            "area_ratio": round(float(area_ratio), 4),
            "reason": geometry_rejection or f"rejected: {method} area is not plausible",
        }

    edge_support, side_edge_support = _edge_support_for_corners(image, corners)
    contrast_score = _border_contrast_score(image, corners)
    stability_score = _downscale_support_stability(image, corners)
    area_score = _preparation_area_score(area_ratio)
    frame_contacts = _frame_contact_count(corners, width, height)
    frame_score = {0: 1.0, 1: 0.88, 2: 0.62}.get(frame_contacts, 0.12)
    source_score = float(
        np.clip(candidate.get("final_score", candidate.get("confidence", 0.0)), 0.0, 1.0)
    )

    confidence = float(np.clip(
        0.22 * geometry["angle_score"]
        + 0.11 * geometry["side_balance_score"]
        + 0.23 * edge_support
        + 0.15 * contrast_score
        + 0.09 * area_score
        + 0.08 * frame_score
        + 0.07 * stability_score
        + 0.05 * source_score,
        0.0,
        1.0,
    ))

    low_contrast_bright_profile = (
        method == "bright"
        and candidate.get("status") == "accept_automatic"
        and candidate.get("candidate_source") == "grabcut"
        and float(candidate.get("confidence", 0.0)) >= 0.58
        and float(candidate.get("angle_score", 0.0)) >= 0.82
        and float(candidate.get("balance_score", 0.0)) >= 0.75
        and float(candidate.get("fill_score", 0.0)) >= 0.90
        and 0.22 <= area_ratio <= 0.82
        and frame_contacts == 0
    )
    bright_profile_accepted = (
        method == "bright"
        and candidate.get("status") == "accept_automatic"
        and float(candidate.get("confidence", 0.0)) >= 0.58
        and geometry["angle_score"] >= 0.50
        and frame_contacts <= 2
        and (
            stability_score >= 0.42
            or low_contrast_bright_profile
        )
    )

    automatic_ok = (
        (
            confidence >= MIN_CONFIDENCE
            and geometry["angle_score"] >= 0.55
            and edge_support >= 0.22
            and stability_score >= 0.42
            and frame_contacts <= 2
        )
        or bright_profile_accepted
    )
    review_ok = (
        confidence >= PREPARATION_REVIEW_MIN_CONFIDENCE
        and geometry["angle_score"] >= 0.38
        and edge_support >= 0.08
        and frame_contacts <= 2
    )

    if automatic_ok:
        status = "accept_automatic"
        reason = (
            f"accepted: {method} passed detector-specific geometry/stability profile"
            if bright_profile_accepted
            else f"accepted: {method} passed unified geometry, edge, contrast and stability scoring"
        )
    elif review_ok:
        status = "review_required"
        reason = f"review required: {method} produced a usable medium-confidence boundary"
    else:
        status = "reject"
        reason = f"rejected: {method} failed unified boundary quality checks"

    return {
        "method_used": method,
        "status": status,
        "detected": status != "reject",
        "corners": [[int(round(x)), int(round(y))] for x, y in corners],
        "confidence": round(confidence, 4),
        "final_score": round(confidence, 4),
        "area_ratio": round(float(area_ratio), 4),
        "edge_support": round(float(edge_support), 4),
        "side_edge_support": [round(float(value), 4) for value in side_edge_support],
        "contrast_score": round(float(contrast_score), 4),
        "angle_score": round(float(geometry["angle_score"]), 4),
        "side_balance_score": round(float(geometry["side_balance_score"]), 4),
        "stability_score": round(float(stability_score), 4),
        "frame_contact_count": int(frame_contacts),
        "source_confidence": round(float(source_score), 4),
        "reason": reason,
    }


def _not_run_preparation_candidate(method, reason):
    return {
        "method_used": method,
        "status": "not_run",
        "detected": False,
        "corners": [],
        "confidence": 0.0,
        "final_score": 0.0,
        "area_ratio": 0.0,
        "edge_support": 0.0,
        "contrast_score": 0.0,
        "angle_score": 0.0,
        "stability_score": 0.0,
        "frame_contact_count": 0,
        "reason": reason,
    }


def detect_preparation_boundary(image):
    """Select a Preparation boundary from Guided, Region and Bright candidates.

    Guided remains the first path. Region and Bright are evaluated lazily only
    when the preceding result is not strong enough. Every candidate is then
    normalized through the same geometry/edge/contrast/stability score.
    """
    gray = _to_gray(image)

    height, width = gray.shape[:2]
    if width < 80 or height < 80:
        candidates = {
            method: _preparation_candidate_payload(image, method, None)
            for method in PREPARATION_ALLOWED_METHODS
        }
        return {
            "detected": False,
            "status": "reject",
            "method_used": None,
            "corners": [],
            "confidence": 0.0,
            "final_score": 0.0,
            "area_ratio": 0.0,
            "edge_support": 0.0,
            "candidates": candidates,
            "allowed_methods": list(PREPARATION_ALLOWED_METHODS),
            "reason": "rejected: image is too small for Preparation boundary detection",
        }

    hough_seed = _extract_hough_document_candidate(image, gray)
    guided_candidate = _extract_guided_region_candidate(image, hough_seed)
    guided = _preparation_candidate_payload(image, "guided", guided_candidate)

    region = _not_run_preparation_candidate(
        "region", "skipped: Guided/Bright produced a strong candidate"
    )
    bright = _not_run_preparation_candidate(
        "bright", "skipped: Guided was already strong"
    )

    guided_strong = (
        guided["status"] == "accept_automatic"
        and guided["confidence"] >= 0.76
        and guided.get("stability_score", 0.0) >= 0.58
    )

    if not guided_strong:
        bright_candidate = detect_bright_document_boundary(image)
        bright = _preparation_candidate_payload(image, "bright", bright_candidate)

    bright_strong = (
        bright["status"] == "accept_automatic"
        and bright.get("stability_score", 0.0) >= 0.42
    )

    if not guided_strong and not bright_strong:
        region_candidates = _extract_region_document_candidates(image, gray)
        region_candidate = region_candidates[0] if region_candidates else None
        region = _preparation_candidate_payload(image, "region", region_candidate)

    candidates = {
        "guided": guided,
        "region": region,
        "bright": bright,
    }

    usable = [
        item for item in candidates.values()
        if item["status"] in {"accept_automatic", "review_required"}
    ]

    if usable:
        selected = max(
            usable,
            key=lambda item: (
                1 if item["status"] == "accept_automatic" else 0,
                item["confidence"],
                item.get("edge_support", 0.0),
            ),
        )
        return {
            **selected,
            "candidates": candidates,
            "allowed_methods": list(PREPARATION_ALLOWED_METHODS),
        }

    diagnostics = [
        item for item in candidates.values()
        if item["status"] != "not_run" and item.get("corners")
    ]
    diagnostic = max(diagnostics, key=lambda item: item["confidence"], default=None)

    return {
        "detected": False,
        "status": "reject",
        "method_used": diagnostic.get("method_used") if diagnostic else None,
        "corners": diagnostic.get("corners", []) if diagnostic else [],
        "confidence": diagnostic.get("confidence", 0.0) if diagnostic else 0.0,
        "final_score": diagnostic.get("final_score", 0.0) if diagnostic else 0.0,
        "area_ratio": diagnostic.get("area_ratio", 0.0) if diagnostic else 0.0,
        "edge_support": diagnostic.get("edge_support", 0.0) if diagnostic else 0.0,
        "candidates": candidates,
        "allowed_methods": list(PREPARATION_ALLOWED_METHODS),
        "reason": "rejected: no candidate passed the unified review-quality floor",
    }
