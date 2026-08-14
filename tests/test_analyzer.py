
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

def test_noise_metric_structure():
    image = np.full(
        (200, 200),
        180,
        dtype=np.uint8
    )

    result = analyze_image(
        image
    )

    noise = result[
        "metrics"
    ]["noise"]

    assert "value" in noise
    assert "p90" in noise
    assert "affected_ratio" in noise
    assert "unit" in noise

    assert noise["value"] >= 0
    assert noise["p90"] >= 0

    assert (
        0
        <= noise["affected_ratio"]
        <= 1
    )


def test_added_noise_increases_noise_metric():
    rng = np.random.default_rng(
        42
    )

    clean = np.full(
        (300, 300),
        180,
        dtype=np.uint8
    )

    noisy = clean.copy()

    noise = rng.normal(
        0,
        20,
        noisy.shape
    )

    noisy = np.clip(
        noisy.astype(
            np.float32
        )
        + noise,
        0,
        255
    ).astype(
        np.uint8
    )

    clean_result = analyze_image(
        clean
    )

    noisy_result = analyze_image(
        noisy
    )

    clean_noise = (
        clean_result[
            "metrics"
        ]["noise"]["value"]
    )

    noisy_noise = (
        noisy_result[
            "metrics"
        ]["noise"]["value"]
    )

    assert noisy_noise > clean_noise


def test_impulse_noise_increases_noise_metric():
    rng = np.random.default_rng(
        7
    )

    clean = np.full(
        (300, 300),
        180,
        dtype=np.uint8
    )

    noisy = clean.copy()

    mask = rng.random(
        noisy.shape
    )

    noisy[
        mask < 0.03
    ] = 0

    noisy[
        mask > 0.97
    ] = 255

    clean_result = analyze_image(
        clean
    )

    noisy_result = analyze_image(
        noisy
    )

    assert (
        noisy_result[
            "metrics"
        ]["noise"]["value"]
        >
        clean_result[
            "metrics"
        ]["noise"]["value"]
    )


def test_clean_flat_image_has_low_noise():
    image = np.full(
        (250, 250),
        160,
        dtype=np.uint8
    )

    result = analyze_image(
        image
    )

    assert (
        result[
            "metrics"
        ]["noise"]["value"]
        < 1.0
    )

def test_clipping_metrics_exist():
    image = np.full(
        (200, 200),
        180,
        dtype=np.uint8
    )

    result = analyze_image(
        image
    )

    metrics = result["metrics"]

    assert (
        "dark_clipped_ratio"
        in metrics
    )

    assert (
        "bright_clipped_ratio"
        in metrics
    )


def test_bright_clipping_detected():
    image = np.full(
        (200, 200),
        255,
        dtype=np.uint8
    )

    result = analyze_image(
        image
    )

    value = (
        result["metrics"]
        ["bright_clipped_ratio"]
        ["value"]
    )

    assert value > 0.95


def test_dark_clipping_detected():
    image = np.zeros(
        (200, 200),
        dtype=np.uint8
    )

    result = analyze_image(
        image
    )

    value = (
        result["metrics"]
        ["dark_clipped_ratio"]
        ["value"]
    )

    assert value > 0.95
def test_bleed_indicators_exist():
    image = np.full(
        (200, 250),
        180,
        dtype=np.uint8
    )

    result = analyze_image(
        image
    )

    metrics = result["metrics"]

    assert (
        "weak_structure_ratio"
        in metrics
    )

    assert (
        "strong_structure_ratio"
        in metrics
    )

    assert (
        "weak_to_strong_ratio"
        in metrics
    )


def test_bleed_indicator_values_are_finite():
    image = np.full(
        (200, 250),
        180,
        dtype=np.uint8
    )

    result = analyze_image(
        image
    )

    for key in [
        "weak_structure_ratio",
        "strong_structure_ratio",
        "weak_to_strong_ratio"
    ]:
        value = (
            result["metrics"]
            [key]["value"]
        )

        assert np.isfinite(
            value
        )

        assert value >= 0

def test_structural_metrics_exist():
    image = np.full(
        (220, 300),
        220,
        dtype=np.uint8
    )

    cv2.putText(
        image,
        "TEXT",
        (50, 130),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.5,
        40,
        2,
        cv2.LINE_AA
    )

    result = analyze_image(
        image
    )

    metrics = result[
        "metrics"
    ]

    required = [
        "component_count",
        "small_component_ratio",
        "mean_component_area",
        "median_component_area",
        "foreground_ratio",
        "thin_structure_ratio"
    ]

    for key in required:
        assert key in metrics
        assert "value" in metrics[key]


def test_structural_ratios_valid():
    image = np.full(
        (200, 300),
        220,
        dtype=np.uint8
    )

    result = analyze_image(
        image
    )

    metrics = result[
        "metrics"
    ]

    for key in [
        "small_component_ratio",
        "foreground_ratio",
        "thin_structure_ratio"
    ]:
        value = metrics[
            key
        ]["value"]

        assert 0 <= value <= 1

        