import argparse
import os
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.document_boundary import (
    MAX_CANDIDATES,
    MIN_AREA_RATIO,
    _candidate_from_contour,
    _extract_hough_document_candidate,
    _extract_region_document_candidates,
    _rank_boundary_candidate,
)


OUTPUT_DIR = Path("evaluation/output/boundary_diagnostic")


def _draw_candidate(image, candidate, label):
    preview = image.copy()

    if candidate is None:
        cv2.putText(preview, f"{label}: NO CANDIDATE", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
        return preview

    corners = np.asarray(candidate["corners"], dtype=np.int32).reshape(4, 2)
    cv2.polylines(preview, [corners.reshape(-1, 1, 2)], True, (0, 255, 0), 4, cv2.LINE_AA)

    for index, (x, y) in enumerate(corners):
        cv2.circle(preview, (int(x), int(y)), 7, (0, 0, 255), -1, cv2.LINE_AA)
        cv2.putText(preview, str(index + 1), (int(x) + 8, max(int(y) - 8, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA)

    score = candidate.get("final_score", candidate.get("confidence", 0.0))
    area = candidate.get("area_ratio", 0.0)

    cv2.putText(preview, f"{label} score={score:.4f} area={area:.4f}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)

    return preview


def _best_contour_candidate(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape[:2]
    image_area = float(width * height)

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    median_intensity = float(np.median(blurred))
    lower = int(max(20, 0.66 * median_intensity))
    upper = int(min(255, max(lower + 20, 1.33 * median_intensity)))

    edges = cv2.Canny(blurred, lower, upper)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    connected = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(connected, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:MAX_CANDIDATES * 4]

    candidates = []

    for contour in contours:
        contour_ratio = float(cv2.contourArea(contour)) / image_area

        if contour_ratio < MIN_AREA_RATIO * 0.60:
            continue

        candidate, _ = _candidate_from_contour(contour, width, height, image_area)

        if candidate is None:
            continue

        candidate["touches_frame"] = False
        candidate = _rank_boundary_candidate(image, candidate)
        candidates.append(candidate)

    if not candidates:
        return None

    candidates.sort(key=lambda item: item["final_score"], reverse=True)
    return candidates[0]


def _boundary_edge_support(image, corners):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    median = float(np.median(blurred))
    lower = int(max(20, 0.60 * median))
    upper = int(min(255, max(lower + 30, 1.40 * median)))

    edges = cv2.Canny(blurred, lower, upper)
    edges = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)), iterations=1)

    corners = np.asarray(corners, dtype=np.float32).reshape(4, 2)
    side_scores = []

    for index in range(4):
        start = corners[index]
        end = corners[(index + 1) % 4]
        length = float(np.linalg.norm(end - start))
        sample_count = max(30, int(round(length / 4.0)))

        xs = np.linspace(start[0], end[0], sample_count)
        ys = np.linspace(start[1], end[1], sample_count)

        hits = 0

        for x, y in zip(xs, ys):
            xi = int(round(x))
            yi = int(round(y))

            if 0 <= xi < edges.shape[1] and 0 <= yi < edges.shape[0] and edges[yi, xi] > 0:
                hits += 1

        side_scores.append(hits / max(sample_count, 1))

    mean_support = float(np.mean(side_scores))
    minimum_support = float(np.min(side_scores))
    final_support = 0.70 * mean_support + 0.30 * minimum_support

    return {
        "score": round(final_support, 4),
        "sides": [round(value, 4) for value in side_scores],
    }

def _guided_region_candidate(image, guide_candidate):
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

def main():
    parser = argparse.ArgumentParser(description="Diagnose Contour, Hough, and Region document-boundary detectors separately.")
    parser.add_argument("image", help="Path to the input document image.")
    args = parser.parse_args()

    input_path = Path(args.image)

    if not input_path.is_file():
        raise FileNotFoundError(f"Input image not found: {input_path}")

    image = cv2.imread(str(input_path), cv2.IMREAD_COLOR)

    if image is None:
        raise RuntimeError(f"OpenCV could not decode: {input_path}")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    contour = _best_contour_candidate(image)
    hough = _extract_hough_document_candidate(image, gray)

    region_candidates = _extract_region_document_candidates(image, gray)
    region = region_candidates[0] if region_candidates else None

    guided = _guided_region_candidate(image, hough)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = {
        "contour": contour,
        "hough": hough,
        "region": region,
        "guided": guided,
    }

    print()
    print("Boundary Diagnostic")
    print("-------------------")
    print("image :", input_path.name)

    for name, candidate in results.items():
        output_path = OUTPUT_DIR / f"{input_path.stem}_{name}.jpg"
        preview = _draw_candidate(image, candidate, name.upper())

        if not cv2.imwrite(str(output_path), preview):
            raise RuntimeError(f"Could not save: {output_path}")

        print()
        print(name)

        if candidate is None:
            print("candidate   : False")
        else:
            edge_support = _boundary_edge_support(image, candidate["corners"])

            print("candidate   : True")
            print("score       :", round(candidate.get("final_score", candidate.get("confidence", 0.0)), 4))
            print("area_ratio  :", round(candidate.get("area_ratio", 0.0), 4))
            print("edge_support:", edge_support["score"])
            print("edge_sides  :", edge_support["sides"])
            print("corners     :", [[int(round(x)), int(round(y))] for x, y in candidate["corners"]])

        print("preview     :", output_path)

    print()


if __name__ == "__main__":
    main()
