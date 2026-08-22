from pathlib import Path

import cv2
import numpy as np

from processing.document_boundary import detect_document_boundary
from processing.document_rectification import rectify_document


INPUT_DIR = Path("evaluation/input")


def _load_image(name):
    path = INPUT_DIR / name
    assert path.is_file(), f"Missing test image: {path}"

    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    assert image is not None, f"Could not decode: {path}"

    return image


def _run_preparation(image):
    boundary = detect_document_boundary(image)

    if not boundary["detected"]:
        return {
            "boundary": boundary,
            "rectified": False,
            "result": None,
        }

    result = rectify_document(image, boundary["corners"])

    return {
        "boundary": boundary,
        "rectified": True,
        "result": result,
    }


def _assert_valid_preparation(image, preparation):
    boundary = preparation["boundary"]

    assert boundary["detected"] is True
    assert len(boundary["corners"]) == 4
    assert preparation["rectified"] is True
    assert preparation["result"] is not None

    result = preparation["result"]

    assert result["image"] is not None
    assert result["image"].size > 0
    assert result["width"] > 0
    assert result["height"] > 0
    assert result["image"].shape[1] == result["width"]
    assert result["image"].shape[0] == result["height"]

    corners = np.asarray(boundary["corners"], dtype=np.int32)
    height, width = image.shape[:2]

    assert np.all(corners[:, 0] >= 0)
    assert np.all(corners[:, 0] < width)
    assert np.all(corners[:, 1] >= 0)
    assert np.all(corners[:, 1] < height)


def test_clear_document_boundary_rectification_chain():
    image = _load_image("b01.jpg")
    original = image.copy()

    preparation = _run_preparation(image)

    _assert_valid_preparation(image, preparation)
    assert np.array_equal(image, original)


def test_cluttered_document_boundary_rectification_chain():
    image = _load_image("b02.jpg")
    original = image.copy()

    preparation = _run_preparation(image)

    _assert_valid_preparation(image, preparation)
    assert np.array_equal(image, original)