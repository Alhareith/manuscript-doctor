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


def detect_text_lines(gray: np.ndarray, strips: int = 31) -> Detection:
    height, width = gray.shape[:2]
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, ink = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    ink = cv2.morphologyEx(
        ink,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (13, 1)),
    )

    projection = ink.mean(axis=1).astype(np.float32)
    projection = cv2.GaussianBlur(projection.reshape(-1, 1), (1, 0), sigmaX=0, sigmaY=2.5).ravel()
    threshold = max(2.0, float(np.percentile(projection, 72) * 0.75))
    peaks = _find_peaks(projection, max(18, height // 50), threshold)
    peaks = peaks[(peaks > 25) & (peaks < height - 25)]

    if len(peaks) < 3:
        return Detection("insufficient_text", int(len(peaks)))

    spacing = float(np.median(np.diff(peaks))) if len(peaks) > 1 else height / 20.0
    search = max(10, int(min(55, spacing * 0.8)))
    centers = np.linspace(0, width - 1, strips).astype(np.int32)
    half = max(8, width // (strips * 2))
    tracks = np.full((len(peaks), strips), np.nan, dtype=np.float32)

    for strip_index, center in enumerate(centers):
        left = max(0, int(center - half))
        right = min(width, int(center + half + 1))
        local = ink[:, left:right].mean(axis=1).astype(np.float32)
        local = cv2.GaussianBlur(local.reshape(-1, 1), (1, 0), sigmaX=0, sigmaY=1.5).ravel()
        support = max(1.5, float(np.percentile(local, 65) * 0.65))

        for line_index, peak in enumerate(peaks):
            low = max(0, int(peak - search))
            high = min(height, int(peak + search + 1))
            offset = int(np.argmax(local[low:high]))
            y = low + offset
            if local[y] >= support:
                tracks[line_index, strip_index] = y

    coverage = np.mean(np.isfinite(tracks), axis=1)
    tracks = tracks[coverage >= 0.60]
    if len(tracks) < 3:
        return Detection("insufficient_text", int(len(tracks)))

    smoothed = []
    x = np.arange(strips)
    for row in tracks:
        valid = np.isfinite(row)
        values = np.interp(x, np.flatnonzero(valid), row[valid]).astype(np.float32)
        values = cv2.GaussianBlur(values.reshape(1, -1), (0, 0), sigmaX=1.15).ravel()
        smoothed.append(values)

    tracks = np.vstack(smoothed)
    targets = np.median(tracks, axis=1)
    residual = tracks - targets[:, None]
    common = np.median(residual, axis=0)
    amplitude = float(np.percentile(common, 95) - np.percentile(common, 5))
    rms = float(np.sqrt(np.mean(common * common)))

    return Detection("ok", len(tracks), amplitude, rms, centers, tracks, targets)


def dewarp(gray: np.ndarray) -> tuple[np.ndarray, dict]:
    started = perf_counter()
    detection = detect_text_lines(gray)

    if detection.status != "ok":
        return gray.copy(), {
            "applied": False,
            "status": "insufficient_text",
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


def run() -> None:
    base = make_fixture()
    height, width = base.shape
    sparse = make_fixture(lines=2)

    fixtures = {
        "warped_document": warp_vertical(
            base,
            lambda x, y: 22 * np.sin(2 * np.pi * x / width)
            + 8 * np.sin(4 * np.pi * x / width),
        ),
        "curved_book_page": warp_vertical(
            base,
            lambda x, y: 28 * ((x - width / 2) / (width / 2)) ** 2 - 7,
        ),
        "flat_document": base.copy(),
        "sparse_text": warp_vertical(
            sparse,
            lambda x, y: 20 * np.sin(2 * np.pi * x / width),
        ),
    }

    print("case,status,before_rms,after_rms,before_amp,after_amp,elapsed_ms")
    for name, image in fixtures.items():
        before = curvature_metric(image)
        result, metadata = dewarp(image)
        after = curvature_metric(result)

        before_rms, before_amp = before if before is not None else (None, None)
        after_rms, after_amp = after if after is not None else (None, None)

        print(
            f"{name},{metadata['status']},{before_rms},{after_rms},"
            f"{before_amp},{after_amp},{metadata['elapsed_ms']:.2f}"
        )


if __name__ == "__main__":
    run()
