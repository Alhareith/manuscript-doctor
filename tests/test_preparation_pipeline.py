from pathlib import Path

import cv2
import numpy as np
import pytest

from processing.preparation_pipeline import prepare_document


INPUT_DIR = Path("evaluation/input")


def _load_image(name):
    path = INPUT_DIR / name
    assert path.is_file(), f"Missing test image: {path}"

    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    assert image is not None, f"Could not decode: {path}"

    return image


def test_prepares_clear_document():
    image = _load_image("b01.jpg")
    result = prepare_document(image)

    assert result["prepared"] is True
    assert result["boundary"]["detected"] is True
    assert result["perspective"]["applied"] is True
    assert result["skew"] is not None
    assert result["deskew"] is not None
    assert result["image"] is not None
    assert result["image"].size > 0


def test_prepares_second_real_document():
    image = _load_image("b02.jpg")
    result = prepare_document(image)

    assert result["prepared"] is True
    assert result["boundary"]["detected"] is True
    assert result["perspective"]["applied"] is True


def test_steps_are_in_correct_order():
    image = _load_image("b01.jpg")
    result = prepare_document(image)

    steps = [item["step"] for item in result["steps"]]

    assert steps == [
        "boundary",
        "perspective",
        "skew_detection",
        "auto_deskew",
    ]


def test_original_image_is_not_modified():
    image = _load_image("b01.jpg")
    original = image.copy()

    prepare_document(image)

    assert np.array_equal(image, original)


def test_returns_independent_result_image():
    image = _load_image("b01.jpg")
    result = prepare_document(image)

    assert result["image"] is not image


def test_stops_safely_when_boundary_is_not_detected():
    image = np.full((600, 800, 3), 220, dtype=np.uint8)
    result = prepare_document(image)

    assert result["prepared"] is False
    assert result["boundary"]["detected"] is False
    assert result["perspective"] is None
    assert result["skew"] is None
    assert result["deskew"] is None
    assert len(result["steps"]) == 1
    assert result["steps"][0]["step"] == "boundary"
    assert result["steps"][0]["status"] == "rejected"
    assert result["reason"].startswith("stopped:")


def test_invalid_input_raises_value_error():
    with pytest.raises(ValueError):
        prepare_document(None)
        