
import cv2
import numpy as np
import pytest

from processing.analyzer import analyze_image


def test_analyzer_returns_expected_structure():
    image = np.full(
        (100, 120, 3),
        150,
        dtype=np.uint8
    )

    result = analyze_image(image)

    assert "dimensions" in result
    assert "metrics" in result
    assert "diagnoses" in result
    assert "preservation_profile" in result


def test_dimensions_are_correct():
    image = np.full(
        (80, 120, 3),
        150,
        dtype=np.uint8
    )

    result = analyze_image(image)

    assert result["dimensions"]["width"] == 120
    assert result["dimensions"]["height"] == 80
    assert result["dimensions"]["channels"] == 3


def test_dark_image_is_detected():
    image = np.full(
        (100, 100, 3),
        30,
        dtype=np.uint8
    )

    result = analyze_image(image)

    codes = {
        diagnosis["code"]
        for diagnosis in result["diagnoses"]
    }

    assert "very_dark" in codes


def test_uniform_image_has_low_contrast():
    image = np.full(
        (100, 100),
        120,
        dtype=np.uint8
    )

    result = analyze_image(image)

    codes = {
        diagnosis["code"]
        for diagnosis in result["diagnoses"]
    }

    assert (
        "very_low_contrast" in codes
        or "low_contrast" in codes
    )


def test_sharp_pattern_has_more_sharpness_than_blurred_pattern():
    image = np.zeros(
        (200, 200),
        dtype=np.uint8
    )

    image[:, ::4] = 255

    blurred = cv2.GaussianBlur(
        image,
        (15, 15),
        5
    )

    sharp_result = analyze_image(image)
    blurred_result = analyze_image(blurred)

    sharpness_original = (
        sharp_result["metrics"]["sharpness"]["value"]
    )

    sharpness_blurred = (
        blurred_result["metrics"]["sharpness"]["value"]
    )

    assert sharpness_original > sharpness_blurred


def test_preservation_profile_has_valid_level():
    image = np.full(
        (100, 100, 3),
        150,
        dtype=np.uint8
    )

    result = analyze_image(image)

    level = result["preservation_profile"]["level"]

    assert level in {
        "low",
        "moderate",
        "high"
    }


def test_grayscale_image_is_supported():
    image = np.full(
        (100, 100),
        140,
        dtype=np.uint8
    )

    result = analyze_image(image)

    assert result["dimensions"]["channels"] == 1


def test_invalid_image_raises_error():
    with pytest.raises(ValueError):
        analyze_image(None)

def test_analyzer_does_not_modify_original_image():
    image = np.random.randint(
        0,
        256,
        (100, 100, 3),
        dtype=np.uint8
    )

    original = image.copy()

    analyze_image(image)

    assert np.array_equal(image, original)

def test_bgra_image_is_supported():
    image = np.full(
        (100, 100, 4),
        150,
        dtype=np.uint8
    )

    result = analyze_image(image)

    assert result["dimensions"]["channels"] == 4

def test_empty_image_raises_error():
    image = np.array([], dtype=np.uint8)

    with pytest.raises(ValueError):
        analyze_image(image)