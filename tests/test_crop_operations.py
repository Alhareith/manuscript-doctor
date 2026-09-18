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


def test_manual_crop_is_exact_on_large_source_image():
    image = np.zeros((3000, 4000, 3), dtype=np.uint8)
    image[:, :] = (25, 35, 45)
    image[600:2400, 800:3200] = (210, 220, 230)

    result = crop(image, 800, 600, 2400, 1800)

    assert result.shape == (1800, 2400, 3)
    assert np.array_equal(result[0, 0], image[600, 800])
    assert np.array_equal(result[-1, -1], image[2399, 3199])


def test_perspective_crop_rectifies_manual_four_corner_scan():
    image = np.full((300, 420, 3), 35, dtype=np.uint8)
    source = np.full((180, 260, 3), 235, dtype=np.uint8)
    cv2.rectangle(source, (18, 18), (242, 162), (25, 25, 25), 3)
    cv2.putText(source, "DOC", (75, 105), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (30, 30, 30), 3)

    src = np.float32([[0, 0], [259, 0], [259, 179], [0, 179]])
    dst = np.float32([[65, 42], [350, 65], [330, 250], [45, 230]])
    warped = cv2.warpPerspective(
        source,
        cv2.getPerspectiveTransform(src, dst),
        (420, 300),
        borderValue=(35, 35, 35),
    )

    result = apply_operation(
        "perspective_crop",
        warped,
        {
            "x1": 65, "y1": 42,
            "x2": 350, "y2": 65,
            "x3": 330, "y3": 250,
            "x4": 45, "y4": 230,
        },
    )

    assert result.shape[0] >= 180
    assert result.shape[1] >= 260
    assert float(np.mean(result)) > float(np.mean(warped))


def test_perspective_crop_rejects_crossed_corners():
    image = make_image()
    with pytest.raises(ValueError):
        apply_operation(
            "perspective_crop",
            image,
            {
                "x1": 10, "y1": 10,
                "x2": 160, "y2": 100,
                "x3": 160, "y3": 10,
                "x4": 10, "y4": 100,
            },
        )
