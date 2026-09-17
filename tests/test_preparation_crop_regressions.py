import cv2
import numpy as np

import processing.preparation_pipeline as preparation_pipeline
from processing.bright_document_fallback import detect_bright_document_boundary
from processing.preparation_pipeline import prepare_document


def _no_skew(_image):
    return {
        "angle": 0.0,
        "confidence": 0.0,
        "line_count": 0,
        "dispersion": 0.0,
        "reason": "synthetic no skew",
    }


def test_fully_visible_page_close_to_frame_is_still_eligible(monkeypatch):
    image = np.full((800, 1200, 3), 55, dtype=np.uint8)

    def detector(proxy):
        height, width = proxy.shape[:2]
        margin_x = max(4, int(round(width * 0.012)))
        margin_y = max(4, int(round(height * 0.012)))
        return {
            "detected": True,
            "status": "accept_automatic",
            "corners": [
                [margin_x, margin_y],
                [width - 1 - margin_x, margin_y],
                [width - 1 - margin_x, height - 1 - margin_y],
                [margin_x, height - 1 - margin_y],
            ],
            "confidence": 0.95,
            "area_ratio": 0.92,
            "reason": "accepted: synthetic fully visible page",
        }

    monkeypatch.setattr(preparation_pipeline, "detect_skew", _no_skew)
    result = prepare_document(image, boundary_detector=detector)

    assert result["boundary"]["automatic_crop_eligible"] is True
    assert result["boundary"]["frame_clearance_ratio"] >= 0.005
    assert result["perspective"] is not None
    assert result["perspective"]["applied"] is True


def test_page_touching_frame_remains_blocked(monkeypatch):
    image = np.full((800, 1200, 3), 55, dtype=np.uint8)

    def detector(proxy):
        height, width = proxy.shape[:2]
        return {
            "detected": True,
            "status": "accept_automatic",
            "corners": [
                [int(width * 0.10), int(height * 0.08)],
                [int(width * 0.90), int(height * 0.08)],
                [int(width * 0.90), height - 1],
                [int(width * 0.10), height - 1],
            ],
            "confidence": 0.95,
            "area_ratio": 0.74,
            "reason": "accepted: synthetic clipped page",
        }

    monkeypatch.setattr(preparation_pipeline, "detect_skew", _no_skew)
    result = prepare_document(image, boundary_detector=detector)

    assert result["boundary"]["automatic_crop_eligible"] is False
    assert result["perspective"] is None


def test_bright_paper_fallback_finds_document_on_textured_background():
    image = np.full((640, 900, 3), (70, 105, 135), dtype=np.uint8)
    corners = np.array(
        [[180, 55], [700, 80], [745, 570], [135, 545]],
        dtype=np.int32,
    )
    cv2.fillConvexPoly(image, corners, (232, 232, 228))

    for row in range(145, 485, 44):
        cv2.line(image, (235, row), (650, row + 12), (95, 95, 95), 3)

    result = detect_bright_document_boundary(image)

    assert result["detected"] is True
    assert result["status"] == "accept_automatic"
    assert len(result["corners"]) == 4
    assert result["confidence"] >= 0.66


def test_bright_paper_fallback_rejects_blank_frame():
    image = np.full((500, 700, 3), 180, dtype=np.uint8)
    result = detect_bright_document_boundary(image)

    assert result["detected"] is False
    assert result["status"] == "reject"
