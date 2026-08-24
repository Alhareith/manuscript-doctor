import cv2
import numpy as np
import pytest

from processing.operations import (
    apply_operation,
    flip_horizontal,
    flip_vertical,
    list_operations,
    rotate_left,
    rotate_right,
)


def make_marked_image():
    image = np.zeros((2, 3), dtype=np.uint8)
    image[0, 0] = 1
    image[0, 2] = 2
    image[1, 0] = 3
    image[1, 2] = 4
    return image


def test_rotate_right_preserves_all_pixels_and_changes_orientation():
    result = rotate_right(make_marked_image())
    expected = np.array([[3, 1], [0, 0], [4, 2]], dtype=np.uint8)
    assert result.shape == (3, 2)
    assert np.array_equal(result, expected)


def test_rotate_left_preserves_all_pixels_and_changes_orientation():
    result = rotate_left(make_marked_image())
    expected = np.array([[2, 4], [0, 0], [1, 3]], dtype=np.uint8)
    assert result.shape == (3, 2)
    assert np.array_equal(result, expected)


def test_vertical_and_horizontal_flip_are_distinct_and_lossless():
    image = make_marked_image()
    assert np.array_equal(flip_vertical(image), cv2.flip(image, 0))
    assert np.array_equal(flip_horizontal(image), cv2.flip(image, 1))
    assert np.array_equal(np.sort(flip_vertical(image).ravel()), np.sort(image.ravel()))
    assert np.array_equal(np.sort(flip_horizontal(image).ravel()), np.sort(image.ravel()))


@pytest.mark.parametrize('operation_id', ['rotate_right', 'rotate_left', 'flip_vertical', 'flip_horizontal'])
def test_orientation_operations_are_registered_and_callable(operation_id):
    image = make_marked_image()
    registered = {item['id'] for item in list_operations()}
    assert operation_id in registered
    result = apply_operation(operation_id, image, {})
    assert result.dtype == image.dtype
    assert result.size == image.size
