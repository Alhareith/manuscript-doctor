import cv2
import numpy as np
import pytest

from processing.document_rectification import rectify_document


def make_perspective_document():
    image = np.zeros((500, 700, 3), dtype=np.uint8)

    corners = np.array(
        [
            [150, 70],
            [570, 120],
            [610, 430],
            [100, 390],
        ],
        dtype=np.int32,
    )

    cv2.fillConvexPoly(image, corners, (240, 240, 240))

    cv2.line(image, (220, 160), (510, 190), (0, 0, 0), 8)

    cv2.line(image, (190, 230), (530, 260), (0, 0, 0), 8)

    return image, corners


def test_rectifies_valid_quadrilateral():
    image, corners = make_perspective_document()

    result = rectify_document(image, corners.tolist())

    assert result["image"] is not None
    assert result["image"].size > 0
    assert result["width"] >= 40
    assert result["height"] >= 40
    assert result["image"].shape[1] == result["width"]
    assert result["image"].shape[0] == result["height"]


def test_preserves_source_corner_order():
    image, corners = make_perspective_document()

    result = rectify_document(image, corners.tolist())

    assert result["source_corners"] == corners.tolist()


def test_returns_valid_transform_matrix():
    image, corners = make_perspective_document()

    result = rectify_document(image, corners.tolist())

    transform = result["transform"]

    assert transform.shape == (3, 3)
    assert np.all(np.isfinite(transform))


def test_does_not_modify_input_image():
    image, corners = make_perspective_document()
    original = image.copy()

    rectify_document(image, corners.tolist())

    assert np.array_equal(image, original)


def test_supports_grayscale_image():
    image, corners = make_perspective_document()

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    result = rectify_document(gray, corners.tolist())

    assert result["image"].ndim == 2
    assert result["image"].shape[1] == result["width"]
    assert result["image"].shape[0] == result["height"]


def test_rejects_invalid_corner_count():
    image, _ = make_perspective_document()

    with pytest.raises(ValueError):
        rectify_document(
            image,
            [
                [10, 10],
                [100, 10],
                [100, 100],
            ],
        )


def test_rejects_out_of_bounds_corners():
    image, _ = make_perspective_document()

    with pytest.raises(ValueError):
        rectify_document(
            image,
            [
                [-10, 20],
                [500, 20],
                [500, 400],
                [20, 400],
            ],
        )


def test_rejects_non_convex_quadrilateral():
    image, _ = make_perspective_document()

    with pytest.raises(ValueError):
        rectify_document(
            image,
            [
                [100, 100],
                [500, 100],
                [200, 200],
                [100, 400],
            ],
        )


def test_rejects_tiny_quadrilateral():
    image, _ = make_perspective_document()

    with pytest.raises(ValueError):
        rectify_document(
            image,
            [
                [10, 10],
                [20, 10],
                [20, 20],
                [10, 20],
            ],
        )


def test_rejects_invalid_image():
    with pytest.raises(ValueError):
        rectify_document(
            None,
            [
                [0, 0],
                [100, 0],
                [100, 100],
                [0, 100],
            ],
        )
