import cv2
import numpy as np
import pytest

from processing.document_boundary import (
    MIN_AREA_RATIO,
    MIN_CONFIDENCE,
    MAX_AREA_RATIO,
    detect_document_boundary,
    detect_preparation_boundary,

)


def make_document_scene():
    image = np.full((700, 1000, 3), 45, dtype=np.uint8)
    corners = np.array([[180, 100], [840, 145], [790, 610], [140, 560]], dtype=np.int32)

    cv2.fillConvexPoly(image, corners, (235, 235, 235))
    cv2.polylines(image, [corners], True, (250, 250, 250), 8)

    return image


def test_detects_clear_document_quadrilateral():
    result = detect_document_boundary(make_document_scene())

    assert result["detected"] is True
    assert len(result["corners"]) == 4
    assert result["confidence"] >= 0.68
    assert 0.18 <= result["area_ratio"] <= 0.98
    assert result["reason"].startswith("accepted:")


def test_detected_corners_are_inside_image_and_ordered():
    image = make_document_scene()
    result = detect_document_boundary(image)

    assert result["detected"] is True

    corners = np.asarray(result["corners"], dtype=np.int32)
    height, width = image.shape[:2]

    assert np.all(corners[:, 0] >= 0)
    assert np.all(corners[:, 0] < width)
    assert np.all(corners[:, 1] >= 0)
    assert np.all(corners[:, 1] < height)

    top_left, top_right, bottom_right, bottom_left = corners

    assert top_left[0] < top_right[0]
    assert bottom_left[0] < bottom_right[0]
    assert top_left[1] < bottom_left[1]
    assert top_right[1] < bottom_right[1]


def test_rejects_blank_image():
    image = np.full((500, 700, 3), 220, dtype=np.uint8)

    result = detect_document_boundary(image)

    assert result["detected"] is False
    assert result["corners"] == []
    assert result["confidence"] == 0.0
    assert result["area_ratio"] == 0.0
    assert result["reason"].startswith("rejected:")


def test_rejects_small_internal_rectangle():
    image = np.full((700, 1000, 3), 40, dtype=np.uint8)

    cv2.rectangle(image, (430, 300), (570, 400), (240, 240, 240), -1)

    result = detect_document_boundary(image)

    assert result["detected"] is False
    assert result["corners"] == []
    assert result["reason"].startswith("rejected:")


def test_detection_does_not_modify_input_image():
    image = make_document_scene()
    original = image.copy()

    detect_document_boundary(image)

    assert np.array_equal(image, original)


def test_supports_grayscale_image():
    image = cv2.cvtColor(make_document_scene(), cv2.COLOR_BGR2GRAY)

    result = detect_document_boundary(image)

    assert result["detected"] is True
    assert len(result["corners"]) == 4


def test_rejects_too_small_image_safely():
    image = np.full((60, 60, 3), 220, dtype=np.uint8)

    result = detect_document_boundary(image)

    assert result["detected"] is False
    assert result["corners"] == []
    assert (
        result["reason"]
        == "rejected: image is too small for reliable boundary detection"
    )


def test_invalid_input_raises_value_error():
    with pytest.raises(ValueError):
        detect_document_boundary(None)


from pathlib import Path

EVALUATION_INPUT_DIR = Path("evaluation/input")


def _load_regression_image(filename):
    path = EVALUATION_INPUT_DIR / filename

    assert path.is_file(), f"Regression image is missing: {path}"

    image = cv2.imread(str(path), cv2.IMREAD_COLOR)

    assert image is not None, f"OpenCV could not decode regression image: {path}"

    return image


def _assert_valid_detected_boundary(image, result):
    assert result["detected"] is True
    assert len(result["corners"]) == 4
    assert result["confidence"] >= MIN_CONFIDENCE
    assert MIN_AREA_RATIO <= result["area_ratio"] <= MAX_AREA_RATIO
    assert result["reason"].startswith("accepted:")

    corners = np.asarray(result["corners"], dtype=np.int32)

    height, width = image.shape[:2]

    assert corners.shape == (4, 2)

    assert np.all(corners[:, 0] >= 0)
    assert np.all(corners[:, 0] < width)

    assert np.all(corners[:, 1] >= 0)
    assert np.all(corners[:, 1] < height)

    assert cv2.isContourConvex(corners.reshape(-1, 1, 2))


def test_regression_clear_background_document():
    image = _load_regression_image("b01.jpg")

    result = detect_document_boundary(image)

    _assert_valid_detected_boundary(image, result)


def test_regression_cluttered_background_document():
    image = _load_regression_image("b02.jpg")

    result = detect_document_boundary(image)

    _assert_valid_detected_boundary(image, result)


def test_preparation_selector_exposes_only_guided_and_region():
    image = make_document_scene()

    result = detect_preparation_boundary(image)

    assert set(result["candidates"]) == {"guided", "region"}
    assert result["allowed_methods"] == ["guided", "region"]
    assert result["method_used"] in {None, "guided", "region"}
    assert result["status"] in {"accept_automatic", "review_required", "reject"}

    if result["method_used"] is not None:
        assert result["method_used"] in {"guided", "region"}
        assert len(result["corners"]) == 4
        assert 0.18 <= result["area_ratio"] <= 0.98


def test_preparation_selector_does_not_modify_input():
    image = make_document_scene()
    original = image.copy()

    detect_preparation_boundary(image)

    assert np.array_equal(image, original)


def test_preparation_selector_rejects_small_image_safely():
    image = np.full((60, 60, 3), 220, dtype=np.uint8)

    result = detect_preparation_boundary(image)

    assert result["status"] == "reject"
    assert result["detected"] is False
    assert result["method_used"] is None
    assert set(result["candidates"]) == {"guided", "region"}
