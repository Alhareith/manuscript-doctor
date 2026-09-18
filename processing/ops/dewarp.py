import cv2
import numpy as np

from .common import _validate_image

CURVATURE_REDUCTION_MIN = 0.70
DEWARP_ANALYSIS_MAX_DIMENSION = 1400
DEWARP_ANALYSIS_MAX_PIXELS = 1_500_000


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


def _build_dense_displacement(detection, height, width):
    line_displacement = detection["tracks"] - detection["targets"][:, None]
    full_x = np.arange(width)
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
    detection = detect_text_line_curvature(gray)

    if detection["status"] != "ok":
        return image.copy(), {
            "applied": False,
            "status": detection["status"],
            "line_count": detection.get("line_count", 0),
            "curvature_reduction": None,
        }

    if detection["amplitude"] < 2.5 and detection["rms"] < 1.2:
        return image.copy(), {
            "applied": False,
            "status": "already_flat",
            "line_count": detection["line_count"],
            "before_rms": detection["rms"],
            "after_rms": detection["rms"],
            "curvature_reduction": 0.0,
        }

    proxy_h, proxy_w = gray.shape[:2]
    dense_proxy = _build_dense_displacement(detection, proxy_h, proxy_w)
    corrected_proxy = _apply_dense(gray, dense_proxy)
    after = detect_text_line_curvature(corrected_proxy)

    if after.get("status") != "ok":
        return image.copy(), {
            "applied": False,
            "status": "verification_failed",
            "line_count": detection["line_count"],
            "before_rms": detection["rms"],
            "curvature_reduction": None,
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
    }


def dewarp_document(image):
    result, _ = dewarp_document_with_metadata(image)
    return result
