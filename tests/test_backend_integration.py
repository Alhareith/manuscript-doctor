from io import BytesIO

import cv2
import numpy as np
import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "UPLOAD_FOLDER": (tmp_path / "uploads"),
            "RESULT_FOLDER": (tmp_path / "results"),
        }
    )

    return app.test_client()


def encode_png(image):
    success, encoded = cv2.imencode(".png", image)

    assert success

    return encoded.tobytes()


def make_document_image():
    image = np.full((240, 320), 200, dtype=np.uint8)

    cv2.putText(
        image, "DOCUMENT", (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 1.3, 25, 3, cv2.LINE_AA
    )

    return image


def upload_image(client, image=None, filename="document.png"):
    if image is None:
        image = make_document_image()

    response = client.post(
        "/api/images",
        data={"image": (BytesIO(encode_png(image)), filename)},
        content_type=("multipart/form-data"),
    )

    return (response, response.get_json())


def test_upload_returns_analysis_and_recommendations(client):
    response, payload = upload_image(client)

    assert response.status_code == 201
    assert payload["success"] is True

    data = payload["data"]

    assert "image" in data
    assert "analysis" in data
    assert "diagnoses" in data

    assert "preservation_profile" in data

    assert "recommendations" in data

    assert "excluded_from_automatic" in data


def test_manual_operation_creates_result(client):
    _, upload_payload = upload_image(client)

    image_id = upload_payload["data"]["image"]["image_id"]

    response = client.post(
        (f"/api/images/" f"{image_id}/operations"),
        json={
            "operation_id": "clahe",
            "parameters": {"clip_limit": 1.5, "tile_grid_size": 8},
        },
    )

    payload = response.get_json()

    assert response.status_code == 201
    assert payload["success"] is True

    result = payload["data"]["result"]

    assert result["format"] == "png"

    assert result["source_image_id"] == image_id

    assert payload["data"]["operation"]["id"] == "clahe"

def test_manual_preview_returns_in_memory_preview_without_final_result(client):
    _, upload_payload = upload_image(client)
    image_id = upload_payload["data"]["image"]["image_id"]

    response = client.post(
        f"/api/images/{image_id}/preview",
        json={
            "operation_id": "clahe",
            "parameters": {
                "clip_limit": 1.5,
                "tile_grid_size": 8,
            },
        },
    )

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True

    preview = payload["data"]["preview"]
    assert preview["data_url"].startswith("data:image/png;base64,")
    assert preview["width"] <= 720
    assert preview["height"] <= 960
    assert payload["data"]["verification"]["status"] == "skipped_for_preview"

    result_folder = client.application.config["RESULT_FOLDER"]
    assert list(result_folder.glob("*.png")) == []


def test_manual_operation_returns_preservation(client):
    _, upload_payload = upload_image(client)

    image_id = upload_payload["data"]["image"]["image_id"]

    response = client.post(
        (f"/api/images/" f"{image_id}/operations"),
        json={
            "operation_id": "clahe",
            "parameters": {"clip_limit": 1.5, "tile_grid_size": 8},
        },
    )

    payload = response.get_json()

    assert "preservation" in payload["data"]

    assert "verification" in payload["data"]


def test_unknown_operation_is_rejected(client):
    _, upload_payload = upload_image(client)

    image_id = upload_payload["data"]["image"]["image_id"]

    response = client.post(
        (f"/api/images/" f"{image_id}/operations"),
        json={"operation_id": ("unknown_operation"), "parameters": {}},
    )

    payload = response.get_json()

    assert response.status_code == 400

    assert payload["error"]["code"] == "INVALID_OPERATION"


def test_invalid_operation_parameters_are_rejected(client):
    _, upload_payload = upload_image(client)

    image_id = upload_payload["data"]["image"]["image_id"]

    response = client.post(
        (f"/api/images/" f"{image_id}/operations"),
        json={"operation_id": "clahe", "parameters": {"clip_limit": -1}},
    )

    payload = response.get_json()

    assert response.status_code == 400

    assert payload["error"]["code"] == ("INVALID_OPERATION_PARAMETERS")


def test_operation_requires_json_body(client):
    _, upload_payload = upload_image(client)

    image_id = upload_payload["data"]["image"]["image_id"]

    response = client.post((f"/api/images/" f"{image_id}/operations"))

    payload = response.get_json()

    assert response.status_code == 400

    assert payload["error"]["code"] == "INVALID_REQUEST_BODY"


def test_pipeline_creates_result(client):
    _, upload_payload = upload_image(client)

    image_id = upload_payload["data"]["image"]["image_id"]

    response = client.post((f"/api/images/" f"{image_id}/pipeline"))

    payload = response.get_json()

    assert response.status_code == 201
    assert payload["success"] is True

    data = payload["data"]

    assert "result" in data
    assert "decision" in data
    assert "steps" in data

    assert "preservation" in data

    assert "binarization_candidates" in data

    assert data["result"]["format"] == "png"


def test_created_result_can_be_retrieved(client):
    _, upload_payload = upload_image(client)

    image_id = upload_payload["data"]["image"]["image_id"]

    operation_response = client.post(
        (f"/api/images/" f"{image_id}/operations"),
        json={
            "operation_id": "clahe",
            "parameters": {"clip_limit": 1.5, "tile_grid_size": 8},
        },
    )

    operation_payload = operation_response.get_json()

    result_id = operation_payload["data"]["result"]["id"]

    response = client.get(f"/api/results/{result_id}")

    assert response.status_code == 200

    assert response.mimetype == "image/png"


def test_result_download_is_attachment(client):
    _, upload_payload = upload_image(client)

    image_id = upload_payload["data"]["image"]["image_id"]

    operation_response = client.post(
        (f"/api/images/" f"{image_id}/operations"),
        json={"operation_id": "clahe", "parameters": {}},
    )

    operation_payload = operation_response.get_json()

    result_id = operation_payload["data"]["result"]["id"]

    response = client.get((f"/api/results/" f"{result_id}/download"))

    assert response.status_code == 200

    disposition = response.headers.get("Content-Disposition", "")

    assert "attachment" in disposition


def test_unknown_image_returns_404(client):
    missing_id = "a" * 32

    response = client.post((f"/api/images/" f"{missing_id}/pipeline"))

    payload = response.get_json()

    assert response.status_code == 404

    assert payload["error"]["code"] == "IMAGE_NOT_FOUND"


def test_invalid_image_id_is_rejected(client):
    response = client.post("/api/images/not-a-uuid/pipeline")

    payload = response.get_json()

    assert response.status_code == 400

    assert payload["error"]["code"] == "INVALID_IMAGE_ID"


def test_unknown_result_returns_404(client):
    missing_id = "b" * 32

    response = client.get(f"/api/results/{missing_id}")

    payload = response.get_json()

    assert response.status_code == 404

    assert payload["error"]["code"] == "RESULT_NOT_FOUND"


def test_manual_operations_can_chain_from_approved_result(client):
    _, upload_payload = upload_image(client)
    image_id = upload_payload["data"]["image"]["image_id"]

    first_response = client.post(
        f"/api/images/{image_id}/operations",
        json={
            "operation_id": "clahe",
            "parameters": {
                "clip_limit": 1.5,
                "tile_grid_size": 8,
            },
        },
    )

    assert first_response.status_code == 201
    first_payload = first_response.get_json()
    first_result_id = first_payload["data"]["result"]["id"]
    assert first_payload["data"]["source_result_id"] is None

    second_response = client.post(
        f"/api/images/{image_id}/operations",
        json={
            "operation_id": "sharpen",
            "parameters": {
                "amount": 0.8,
                "sigma": 1.0,
            },
            "source_result_id": first_result_id,
        },
    )

    assert second_response.status_code == 201
    second_payload = second_response.get_json()
    assert second_payload["success"] is True
    assert second_payload["data"]["source_result_id"] == first_result_id
    assert second_payload["data"]["result"]["id"] != first_result_id


def test_manual_chain_rejects_result_from_another_image(client):
    _, first_upload = upload_image(client)
    _, second_upload = upload_image(client, filename="second.png")

    first_image_id = first_upload["data"]["image"]["image_id"]
    second_image_id = second_upload["data"]["image"]["image_id"]

    first_response = client.post(
        f"/api/images/{first_image_id}/operations",
        json={
            "operation_id": "clahe",
            "parameters": {
                "clip_limit": 1.5,
                "tile_grid_size": 8,
            },
        },
    )

    first_result_id = first_response.get_json()["data"]["result"]["id"]

    response = client.post(
        f"/api/images/{second_image_id}/operations",
        json={
            "operation_id": "sharpen",
            "parameters": {
                "amount": 0.8,
                "sigma": 1.0,
            },
            "source_result_id": first_result_id,
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "SOURCE_RESULT_MISMATCH"
