import cv2
import numpy as np
import pytest

from processing.auto_deskew import apply_auto_deskew
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


def test_applies_auto_deskew_when_safe():
    image = make_line_document(7.0)

    before = detect_skew(image)
    result = apply_auto_deskew(image, before)
    after = detect_skew(result["image"])

    assert result["applied"] is True
    assert result["transform"] is not None
    assert abs(after["angle"]) <= 0.5


def test_corrects_negative_skew():
    image = make_line_document(-7.0)

    before = detect_skew(image)
    result = apply_auto_deskew(image, before)
    after = detect_skew(result["image"])

    assert result["applied"] is True
    assert abs(after["angle"]) <= 0.5


def test_skips_near_zero_skew():
    image = make_line_document(0.0)

    skew = detect_skew(image)
    result = apply_auto_deskew(image, skew)

    assert result["applied"] is False
    assert result["transform"] is None
    assert result["reason"].startswith("skipped:")


def test_skips_low_confidence():
    image = make_line_document(7.0)

    skew = {
        "angle": -7.0,
        "confidence": 0.40,
        "line_count": 10,
        "dispersion": 0.5,
    }

    result = apply_auto_deskew(image, skew)

    assert result["applied"] is False
    assert result["transform"] is None
    assert "confidence" in result["reason"]


def test_skips_unsafe_large_angle():
    image = make_line_document(0.0)

    skew = {
        "angle": 50.0,
        "confidence": 0.95,
        "line_count": 20,
        "dispersion": 0.5,
    }

    result = apply_auto_deskew(image, skew)

    assert result["applied"] is False
    assert result["transform"] is None
    assert "safe automatic correction range" in result["reason"]

def test_does_not_modify_input_image():
    image = make_line_document(7.0)
    original = image.copy()

    skew = detect_skew(image)
    apply_auto_deskew(image, skew)

    assert np.array_equal(image, original)


def test_skipped_result_returns_copy():
    image = make_line_document(0.0)

    skew = detect_skew(image)
    result = apply_auto_deskew(image, skew)

    assert result["image"] is not image
    assert np.array_equal(result["image"], image)


def test_supports_grayscale_image():
    image = cv2.cvtColor(make_line_document(7.0), cv2.COLOR_BGR2GRAY)

    skew = detect_skew(image)
    result = apply_auto_deskew(image, skew)
    after = detect_skew(result["image"])

    assert result["applied"] is True
    assert result["image"].ndim == 2
    assert abs(after["angle"]) <= 0.5


def test_rejects_invalid_skew_result():
    image = make_line_document()

    with pytest.raises(ValueError):
        apply_auto_deskew(image, {"angle": 5.0})


def test_rejects_invalid_image():
    skew = {
        "angle": 5.0,
        "confidence": 0.9,
        "line_count": 10,
        "dispersion": 0.5,
    }

    with pytest.raises(ValueError):
        apply_auto_deskew(None, skew)


from processing.auto_deskew import _apply_safe_crop


def test_rejects_unsafe_post_deskew_crop():
    image = np.full((700, 1000, 3), 255, dtype=np.uint8)

    safe_crop = {
        "x": 71,
        "y": 114,
        "width": 936,
        "height": 589,
        "area": 551304,
        "retention_ratio": 0.787,
    }

    result, applied, reason = _apply_safe_crop(image, safe_crop)

    assert applied is False
    assert np.array_equal(result, image)
    assert "remove too much valid document area" in reason


def test_accepts_safe_post_deskew_crop():
    image = np.full((700, 1000, 3), 255, dtype=np.uint8)

    safe_crop = {
        "x": 10,
        "y": 10,
        "width": 980,
        "height": 680,
        "area": 666400,
        "retention_ratio": 0.96,
    }

    result, applied, reason = _apply_safe_crop(image, safe_crop)

    assert applied is True
    assert result.shape == (680, 980, 3)
    assert "retained a safe amount" in reason
