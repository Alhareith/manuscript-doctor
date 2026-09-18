from pathlib import Path

import cv2
import numpy as np
import pytest

import processing.preparation_pipeline as preparation_pipeline
from processing.document_boundary import detect_preparation_boundary
from processing.preparation_pipeline import prepare_document
from processing.preparation_verification import verify_preparation


INPUT_DIR = Path("evaluation/input")


def _load_image(name):
    path = INPUT_DIR / name
    assert path.is_file(), f"Missing test image: {path}"

    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    assert image is not None, f"Could not decode: {path}"

    return image


def test_prepares_clear_document():
    image = _load_image("b01.jpg")
    result = prepare_document(image)

    assert result["prepared"] is True
    assert result["boundary"]["detected"] is True
    assert result["perspective"]["applied"] is True
    assert result["skew"] is not None
    assert result["deskew"] is not None
    assert result["orientation"]["requires_manual_review"] is True
    assert result["orientation"]["automatic_180_correction"] is False
    assert result["image"] is not None
    assert result["image"].size > 0


def test_prepares_second_real_document():
    image = _load_image("b02.jpg")
    result = prepare_document(image)

    assert result["prepared"] is True
    assert result["boundary"]["detected"] is True
    assert result["perspective"]["applied"] is True


def test_steps_are_in_correct_order():
    image = _load_image("b01.jpg")
    result = prepare_document(image)

    steps = [item["step"] for item in result["steps"]]

    assert steps == [
        "boundary",
        "perspective",
        "skew_detection",
        "auto_deskew",
    ]


def test_original_image_is_not_modified():
    image = _load_image("b01.jpg")
    original = image.copy()

    prepare_document(image)

    assert np.array_equal(image, original)


def test_returns_independent_result_image():
    image = _load_image("b01.jpg")
    result = prepare_document(image)

    assert result["image"] is not image


def test_deskew_only_fallback_works_without_boundary_or_crop():
    image = np.full((600, 800, 3), 255, dtype=np.uint8)
    for y in range(180, 480, 55):
        cv2.line(image, (120, y), (680, y), (0, 0, 0), 4)

    center = (image.shape[1] / 2.0, image.shape[0] / 2.0)
    matrix = cv2.getRotationMatrix2D(center, 6.0, 1.0)
    rotated = cv2.warpAffine(
        image,
        matrix,
        (image.shape[1], image.shape[0]),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )
    result = prepare_document(rotated)

    assert result["boundary"]["detected"] is False
    assert result["perspective"] is None
    assert result["prepared"] is True
    assert result["skew"] is not None
    assert result["deskew"] is not None
    assert result["deskew"]["applied"] is True
    assert result["deskew"]["crop_applied"] is False
    assert result["image"].shape[0] >= rotated.shape[0]
    assert result["image"].shape[1] >= rotated.shape[1]
    assert any(step["step"] == "auto_deskew" and step["status"] == "applied" for step in result["steps"])


def test_c04_preparation_fallback_restores_document_crop():
    image = _load_image("check/c04.jpg")
    result = prepare_document(
        image,
        boundary_detector=detect_preparation_boundary,
    )

    assert result["prepared"] is True
    assert result["boundary"]["detected"] is True
    assert result["boundary"]["automatic_crop_eligible"] is True
    assert result["perspective"]["applied"] is True
    assert result["image"].shape[0] < image.shape[0]
    assert result["image"].shape[1] < image.shape[1]


def test_c05_review_boundary_uses_safe_deskew_only():
    image = _load_image("check/c05.jpg")
    result = prepare_document(
        image,
        boundary_detector=detect_preparation_boundary,
    )
    verification = verify_preparation(result)

    assert result["prepared"] is True
    assert result["boundary"]["detected"] is True
    assert result["boundary"]["automatic_crop_eligible"] is False
    assert result["perspective"] is None
    assert result["deskew"]["applied"] is True
    assert result["deskew"]["crop_applied"] is False
    assert verification["verified"] is True
    assert abs(verification["residual_skew"]["angle"]) <= 0.75


def test_c06_review_only_geometry_defers_without_unsafe_crop():
    image = _load_image("check/c06.jpg")
    result = prepare_document(
        image,
        boundary_detector=detect_preparation_boundary,
    )
    verification = verify_preparation(result)

    assert result["prepared"] is False
    assert result["boundary"]["detected"] is True
    assert result["boundary"]["status"] == "review_required"
    assert result["boundary"]["automatic_crop_eligible"] is False
    assert result["perspective"] is None
    assert result["deskew"]["applied"] is False
    assert verification["verified"] is False


def test_c08_preparation_and_verification_are_repeatable():
    image = _load_image("check/c08.jpg")

    observations = []
    for _ in range(5):
        result = prepare_document(image, boundary_detector=detect_preparation_boundary)
        verification = verify_preparation(result)
        observations.append(
            (
                result["boundary"]["corners"],
                result["skew"],
                result["deskew"],
                verification["status"],
                verification["verified"],
                result["orientation"]["automatic_180_correction"],
            )
        )

    assert all(observation == observations[0] for observation in observations)
    assert observations[0][4] is True
    assert observations[0][5] is False


def test_invalid_input_raises_value_error():
    with pytest.raises(ValueError):
        prepare_document(None)


