import cv2
import numpy as np
import pytest

from processing.operations import OPERATIONS, apply_operation


SAFE_COURSE_OPERATIONS = {
    "erosion",
    "dilation",
    "morphological_gradient",
    "gaussian_blur",
    "laplacian_sharpen",
    "sobel_edges",
    "contrast_stretch",
    "log_transform",
}


def _gray_document():
    image = np.full((64, 96), 220, dtype=np.uint8)
    cv2.rectangle(image, (14, 18), (82, 45), 70, 2)
    cv2.line(image, (20, 28), (76, 28), 40, 2)
    cv2.line(image, (20, 36), (68, 36), 55, 2)
    return image


def _bgra_document():
    gray = _gray_document()
    bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    alpha = np.full(gray.shape, 173, dtype=np.uint8)
    return np.dstack((bgr, alpha))


def _dark_foreground_square():
    image = np.full((41, 41), 255, dtype=np.uint8)
    cv2.rectangle(image, (15, 15), (25, 25), 0, -1)
    return image


def test_safe_course_operations_are_registered_and_manual_only():
    assert SAFE_COURSE_OPERATIONS <= set(OPERATIONS)
    for operation_id in SAFE_COURSE_OPERATIONS:
        assert OPERATIONS[operation_id]["automatic"] is False


@pytest.mark.parametrize("operation_id", sorted(SAFE_COURSE_OPERATIONS))
def test_course_operation_returns_uint8_nonempty_image(operation_id):
    result = apply_operation(operation_id, _gray_document(), {})
    assert isinstance(result, np.ndarray)
    assert result.size > 0
    assert result.dtype == np.uint8


def test_erosion_reduces_dark_document_foreground():
    image = _dark_foreground_square()
    result = apply_operation("erosion", image, {"kernel_size": 3, "iterations": 1})
    assert np.count_nonzero(result < 128) < np.count_nonzero(image < 128)


def test_dilation_expands_dark_document_foreground():
    image = _dark_foreground_square()
    result = apply_operation("dilation", image, {"kernel_size": 3, "iterations": 1})
    assert np.count_nonzero(result < 128) > np.count_nonzero(image < 128)


def test_morphological_gradient_highlights_boundaries():
    image = _dark_foreground_square()
    result = apply_operation("morphological_gradient", image, {"kernel_size": 3})
    assert result.max() > 0
    assert result[20, 20] == 0
    assert np.count_nonzero(result) > 0


def test_gaussian_blur_spreads_impulse_and_reduces_peak():
    image = np.zeros((31, 31), dtype=np.uint8)
    image[15, 15] = 255
    result = apply_operation("gaussian_blur", image, {"kernel_size": 5, "sigma": 0.0})
    assert 0 < result[15, 15] < 255
    assert result[15, 16] > 0


def test_laplacian_sharpen_uses_absolute_laplacian_boost():
    image = np.full((31, 31), 200, dtype=np.uint8)
    image[:, 15] = 80
    result = apply_operation("laplacian_sharpen", image, {"amount": 0.5, "kernel_size": 3})
    assert result[15, 15] >= image[15, 15]
    assert result[15, 14] >= image[15, 14]


def test_sobel_edges_flat_image_is_zero():
    image = np.full((24, 24), 100, dtype=np.uint8)
    result = apply_operation("sobel_edges", image, {"kernel_size": 3})
    assert np.count_nonzero(result) == 0


def test_contrast_stretch_uses_requested_range():
    image = np.array([[50, 100, 150]], dtype=np.uint8)
    result = apply_operation("contrast_stretch", image, {"low_percentile": 0, "high_percentile": 100})
    assert tuple(int(value) for value in result[0]) == (0, 127, 254)


def test_log_transform_uses_zip_per_image_normalization():
    image = np.full((16, 16), 50, dtype=np.uint8)
    result = apply_operation("log_transform", image, {"strength": 1.0})
    assert int(result[0, 0]) == 255

    endpoints = np.array([[0, 255]], dtype=np.uint8)
    endpoint_result = apply_operation("log_transform", endpoints, {"strength": 1.0})
    assert tuple(int(value) for value in endpoint_result[0]) == (0, 255)


def test_gaussian_blur_preserves_bgra_alpha_channel():
    image = _bgra_document()
    result = apply_operation("gaussian_blur", image, {"kernel_size": 5, "sigma": 0.0})
    assert result.shape == image.shape
    assert np.array_equal(result[:, :, 3], image[:, :, 3])


def test_contrast_stretch_preserves_colour_shape():
    image = cv2.cvtColor(_gray_document(), cv2.COLOR_GRAY2BGR)
    result = apply_operation("contrast_stretch", image, {"low_percentile": 2, "high_percentile": 98})
    assert result.shape == image.shape


def test_log_transform_preserves_colour_shape():
    image = cv2.cvtColor(_gray_document(), cv2.COLOR_GRAY2BGR)
    result = apply_operation("log_transform", image, {"strength": 1.0})
    assert result.shape == image.shape


def test_sobel_edges_returns_gray_map():
    result = apply_operation("sobel_edges", _bgra_document(), {"kernel_size": 3})
    assert result.ndim == 2
    assert result.shape == _gray_document().shape


@pytest.mark.parametrize(
    "operation_id, params",
    [
        ("erosion", {"kernel_size": 4}),
        ("dilation", {"iterations": 0}),
        ("morphological_gradient", {"kernel_size": 2}),
        ("gaussian_blur", {"kernel_size": 4}),
        ("gaussian_blur", {"sigma": -1}),
        ("laplacian_sharpen", {"kernel_size": 2}),
        ("laplacian_sharpen", {"amount": -0.1}),
        ("sobel_edges", {"kernel_size": 2}),
        ("contrast_stretch", {"low_percentile": 99, "high_percentile": 2}),
        ("log_transform", {"strength": 0}),
    ],
)
def test_course_operations_reject_invalid_parameters(operation_id, params):
    with pytest.raises(ValueError):
        apply_operation(operation_id, _gray_document(), params)
