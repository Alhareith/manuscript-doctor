import cv2
import numpy as np


MIN_AREA_RATIO = 0.14
MAX_AREA_RATIO = 0.94
MIN_SCORE = 0.68
REVIEW_SCORE = 0.44
MIN_CLEARANCE_RATIO = 0.0


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
    values = []
    for index in range(4):
        previous = corners[(index - 1) % 4] - corners[index]
        following = corners[(index + 1) % 4] - corners[index]
        denominator = np.linalg.norm(previous) * np.linalg.norm(following)
        if denominator <= 1e-6:
            return None
        cosine = np.clip(float(np.dot(previous, following) / denominator), -1.0, 1.0)
        values.append(float(np.degrees(np.arccos(cosine))))
    return np.asarray(values, dtype=np.float32)


def _border_contrast(gray, corners):
    height, width = gray.shape[:2]
    polygon = np.round(corners).astype(np.int32)
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillConvexPoly(mask, polygon, 255)

    band = max(5, int(round(min(height, width) * 0.014)))
    if band % 2 == 0:
        band += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (band, band))
    inner = cv2.subtract(mask, cv2.erode(mask, kernel))
    outer = cv2.subtract(cv2.dilate(mask, kernel), mask)

    if cv2.countNonZero(inner) < 80 or cv2.countNonZero(outer) < 80:
        return 0.0

    inner_mean = cv2.mean(gray, mask=inner)[0]
    outer_mean = cv2.mean(gray, mask=outer)[0]
    return float(np.clip(abs(inner_mean - outer_mean) / 45.0, 0.0, 1.0))


def _build_edges(gray):
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    median_value = float(np.median(blurred))
    lower = int(max(18, 0.55 * median_value))
    upper = int(min(255, max(lower + 25, 1.45 * median_value)))
    edges = cv2.Canny(blurred, lower, upper)
    return cv2.dilate(edges, np.ones((3, 3), dtype=np.uint8), iterations=1)


def _edge_support(edges, corners):
    height, width = edges.shape[:2]
    thickness = max(2, int(round(min(height, width) * 0.006)))
    values = []
    corners = _order(corners)

    for index in range(4):
        mask = np.zeros((height, width), dtype=np.uint8)
        a = tuple(np.round(corners[index]).astype(np.int32))
        b = tuple(np.round(corners[(index + 1) % 4]).astype(np.int32))
        cv2.line(mask, a, b, 255, thickness=thickness, lineType=cv2.LINE_AA)
        total = cv2.countNonZero(mask)
        if total <= 0:
            values.append(0.0)
            continue
        overlap = cv2.bitwise_and(edges, mask)
        values.append(float(cv2.countNonZero(overlap)) / float(total))

    if not values:
        return 0.0
    return float(np.mean(values))


def _frame_contacts(corners, width, height, margin_ratio=0.025):
    margin_x = width * margin_ratio
    margin_y = height * margin_ratio
    return int(sum([
        np.min(corners[:, 0]) <= margin_x,
        np.max(corners[:, 0]) >= width - 1 - margin_x,
        np.min(corners[:, 1]) <= margin_y,
        np.max(corners[:, 1]) >= height - 1 - margin_y,
    ]))


def _candidate_from_contour(contour, gray, edges, width, height, image_area, source):
    contour_area = float(cv2.contourArea(contour))
    if contour_area < image_area * 0.12:
        return None

    hull = cv2.convexHull(contour)
    perimeter = float(cv2.arcLength(hull, True))
    if perimeter <= 0:
        return None

    quadrilateral = None
    for epsilon_ratio in (0.012, 0.018, 0.025, 0.035, 0.05, 0.07, 0.10):
        approximation = cv2.approxPolyDP(hull, epsilon_ratio * perimeter, True)
        if len(approximation) == 4 and cv2.isContourConvex(approximation):
            quadrilateral = approximation.reshape(4, 2)
            break

    if quadrilateral is None:
        return None

    corners = _order(quadrilateral)
    polygon_area = abs(float(cv2.contourArea(corners)))
    area_ratio = polygon_area / max(float(image_area), 1.0)
    if area_ratio < MIN_AREA_RATIO or area_ratio > MAX_AREA_RATIO:
        return None

    angles = _angles(corners)
    if angles is None or np.min(angles) < 25.0 or np.max(angles) > 155.0:
        return None

    sides = np.asarray(
        [
            np.linalg.norm(corners[(index + 1) % 4] - corners[index])
            for index in range(4)
        ],
        dtype=np.float32,
    )
    if np.min(sides) < np.hypot(width, height) * 0.08:
        return None

    angle_error = float(np.mean(np.abs(angles - 90.0)))
    angle_score = float(np.clip(1.0 - angle_error / 60.0, 0.0, 1.0))
    balance_score = float(
        np.sqrt(
            (min(sides[0], sides[2]) / max(sides[0], sides[2]))
            * (min(sides[1], sides[3]) / max(sides[1], sides[3]))
        )
    )
    fill_score = float(np.clip(contour_area / max(polygon_area, 1.0), 0.0, 1.0))
    edge_support = _edge_support(edges, corners)
    contrast_score = _border_contrast(gray, corners)
    contacts = _frame_contacts(corners, width, height)
    frame_score = {0: 1.0, 1: 0.88, 2: 0.62}.get(contacts, 0.12)

    low_area_score = float(np.clip((area_ratio - MIN_AREA_RATIO) / 0.16, 0.0, 1.0))
    high_area_score = float(np.clip((MAX_AREA_RATIO - area_ratio) / 0.10, 0.0, 1.0))
    area_score = min(low_area_score, high_area_score)

    score = float(np.clip(
        0.24 * angle_score
        + 0.12 * balance_score
        + 0.20 * edge_support
        + 0.15 * contrast_score
        + 0.10 * fill_score
        + 0.09 * area_score
        + 0.10 * frame_score,
        0.0,
        1.0,
    ))

    return {
        "corners": corners,
        "confidence": score,
        "area_ratio": float(area_ratio),
        "edge_support": float(edge_support),
        "contrast_score": float(contrast_score),
        "angle_score": float(angle_score),
        "balance_score": float(balance_score),
        "fill_score": float(fill_score),
        "frame_contact_count": contacts,
        "source": source,
    }