def test_boundary_proxy_restores_corners_to_original_coordinates():
    image = np.full((800, 1200, 3), 220, dtype=np.uint8)
    seen_shapes = []

    def detector(proxy):
        seen_shapes.append(proxy.shape)
        return {
            "detected": True,
            "corners": [[40, 30], [360, 30], [360, 230], [40, 230]],
            "confidence": 0.95,
            "area_ratio": 0.5,
            "reason": "accepted: test candidate",
        }

    result = prepare_document(
        image,
        boundary_detector=detector,
        boundary_max_dimension=400,
    )

    assert seen_shapes == [(267, 400, 3)]
    assert result["boundary"]["corners"] == [
        [120, 90],
        [1080, 90],
        [1080, 690],
        [120, 690],
    ]
    assert result["boundary"]["detection_dimensions"] == {
        "width": 400,
        "height": 267,
    }
    assert result["boundary"]["detection_scale"] == round(400 / 1200, 6)


def test_boundary_proxy_does_not_resize_small_images():
    image = np.full((300, 350, 3), 220, dtype=np.uint8)
    seen_shapes = []

    def detector(proxy):
        seen_shapes.append(proxy.shape)
        return {
            "detected": False,
            "corners": [],
            "confidence": 0.0,
            "area_ratio": 0.0,
            "reason": "rejected: test candidate",
        }

    prepare_document(
        image,
        boundary_detector=detector,
        boundary_max_dimension=400,
    )

    assert seen_shapes == [image.shape]


def test_boundary_proxy_rejects_invalid_dimension():
    image = np.zeros((100, 100, 3), dtype=np.uint8)

    with pytest.raises(ValueError, match="positive integer"):
        prepare_document(image, boundary_max_dimension=0)

    with pytest.raises(ValueError, match="positive integer"):
        prepare_document(image, boundary_max_dimension=400.0)


def test_partial_document_touching_frame_never_gets_automatic_perspective_crop(monkeypatch):
    image = np.full((700, 1000, 3), 230, dtype=np.uint8)

    def detector(proxy):
        h, w = proxy.shape[:2]
        return {
            "detected": True,
            "status": "accept_automatic",
            "corners": [
                [int(w * 0.10), int(h * 0.10)],
                [int(w * 0.90), int(h * 0.10)],
                [int(w * 0.90), h - 1],
                [int(w * 0.10), h - 1],
            ],
            "confidence": 0.95,
            "area_ratio": 0.72,
            "reason": "accepted: synthetic partial document",
        }

    monkeypatch.setattr(
        preparation_pipeline,
        "detect_skew",
        lambda _image: {
            "angle": 0.0,
            "confidence": 0.0,
            "line_count": 0,
            "dispersion": 0.0,
            "reason": "synthetic no skew",
        },
    )

    result = prepare_document(image, boundary_detector=detector)

    assert result["boundary"]["detected"] is True
    assert result["boundary"]["automatic_crop_eligible"] is False
    assert result["boundary"]["frame_clearance_ratio"] < preparation_pipeline.PREPARATION_MIN_FRAME_CLEARANCE_RATIO
    assert result["perspective"] is None
    assert result["deskew"]["crop_applied"] is False
    assert "partially clipped" in result["boundary"]["automatic_crop_reason"]


def test_review_required_boundary_is_not_applied_as_automatic_perspective(monkeypatch):
    image = np.full((700, 1000, 3), 230, dtype=np.uint8)

    def detector(proxy):
        h, w = proxy.shape[:2]
        return {
            "detected": True,
            "status": "review_required",
            "corners": [
                [int(w * 0.12), int(h * 0.12)],
                [int(w * 0.88), int(h * 0.12)],
                [int(w * 0.88), int(h * 0.88)],
                [int(w * 0.12), int(h * 0.88)],
            ],
            "confidence": 0.55,
            "area_ratio": 0.58,
            "reason": "review required: synthetic candidate",
        }

    monkeypatch.setattr(
        preparation_pipeline,
        "detect_skew",
        lambda _image: {
            "angle": 0.0,
            "confidence": 0.0,
            "line_count": 0,
            "dispersion": 0.0,
            "reason": "synthetic no skew",
        },
    )

    result = prepare_document(image, boundary_detector=detector)

    assert result["boundary"]["automatic_crop_eligible"] is False
    assert result["perspective"] is None
    assert "review_required" in result["boundary"]["automatic_crop_reason"]


def test_large_image_skew_detection_uses_bounded_proxy(monkeypatch):
    image = np.full((3000, 4000, 3), 245, dtype=np.uint8)
    seen_shapes = []

    def detector(_proxy):
        return {
            "detected": False,
            "corners": [],
            "confidence": 0.0,
            "area_ratio": 0.0,
            "reason": "rejected: synthetic no boundary",
        }

    def fake_detect_skew(proxy):
        seen_shapes.append(proxy.shape)
        return {
            "angle": 0.0,
            "confidence": 0.0,
            "line_count": 0,
            "dispersion": 0.0,
            "reason": "synthetic no skew",
        }

    monkeypatch.setattr(preparation_pipeline, "detect_skew", fake_detect_skew)
    result = prepare_document(image, boundary_detector=detector)

    assert len(seen_shapes) == 1
    assert max(seen_shapes[0][:2]) == preparation_pipeline.SKEW_DETECTION_MAX_DIMENSION
    assert result["skew"]["detection_dimensions"] == {
        "width": 1280,
        "height": 960,
    }
    assert result["skew"]["detection_scale"] == round(1280 / 4000, 6)
