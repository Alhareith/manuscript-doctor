"""Experimental gate for Text-Line -> Curvature -> Mesh Dewarping.

This file is research-only. It is intentionally isolated from processing/, app.py,
the operation registry and the UI. Running it must not change production behavior.

The experiment checks four mandatory cases:
1) warped text document,
2) curved book-like page,
3) already-flat document (must be a no-op),
4) sparse-text document (must abstain).

The current prototype uses horizontal text-energy projections as line evidence,
estimates local baseline curvature across vertical strips, and applies a dense
vertical mesh with cv2.remap. It is not production-ready until all gates pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import cv2
import numpy as np

CURVATURE_REDUCTION_MIN = 0.70
TEXT_STRUCTURE_F1_MIN = 0.90
FLAT_STRUCTURE_F1_MIN = 0.98


@dataclass
class Detection:
    status: str
    line_count: int
    amplitude: float = 0.0
    rms: float = 0.0
    centers: np.ndarray | None = None
    tracks: np.ndarray | None = None
    targets: np.ndarray | None = None


def _find_peaks(signal: np.ndarray, min_distance: int, threshold: float) -> np.ndarray:
    candidates = []
    for index in range(1, len(signal) - 1):
        if signal[index] >= signal[index - 1] and signal[index] >= signal[index + 1] and signal[index] >= threshold:
            candidates.append(index)

    if not candidates:
        return np.array([], dtype=np.int32)

    ranked = sorted(candidates, key=lambda index: float(signal[index]), reverse=True)
    accepted: list[int] = []
    for index in ranked:
        if all(abs(index - previous) >= min_distance for previous in accepted):
            accepted.append(index)

    return np.array(sorted(accepted), dtype=np.int32)


def _strip_profile(ink: np.ndarray, center: int, half_width: int) -> np.ndarray:
    height, width = ink.shape[:2]
    left = max(0, int(center - half_width))
    right = min(width, int(center + half_width + 1))
    profile = ink[:, left:right].mean(axis=1).astype(np.float32)
    return cv2.GaussianBlur(
        profile.reshape(-1, 1),
        (1, 0),
        sigmaX=0,
        sigmaY=1.4,
    ).ravel()


def detect_text_lines(gray: np.ndarray, strips: int = 41) -> Detection:
    """Track text baselines continuously from the page centre to both sides.

    The previous prototype searched for every line independently in every
    vertical strip. That allowed two tracks to lock onto the same physical
    line, or for one track to jump to its neighbour. This version seeds lines
    once in the centre strip and then follows each seed outward with a bounded
    velocity model. Track ordering and minimum separation are enforced at
    every strip, so crossing and duplicate tracks are rejected instead of
    being used to build a destructive mesh.
    """
    height, width = gray.shape[:2]
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, ink = cv2.threshold(
        blurred,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )
    ink = cv2.morphologyEx(
        ink,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (13, 1)),
    )

    projection = ink.mean(axis=1).astype(np.float32)
    projection = cv2.GaussianBlur(
        projection.reshape(-1, 1),
        (1, 0),
        sigmaX=0,
        sigmaY=2.5,
    ).ravel()
    threshold = max(2.0, float(np.percentile(projection, 72) * 0.75))
    global_peaks = _find_peaks(
        projection,
        max(18, height // 50),
        threshold,
    )
    global_peaks = global_peaks[
        (global_peaks > 25) & (global_peaks < height - 25)
    ]

    # Sparse pages must abstain. Four or fewer global text bands are not
    # enough evidence to estimate a trustworthy page-wide deformation field.
    if len(global_peaks) < 5:
        return Detection("insufficient_text", int(len(global_peaks)))

    global_spacing = np.diff(global_peaks).astype(np.float32)
    median_spacing = float(np.median(global_spacing))
    if (
        median_spacing < 12.0
        or float(np.max(global_spacing)) > median_spacing * 2.5
    ):
        return Detection("insufficient_text", int(len(global_peaks)))

    centers = np.linspace(
        int(round(width * 0.05)),
        int(round(width * 0.95)),
        strips,
    ).astype(np.int32)
    strip_step = max(1, int(centers[1] - centers[0]))
    half_width = max(6, int(round(strip_step * 0.55)))
    profiles = np.vstack([
        _strip_profile(ink, int(center), half_width)
        for center in centers
    ])

    middle = strips // 2
    center_profile = profiles[middle]
    center_threshold = max(
        2.0,
        float(np.percentile(center_profile, 70) * 0.55),
    )
    seeds = _find_peaks(
        center_profile,
        max(12, int(round(median_spacing * 0.55))),
        center_threshold,
    )
    seeds = seeds[(seeds > 25) & (seeds < height - 25)]

    if len(seeds) < 5:
        return Detection("insufficient_text", int(len(seeds)))

    seed_spacing = np.diff(seeds).astype(np.float32)
    tracked_spacing = float(np.median(seed_spacing))
    if (
        tracked_spacing < 12.0
        or float(np.min(seed_spacing)) < tracked_spacing * 0.55
        or float(np.max(seed_spacing)) > tracked_spacing * 1.8
    ):
        return Detection("insufficient_text", int(len(seeds)))

    tracks = np.full((len(seeds), strips), np.nan, dtype=np.float32)
    tracks[:, middle] = seeds.astype(np.float32)

    max_step = max(4, min(20, int(round(tracked_spacing * 0.38))))
    minimum_separation = tracked_spacing * 0.50

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
                high = min(
                    height,
                    int(np.ceil(predicted_y + max_step + 1)),
                )
                if high <= low:
                    return Detection("unstable_tracking", int(len(seeds)))

                rows = np.arange(low, high, dtype=np.float32)
                response = profiles[next_index, low:high]
                # The response term follows the text evidence; the distance
                # penalty keeps the line on a continuous path instead of
                # jumping to a stronger neighbouring baseline.
                score = response - (np.abs(rows - predicted_y) * 0.35)
                next_positions[line_index] = rows[int(np.argmax(score))]

            separation = np.diff(next_positions)
            if np.any(separation < minimum_separation):
                return Detection("unstable_tracking", int(len(seeds)))

            tracks[:, next_index] = next_positions
            step = np.clip(
                next_positions - current,
                -max_step,
                max_step,
            )
            velocity = (step * 0.65) + (velocity * 0.15)
            strip_index = next_index

    smoothed = np.vstack([
        cv2.GaussianBlur(
            row.reshape(1, -1),
            (0, 0),
            sigmaX=0.8,
        ).ravel()
        for row in tracks
    ]).astype(np.float32)

    targets = np.median(smoothed, axis=1)
    residual = smoothed - targets[:, None]
    common = np.median(residual, axis=0)

    # Stable lines should agree on the same page deformation. If individual
    # tracks disagree strongly, the mesh is not trustworthy and we abstain.
    disagreement = float(
        np.median(np.abs(residual - common[None, :]))
    )
    if disagreement > max(2.0, tracked_spacing * 0.12):
        return Detection("unstable_tracking", int(len(seeds)))

    amplitude = float(
        np.percentile(common, 95) - np.percentile(common, 5)
    )
    rms = float(np.sqrt(np.mean(common * common)))

    return Detection(
        "ok",
        len(smoothed),
        amplitude,
        rms,
        centers,
        smoothed,
        targets,
    )


def dewarp(gray: np.ndarray) -> tuple[np.ndarray, dict]:
    started = perf_counter()
    detection = detect_text_lines(gray)

    if detection.status != "ok":
        return gray.copy(), {
            "applied": False,
            "status": detection.status,
            "line_count": detection.line_count,
            "elapsed_ms": (perf_counter() - started) * 1000,
        }

    if detection.amplitude < 2.5 and detection.rms < 1.2:
        return gray.copy(), {
            "applied": False,
            "status": "already_flat",
            "line_count": detection.line_count,
            "amplitude": detection.amplitude,
            "rms": detection.rms,
            "elapsed_ms": (perf_counter() - started) * 1000,
        }

    height, width = gray.shape[:2]
    line_displacement = detection.tracks - detection.targets[:, None]
    full_x = np.arange(width)
    expanded = np.vstack([
        np.interp(full_x, detection.centers, row)
        for row in line_displacement
    ])

    order = np.argsort(detection.targets)
    y_anchors = detection.targets[order]
    expanded = expanded[order]
    y_anchors = np.concatenate(([0.0], y_anchors, [height - 1.0]))
    expanded = np.vstack([expanded[0] * 0.35, expanded, expanded[-1] * 0.35])

    dense = np.empty((height, width), dtype=np.float32)
    ys = np.arange(height)
    for x_index in range(width):
        dense[:, x_index] = np.interp(ys, y_anchors, expanded[:, x_index])

    yy, xx = np.indices((height, width), dtype=np.float32)
    result = cv2.remap(
        gray,
        xx,
        yy + dense,
        cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )

    return result, {
        "applied": True,
        "status": "applied",
        "line_count": detection.line_count,
        "amplitude": detection.amplitude,
        "rms": detection.rms,
        "elapsed_ms": (perf_counter() - started) * 1000,
    }


def make_fixture(width: int = 900, height: int = 1200, lines: int = 26, seed: int = 3) -> np.ndarray:
    rng = np.random.default_rng(seed)
    image = np.full((height, width), 242, dtype=np.uint8)
    noise = rng.normal(0, 2, image.shape).astype(np.int16)
    image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    y_values = np.linspace(90, height - 100, lines).astype(int)
    for y in y_values:
        x = 75
        while x < width - 80:
            length = int(rng.integers(18, 55))
            gap = int(rng.integers(6, 16))
            cv2.line(
                image,
                (x, y),
                (min(width - 80, x + length), y),
                int(rng.integers(35, 90)),
                int(rng.integers(1, 3)),
                cv2.LINE_AA,
            )
            x += length + gap

    return image


def warp_vertical(image: np.ndarray, displacement) -> np.ndarray:
    height, width = image.shape
    yy, xx = np.indices((height, width), dtype=np.float32)
    delta = displacement(xx, yy).astype(np.float32)
    return cv2.remap(
        image,
        xx,
        yy - delta,
        cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def curvature_metric(image: np.ndarray) -> tuple[float, float] | None:
    detected = detect_text_lines(image)
    if detected.status != "ok":
        return None
    return detected.rms, detected.amplitude


def text_structure_f1(reference: np.ndarray, candidate: np.ndarray, tolerance: int = 2) -> dict:
    """Measure whether dark text structure is preserved after rectification.

    The metric compares binarized dark-stroke masks with a small spatial
    tolerance. This is intentionally stricter than visual sharpness: a result
    cannot pass merely because lines look straighter if character strokes have
    moved or disappeared.
    """
    ref_blur = cv2.GaussianBlur(reference, (3, 3), 0)
    cand_blur = cv2.GaussianBlur(candidate, (3, 3), 0)

    _, ref = cv2.threshold(
        ref_blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    _, cand = cv2.threshold(
        cand_blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )

    cleanup = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 1))
    ref = cv2.morphologyEx(ref, cv2.MORPH_OPEN, cleanup)
    cand = cv2.morphologyEx(cand, cv2.MORPH_OPEN, cleanup)

    ref_mask = ref > 0
    cand_mask = cand > 0
    tolerance_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (2 * tolerance + 1, 2 * tolerance + 1),
    )
    ref_dilated = cv2.dilate(ref, tolerance_kernel) > 0
    cand_dilated = cv2.dilate(cand, tolerance_kernel) > 0

    precision = float(
        np.count_nonzero(cand_mask & ref_dilated)
        / max(1, np.count_nonzero(cand_mask))
    )
    recall = float(
        np.count_nonzero(ref_mask & cand_dilated)
        / max(1, np.count_nonzero(ref_mask))
    )
    f1 = float(2 * precision * recall / max(1e-9, precision + recall))

    return {"f1": f1, "precision": precision, "recall": recall}


def curvature_reduction(before, after) -> float | None:
    if before is None or after is None:
        return None
    before_rms = float(before[0])
    after_rms = float(after[0])
    if before_rms <= 1e-9:
        return 1.0 if after_rms <= before_rms + 1e-9 else -1.0
    return float((before_rms - after_rms) / before_rms)


def evaluate_case(name: str, source: np.ndarray, target: np.ndarray) -> dict:
    before = curvature_metric(source)
    result, metadata = dewarp(source)
    after = curvature_metric(result)
    structure_reference = source if name == "sparse_text" else target
    structure = text_structure_f1(structure_reference, result)
    reduction = curvature_reduction(before, after)

    reasons = []

    if name == "flat_document":
        if metadata.get("status") != "already_flat" or metadata.get("applied"):
            reasons.append("flat_document_was_modified")
        if structure["f1"] < FLAT_STRUCTURE_F1_MIN:
            reasons.append("flat_structure_not_preserved")
    elif name == "sparse_text":
        if metadata.get("applied") or metadata.get("status") not in {"insufficient_text", "unstable_tracking"}:
            reasons.append("sparse_case_did_not_abstain")
        if structure["f1"] < FLAT_STRUCTURE_F1_MIN:
            reasons.append("sparse_source_structure_not_preserved")
    else:
        if reduction is None or reduction < CURVATURE_REDUCTION_MIN:
            reasons.append("curvature_reduction_below_70_percent")
        if structure["f1"] < TEXT_STRUCTURE_F1_MIN:
            reasons.append("text_structure_f1_below_0_90")

    return {
        "case": name,
        "pass": not reasons,
        "reasons": reasons,
        "status": metadata.get("status"),
        "applied": bool(metadata.get("applied")),
        "before_rms": None if before is None else float(before[0]),
        "after_rms": None if after is None else float(after[0]),
        "curvature_reduction": reduction,
        "structure_f1": structure["f1"],
        "structure_precision": structure["precision"],
        "structure_recall": structure["recall"],
        "elapsed_ms": float(metadata.get("elapsed_ms", 0.0)),
    }


def run() -> None:
    base = make_fixture()
    height, width = base.shape
    sparse = make_fixture(lines=2)

    fixtures = {
        "warped_document": (
            warp_vertical(
                base,
                lambda x, y: 22 * np.sin(2 * np.pi * x / width)
                + 8 * np.sin(4 * np.pi * x / width),
            ),
            base,
        ),
        "curved_book_page": (
            warp_vertical(
                base,
                lambda x, y: 28 * ((x - width / 2) / (width / 2)) ** 2 - 7,
            ),
            base,
        ),
        "flat_document": (base.copy(), base),
        "sparse_text": (
            warp_vertical(
                sparse,
                lambda x, y: 20 * np.sin(2 * np.pi * x / width),
            ),
            sparse,
        ),
    }

    print(
        "case,pass,status,before_rms,after_rms,curvature_reduction,"
        "structure_f1,elapsed_ms,reasons"
    )
    failures = []

    for name, (source, target) in fixtures.items():
        evaluation = evaluate_case(name, source, target)
        if not evaluation["pass"]:
            failures.append(name)

        print(
            f"{name},{evaluation['pass']},{evaluation['status']},"
            f"{evaluation['before_rms']},{evaluation['after_rms']},"
            f"{evaluation['curvature_reduction']},"
            f"{evaluation['structure_f1']:.4f},"
            f"{evaluation['elapsed_ms']:.2f},"
            f"{'|'.join(evaluation['reasons']) or 'ok'}"
        )

    print(
        "FINAL_GATE="
        + ("PASS" if not failures else "FAIL")
        + (" failures=" + ",".join(failures) if failures else "")
    )


if __name__ == "__main__":
    run()