def _collect_mask_candidates(mask, gray, edges, source):
    height, width = gray.shape[:2]
    image_area = float(height * width)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        candidate = _candidate_from_contour(
            contour, gray, edges, width, height, image_area, source
        )
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def _brightness_masks(bgr):
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    luminance = lab[:, :, 0]
    saturation = hsv[:, :, 1]
    height, width = luminance.shape[:2]

    kernel_size = max(5, int(round(min(height, width) * 0.014)))
    if kernel_size % 2 == 0:
        kernel_size += 1
    close_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
    )

    for luminance_percentile, saturation_percentile in (
        (55, 70),
        (60, 82),
        (65, 70),
        (72, 82),
    ):
        luminance_threshold = float(np.percentile(luminance, luminance_percentile))
        saturation_limit = max(
            55.0, float(np.percentile(saturation, saturation_percentile))
        )
        mask = np.where(
            (luminance >= luminance_threshold)
            & (saturation <= saturation_limit),
            255,
            0,
        ).astype(np.uint8)
        mask = cv2.morphologyEx(
            mask, cv2.MORPH_CLOSE, close_kernel, iterations=2
        )
        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_OPEN,
            np.ones((5, 5), dtype=np.uint8),
            iterations=1,
        )
        yield (
            f"brightness_{luminance_percentile}_{saturation_percentile}",
            mask,
        )


def _grabcut_mask(bgr):
    height, width = bgr.shape[:2]
    mask = np.full((height, width), cv2.GC_PR_BGD, dtype=np.uint8)

    border_x = max(4, int(round(width * 0.025)))
    border_y = max(4, int(round(height * 0.025)))
    mask[:border_y, :] = cv2.GC_BGD
    mask[-border_y:, :] = cv2.GC_BGD
    mask[:, :border_x] = cv2.GC_BGD
    mask[:, -border_x:] = cv2.GC_BGD

    mask[
        int(height * 0.08):int(height * 0.92),
        int(width * 0.08):int(width * 0.92),
    ] = cv2.GC_PR_FGD
    mask[
        int(height * 0.20):int(height * 0.80),
        int(width * 0.18):int(width * 0.82),
    ] = cv2.GC_FGD

    background_model = np.zeros((1, 65), dtype=np.float64)
    foreground_model = np.zeros((1, 65), dtype=np.float64)

    try:
        cv2.grabCut(
            bgr,
            mask,
            None,
            background_model,
            foreground_model,
            1,
            cv2.GC_INIT_WITH_MASK,
        )
    except cv2.error:
        return None

    return np.where(
        (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD),
        255,
        0,
    ).astype(np.uint8)


