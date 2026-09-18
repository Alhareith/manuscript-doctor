from io import BytesIO

import cv2
import numpy as np

from app import create_app
from processing.operations import get_operation
from processing.ops.dewarp import dewarp_document_with_metadata


def _text_page(width=700, height=900, lines=18):
    image = np.full((height, width), 242, dtype=np.uint8)
    ys = np.linspace(70, height - 70, lines).astype(int)
    for y in ys:
        for x in range(60, width - 80, 70):
            cv2.line(image, (x, y), (min(width - 60, x + 48), y), 55, 2, cv2.LINE_AA)
    return image


def _warp(image, amplitude=22):
    h, w = image.shape
    yy, xx = np.indices((h, w), dtype=np.float32)
    delta = amplitude * np.sin(2 * np.pi * xx / w)
    return cv2.remap(
        image,
        xx,
        yy - delta.astype(np.float32),
        cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def test_document_dewarp_is_registered_manual_only():
    operation = get_operation("document_dewarp")
    assert operation["automatic"] is False
    assert operation["category"] == "geometry"


def test_dewarp_abstains_on_flat_document():
    image = _text_page()
    result, metadata = dewarp_document_with_metadata(image)

    assert metadata["applied"] is False
    assert metadata["status"] == "already_flat"
    assert np.array_equal(result, image)


def test_dewarp_abstains_when_text_is_sparse():
    image = _text_page(lines=2)
    result, metadata = dewarp_document_with_metadata(image)

    assert metadata["applied"] is False
    assert metadata["status"] in {"insufficient_text", "unstable_tracking"}
    assert np.array_equal(result, image)


def test_dewarp_applies_only_after_70_percent_gate():
    image = _warp(_text_page())
    result, metadata = dewarp_document_with_metadata(image)

    assert metadata["applied"] is True
    assert metadata["status"] == "applied"
    assert metadata["curvature_reduction"] >= 0.70
    assert result.shape == image.shape


def test_dewarp_preview_api_returns_decision_metadata(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "UPLOAD_FOLDER": tmp_path / "uploads",
            "RESULT_FOLDER": tmp_path / "results",
        }
    )
    client = app.test_client()

    source = _warp(_text_page())
    ok, encoded = cv2.imencode(".png", source)
    assert ok

    upload = client.post(
        "/api/images",
        data={"image": (BytesIO(encoded.tobytes()), "warped.png")},
        content_type="multipart/form-data",
    )
    assert upload.status_code == 201, upload.get_json()
    image_id = upload.get_json()["data"]["image"]["image_id"]

    preview = client.post(
        f"/api/images/{image_id}/preview",
        json={"operation_id": "document_dewarp", "parameters": {}},
        headers={"X-Preview-Format": "jpeg"},
    )
    assert preview.status_code == 200, preview.get_json()
    data = preview.get_json()["data"]

    assert data["operation"]["id"] == "document_dewarp"
    assert isinstance(data["dewarping"], dict)
    assert "applied" in data["dewarping"]
    assert data["preview"]["data_url"].startswith("data:image/")
