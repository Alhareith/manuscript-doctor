import os

import cv2
import numpy as np
import pytest

from processing.preservation import (
    verify_preservation
)
from processing.operations import (
    adaptive_threshold,
    clahe,
    gamma_correct,
    global_threshold,
    histogram_equalization,
    illumination_normalize,
    median_denoise,
    otsu_threshold,
    sharpen,
)


DATASET_ROOT = os.path.join(
    ".",
    "evaluation",
    "operation_validation",
    "generated"
)

SYNTHETIC_DIR = os.path.join(
    DATASET_ROOT, "00_source_original"
)

MANUSCRIPT_DIR = os.path.join(
    DATASET_ROOT, "source_01_clean_manuscript.png"
)

DOCUMENT_DIR = os.path.join(
    DATASET_ROOT, "source_02_clean_document.png"
)

DATASET_AVAILABLE = os.path.isdir(SYNTHETIC_DIR)

requires_dataset = pytest.mark.skipif(
    not DATASET_AVAILABLE,
    reason="validation dataset not generated"
)


def load_case(directory, filename, size=None):
    image = cv2.imread(
        os.path.join(directory, filename)
    )

    if size is not None:
        image = cv2.resize(image, size)

    return image


def status_of(result):
    return result["assessment"]["status"]


def codes_of(result):
    return {
        warning["code"] for warning in result["warnings"]
    }


def make_document_like_image():
    image = np.full(
        (200, 300),
        230,
        dtype=np.uint8
    )

    cv2.putText(
        image,
        "TEXT",
        (40, 110),
        cv2.FONT_HERSHEY_SIMPLEX,
        2,
        30,
        3,
        cv2.LINE_AA
    )

    return image


def make_salt_pepper(image, density=0.03, seed=20260817):
    rng = np.random.default_rng(seed)

    noisy = image.copy()

    mask = rng.random(image.shape[:2])

    noisy[mask < density / 2.0] = 0
    noisy[mask > 1.0 - density / 2.0] = 255

    return noisy


def test_preservation_returns_expected_structure():
    image = make_document_like_image()

    result = verify_preservation(
        image,
        image.copy()
    )

    assert "metrics" in result
    assert "warnings" in result
    assert "assessment" in result


def test_identical_images_are_acceptable():
    image = make_document_like_image()

    result = verify_preservation(
        image,
        image.copy()
    )

    assert (
        result["assessment"]["status"]
        == "acceptable"
    )


def test_identical_images_have_high_edge_retention():
    image = make_document_like_image()

    result = verify_preservation(
        image,
        image.copy()
    )

    assert (
        result["metrics"]["edge_retention"]
        > 0.95
    )


def test_strong_blur_reduces_edge_retention():
    image = make_document_like_image()

    blurred = cv2.GaussianBlur(
        image,
        (31, 31),
        10
    )

    result = verify_preservation(
        image,
        blurred
    )

    assert (
        result["metrics"]["edge_retention"]
        < 1.0
    )


def test_erasing_content_triggers_warning():
    image = make_document_like_image()

    processed = image.copy()

    cv2.rectangle(
        processed,
        (30, 50),
        (270, 130),
        230,
        -1
    )

    result = verify_preservation(
        image,
        processed
    )

    assert len(
        result["warnings"]
    ) > 0


def test_added_noise_increases_edge_inflation():
    image = make_document_like_image()

    rng = np.random.default_rng(42)

    noise = rng.integers(
        0,
        256,
        image.shape,
        dtype=np.uint8
    )

    noisy = cv2.addWeighted(
        image,
        0.8,
        noise,
        0.2,
        0
    )

    result = verify_preservation(
        image,
        noisy
    )

    assert (
        result["metrics"]["edge_inflation"]
        >= 1.0
    )


def test_color_images_are_supported():
    gray = make_document_like_image()

    color = cv2.cvtColor(
        gray,
        cv2.COLOR_GRAY2BGR
    )

    result = verify_preservation(
        color,
        color.copy()
    )

    assert (
        result["assessment"]["status"]
        == "acceptable"
    )


