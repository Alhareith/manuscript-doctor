import cv2
import numpy as np

from .common import _validate_image

CURVATURE_REDUCTION_MIN = 0.70
DEWARP_ANALYSIS_MAX_DIMENSION = 1200
DEWARP_ANALYSIS_MAX_PIXELS = 1_000_000


def _to_gray(image):
    if image.ndim == 2:
        return image
    if image.shape[2] == 1:
        return image[:, :, 0]
    if image.shape[2] == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)


def _proxy(image):
    h, w = image.shape[:2]
    if h * w <= DEWARP_ANALYSIS_MAX_PIXELS and max(h, w) <= DEWARP_ANALYSIS_MAX_DIMENSION:
        return image, 1.0
    pixel_scale = (DEWARP_ANALYSIS_MAX_PIXELS / max(h * w, 1)) ** 0.5
    dimension_scale = DEWARP_ANALYSIS_MAX_DIMENSION / max(h, w)
    scale = min(1.0, pixel_scale, dimension_scale)
    size = (max(1, int(round(w * scale))), max(1, int(round(h * scale))))
    return cv2.resize(image, size, interpolation=cv2.INTER_AREA), scale


def _find_peaks(signal, min_distance, threshold):
    candidates = [
        i for i in range(1, len(signal) - 1)
        if signal[i] >= signal[i - 1]
        and signal[i] >= signal[i + 1]
        and signal[i] >= threshold
    ]
    ranked = sorted(candidates, key=lambda i: float(signal[i]), reverse=True)
    accepted = []
    for index in ranked:
        if all(abs(index - other) >= min_distance for other in accepted):
            accepted.append(index)
    return np.array(sorted(accepted), dtype=np.int32)


def _strip_profile(ink, center, half_width):
    h, w = ink.shape[:2]
    left = max(0, int(center - half_width))
    right = min(w, int(center + half_width + 1))
    profile = ink[:, left:right].mean(axis=1).astype(np.float32)
    return cv2.GaussianBlur(profile.reshape(-1, 1), (1, 0), sigmaX=0, sigmaY=1.4).ravel()


