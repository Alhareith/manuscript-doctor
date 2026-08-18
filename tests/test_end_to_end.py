from io import BytesIO

import cv2
import numpy as np
import pytest

from app import create_app


@pytest.fixture
def app_and_client(tmp_path):
    upload_folder = tmp_path / "uploads"
    result_folder = tmp_path / "results"

    app = create_app({
        "TESTING": True,
        "UPLOAD_FOLDER": upload_folder,
        "RESULT_FOLDER": result_folder
    })

    return (
        app,
        app.test_client(),
        upload_folder,
        result_folder
    )


def encode_png(image):
    success, encoded = cv2.imencode(
        ".png",
        image
    )

    assert success

    return encoded.tobytes()


def make_document():
    image = np.full(
        (320, 480),
        205,
        dtype=np.uint8
    )

    cv2.putText(
        image,
        "MANUSCRIPT",
        (40, 130),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.4,
        45,
        3,
        cv2.LINE_AA
    )

    cv2.line(
        image,
        (45, 175),
        (410, 175),
        70,
        2
    )

    cv2.putText(
        image,
        "TEXT DETAILS",
        (70, 230),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        65,
        2,
        cv2.LINE_AA
    )

    return image


def upload_document(
    client,
    image=None,
    filename="document.png"
):
    if image is None:
        image = make_document()

    return client.post(
        "/api/images",
        data={
            "image": (
                BytesIO(
                    encode_png(image)
                ),
                filename
            )
        },
        content_type="multipart/form-data"
    )


def get_image_id(response):
    data = response.get_json()["data"]

    image = data["image"]

    return (
        image.get("id")
        or image.get("image_id")
        or image.get("uuid")
    )


def get_result_id(response):
    return (
        response
        .get_json()["data"]
        ["result"]["id"]
    )


def test_upload_analysis_flow(
    app_and_client
):
    _, client, _, _ = app_and_client

    response = upload_document(client)

    assert response.status_code == 201

    payload = response.get_json()

    assert payload["success"] is True
    assert payload["error"] is None

    data = payload["data"]

    assert get_image_id(response)

    assert "analysis" in data
    assert "metrics" in data["analysis"]
    assert "diagnoses" in data

    assert "preservation_profile" in data
    assert "recommendations" in data
    assert "excluded_from_automatic" in data


def test_analysis_contains_real_metric_values(
    app_and_client
):
    _, client, _, _ = app_and_client

    response = upload_document(client)

    metrics = (
        response
        .get_json()["data"]
        ["analysis"]["metrics"]
    )

    required = [
        "brightness",
        "contrast",
        "sharpness",
        "noise",
        "illumination_variation",
        "edge_density"
    ]

    for key in required:
        assert key in metrics
        assert "value" in metrics[key]

        value = metrics[key]["value"]

        assert isinstance(
            value,
            (int, float)
        )

        assert np.isfinite(value)


def test_original_can_be_retrieved(
    app_and_client
):
    _, client, _, _ = app_and_client

    upload = upload_document(client)

    image_id = get_image_id(upload)

    response = client.get(
        f"/api/images/{image_id}"
    )

    assert response.status_code == 200

    image = cv2.imdecode(
        np.frombuffer(
            response.data,
            dtype=np.uint8
        ),
        cv2.IMREAD_UNCHANGED
    )

    assert image is not None


def test_manual_clahe_flow(
    app_and_client
):
    _, client, _, _ = app_and_client

    upload = upload_document(client)

    image_id = get_image_id(upload)

    response = client.post(
        f"/api/images/{image_id}/operations",
        json={
            "operation_id": "clahe",
            "parameters": {
                "clip_limit": 1.5,
                "tile_grid_size": 8
            }
        }
    )

    assert response.status_code == 201

    data = response.get_json()["data"]

    assert data["result"]["id"]
    assert data["result"]["format"] == "png"

    assert (
        data["result"]["source_image_id"]
        == image_id
    )

    assert data["operation"]["id"] == "clahe"

    assert "preservation" in data
    assert "verification" in data