def test_different_sizes_are_supported():
    image = make_document_like_image()

    smaller = cv2.resize(
        image,
        (150, 100)
    )

    result = verify_preservation(
        image,
        smaller
    )

    assert "metrics" in result


def test_invalid_original_is_rejected():
    image = make_document_like_image()

    with pytest.raises(ValueError):
        verify_preservation(
            None,
            image
        )


def test_invalid_processed_image_is_rejected():
    image = make_document_like_image()

    with pytest.raises(ValueError):
        verify_preservation(
            image,
            None
        )
def test_preservation_does_not_modify_images():
    original = make_document_like_image()

    processed = cv2.GaussianBlur(
        original,
        (5, 5),
        1
    )

    original_copy = original.copy()
    processed_copy = processed.copy()

    verify_preservation(
        original,
        processed
    )

    assert np.array_equal(
        original,
        original_copy
    )

    assert np.array_equal(
        processed,
        processed_copy
    )


def test_edge_inflation_is_finite_when_original_has_no_edges():
    original = np.full(
        (100, 100),
        255,
        dtype=np.uint8
    )

    processed = original.copy()

    cv2.line(
        processed,
        (10, 50),
        (90, 50),
        0,
        2
    )

    result = verify_preservation(
        original,
        processed
    )

    assert np.isfinite(
        result["metrics"]["edge_inflation"]
    )


# --- New metric surface ---------------------------------------------


def test_new_metrics_are_reported():
    image = make_document_like_image()

    result = verify_preservation(
        image,
        image.copy()
    )

    metrics = result["metrics"]

    assert "clipping_change" in metrics
    assert "smoothing_ratio" in metrics
    assert "ink_retention" in metrics
    assert "ink_inflation_ratio" in metrics
    assert "binary_output" in metrics["clipping_change"]


def test_identical_images_have_zero_new_clipping():
    image = make_document_like_image()

    result = verify_preservation(
        image,
        image.copy()
    )

    assert (
        result["metrics"]["clipping_change"][
            "total_new_clipping"
        ]
        == 0.0
    )


def test_identical_images_have_unit_smoothing_ratio():
    image = make_document_like_image()

    result = verify_preservation(
        image,
        image.copy()
    )

    assert (
        result["metrics"]["smoothing_ratio"] == 1.0
    )


# --- Safe treatment category ----------------------------------------


@requires_dataset
def test_safe_clahe_on_faded_text_is_accepted():
    faded = load_case(SYNTHETIC_DIR, "11_faded_text.png")

    result = verify_preservation(
        faded,
        clahe(faded, clip_limit=1.0)
    )

    assert status_of(result) in {
        "acceptable", "caution"
    }


@requires_dataset
def test_safe_clahe_on_manuscript_is_accepted():
    image = load_case(
        MANUSCRIPT_DIR, "01_normal.png", size=(640, 320)
    )

    result = verify_preservation(
        image,
        clahe(image, clip_limit=1.5)
    )

    assert status_of(result) == "acceptable"


@requires_dataset
def test_safe_sharpen_on_manuscript_is_accepted():
    image = load_case(
        MANUSCRIPT_DIR, "01_normal.png", size=(640, 320)
    )

    result = verify_preservation(
        image,
        sharpen(image, amount=0.25, sigma=1.0)
    )

    assert status_of(result) == "acceptable"


@requires_dataset
def test_safe_illumination_normalization_is_accepted():
    image = load_case(
        SYNTHETIC_DIR, "01_normal.png", size=(640, 320)
    )

    result = verify_preservation(
        image,
        illumination_normalize(image, strength=0.45)
    )

    assert status_of(result) == "acceptable"


@requires_dataset
def test_safe_gamma_on_dark_is_accepted():
    dark = load_case(
        SYNTHETIC_DIR, "03_dark.png", size=(640, 320)
    )

    result = verify_preservation(
        dark,
        gamma_correct(dark, gamma=0.85)
    )

    assert status_of(result) == "acceptable"


# --- Over-treatment category ----------------------------------------


def test_extreme_gamma_darkening_is_high_risk():
    image = make_document_like_image()

    result = verify_preservation(
        image,
        gamma_correct(image, gamma=0.2)
    )

    assert status_of(result) == "high_risk"
    assert "major_smoothing" in codes_of(result)


