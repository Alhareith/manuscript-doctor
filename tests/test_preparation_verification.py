from copy import deepcopy
from pathlib import Path

import cv2
import numpy as np
import pytest

from processing.preparation_pipeline import prepare_document
from processing.preparation_verification import verify_preparation


INPUT_DIR = Path("evaluation/input")


def _load_image(name):
    path = INPUT_DIR / name
    assert path.is_file(), f"Missing test image: {path}"

    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    assert image is not None, f"Could not decode: {path}"

    return image


def test_accepts_verified_clear_document():
    result = prepare_document(_load_image("b01.jpg"))
    verification = verify_preparation(result)

    assert verification["status"] == "accept"
    assert verification["verified"] is True
    assert abs(verification["residual_skew"]["angle"]) <= 0.75


def test_accepts_verified_second_document():
    result = prepare_document(_load_image("b02.jpg"))
    verification = verify_preparation(result)

    assert verification["status"] == "accept"
    assert verification["verified"] is True
    assert abs(verification["residual_skew"]["angle"]) <= 0.75


def test_accepts_high_confidence_deskew_only_document():
    result = prepare_document(_load_image("check/c05.jpg"))
    verification = verify_preparation(result)

    assert result["prepared"] is True
    assert result["deskew"]["applied"] is True
    assert result["deskew"]["crop_applied"] is False
    assert verification["status"] == "accept"
    assert verification["verified"] is True
    assert any("deskew-only accepted" in item["reason"] for item in verification["checks"])





def test_rejects_unprepared_result():
    image = np.full((600, 800, 3), 220, dtype=np.uint8)
    result = prepare_document(image)
    verification = verify_preparation(result)

    assert result["prepared"] is False
    assert verification["status"] == "reject"
    assert verification["verified"] is False


def test_rejects_invalid_boundary_metadata():
    result = prepare_document(_load_image("b01.jpg"))
    broken = deepcopy(result)

    broken["boundary"]["corners"] = broken["boundary"]["corners"][:3]

    verification = verify_preparation(broken)

    assert verification["status"] == "reject"
    assert verification["verified"] is False

    boundary_check = next(item for item in verification["checks"] if item["check"] == "boundary")
    assert boundary_check["passed"] is False


def test_rejects_invalid_perspective_metadata():
    result = prepare_document(_load_image("b01.jpg"))
    broken = deepcopy(result)

    broken["perspective"]["width"] = 10

    verification = verify_preparation(broken)

    assert verification["status"] == "reject"
    assert verification["verified"] is False

    perspective_check = next(item for item in verification["checks"] if item["check"] == "perspective")
    assert perspective_check["passed"] is False


def test_rejects_unsafe_applied_crop_metadata():
    result = prepare_document(_load_image("b01.jpg"))
    broken = deepcopy(result)

    broken["deskew"]["crop_applied"] = True
    broken["deskew"]["safe_crop"] = {
        "x": 10,
        "y": 10,
        "width": 100,
        "height": 100,
        "area": 10000,
        "retention_ratio": 0.80,
    }

    verification = verify_preparation(broken)

    assert verification["status"] == "reject"
    assert verification["verified"] is False

    crop_check = next(item for item in verification["checks"] if item["check"] == "post_deskew_crop")
    assert crop_check["passed"] is False


def test_does_not_modify_prepared_image():
    result = prepare_document(_load_image("b01.jpg"))
    original = result["image"].copy()

    verify_preparation(result)

    assert np.array_equal(result["image"], original)


def test_invalid_result_raises_value_error():
    with pytest.raises(ValueError):
        verify_preparation(None)