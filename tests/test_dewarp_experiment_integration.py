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


def _irregular_form_page(width=1000, height=760):
    image = np.full((height, width), 245, dtype=np.uint8)
    rows = [55, 95, 145, 215, 280, 300, 370, 455, 545, 640, 705]
    for y in rows:
        cv2.line(image, (45, y), (width - 45, y), 70, 2)
    for x in [45, 220, 470, 700, width - 45]:
        cv2.line(image, (x, 55), (x, 705), 90, 1)
    for y in [82, 128, 190, 260, 340, 420, 505, 600, 685]:
        cv2.putText(
            image,
            "FIELD VALUE",
            (75, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            55,
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            image,
            "DOCUMENT",
            (560, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            55,
            1,
            cv2.LINE_AA,
        )
    return image


def test_dewarp_handles_irregular_form_structure():
    source = _irregular_form_page()
    h, w = source.shape
    yy, xx = np.indices((h, w), dtype=np.float32)
    delta = (
        22.0 * np.sin(2.0 * np.pi * xx / w)
        + 6.0 * np.sin(4.0 * np.pi * xx / w)
    ).astype(np.float32)
    warped = cv2.remap(
        source,
        xx,
        yy - delta,
        cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )

    result, metadata = dewarp_document_with_metadata(warped)

    assert metadata["applied"] is True
    assert metadata["curvature_reduction"] >= 0.70
    assert metadata["method"] in {"text_lines", "edge_profile"}
    assert result.shape == warped.shape
