from io import BytesIO

import cv2
import numpy as np
import pytest

from app import create_app
from processing.operations import apply_operation, crop


def make_image():
    image = np.zeros((120, 180, 3), dtype=np.uint8)
    image[:, :] = (20, 40, 60)
    image[10:90, 30:140] = (200, 210, 220)
    return image


def test_crop_returns_copy_with_expected_shape_and_pixels():
    image = make_image()
    result = crop(image, 30, 10, 110, 80)

    assert result.shape == (80, 110, 3)
    assert np.array_equal(result[0, 0], image[10, 30])
    result[0, 0] = 0
    assert not np.array_equal(result[0, 0], image[10, 30])


def test_crop_rejects_invalid_rectangles():
    image = make_image()
    for params in (
        (-1, 0, 10, 10),
        (0, -1, 10, 10),
        (0, 0, 0, 10),
        (0, 0, 10, 0),
        (170, 0, 20, 10),
        (0, 115, 10, 10),
        (0, 0, float("nan"), 10),
    ):
        with pytest.raises(ValueError):
            crop(image, *params)


def test_crop_is_registered_for_generic_operation_dispatch():
    result = apply_operation("crop", make_image(), {"x": 30, "y": 10, "width": 110, "height": 80})
    assert result.shape[:2] == (80, 110)


def test_crop_works_through_api_and_can_use_previous_result(tmp_path):
    app = create_app({"TESTING": True, "UPLOAD_FOLDER": tmp_path / "uploads", "RESULT_FOLDER": tmp_path / "results"})
    client = app.test_client()
    ok, encoded = cv2.imencode(".png", make_image())
    assert ok
    uploaded = client.post(
        "/api/images",
        data={"image": (BytesIO(encoded.tobytes()), "crop.png")},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 201, uploaded.get_json()
    image_id = uploaded.get_json()["data"]["image"]["image_id"]

    preview = client.post(
        f"/api/images/{image_id}/preview",
        json={"operation_id": "crop", "parameters": {"x": 30, "y": 10, "width": 110, "height": 80}},
    )
    assert preview.status_code == 200, preview.get_json()
    preview_data = preview.get_json()["data"]["preview"]
    assert preview_data["width"] <= 720
    assert preview_data["height"] <= 960

    first = client.post(
        f"/api/images/{image_id}/operations",
        json={"operation_id": "crop", "parameters": {"x": 30, "y": 10, "width": 110, "height": 80}},
    )
    assert first.status_code == 201, first.get_json()
    first_data = first.get_json()["data"]
    assert first_data["result"]["width"] == 110
    assert first_data["result"]["height"] == 80

    second = client.post(
        f"/api/images/{image_id}/operations",
        json={"operation_id": "crop", "parameters": {"x": 5, "y": 5, "width": 50, "height": 40}, "source_result_id": first_data["result"]["id"]},
    )
    assert second.status_code == 201, second.get_json()
    assert second.get_json()["data"]["source_result_id"] == first_data["result"]["id"]
    assert second.get_json()["data"]["result"]["width"] == 50
    assert second.get_json()["data"]["result"]["height"] == 40


def test_crop_api_rejects_rectangle_outside_source(tmp_path):
    app = create_app({"TESTING": True, "UPLOAD_FOLDER": tmp_path / "uploads", "RESULT_FOLDER": tmp_path / "results"})
    client = app.test_client()
    ok, encoded = cv2.imencode(".png", make_image())
    assert ok
    uploaded = client.post(
        "/api/images",
        data={"image": (BytesIO(encoded.tobytes()), "invalid-crop.png")},
        content_type="multipart/form-data",
    )
    image_id = uploaded.get_json()["data"]["image"]["image_id"]

    response = client.post(
        f"/api/images/{image_id}/operations",
        json={"operation_id": "crop", "parameters": {"x": 170, "y": 0, "width": 20, "height": 10}},
    )
    assert response.status_code in (400, 422)
    assert response.get_json()["success"] is False
