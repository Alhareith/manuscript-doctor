import cv2
import numpy as np
import pytest

from processing.skew_detector import detect_skew


def make_line_document(angle=0.0):
    image = np.full((700, 1000, 3), 255, dtype=np.uint8)

    for y in range(180, 540, 60):
        cv2.line(image, (150, y), (850, y), (0, 0, 0), 4)

    if abs(angle) < 1e-6:
        return image

    matrix = cv2.getRotationMatrix2D((500, 350), angle, 1.0)

    return cv2.warpAffine(
        image,
        matrix,
        (1000, 700),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255)
    )


def test_detects_positive_skew():
    image = make_line_document(-5.0)
    result = detect_skew(image)

    assert result["line_count"] >= 3
    assert result["confidence"] > 0
    assert result["dispersion"] >= 0
    assert abs(result["angle"] - 5.0) <= 0.5


def test_detects_negative_skew():
    image = make_line_document(5.0)
    result = detect_skew(image)

    assert result["line_count"] >= 3
    assert result["confidence"] > 0
    assert result["dispersion"] >= 0
    assert abs(result["angle"] + 5.0) <= 0.5


def test_detects_near_zero_skew():
    image = make_line_document(0.0)
    result = detect_skew(image)

    assert result["line_count"] >= 3
    assert abs(result["angle"]) <= 0.5


def test_detects_larger_positive_skew():
    image = make_line_document(-12.0)
    result = detect_skew(image)

    assert result["line_count"] >= 3
    assert abs(result["angle"] - 12.0) <= 0.7


def test_detects_larger_negative_skew():
    image = make_line_document(12.0)
    result = detect_skew(image)

    assert result["line_count"] >= 3
    assert abs(result["angle"] + 12.0) <= 0.7


def test_rejects_blank_image_safely():
    image = np.full((700, 1000, 3), 255, dtype=np.uint8)
    result = detect_skew(image)

    assert result["angle"] == 0.0
    assert result["confidence"] == 0.0
    assert result["line_count"] == 0
    assert result["dispersion"] == 0.0
    assert result["reason"].startswith("rejected:")


def test_rejects_small_image_safely():
    image = np.full((50, 50, 3), 255, dtype=np.uint8)
    result = detect_skew(image)

    assert result["angle"] == 0.0
    assert result["confidence"] == 0.0
    assert result["line_count"] == 0
    assert result["reason"].startswith("rejected:")


def test_supports_grayscale_image():
    image = cv2.cvtColor(make_line_document(-5.0), cv2.COLOR_BGR2GRAY)
    result = detect_skew(image)

    assert result["line_count"] >= 3
    assert abs(result["angle"] - 5.0) <= 0.5


def test_does_not_modify_input_image():
    image = make_line_document(-5.0)
    original = image.copy()

    detect_skew(image)

    assert np.array_equal(image, original)


def test_invalid_input_raises_value_error():
    with pytest.raises(ValueError):
        detect_skew(None)
        