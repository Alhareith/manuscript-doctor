import cv2
import numpy as np
import pytest

from processing.preservation import (
    verify_preservation
)


def make_document_like_image():
    image = np.full(
        (200, 300),
        230,
        dtype=np.uint8
    )

    cv2.putText(
        image,
        "TEXT",
        (40, 110),
        cv2.FONT_HERSHEY_SIMPLEX,
        2,
        30,
        3,
        cv2.LINE_AA
    )

    return image


def test_preservation_returns_expected_structure():
    image = make_document_like_image()

    result = verify_preservation(
        image,
        image.copy()
    )

    assert "metrics" in result
    assert "warnings" in result
    assert "assessment" in result


def test_identical_images_are_acceptable():
    image = make_document_like_image()

    result = verify_preservation(
        image,
        image.copy()
    )

    assert (
        result["assessment"]["status"]
        == "acceptable"
    )


def test_identical_images_have_high_edge_retention():
    image = make_document_like_image()

    result = verify_preservation(
        image,
        image.copy()
    )

    assert (
        result["metrics"]["edge_retention"]
        > 0.95
    )


def test_strong_blur_reduces_edge_retention():
    image = make_document_like_image()

    blurred = cv2.GaussianBlur(
        image,
        (31, 31),
        10
    )

    result = verify_preservation(
        image,
        blurred
    )

    assert (
        result["metrics"]["edge_retention"]
        < 1.0
    )


def test_erasing_content_triggers_warning():
    image = make_document_like_image()

    processed = image.copy()

    cv2.rectangle(
        processed,
        (30, 50),
        (270, 130),
        230,
        -1
    )

    result = verify_preservation(
        image,
        processed
    )

    assert len(
        result["warnings"]
    ) > 0


def test_added_noise_increases_edge_inflation():
    image = make_document_like_image()

    rng = np.random.default_rng(42)

    noise = rng.integers(
        0,
        256,
        image.shape,
        dtype=np.uint8
    )

    noisy = cv2.addWeighted(
        image,
        0.8,
        noise,
        0.2,
        0
    )

    result = verify_preservation(
        image,
        noisy
    )

    assert (
        result["metrics"]["edge_inflation"]
        >= 1.0
    )


def test_color_images_are_supported():
    gray = make_document_like_image()

    color = cv2.cvtColor(
        gray,
        cv2.COLOR_GRAY2BGR
    )

    result = verify_preservation(
        color,
        color.copy()
    )

    assert (
        result["assessment"]["status"]
        == "acceptable"
    )


def test_different_sizes_are_supported():
    image = make_document_like_image()

    smaller = cv2.resize(
        image,
        (150, 100)
    )

    result = verify_preservation(
        image,
        smaller
    )

    assert "metrics" in result


def test_invalid_original_is_rejected():
    image = make_document_like_image()

    with pytest.raises(ValueError):
        verify_preservation(
            None,
            image
        )


def test_invalid_processed_image_is_rejected():
    image = make_document_like_image()

    with pytest.raises(ValueError):
        verify_preservation(
            image,
            None
        )
def test_preservation_does_not_modify_images():
    original = make_document_like_image()

    processed = cv2.GaussianBlur(
        original,
        (5, 5),
        1
    )

    original_copy = original.copy()
    processed_copy = processed.copy()

    verify_preservation(
        original,
        processed
    )

    assert np.array_equal(
        original,
        original_copy
    )

    assert np.array_equal(
        processed,
        processed_copy
    )