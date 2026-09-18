from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
import pytest

from app import create_app
from processing.skew_detector import detect_skew


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "evaluation" / "input"

REAL_PREPARATION_CASES = [
    "b01.jpg",
    "b02.jpg",
    "check/c04.jpg",
    "check/c05.jpg",
]

SAFE_DEFER_CASES = [
    "check/c06.jpg",
]


def make_client(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "UPLOAD_FOLDER": tmp_path / "uploads",
            "RESULT_FOLDER": tmp_path / "results",
            "PREPARATION_PREVIEW_FOLDER": tmp_path / "preparation_previews",
        }
    )
    return app.test_client()


def upload_exact(client, path):
    raw = path.read_bytes()
    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    assert image is not None

    response = client.post(
        "/api/images?defer_analysis=1",
        data={"image": (BytesIO(raw), path.name)},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201, response.get_json()

    data = response.get_json()["data"]
    image_id = data["image"]["image_id"]
    assert data["analysis_deferred"] is True
    assert data["image"]["width"] == image.shape[1]
    assert data["image"]["height"] == image.shape[0]

    stored = client.get(f"/api/images/{image_id}")
    assert stored.status_code == 200
    assert stored.data == raw

    return image_id, image


def test_instant_exam_upload_path_keeps_original_file_for_geometry():
    source = (ROOT / "static" / "js" / "parts" / "04-examination.js").read_text(
        encoding="utf-8"
    )

    assert 'body.append("image", file' in source
    assert "createProcessingUpload" not in source
    assert "jpegBlobFromBitmap" not in source
    assert "resizeWidth" not in source


def test_crop_editor_uses_real_source_limits():
    source = (ROOT / "static" / "js" / "parts" / "05-manual-parameters.js").read_text(
        encoding="utf-8"
    )

    assert 'input.max = String(Math.max(1, Math.round(max)))' in source
    assert 'const marginX = Math.max(1, Math.round(dimensions.width * 0.05))' in source
    assert 'const marginY = Math.max(1, Math.round(dimensions.height * 0.05))' in source


@pytest.mark.parametrize("relative_path", REAL_PREPARATION_CASES)
def test_real_documents_survive_exact_upload_and_preparation(
    tmp_path,
    relative_path,
):
    client = make_client(tmp_path)
    path = INPUT_DIR / relative_path
    assert path.is_file(), f"Missing regression image: {path}"

    image_id, original = upload_exact(client, path)

    preview = client.post(
        f"/api/images/{image_id}/preparation/preview",
        json={"source_result_id": None},
    )
    assert preview.status_code == 200, preview.get_json()

    preview_data = preview.get_json()["data"]
    preparation = preview_data["preparation"]
    assert preview_data["preparation_id"]
    assert preview_data["source_result_id"] is None
    assert preparation["prepared"] is True
    perspective = preparation.get("perspective") or {}
    deskew = preparation.get("deskew") or {}
    assert (
        perspective.get("applied") is True
        or deskew.get("applied") is True
    )

    approval = client.post(
        f"/api/images/{image_id}/preparation/{preview_data['preparation_id']}/approve"
    )
    assert approval.status_code == 201, approval.get_json()

    approved = approval.get_json()["data"]
    result = approved["result"]
    assert result["id"]
    assert result["operation_id"] == "document_prepare"
    assert result["parent_result_id"] is None
    assert result["width"] >= 40
    assert result["height"] >= 40

    result_response = client.get(f"/api/results/{result['id']}")
    assert result_response.status_code == 200
    decoded = cv2.imdecode(
        np.frombuffer(result_response.data, dtype=np.uint8),
        cv2.IMREAD_UNCHANGED,
    )
    assert decoded is not None and decoded.size > 0

    residual = detect_skew(decoded)
    if residual["confidence"] > 0:
        assert abs(float(residual["angle"])) <= 2.0

    # Geometric preparation must never create an implausibly huge canvas.
    assert decoded.shape[0] <= max(original.shape[0], original.shape[1]) * 2
    assert decoded.shape[1] <= max(original.shape[0], original.shape[1]) * 2


@pytest.mark.parametrize("relative_path", SAFE_DEFER_CASES)
def test_uncertain_real_document_defers_without_unsafe_automatic_crop(
    tmp_path,
    relative_path,
):
    client = make_client(tmp_path)
    path = INPUT_DIR / relative_path
    image_id, _ = upload_exact(client, path)

    preview = client.post(
        f"/api/images/{image_id}/preparation/preview",
        json={"source_result_id": None},
    )

    assert preview.status_code == 422
    payload = preview.get_json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "PREPARATION_REJECTED"

    preparation = payload["error"]["details"]["preparation"]
    assert preparation["prepared"] is False
    assert preparation["boundary"]["status"] == "review_required"
    assert preparation["boundary"]["automatic_crop_eligible"] is False
    assert preparation["perspective"] is None
    assert preparation["deskew"]["applied"] is False


def test_full_image_crop_is_not_artificially_limited(tmp_path):
    client = make_client(tmp_path)
    path = INPUT_DIR / "b01.jpg"
    image_id, original = upload_exact(client, path)
    height, width = original.shape[:2]

    response = client.post(
        f"/api/images/{image_id}/operations",
        json={
            "operation_id": "crop",
            "parameters": {
                "x": 0,
                "y": 0,
                "width": width,
                "height": height,
            },
            "source_result_id": None,
        },
    )
    assert response.status_code == 201, response.get_json()
    result = response.get_json()["data"]["result"]
    assert result["width"] == width
    assert result["height"] == height

    downloaded = client.get(f"/api/results/{result['id']}")
    decoded = cv2.imdecode(
        np.frombuffer(downloaded.data, dtype=np.uint8),
        cv2.IMREAD_UNCHANGED,
    )
    assert np.array_equal(decoded, original)


@pytest.mark.parametrize(
    "operation_id",
    ["rotate_right", "rotate_left", "flip_vertical", "flip_horizontal"],
)
def test_orientation_buttons_preserve_pixels_on_exact_uploaded_source(
    tmp_path,
    operation_id,
):
    client = make_client(tmp_path)
    path = INPUT_DIR / "b01.jpg"
    image_id, original = upload_exact(client, path)

    response = client.post(
        f"/api/images/{image_id}/operations",
        json={
            "operation_id": operation_id,
            "parameters": {},
            "source_result_id": None,
        },
    )
    assert response.status_code == 201, response.get_json()

    result = response.get_json()["data"]["result"]
    downloaded = client.get(f"/api/results/{result['id']}")
    decoded = cv2.imdecode(
        np.frombuffer(downloaded.data, dtype=np.uint8),
        cv2.IMREAD_UNCHANGED,
    )
    assert decoded is not None

    if operation_id in {"rotate_right", "rotate_left"}:
        assert decoded.shape[:2] == (original.shape[1], original.shape[0])
    else:
        assert decoded.shape == original.shape

    assert decoded.size == original.size


def test_manual_deskew_keeps_complete_content_canvas(tmp_path):
    client = make_client(tmp_path)
    path = INPUT_DIR / "b01.jpg"
    image_id, original = upload_exact(client, path)

    response = client.post(
        f"/api/images/{image_id}/operations",
        json={
            "operation_id": "deskew",
            "parameters": {"angle": 5.0},
            "source_result_id": None,
        },
    )
    assert response.status_code == 201, response.get_json()

    result = response.get_json()["data"]["result"]
    assert result["width"] >= original.shape[1]
    assert result["height"] >= original.shape[0]


def test_preparation_uses_current_manual_chain_source(tmp_path):
    client = make_client(tmp_path)
    path = INPUT_DIR / "b01.jpg"
    image_id, _ = upload_exact(client, path)

    rotated = client.post(
        f"/api/images/{image_id}/operations",
        json={
            "operation_id": "rotate_right",
            "parameters": {},
            "source_result_id": None,
        },
    )
    assert rotated.status_code == 201, rotated.get_json()
    rotated_result = rotated.get_json()["data"]["result"]

    preview = client.post(
        f"/api/images/{image_id}/preparation/preview",
        json={"source_result_id": rotated_result["id"]},
    )
    assert preview.status_code == 200, preview.get_json()
    preview_data = preview.get_json()["data"]
    assert preview_data["source_result_id"] == rotated_result["id"]

    approval = client.post(
        f"/api/images/{image_id}/preparation/{preview_data['preparation_id']}/approve"
    )
    assert approval.status_code == 201, approval.get_json()

    approved = approval.get_json()["data"]
    assert approved["source_result_id"] == rotated_result["id"]
    assert approved["result"]["parent_result_id"] == rotated_result["id"]
    assert approved["result"]["operation_id"] == "document_prepare"
