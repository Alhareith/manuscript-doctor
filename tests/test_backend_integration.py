from io import BytesIO

import cv2
import numpy as np
import pytest
import app as app_module


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

def test_super_resolution_manual_operation_scales_result(client):
    source = make_document_image()
    _, upload_payload = upload_image(client, image=source)
    image_id = upload_payload["data"]["image"]["image_id"]

    response = client.post(
        f"/api/images/{image_id}/operations",
        json={
            "operation_id": "super_resolution",
            "parameters": {"scale": 2, "amount": 0.35, "sigma": 1.0},
        },
    )

    payload = response.get_json()
    assert response.status_code == 201
    assert payload["success"] is True
    assert payload["data"]["operation"]["id"] == "super_resolution"
    assert payload["data"]["result"]["width"] == source.shape[1] * 2
    assert payload["data"]["result"]["height"] == source.shape[0] * 2


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
    first_result = first_payload["data"]["result"]

    assert first_result["origin"] == "manual"
    assert first_result["status"] == "approved"
    assert first_result["parent_result_id"] is None
    assert first_result["operation_id"] == "clahe"

    first_result_id = first_result["id"]

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

    second_result = second_payload["data"]["result"]
    assert second_result["origin"] == "manual"
    assert second_result["status"] == "approved"
    assert second_result["parent_result_id"] == first_result_id
    assert second_result["operation_id"] == "sharpen"



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


def test_smart_pipeline_result_has_unified_metadata(client):
    _, upload_payload = upload_image(client)
    image_id = upload_payload["data"]["image"]["image_id"]

    response = client.post(f"/api/images/{image_id}/pipeline")

    assert response.status_code == 201

    payload = response.get_json()
    result = payload["data"]["result"]

    assert result["origin"] == "smart"
    assert result["parent_result_id"] is None
    assert result["operation_id"] is None
    assert result["status"] in {
        "accepted",
        "accepted_with_caution",
        "review_required",
        "unchanged_due_to_risk",
    }


def _fake_preparation(image, boundary_detector):
    prepared = cv2.flip(image, 1)

    return {
        "prepared": True,
        "image": prepared,
        "boundary": {
            "detected": True,
            "status": "review_required",
            "method_used": "guided",
            "corners": [[1, 1], [100, 1], [100, 100], [1, 100]],
            "confidence": 0.61,
            "final_score": 0.61,
            "area_ratio": 0.70,
            "edge_support": 0.55,
            "reason": "review required: guided candidate",
        },
        "perspective": {"applied": True, "width": 320, "height": 240},
        "skew": {"angle": 1.2, "confidence": 0.82},
        "deskew": {
            "applied": True,
            "angle": 1.2,
            "confidence": 0.82,
            "crop_applied": True,
            "crop_reason": "test",
        },
        "steps": [],
        "reason": "prepared for review",
    }


def test_preparation_preview_can_be_approved(client, monkeypatch):
    monkeypatch.setattr(app_module, "prepare_document", _fake_preparation)

    _, upload_payload = upload_image(client)
    image_id = upload_payload["data"]["image"]["image_id"]

    preview_response = client.post(
        f"/api/images/{image_id}/preparation/preview"
    )

    assert preview_response.status_code == 200
    preview_payload = preview_response.get_json()
    preview_data = preview_payload["data"]
    preparation_id = preview_data["preparation_id"]

    assert preview_data["method_used"] == "guided"
    assert preview_data["status"] == "review_required"
    assert client.get(
        f"/api/preparation/{preparation_id}"
    ).status_code == 200

    approve_response = client.post(
        f"/api/images/{image_id}/preparation/{preparation_id}/approve"
    )

    assert approve_response.status_code == 201
    approve_payload = approve_response.get_json()
    result = approve_payload["data"]["result"]

    assert result["origin"] == "preparation"
    assert result["status"] == "approved"
    assert result["method_used"] == "guided"
    assert result["source_image_id"] == image_id


def test_preparation_reject_does_not_create_final_result(client, monkeypatch):
    monkeypatch.setattr(app_module, "prepare_document", _fake_preparation)

    _, upload_payload = upload_image(client)
    image_id = upload_payload["data"]["image"]["image_id"]

    preview_response = client.post(
        f"/api/images/{image_id}/preparation/preview"
    )
    preparation_id = preview_response.get_json()["data"]["preparation_id"]

    reject_response = client.post(
        f"/api/images/{image_id}/preparation/{preparation_id}/reject"
    )

    assert reject_response.status_code == 200
    assert reject_response.get_json()["data"]["status"] == "rejected"
    assert client.get(
        f"/api/preparation/{preparation_id}"
    ).status_code == 404


def test_preparation_cannot_be_approved_for_another_image(client, monkeypatch):
    monkeypatch.setattr(app_module, "prepare_document", _fake_preparation)

    _, first_upload = upload_image(client)
    _, second_upload = upload_image(client, filename="second.png")

    first_image_id = first_upload["data"]["image"]["image_id"]
    second_image_id = second_upload["data"]["image"]["image_id"]

    preview_response = client.post(
        f"/api/images/{first_image_id}/preparation/preview"
    )
    preparation_id = preview_response.get_json()["data"]["preparation_id"]

    response = client.post(
        f"/api/images/{second_image_id}/preparation/{preparation_id}/approve"
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "PREPARATION_SOURCE_MISMATCH"




def test_manual_preview_supports_optional_jpeg_transport(client):
    _, upload_payload = upload_image(client)
    image_id = upload_payload["data"]["image"]["image_id"]

    response = client.post(
        f"/api/images/{image_id}/preview",
        json={
            "operation_id": "clahe",
            "parameters": {"clip_limit": 1.5, "tile_grid_size": 8},
        },
        headers={"X-Preview-Format": "jpeg"},
    )

    payload = response.get_json()
    assert response.status_code == 200
    preview = payload["data"]["preview"]
    assert preview["format"] == "jpeg"
    assert preview["data_url"].startswith("data:image/jpeg;base64,")
    assert len(preview["data_url"]) < 600_000
