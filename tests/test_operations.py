
import cv2
import numpy as np
import pytest

from processing.operations import (
    apply_operation,
    clahe,
    get_operation,
    histogram_equalization,
    list_operations,
    median_denoise,
    sharpen,
    global_threshold,
    otsu_threshold,
    adaptive_threshold,
    morphological_opening,
    morphological_closing,
    bilateral_denoise,
    non_local_means_denoise,
    illumination_normalize,
    gamma_correct,
    intensity_adjust,
    faded_text_enhance,
    background_suppress,
    weak_structure_suppress,
    morphological_top_hat,
    morphological_black_hat
)


def make_color_image():
    image = np.full(
        (120, 160, 3),
        180,
        dtype=np.uint8
    )

    cv2.rectangle(
        image,
        (30, 30),
        (130, 90),
        (30, 30, 30),
        -1
    )

    return image


def make_grayscale_image():
    image = np.full(
        (120, 160),
        180,
        dtype=np.uint8
    )

    cv2.rectangle(
        image,
        (30, 30),
        (130, 90),
        30,
        -1
    )

    return image


def assert_binary(image):
    values = set(
        np.unique(image).tolist()
    )

    assert values.issubset({0, 255})


def test_clahe_preserves_color_shape_and_dtype():
    image = make_color_image()

    result = clahe(image)

    assert result.shape == image.shape
    assert result.dtype == image.dtype


def test_histogram_equalization_preserves_color_shape():
    image = make_color_image()

    result = histogram_equalization(image)

    assert result.shape == image.shape


def test_median_denoise_preserves_shape():
    image = make_color_image()

    result = median_denoise(image)

    assert result.shape == image.shape


def test_sharpen_preserves_shape_and_dtype():
    image = make_color_image()

    result = sharpen(image)

    assert result.shape == image.shape
    assert result.dtype == np.uint8


def test_global_threshold_returns_binary_image():
    image = make_color_image()

    result = global_threshold(image)

    assert result.ndim == 2
    assert_binary(result)


def test_otsu_threshold_returns_binary_image():
    image = make_grayscale_image()

    result = otsu_threshold(image)

    assert result.ndim == 2
    assert_binary(result)


def test_adaptive_threshold_returns_binary_image():
    image = make_color_image()

    result = adaptive_threshold(image)

    assert result.ndim == 2
    assert_binary(result)


def test_morphological_opening_returns_grayscale():
    image = make_color_image()

    result = morphological_opening(image)

    assert result.ndim == 2
    assert result.shape == image.shape[:2]


def test_morphological_closing_returns_grayscale():
    image = make_color_image()

    result = morphological_closing(image)

    assert result.ndim == 2
    assert result.shape == image.shape[:2]


@pytest.mark.parametrize(
    "operation",
    [
        clahe,
        histogram_equalization,
        median_denoise,
        sharpen,
        global_threshold,
        otsu_threshold,
        adaptive_threshold,
        morphological_opening,
        morphological_closing,
        morphological_top_hat,
        morphological_black_hat
    ]
)
def test_operations_do_not_modify_original(operation):
    image = make_color_image()

    original = image.copy()

    operation(image)

    assert np.array_equal(
        image,
        original
    )


def test_clahe_supports_grayscale():
    image = make_grayscale_image()

    result = clahe(image)

    assert result.shape == image.shape


def test_clahe_preserves_alpha_channel():
    bgr = make_color_image()

    alpha = np.full(
        bgr.shape[:2],
        200,
        dtype=np.uint8
    )

    image = np.dstack(
        (
            bgr,
            alpha
        )
    )

    result = clahe(image)

    assert result.shape == image.shape

    assert np.array_equal(
        result[:, :, 3],
        alpha
    )


def test_even_median_kernel_is_rejected():
    image = make_color_image()

    with pytest.raises(ValueError):
        median_denoise(
            image,
            kernel_size=4
        )


def test_invalid_threshold_is_rejected():
    image = make_color_image()

    with pytest.raises(ValueError):
        global_threshold(
            image,
            threshold=300
        )


def test_invalid_adaptive_block_size_is_rejected():
    image = make_color_image()

    with pytest.raises(ValueError):
        adaptive_threshold(
            image,
            block_size=10
        )


def test_invalid_sharpen_amount_is_rejected():
    image = make_color_image()

    with pytest.raises(ValueError):
        sharpen(
            image,
            amount=3
        )


def test_invalid_image_is_rejected():
    with pytest.raises(ValueError):
        clahe(None)


def test_empty_image_is_rejected():
    image = np.array(
        [],
        dtype=np.uint8
    )

    with pytest.raises(ValueError):
        median_denoise(image)