def test_manual_result_can_be_retrieved(
    app_and_client
):
    _, client, _, _ = app_and_client

    upload = upload_document(client)

    image_id = get_image_id(upload)

    operation = client.post(
        f"/api/images/{image_id}/operations",
        json={
            "operation_id": "clahe",
            "parameters": {}
        }
    )

    result_id = get_result_id(
        operation
    )

    response = client.get(
        f"/api/results/{result_id}"
    )

    assert response.status_code == 200
    assert response.mimetype == "image/png"


def test_result_download(
    app_and_client
):
    _, client, _, _ = app_and_client

    upload = upload_document(client)

    image_id = get_image_id(upload)

    operation = client.post(
        f"/api/images/{image_id}/operations",
        json={
            "operation_id": "sharpen",
            "parameters": {}
        }
    )

    result_id = get_result_id(
        operation
    )

    response = client.get(
        f"/api/results/{result_id}/download"
    )

    assert response.status_code == 200

    disposition = response.headers.get(
        "Content-Disposition",
        ""
    )

    assert "attachment" in disposition


def test_smart_pipeline_flow(
    app_and_client
):
    _, client, _, _ = app_and_client

    upload = upload_document(client)

    image_id = get_image_id(upload)

    response = client.post(
        f"/api/images/{image_id}/pipeline"
    )

    assert response.status_code == 201

    payload = response.get_json()

    assert payload["success"] is True

    data = payload["data"]

    assert data["result"]["id"]

    assert data["decision"]["status"] in {
        "no_treatment",
        "accepted",
        "accepted_with_caution",
        "unchanged_due_to_risk",
        "review_required"
    }

    assert isinstance(
        data["steps"],
        list
    )

    assert "preservation" in data

    assert (
        "binarization_candidates"
        in data
    )

    assert "policy" in data


def test_pipeline_result_retrieval(
    app_and_client
):
    _, client, _, _ = app_and_client

    upload = upload_document(client)

    image_id = get_image_id(upload)

    pipeline = client.post(
        f"/api/images/{image_id}/pipeline"
    )

    result_id = get_result_id(
        pipeline
    )

    response = client.get(
        f"/api/results/{result_id}"
    )

    assert response.status_code == 200

    result_image = cv2.imdecode(
        np.frombuffer(
            response.data,
            dtype=np.uint8
        ),
        cv2.IMREAD_UNCHANGED
    )

    assert result_image is not None


def test_manual_operation_does_not_modify_original(
    app_and_client
):
    (
        _,
        client,
        upload_folder,
        _
    ) = app_and_client

    upload = upload_document(client)

    image_id = get_image_id(upload)

    stored_file = next(
        upload_folder.glob(
            f"{image_id}.*"
        )
    )

    before = stored_file.read_bytes()

    client.post(
        f"/api/images/{image_id}/operations",
        json={
            "operation_id": "sharpen",
            "parameters": {
                "amount": 0.25,
                "kernel_size": 3
            }
        }
    )

    after = stored_file.read_bytes()

    assert before == after


def test_pipeline_does_not_modify_original(
    app_and_client
):
    (
        _,
        client,
        upload_folder,
        _
    ) = app_and_client

    upload = upload_document(client)

    image_id = get_image_id(upload)

    stored_file = next(
        upload_folder.glob(
            f"{image_id}.*"
        )
    )

    before = stored_file.read_bytes()

    client.post(
        f"/api/images/{image_id}/pipeline"
    )

    after = stored_file.read_bytes()

    assert before == after


def test_results_have_unique_ids(
    app_and_client
):
    _, client, _, _ = app_and_client

    upload = upload_document(client)

    image_id = get_image_id(upload)

    first = client.post(
        f"/api/images/{image_id}/operations",
        json={
            "operation_id": "clahe",
            "parameters": {}
        }
    )

    second = client.post(
        f"/api/images/{image_id}/operations",
        json={
            "operation_id": "sharpen",
            "parameters": {}
        }
    )

    assert (
        get_result_id(first)
        != get_result_id(second)
    )


def test_corrupt_image_rejected(
    app_and_client
):
    _, client, _, _ = app_and_client

    response = client.post(
        "/api/images",
        data={
            "image": (
                BytesIO(
                    b"not an image"
                ),
                "broken.jpg"
            )
        },
        content_type="multipart/form-data"
    )

    assert response.status_code == 400

    assert (
        response.get_json()
        ["error"]["code"]
        == "UNREADABLE_IMAGE"
    )


