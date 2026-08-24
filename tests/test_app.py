from io import BytesIO

import cv2
import numpy as np
import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    upload_folder = tmp_path / "uploads"
    result_folder = tmp_path / "results"

    app = create_app({
        "TESTING": True,
        "UPLOAD_FOLDER": upload_folder,
        "RESULT_FOLDER": result_folder
    })

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def make_test_image():
    image = np.full((100, 100, 3), 255, dtype=np.uint8)
    success, encoded = cv2.imencode(".jpg", image)

    assert success

    return encoded.tobytes()


def test_home_page(client):
    response = client.get("/")

    assert response.status_code == 200


def test_upload_valid_image(client):
    image_bytes = make_test_image()

    response = client.post(
        "/api/images",
        data={
            "image": (BytesIO(image_bytes), "test.jpg")
        },
        content_type="multipart/form-data"
    )

    payload = response.get_json()

    assert response.status_code == 201
    assert payload["success"] is True
    assert payload["data"]["image"]["image_id"]


def test_upload_without_file(client):
    response = client.post("/api/images")

    payload = response.get_json()

    assert response.status_code == 400
    assert payload["error"]["code"] == "NO_FILE"


def test_reject_unsupported_extension(client):
    response = client.post(
        "/api/images",
        data={
            "image": (BytesIO(b"hello"), "test.txt")
        },
        content_type="multipart/form-data"
    )

    payload = response.get_json()

    assert response.status_code == 400
    assert payload["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_reject_fake_image(client):
    response = client.post(
        "/api/images",
        data={
            "image": (BytesIO(b"not an image"), "fake.jpg")
        },
        content_type="multipart/form-data"
    )

    payload = response.get_json()

    assert response.status_code == 400
    assert payload["error"]["code"] == "UNREADABLE_IMAGE"


def test_duplicate_names_generate_different_ids(client):
    first = client.post(
        "/api/images",
        data={
            "image": (BytesIO(make_test_image()), "same.jpg")
        },
        content_type="multipart/form-data"
    )

    second = client.post(
        "/api/images",
        data={
            "image": (BytesIO(make_test_image()), "same.jpg")
        },
        content_type="multipart/form-data"
    )

    first_id = first.get_json()["data"]["image"]["image_id"]
    second_id = second.get_json()["data"]["image"]["image_id"]

    assert first_id != second_id


def test_unknown_image(client):
    response = client.get(
        "/api/images/00000000000000000000000000000000"
    )

    payload = response.get_json()

    assert response.status_code == 404
    assert payload["error"]["code"] == "IMAGE_NOT_FOUND"


def test_file_size_limit(tmp_path):
    app = create_app({
        "TESTING": True,
        "MAX_CONTENT_LENGTH": 100,
        "UPLOAD_FOLDER": tmp_path / "uploads",
        "RESULT_FOLDER": tmp_path / "results"
    })

    client = app.test_client()

    response = client.post(
        "/api/images",
        data={
            "image": (BytesIO(b"x" * 500), "large.jpg")
        },
        content_type="multipart/form-data"
    )

    payload = response.get_json()

    assert response.status_code == 413
    assert payload["error"]["code"] == "FILE_TOO_LARGE"

def test_reject_large_dimensions(tmp_path):
    app = create_app({
        "TESTING": True,
        "MAX_IMAGE_PIXELS": 100,
        "UPLOAD_FOLDER": tmp_path / "uploads",
        "RESULT_FOLDER": tmp_path / "results"
    })

    client = app.test_client()

    image = np.full((20, 20, 3), 255, dtype=np.uint8)
    success, encoded = cv2.imencode(".jpg", image)

    assert success

    response = client.post(
        "/api/images",
        data={
            "image": (
                BytesIO(encoded.tobytes()),
                "large_dimensions.jpg"
            )
        },
        content_type="multipart/form-data"
    )

    payload = response.get_json()

    assert response.status_code == 400
    assert payload["error"]["code"] == "IMAGE_DIMENSIONS_TOO_LARGE"

def test_uploaded_bytes_are_preserved(app, client):
    original_bytes = make_test_image()

    response = client.post(
        "/api/images",
        data={
            "image": (BytesIO(original_bytes), "original.jpg")
        },
        content_type="multipart/form-data"
    )

    image_id = response.get_json()["data"]["image"]["image_id"]

    upload_folder = app.config["UPLOAD_FOLDER"]

    stored_files = list(upload_folder.glob(f"{image_id}.*"))

    assert len(stored_files) == 1
    assert stored_files[0].read_bytes() == original_bytes

def test_reject_unsupported_image_depth(client):
    image = np.full(
        (100, 100),
        1000,
        dtype=np.uint16
    )

    success, encoded = cv2.imencode(".png", image)

    assert success

    response = client.post(
        "/api/images",
        data={
            "image": (
                BytesIO(encoded.tobytes()),
                "depth16.png"
            )
        },
        content_type="multipart/form-data"
    )

    payload = response.get_json()

    assert response.status_code == 400
    assert payload["error"]["code"] == "UNSUPPORTED_IMAGE_DEPTH"