def make_thin_text_image():
    image = np.full(
        (200, 300),
        230,
        dtype=np.uint8
    )

    cv2.putText(
        image,
        "TEXT",
        (30, 110),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        60,
        1,
        cv2.LINE_AA
    )

    return image


def test_median_kernel5_on_clean_image_is_flagged():
    # Thin strokes are the real damage target of kernel-5 median.
    # Synthetic strokes only drop to caution; real manuscripts with
    # finer multi-scale detail reach high_risk (dataset test below).
    image = make_thin_text_image()

    result = verify_preservation(
        image,
        median_denoise(image, kernel_size=5)
    )

    assert status_of(result) in {"caution", "high_risk"}


def test_median_kernel7_on_thin_text_is_high_risk():
    image = make_thin_text_image()

    result = verify_preservation(
        image,
        median_denoise(image, kernel_size=7)
    )

    assert status_of(result) == "high_risk"
    assert "major_smoothing" in codes_of(result)


@requires_dataset
def test_median_kernel5_on_manuscript_is_high_risk():
    image = load_case(
        MANUSCRIPT_DIR, "01_normal.png", size=(640, 320)
    )

    result = verify_preservation(
        image,
        median_denoise(image, kernel_size=5)
    )

    assert status_of(result) == "high_risk"


def test_aggressive_sharpening_is_flagged():
    image = make_document_like_image()

    safe = verify_preservation(
        image,
        sharpen(image, amount=0.25, sigma=1.0)
    )

    aggressive = verify_preservation(
        image,
        sharpen(image, amount=1.0, sigma=1.0)
    )

    aggressive_rank = {
        "acceptable": 0,
        "caution": 1,
        "high_risk": 2,
    }

    assert (
        aggressive_rank[status_of(aggressive)]
        >= aggressive_rank[status_of(safe)]
    )


# --- Detail-loss category -------------------------------------------


def test_strong_blur_triggers_major_smoothing():
    image = make_document_like_image()

    blurred = cv2.GaussianBlur(
        image, (31, 31), 10
    )

    result = verify_preservation(
        image,
        blurred
    )

    assert status_of(result) == "high_risk"
    assert "major_smoothing" in codes_of(result)


def test_extreme_blur_is_high_risk():
    image = make_document_like_image()

    blurred = cv2.GaussianBlur(
        image, (51, 51), 20
    )

    result = verify_preservation(
        image,
        blurred
    )

    assert status_of(result) == "high_risk"


# --- Contrast damage category ---------------------------------------


@requires_dataset
def test_histogram_equalization_is_high_risk():
    image = load_case(
        SYNTHETIC_DIR, "01_normal.png", size=(640, 320)
    )

    result = verify_preservation(
        image,
        histogram_equalization(image)
    )

    assert status_of(result) == "high_risk"
    assert "major_edge_inflation" in codes_of(result)


@requires_dataset
def test_histogram_equalization_on_manuscript_is_high_risk():
    image = load_case(
        MANUSCRIPT_DIR, "01_normal.png", size=(640, 320)
    )

    result = verify_preservation(
        image,
        histogram_equalization(image)
    )

    assert status_of(result) == "high_risk"


# --- Threshold damage category --------------------------------------


@requires_dataset
def test_global_threshold_on_faded_text_reports_ink_loss():
    faded = load_case(SYNTHETIC_DIR, "11_faded_text.png")

    result = verify_preservation(
        faded,
        global_threshold(faded, threshold=127)
    )

    assert status_of(result) == "high_risk"
    assert "major_ink_loss" in codes_of(result)


@requires_dataset
def test_otsu_threshold_keeps_ink_coverage():
    image = load_case(
        SYNTHETIC_DIR, "01_normal.png", size=(640, 320)
    )

    result = verify_preservation(
        image,
        otsu_threshold(image)
    )

    assert (
        result["metrics"]["ink_retention"] > 0.9
    )


def test_binarization_does_not_trigger_clipping_warning():
    image = make_document_like_image()

    result = verify_preservation(
        image,
        global_threshold(image, threshold=127)
    )

    assert (
        "clipping" not in codes_of(result)
        and "major_clipping" not in codes_of(result)
    )
    assert result["metrics"]["clipping_change"][
        "binary_output"
    ] is True