def detect_text_line_curvature(gray, strips=41):
    h, w = gray.shape[:2]
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, ink = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    ink = cv2.morphologyEx(
        ink,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (13, 1)),
    )

    projection = ink.mean(axis=1).astype(np.float32)
    projection = cv2.GaussianBlur(
        projection.reshape(-1, 1), (1, 0), sigmaX=0, sigmaY=2.5
    ).ravel()
    threshold = max(2.0, float(np.percentile(projection, 72) * 0.75))
    peaks = _find_peaks(projection, max(18, h // 50), threshold)
    peaks = peaks[(peaks > 25) & (peaks < h - 25)]

    if len(peaks) < 5:
        return {"status": "insufficient_text", "line_count": int(len(peaks))}

    spacing_values = np.diff(peaks).astype(np.float32)
    spacing = float(np.median(spacing_values))
    if spacing < 12.0 or float(np.max(spacing_values)) > spacing * 2.5:
        return {"status": "insufficient_text", "line_count": int(len(peaks))}

    centers = np.linspace(int(round(w * 0.05)), int(round(w * 0.95)), strips).astype(np.int32)
    step = max(1, int(centers[1] - centers[0]))
    half_width = max(6, int(round(step * 0.55)))
    profiles = np.vstack([_strip_profile(ink, int(c), half_width) for c in centers])

    middle = strips // 2
    middle_profile = profiles[middle]
    middle_threshold = max(2.0, float(np.percentile(middle_profile, 70) * 0.55))
    seeds = _find_peaks(
        middle_profile,
        max(12, int(round(spacing * 0.55))),
        middle_threshold,
    )
    seeds = seeds[(seeds > 25) & (seeds < h - 25)]
    if len(seeds) < 5:
        return {"status": "insufficient_text", "line_count": int(len(seeds))}

    seed_gaps = np.diff(seeds).astype(np.float32)
    tracked_spacing = float(np.median(seed_gaps))
    if (
        tracked_spacing < 12.0
        or float(np.min(seed_gaps)) < tracked_spacing * 0.55
        or float(np.max(seed_gaps)) > tracked_spacing * 1.8
    ):
        return {"status": "unstable_tracking", "line_count": int(len(seeds))}

    tracks = np.full((len(seeds), strips), np.nan, dtype=np.float32)
    tracks[:, middle] = seeds.astype(np.float32)
    max_step = max(4, min(20, int(round(tracked_spacing * 0.38))))
    min_separation = tracked_spacing * 0.50

    for direction in (-1, 1):
        strip_index = middle
        velocity = np.zeros(len(seeds), dtype=np.float32)

        while 0 <= strip_index + direction < strips:
            next_index = strip_index + direction
            current = tracks[:, strip_index].astype(np.float32)
            prediction = current + velocity
            next_positions = np.empty_like(current)

            for line_index, predicted_y in enumerate(prediction):
                low = max(0, int(np.floor(predicted_y - max_step)))
                high = min(h, int(np.ceil(predicted_y + max_step + 1)))
                if high <= low:
                    return {"status": "unstable_tracking", "line_count": int(len(seeds))}
                rows = np.arange(low, high, dtype=np.float32)
                response = profiles[next_index, low:high]
                score = response - (np.abs(rows - predicted_y) * 0.35)
                next_positions[line_index] = rows[int(np.argmax(score))]

            if np.any(np.diff(next_positions) < min_separation):
                return {"status": "unstable_tracking", "line_count": int(len(seeds))}

            tracks[:, next_index] = next_positions
            step_delta = np.clip(next_positions - current, -max_step, max_step)
            velocity = (step_delta * 0.65) + (velocity * 0.15)
            strip_index = next_index

    tracks = np.vstack([
        cv2.GaussianBlur(row.reshape(1, -1), (0, 0), sigmaX=0.8).ravel()
        for row in tracks
    ]).astype(np.float32)

    targets = np.median(tracks, axis=1)
    residual = tracks - targets[:, None]
    common = np.median(residual, axis=0)
    disagreement = float(np.median(np.abs(residual - common[None, :])))
    if disagreement > max(2.0, tracked_spacing * 0.12):
        return {"status": "unstable_tracking", "line_count": int(len(tracks))}

    amplitude = float(np.percentile(common, 95) - np.percentile(common, 5))
    rms = float(np.sqrt(np.mean(common * common)))
    return {
        "status": "ok",
        "line_count": int(len(tracks)),
        "amplitude": amplitude,
        "rms": rms,
        "centers": centers,
        "tracks": tracks,
        "targets": targets,
    }



def _profile_shift(reference, candidate, max_step):
    """Estimate the local vertical offset between neighboring horizontal-edge profiles."""
    length = len(reference)
    low = max(5, int(round(length * 0.05)))
    high = min(length - 5, int(round(length * 0.95)))
    best_score = -2.0
    best_shift = 0

    for shift in range(-max_step, max_step + 1):
        if shift >= 0:
            ref = reference[low : high - shift if shift else high]
            cur = candidate[low + shift : high]
        else:
            amount = -shift
            ref = reference[low + amount : high]
            cur = candidate[low : high - amount]

        if len(ref) < 30:
            continue

        ref = ref.astype(np.float32) - float(np.mean(ref))
        cur = cur.astype(np.float32) - float(np.mean(cur))
        denominator = float(np.linalg.norm(ref) * np.linalg.norm(cur))
        score = float(np.dot(ref, cur) / denominator) if denominator > 1e-6 else -1.0

        if score > best_score:
            best_score = score
            best_shift = shift

    return best_score, best_shift


def detect_horizontal_structure_curvature(gray, strips=41):
    """
    Conservative fallback for forms/tables where full-width text-line peaks are unreliable.
    It tracks horizontal edge-energy continuity across neighboring vertical strips.
    """
    h, w = gray.shape[:2]
    if h < 80 or w < 120:
        return {"status": "insufficient_structure", "line_count": 0, "mode": "edge_profile"}

    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    gradient_y = np.abs(cv2.Sobel(blurred, cv2.CV_32F, 0, 1, ksize=3))
    gradient_x = np.abs(cv2.Sobel(blurred, cv2.CV_32F, 1, 0, ksize=3))

    row_energy = gradient_y.mean(axis=1).astype(np.float32)
    row_energy = cv2.GaussianBlur(
        row_energy.reshape(-1, 1),
        (1, 0),
        sigmaX=0,
        sigmaY=1.2,
    ).ravel()
    threshold = max(1.0, float(np.percentile(row_energy, 70) * 0.70))
    peaks = _find_peaks(row_energy, max(8, h // 60), threshold)
    peaks = peaks[(peaks > 10) & (peaks < h - 10)]

    horizontal_evidence = float(
        np.mean(gradient_y) / max(float(np.mean(gradient_x)), 1e-6)
    )
    if len(peaks) < 5 or horizontal_evidence < 0.65:
        return {
            "status": "insufficient_structure",
            "line_count": int(len(peaks)),
            "horizontal_evidence": horizontal_evidence,
            "mode": "edge_profile",
        }

    centers = np.linspace(
        int(round(w * 0.04)),
        int(round(w * 0.96)),
        strips,
    ).astype(np.int32)
    step = max(1, int(centers[1] - centers[0]))
    half_width = max(5, int(round(step * 1.4)))

    profiles = []
    for center in centers:
        left = max(0, int(center - half_width))
        right = min(w, int(center + half_width + 1))
        profile = gradient_y[:, left:right].mean(axis=1).astype(np.float32)
        profile = cv2.GaussianBlur(
            profile.reshape(-1, 1),
            (1, 0),
            sigmaX=0,
            sigmaY=1.2,
        ).ravel()
        profiles.append(profile)
    profiles = np.vstack(profiles)

    middle = strips // 2
    shifts = np.zeros(strips, dtype=np.float32)
    confidence = np.zeros(strips, dtype=np.float32)
    confidence[middle] = 1.0
    max_step = max(3, min(14, int(round(h * 0.018))))

    for direction in (-1, 1):
        strip_index = middle
        while 0 <= strip_index + direction < strips:
            next_index = strip_index + direction
            score, shift = _profile_shift(
                profiles[strip_index],
                profiles[next_index],
                max_step,
            )
            shifts[next_index] = shifts[strip_index] + float(shift)
            confidence[next_index] = float(score)
            strip_index = next_index

    valid_confidence = np.delete(confidence, middle)
    median_confidence = float(np.median(valid_confidence))
    confident_ratio = float(np.mean(valid_confidence >= 0.25))
    if median_confidence < 0.42 or confident_ratio < 0.70:
        return {
            "status": "unstable_tracking",
            "line_count": int(len(peaks)),
            "confidence": median_confidence,
            "mode": "edge_profile",
        }

    smooth = cv2.GaussianBlur(
        shifts.reshape(1, -1),
        (0, 0),
        sigmaX=1.35,
    ).ravel()
    smooth -= float(np.median(smooth))

    # Remove affine slope: deskew/perspective belong to their own geometry tools.
    axis = np.linspace(-1.0, 1.0, strips).astype(np.float32)
    slope, intercept = np.polyfit(axis, smooth, 1)
    curvature = smooth - ((slope * axis) + intercept)
    curvature = cv2.GaussianBlur(
        curvature.reshape(1, -1),
        (0, 0),
        sigmaX=1.0,
    ).ravel().astype(np.float32)

    max_displacement = max(6.0, h * 0.08)
    if float(np.max(np.abs(curvature))) > max_displacement:
        return {
            "status": "unstable_tracking",
            "line_count": int(len(peaks)),
            "confidence": median_confidence,
            "mode": "edge_profile",
        }

    amplitude = float(np.percentile(curvature, 95) - np.percentile(curvature, 5))
    rms = float(np.sqrt(np.mean(curvature * curvature)))
    return {
        "status": "ok",
        "line_count": int(len(peaks)),
        "amplitude": amplitude,
        "rms": rms,
        "centers": centers,
        "column_displacement": curvature,
        "confidence": median_confidence,
        "horizontal_evidence": horizontal_evidence,
        "mode": "edge_profile",
    }


def detect_document_curvature(gray):
    primary = detect_text_line_curvature(gray)
    if primary.get("status") == "ok":
        primary = dict(primary)
        primary["mode"] = "text_lines"
        return primary

    fallback = detect_horizontal_structure_curvature(gray)
    if fallback.get("status") == "ok":
        return fallback

    # Preserve the more informative safety status.
    if primary.get("status") == "unstable_tracking":
        return primary
    return fallback if fallback.get("line_count", 0) else primary

def _build_dense_displacement(detection, height, width):
    full_x = np.arange(width)

    if detection.get("mode") == "edge_profile":
        column = np.interp(
            full_x,
            detection["centers"],
            detection["column_displacement"],
        ).astype(np.float32)
        return np.tile(column, (height, 1))

    line_displacement = detection["tracks"] - detection["targets"][:, None]
    expanded = np.vstack([
        np.interp(full_x, detection["centers"], row)
        for row in line_displacement
    ])

    order = np.argsort(detection["targets"])
    y_anchors = detection["targets"][order]
    expanded = expanded[order]
    y_anchors = np.concatenate(([0.0], y_anchors, [height - 1.0]))
    expanded = np.vstack([expanded[0] * 0.35, expanded, expanded[-1] * 0.35])

    dense = np.empty((height, width), dtype=np.float32)
    ys = np.arange(height)
    for x_index in range(width):
        dense[:, x_index] = np.interp(ys, y_anchors, expanded[:, x_index])
    return dense


def _apply_dense(image, dense):
    h, w = image.shape[:2]
    yy, xx = np.indices((h, w), dtype=np.float32)
    return cv2.remap(
        image,
        xx,
        yy + dense,
        cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def dewarp_document_with_metadata(image):
    _validate_image(image)
    source_proxy, scale = _proxy(image)
    gray = _to_gray(source_proxy)
    detection = detect_document_curvature(gray)

    if detection.get("status") != "ok":
        return image.copy(), {
            "applied": False,
            "status": detection.get("status", "insufficient_text"),
            "line_count": detection.get("line_count", 0),
            "curvature_reduction": None,
            "method": detection.get("mode"),
            "confidence": detection.get("confidence"),
        }

    if detection["amplitude"] < 2.5 and detection["rms"] < 1.2:
        return image.copy(), {
            "applied": False,
            "status": "already_flat",
            "line_count": detection["line_count"],
            "before_rms": detection["rms"],
            "after_rms": detection["rms"],
            "curvature_reduction": 0.0,
            "method": detection.get("mode"),
            "confidence": detection.get("confidence"),
        }

    proxy_h, proxy_w = gray.shape[:2]
    dense_proxy = _build_dense_displacement(detection, proxy_h, proxy_w)
    corrected_proxy = _apply_dense(gray, dense_proxy)
    after = (
        detect_horizontal_structure_curvature(corrected_proxy)
        if detection.get("mode") == "edge_profile"
        else detect_text_line_curvature(corrected_proxy)
    )

    # Form/table fallback is allowed up to three conservative residual passes.
    # Because its displacement is column-wise, the maps compose additively.
    passes = 1
    if detection.get("mode") == "edge_profile":
        cumulative = dense_proxy.copy()
        while after.get("status") == "ok" and passes < 3:
            reduction = float(
                (detection["rms"] - after["rms"]) / max(detection["rms"], 1e-6)
            )
            if reduction >= CURVATURE_REDUCTION_MIN:
                break

            residual_dense = _build_dense_displacement(after, proxy_h, proxy_w)
            max_residual = float(np.max(np.abs(residual_dense)))
            if max_residual < 0.20:
                break

            cumulative += residual_dense
            max_total = max(6.0, proxy_h * 0.10)
            if float(np.max(np.abs(cumulative))) > max_total:
                return image.copy(), {
                    "applied": False,
                    "status": "unstable_tracking",
                    "line_count": detection["line_count"],
                    "curvature_reduction": None,
                    "method": "edge_profile",
                    "confidence": detection.get("confidence"),
                }

            dense_proxy = cumulative
            corrected_proxy = _apply_dense(gray, dense_proxy)
            after = detect_horizontal_structure_curvature(corrected_proxy)
            passes += 1

    if after.get("status") != "ok":
        return image.copy(), {
            "applied": False,
            "status": "verification_failed",
            "line_count": detection["line_count"],
            "before_rms": detection["rms"],
            "curvature_reduction": None,
            "method": detection.get("mode"),
            "confidence": detection.get("confidence"),
            "passes": passes,
        }

    reduction = float(
        (detection["rms"] - after["rms"]) / max(detection["rms"], 1e-6)
    )
    if reduction < CURVATURE_REDUCTION_MIN:
        return image.copy(), {
            "applied": False,
            "status": "insufficient_improvement",
            "line_count": detection["line_count"],
            "before_rms": detection["rms"],
            "after_rms": after["rms"],
            "curvature_reduction": reduction,
            "method": detection.get("mode"),
            "confidence": detection.get("confidence"),
            "passes": passes,
        }

    h, w = image.shape[:2]
    if scale == 1.0:
        dense_full = dense_proxy
    else:
        dense_full = cv2.resize(dense_proxy, (w, h), interpolation=cv2.INTER_LINEAR)
        dense_full *= float(h) / float(proxy_h)

    result = _apply_dense(image, dense_full)
    return result, {
        "applied": True,
        "status": "applied",
        "line_count": detection["line_count"],
        "before_rms": detection["rms"],
        "after_rms": after["rms"],
        "curvature_reduction": reduction,
        "method": detection.get("mode"),
        "confidence": detection.get("confidence"),
        "passes": passes,
    }

def dewarp_document(image):
    result, _ = dewarp_document_with_metadata(image)
    return result