def detect_bright_document_boundary(image):
    """Hybrid bright/region detector used as an official weak-primary fallback."""
    if image is None or not isinstance(image, np.ndarray) or image.size == 0:
        raise ValueError("Image must be a valid NumPy array.")

    if image.ndim == 2:
        bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.ndim == 3 and image.shape[2] == 1:
        bgr = cv2.cvtColor(image[:, :, 0], cv2.COLOR_GRAY2BGR)
    elif image.ndim == 3 and image.shape[2] == 4:
        bgr = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    elif image.ndim == 3 and image.shape[2] == 3:
        bgr = image.copy()
    else:
        raise ValueError("Unsupported image format.")

    height, width = bgr.shape[:2]
    if min(height, width) < 80:
        return {
            "detected": False,
            "status": "reject",
            "method_used": "bright",
            "corners": [],
            "confidence": 0.0,
            "area_ratio": 0.0,
            "reason": "rejected: image is too small for bright-document detection",
        }

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    if float(np.std(gray)) < 3.0:
        return {
            "detected": False,
            "status": "reject",
            "method_used": "bright",
            "corners": [],
            "confidence": 0.0,
            "area_ratio": 0.0,
            "reason": "rejected: image lacks enough visual structure for a document boundary",
        }

    edges = _build_edges(gray)
    candidates = []

    for source, mask in _brightness_masks(bgr):
        candidates.extend(_collect_mask_candidates(mask, gray, edges, source))

    candidates.sort(key=lambda item: item["confidence"], reverse=True)
    brightness_best = candidates[0] if candidates else None

    needs_grabcut = (
        brightness_best is None
        or brightness_best["confidence"] < 0.64
        or (
            brightness_best["frame_contact_count"] > 0
            and brightness_best["confidence"] < 0.69
        )
    )
    if needs_grabcut:
        cv2.setRNGSeed(0)
        grabcut = _grabcut_mask(bgr)
        if grabcut is not None:
            grab_candidates = _collect_mask_candidates(grabcut, gray, edges, "grabcut")
            grab_candidates.sort(key=lambda item: item["confidence"], reverse=True)
            grab_best = grab_candidates[0] if grab_candidates else None
            grab_is_geometrically_better = (
                grab_best is not None
                and brightness_best is not None
                and grab_best["frame_contact_count"] < brightness_best["frame_contact_count"]
                and grab_best["angle_score"] >= brightness_best["angle_score"] + 0.10
                and grab_best["confidence"] >= brightness_best["confidence"] - 0.01
            )
            if (
                brightness_best is None
                or brightness_best["confidence"] < 0.55
                or (
                    grab_best is not None
                    and grab_best["confidence"] >= brightness_best["confidence"] + 0.03
                )
                or grab_is_geometrically_better
            ):
                candidates.extend(grab_candidates)
                candidates.sort(key=lambda item: item["confidence"], reverse=True)

    if not candidates:
        return {
            "detected": False,
            "status": "reject",
            "method_used": "bright",
            "corners": [],
            "confidence": 0.0,
            "area_ratio": 0.0,
            "reason": "rejected: bright-document detector found no document-like quadrilateral",
        }

    best = candidates[0]
    confidence = float(best["confidence"])
    low_contrast_geometry_rescue = (
        confidence >= 0.58
        and best["contrast_score"] < 0.12
        and (best["contrast_score"] >= 0.025 or best["edge_support"] >= 0.05)
        and best["angle_score"] >= 0.80
        and best["balance_score"] >= 0.70
        and best["fill_score"] >= 0.82
        and best["frame_contact_count"] == 0
        and best["source"] == "grabcut"
    )
    near_frame_geometry_rescue = (
        confidence >= 0.62
        and best["angle_score"] >= 0.84
        and best["balance_score"] >= 0.72
        and best["fill_score"] >= 0.88
        and best["edge_support"] >= 0.14
        and best["contrast_score"] >= 0.14
        and best["frame_contact_count"] <= 2
    )
    clean_geometry_rescue = (
        confidence >= 0.64
        and best["angle_score"] >= 0.80
        and best["balance_score"] >= 0.72
        and best["fill_score"] >= 0.86
        and (best["contrast_score"] >= 0.05 or best["edge_support"] >= 0.08)
        and best["frame_contact_count"] == 0
    )

    if (
        confidence >= MIN_SCORE
        or low_contrast_geometry_rescue
        or near_frame_geometry_rescue
        or clean_geometry_rescue
    ):
        status = "accept_automatic"
        detected = True
        reason = (
            "accepted: low-contrast page passed geometry/region rescue"
            if low_contrast_geometry_rescue and confidence < MIN_SCORE
            else (
                "accepted: near-frame page passed geometry/edge rescue"
                if near_frame_geometry_rescue and confidence < MIN_SCORE
                else (
                    "accepted: clean page passed geometry rescue"
                    if clean_geometry_rescue and confidence < MIN_SCORE
                    else "accepted: bright-document candidate passed hybrid scoring"
                )
            )
        )
    elif confidence >= REVIEW_SCORE:
        status = "review_required"
        detected = True
        reason = "review required: bright-document candidate is usable but not safe for automatic crop"
    else:
        status = "reject"
        detected = False
        reason = "rejected: bright-document candidate failed the review-quality floor"

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
        "edge_support": round(best["edge_support"], 4),
        "contrast_score": round(best["contrast_score"], 4),
        "angle_score": round(best["angle_score"], 4),
        "balance_score": round(best["balance_score"], 4),
        "fill_score": round(best["fill_score"], 4),
        "frame_contact_count": int(best["frame_contact_count"]),
        "candidate_source": best["source"],
        "reason": reason,
    }