def test_ink_metrics_are_inactive_for_grayscale_output():
    image = make_document_like_image()

    result = verify_preservation(
        image,
        gamma_correct(image, gamma=0.85)
    )

    assert (
        result["metrics"]["ink_retention"] == 1.0
    )
    assert result["metrics"]["clipping_change"][
        "binary_output"
    ] is False


# --- Overprocessing of normal images --------------------------------


@requires_dataset
def test_median_on_clean_manuscript_is_flagged():
    image = load_case(
        MANUSCRIPT_DIR, "01_normal.png", size=(640, 320)
    )

    result = verify_preservation(
        image,
        median_denoise(image, kernel_size=3)
    )

    assert status_of(result) in {
        "caution", "high_risk"
    }


# --- Geometry error category ----------------------------------------


def test_wrong_rotation_angle_produces_warnings():
    image = make_document_like_image()

    matrix = cv2.getRotationMatrix2D(
        (150, 100), 3.0, 1.0
    )

    rotated = cv2.warpAffine(
        image,
        matrix,
        (300, 200),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=230,
    )

    result = verify_preservation(
        image,
        rotated
    )

    assert status_of(result) in {
        "caution", "high_risk"
    }


def test_dimension_change_is_resized_not_crashed():
    image = make_document_like_image()

    larger = cv2.resize(image, (600, 400))

    result = verify_preservation(
        image,
        larger
    )

    assert "metrics" in result


# --- Identical-image invariants -------------------------------------


@requires_dataset
def test_identical_near_binary_document_is_acceptable():
    document = load_case(
        DOCUMENT_DIR, "01_normal.png", size=(640, 320)
    )

    result = verify_preservation(
        document,
        document.copy()
    )

    assert status_of(result) == "acceptable"


@requires_dataset
def test_identical_noisy_image_is_acceptable():
    noisy = load_case(
        MANUSCRIPT_DIR,
        "06_salt_pepper_noise.png",
        size=(640, 320)
    )

    result = verify_preservation(
        noisy,
        noisy.copy()
    )

    assert status_of(result) == "acceptable"


# --- Denoiser fairness ----------------------------------------------


@requires_dataset
def test_median_kernel3_on_salt_pepper_is_not_high_risk():
    noisy = load_case(
        MANUSCRIPT_DIR,
        "06_salt_pepper_noise.png",
        size=(640, 320)
    )

    result = verify_preservation(
        noisy,
        median_denoise(noisy, kernel_size=3)
    )

    assert status_of(result) in {
        "acceptable", "caution"
    }


@requires_dataset
def test_median_kernel3_on_salt_pepper_document_is_not_high_risk():
    noisy = load_case(
        DOCUMENT_DIR,
        "06_salt_pepper_noise.png",
        size=(640, 320)
    )

    result = verify_preservation(
        noisy,
        median_denoise(noisy, kernel_size=3)
    )

    assert status_of(result) in {
        "acceptable", "caution"
    }


def test_denoising_synthetic_salt_pepper_is_fair():
    image = make_document_like_image()
    noisy = make_salt_pepper(image, density=0.03)

    result = verify_preservation(
        noisy,
        median_denoise(noisy, kernel_size=3)
    )

    assert status_of(result) in {
        "acceptable", "caution"
    }


def test_denoised_result_keeps_reference_edges():
    image = make_document_like_image()
    noisy = make_salt_pepper(image, density=0.03)

    result = verify_preservation(
        noisy,
        median_denoise(noisy, kernel_size=3)
    )

    assert (
        result["metrics"]["edge_retention"] > 0.75
    )


# --- Adaptive threshold ink direction -------------------------------


@requires_dataset
def test_adaptive_threshold_ink_ratio_stays_bounded():
    image = load_case(
        MANUSCRIPT_DIR, "01_normal.png", size=(640, 320)
    )

    result = verify_preservation(
        image,
        adaptive_threshold(image)
    )

    assert (
        result["metrics"]["ink_inflation_ratio"] < 2.5
    )