def test_non_uint8_image_is_rejected():
    image = np.zeros(
        (100, 100),
        dtype=np.uint16
    )

    with pytest.raises(ValueError):
        clahe(image)


def test_registry_contains_expected_operations():
    operations = list_operations()

    ids = {
        operation["id"]
        for operation in operations
    }

    assert {
        "clahe",
        "histogram_equalization",
        "median_denoise",
        "sharpen",
        "global_threshold",
        "otsu_threshold",
        "adaptive_threshold",
        "morphological_opening",
        "morphological_closing"
    }.issubset(ids)


def test_registry_does_not_expose_function_objects():
    operations = list_operations()

    for operation in operations:
        assert "function" not in operation


def test_unknown_operation_is_rejected():
    with pytest.raises(ValueError):
        get_operation(
            "unknown_operation"
        )


def test_registered_operation_can_be_executed():
    image = make_color_image()

    result = apply_operation(
        "clahe",
        image
    )

    assert result.shape == image.shape


def test_registered_operation_accepts_parameters():
    image = make_color_image()

    result = apply_operation(
        "median_denoise",
        image,
        {
            "kernel_size": 5
        }
    )

    assert result.shape == image.shape


def test_params_must_be_dictionary():
    image = make_color_image()

    with pytest.raises(ValueError):
        apply_operation(
            "clahe",
            image,
            "invalid"
        )

def test_clahe_default_matches_evaluated_default():
    image = make_color_image()

    default_result = clahe(image)

    explicit_result = clahe(
        image,
        clip_limit=1.5,
        tile_grid_size=8
    )

    assert np.array_equal(
        default_result,
        explicit_result
    )


def test_sharpen_default_matches_evaluated_default():
    image = make_color_image()

    default_result = sharpen(image)

    explicit_result = sharpen(
        image,
        amount=0.25,
        kernel_size=3
    )

    assert np.array_equal(
        default_result,
        explicit_result
    )

def test_bilateral_denoise_preserves_shape():
    image = np.full(
        (120, 160),
        180,
        dtype=np.uint8
    )

    result = bilateral_denoise(
        image
    )

    assert result.shape == image.shape
    assert result.dtype == np.uint8


def test_non_local_means_preserves_shape():
    image = np.full(
        (120, 160),
        180,
        dtype=np.uint8
    )

    result = non_local_means_denoise(
        image
    )

    assert result.shape == image.shape
    assert result.dtype == np.uint8


def test_bilateral_rejects_invalid_diameter():
    image = np.full(
        (100, 100),
        180,
        dtype=np.uint8
    )

    with pytest.raises(ValueError):
        bilateral_denoise(
            image,
            diameter=0
        )


def test_nlm_rejects_invalid_template_window():
    image = np.full(
        (100, 100),
        180,
        dtype=np.uint8
    )

    with pytest.raises(ValueError):
        non_local_means_denoise(
            image,
            template_window_size=6
        )


def test_nlm_rejects_invalid_search_window():
    image = np.full(
        (100, 100),
        180,
        dtype=np.uint8
    )

    with pytest.raises(ValueError):
        non_local_means_denoise(
            image,
            search_window_size=20
        )
def test_illumination_normalize_preserves_shape():
    image = np.full(
        (180, 240),
        180,
        dtype=np.uint8
    )

    result = illumination_normalize(
        image
    )

    assert result.shape == image.shape
    assert result.dtype == np.uint8


def test_illumination_normalize_color():
    image = np.full(
        (180, 240, 3),
        180,
        dtype=np.uint8
    )

    result = illumination_normalize(
        image
    )

    assert result.shape == image.shape
    assert result.dtype == np.uint8


def test_illumination_normalize_preserves_alpha():
    image = np.full(
        (100, 120, 4),
        180,
        dtype=np.uint8
    )

    image[:, :, 3] = 123

    result = illumination_normalize(
        image
    )

    assert result.shape == image.shape

    assert np.array_equal(
        result[:, :, 3],
        image[:, :, 3]
    )


def test_illumination_normalize_rejects_even_kernel():
    image = np.full(
        (100, 100),
        180,
        dtype=np.uint8
    )

    with pytest.raises(ValueError):
        illumination_normalize(
            image,
            kernel_size=50
        )


def test_illumination_normalize_rejects_small_kernel():
    image = np.full(
        (100, 100),
        180,
        dtype=np.uint8
    )

    with pytest.raises(ValueError):
        illumination_normalize(
            image,
            kernel_size=9
        )