def test_unsupported_extension_rejected(
    app_and_client
):
    _, client, _, _ = app_and_client

    response = client.post(
        "/api/images",
        data={
            "image": (
                BytesIO(b"data"),
                "document.txt"
            )
        },
        content_type="multipart/form-data"
    )

    assert response.status_code == 400

    assert (
        response.get_json()
        ["error"]["code"]
        == "UNSUPPORTED_FILE_TYPE"
    )


def test_16bit_png_rejected(
    app_and_client
):
    _, client, _, _ = app_and_client

    image = np.full(
        (100, 100),
        40000,
        dtype=np.uint16
    )

    success, encoded = cv2.imencode(
        ".png",
        image
    )

    assert success

    response = client.post(
        "/api/images",
        data={
            "image": (
                BytesIO(
                    encoded.tobytes()
                ),
                "document.png"
            )
        },
        content_type="multipart/form-data"
    )

    assert response.status_code == 400

    assert (
        response.get_json()
        ["error"]["code"]
        == "UNSUPPORTED_IMAGE_DEPTH"
    )


def test_invalid_operation_rejected(
    app_and_client
):
    _, client, _, result_folder = (
        app_and_client
    )

    upload = upload_document(client)

    image_id = get_image_id(upload)

    before = list(
        result_folder.glob("*.png")
    )

    response = client.post(
        f"/api/images/{image_id}/operations",
        json={
            "operation_id": "invalid",
            "parameters": {}
        }
    )

    after = list(
        result_folder.glob("*.png")
    )

    assert response.status_code == 400

    assert (
        response.get_json()
        ["error"]["code"]
        == "INVALID_OPERATION"
    )

    assert len(after) == len(before)


def test_invalid_parameters_rejected(
    app_and_client
):
    _, client, _, result_folder = (
        app_and_client
    )

    upload = upload_document(client)

    image_id = get_image_id(upload)

    before = list(
        result_folder.glob("*.png")
    )

    response = client.post(
        f"/api/images/{image_id}/operations",
        json={
            "operation_id": "median_denoise",
            "parameters": {
                "kernel_size": 4
            }
        }
    )

    after = list(
        result_folder.glob("*.png")
    )

    assert response.status_code == 400

    assert (
        response.get_json()
        ["error"]["code"]
        == "INVALID_OPERATION_PARAMETERS"
    )

    assert len(after) == len(before)


def test_invalid_image_id_rejected(
    app_and_client
):
    _, client, _, _ = app_and_client

    response = client.post(
        "/api/images/not-a-uuid/pipeline"
    )

    assert response.status_code == 400

    assert (
        response.get_json()
        ["error"]["code"]
        == "INVALID_IMAGE_ID"
    )


def test_unknown_image_returns_404(
    app_and_client
):
    _, client, _, _ = app_and_client

    response = client.post(
        "/api/images/"
        + ("a" * 32)
        + "/pipeline"
    )

    assert response.status_code == 404

    assert (
        response.get_json()
        ["error"]["code"]
        == "IMAGE_NOT_FOUND"
    )


def test_invalid_result_id_rejected(
    app_and_client
):
    _, client, _, _ = app_and_client

    response = client.get(
        "/api/results/not-a-uuid"
    )

    assert response.status_code == 400

    assert (
        response.get_json()
        ["error"]["code"]
        == "INVALID_RESULT_ID"
    )


def test_unknown_result_returns_404(
    app_and_client
):
    _, client, _, _ = app_and_client

    response = client.get(
        "/api/results/"
        + ("b" * 32)
    )

    assert response.status_code == 404

    assert (
        response.get_json()
        ["error"]["code"]
        == "RESULT_NOT_FOUND"
    )


def test_success_response_contract(
    app_and_client
):
    _, client, _, _ = app_and_client

    response = upload_document(client)

    payload = response.get_json()

    assert payload["success"] is True
    assert payload["message"]
    assert payload["data"] is not None
    assert payload["error"] is None


def test_error_response_contract(
    app_and_client
):
    _, client, _, _ = app_and_client

    response = client.post(
        "/api/images"
    )

    payload = response.get_json()

    assert payload["success"] is False
    assert payload["data"] is None

    assert payload["error"]["code"]

    assert "details" in payload["error"]