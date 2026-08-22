from pathlib import Path

import cv2
import numpy as np
import pytest

from processing.smart_document_pipeline import run_smart_document_pipeline


INPUT_DIR = Path("evaluation/input")


def _load_image(name):
    path = INPUT_DIR / name
    assert path.is_file(), f"Missing test image: {path}"

    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    assert image is not None, f"Could not decode: {path}"

    return image


def test_runs_full_pipeline_for_valid_document():
    image = _load_image("b01.jpg")
    result = run_smart_document_pipeline(image)

    assert result["preparation"]["prepared"] is True
    assert result["preparation_verification"]["status"] == "accept"
    assert result["prepared_analysis"] is not None
    assert result["treatment"] is not None
    assert result["decision"]["stage"] == "treatment"


def test_runs_full_pipeline_for_second_valid_document():
    image = _load_image("b02.jpg")
    result = run_smart_document_pipeline(image)

    assert result["preparation"]["prepared"] is True
    assert result["preparation_verification"]["verified"] is True
    assert result["prepared_image"] is not None
    assert result["prepared_analysis"] is not None
    assert result["treatment"] is not None


def test_stops_when_preparation_fails():
    image = np.full((600, 800, 3), 220, dtype=np.uint8)
    result = run_smart_document_pipeline(image)

    assert result["preparation"]["prepared"] is False
    assert result["prepared_analysis"] is None
    assert result["treatment"] is None
    assert result["decision"]["status"] == "stopped"
    assert result["decision"]["stage"] == "preparation"


def test_does_not_modify_original_image():
    image = _load_image("b01.jpg")
    original = image.copy()

    run_smart_document_pipeline(image)

    assert np.array_equal(image, original)


def test_prepared_image_exists_before_treatment():
    image = _load_image("b01.jpg")
    result = run_smart_document_pipeline(image)

    assert result["prepared_image"] is not None
    assert result["prepared_image"].size > 0
    assert result["prepared_analysis"] is not None


def test_output_image_is_valid():
    image = _load_image("b01.jpg")
    result = run_smart_document_pipeline(image)

    assert result["image"] is not None
    assert isinstance(result["image"], np.ndarray)
    assert result["image"].size > 0


def test_invalid_input_raises_value_error():
    with pytest.raises(ValueError):
        run_smart_document_pipeline(None)