def test_illumination_normalize_rejects_invalid_strength():
    image = np.full(
        (100, 100),
        180,
        dtype=np.uint8
    )

    with pytest.raises(ValueError):
        illumination_normalize(
            image,
            strength=1.5
        )

def test_illumination_normalization_reduces_gradient():
    height = 240
    width = 400

    gradient = np.linspace(
        90,
        220,
        width,
        dtype=np.float32
    )

    image = np.tile(
        gradient,
        (height, 1)
    ).astype(
        np.uint8
    )

    cv2.putText(
        image,
        "DOCUMENT",
        (60, 130),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.2,
        35,
        3,
        cv2.LINE_AA
    )

    result = illumination_normalize(
        image,
        kernel_size=51,
        strength=0.65
    )

    before_left = float(
        np.mean(
            image[:, :50]
        )
    )

    before_right = float(
        np.mean(
            image[:, -50:]
        )
    )

    after_left = float(
        np.mean(
            result[:, :50]
        )
    )

    after_right = float(
        np.mean(
            result[:, -50:]
        )
    )

    before_difference = abs(
        before_left
        - before_right
    )

    after_difference = abs(
        after_left
        - after_right
    )

    assert (
        after_difference
        < before_difference
    )

def test_gamma_correct_preserves_shape():
    image = np.full(
        (120, 160),
        100,
        dtype=np.uint8
    )

    result = gamma_correct(
        image,
        gamma=1.2
    )

    assert result.shape == image.shape
    assert result.dtype == np.uint8


def test_gamma_correct_rejects_invalid_gamma():
    image = np.full(
        (100, 100),
        150,
        dtype=np.uint8
    )

    with pytest.raises(ValueError):
        gamma_correct(
            image,
            gamma=0
        )


def test_intensity_adjust_preserves_shape():
    image = np.full(
        (120, 160),
        100,
        dtype=np.uint8
    )

    result = intensity_adjust(
        image,
        alpha=1.05,
        beta=5
    )

    assert result.shape == image.shape
    assert result.dtype == np.uint8


def test_intensity_adjust_rejects_invalid_alpha():
    image = np.full(
        (100, 100),
        150,
        dtype=np.uint8
    )

    with pytest.raises(ValueError):
        intensity_adjust(
            image,
            alpha=0
        )


def test_faded_text_enhance_preserves_shape():
    image = np.full(
        (160, 220),
        190,
        dtype=np.uint8
    )

    cv2.putText(
        image,
        "TEXT",
        (40, 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.2,
        145,
        2,
        cv2.LINE_AA
    )

    result = faded_text_enhance(
        image
    )

    assert result.shape == image.shape
    assert result.dtype == np.uint8

def test_background_suppress_preserves_shape():
    image = np.full(
        (160, 220),
        180,
        dtype=np.uint8
    )

    result = background_suppress(
        image
    )

    assert result.shape == image.shape
    assert result.dtype == np.uint8


def test_background_suppress_rejects_even_kernel():
    image = np.full(
        (100, 100),
        180,
        dtype=np.uint8
    )

    with pytest.raises(ValueError):
        background_suppress(
            image,
            kernel_size=30
        )


def test_weak_structure_suppress_preserves_shape():
    image = np.full(
        (160, 220),
        180,
        dtype=np.uint8
    )

    result = weak_structure_suppress(
        image
    )

    assert result.shape == image.shape
    assert result.dtype == np.uint8


def test_weak_structure_suppress_invalid_threshold():
    image = np.full(
        (100, 100),
        180,
        dtype=np.uint8
    )

    with pytest.raises(ValueError):
        weak_structure_suppress(
            image,
            threshold=0
        )

def test_top_hat_preserves_dimensions():
    image = np.full(
        (120, 160),
        180,
        dtype=np.uint8
    )

    result = morphological_top_hat(
        image,
        kernel_size=3
    )

    assert result.shape == image.shape
    assert result.dtype == np.uint8


def test_black_hat_preserves_dimensions():
    image = np.full(
        (120, 160),
        180,
        dtype=np.uint8
    )

    result = morphological_black_hat(
        image,
        kernel_size=5
    )

    assert result.shape == image.shape
    assert result.dtype == np.uint8


def test_top_hat_rejects_even_kernel():
    image = np.full(
        (100, 100),
        180,
        dtype=np.uint8
    )

    with pytest.raises(ValueError):
        morphological_top_hat(
            image,
            kernel_size=4
        )


def test_black_hat_rejects_even_kernel():
    image = np.full(
        (100, 100),
        180,
        dtype=np.uint8
    )

    with pytest.raises(ValueError):
        morphological_black_hat(
            image,
            kernel_size=4
        )
