
import cv2
import numpy as np
import pytest

import processing.pipeline as pipeline


def make_image():
    image = np.full(
        (160, 240),
        220,
        dtype=np.uint8
    )

    cv2.putText(
        image,
        "TEXT",
        (30, 90),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.5,
        30,
        2,
        cv2.LINE_AA
    )

    return image


def make_analysis(
    preservation_level="low"
):
    return {
        "diagnoses": [],
        "preservation_profile": {
            "level": preservation_level
        }
    }


def acceptable_preservation():
    return {
        "metrics": {},
        "warnings": [],
        "assessment": {
            "status": "acceptable",
            "message": "acceptable"
        }
    }


def caution_preservation():
    return {
        "metrics": {},
        "warnings": [
            {
                "severity": "medium"
            }
        ],
        "assessment": {
            "status": "caution",
            "message": "caution"
        }
    }


def high_risk_preservation():
    return {
        "metrics": {},
        "warnings": [
            {
                "severity": "high"
            }
        ],
        "assessment": {
            "status": "high_risk",
            "message": "high risk"
        }
    }


def test_no_treatment_returns_unchanged_copy(
    monkeypatch
):
    image = make_image()
    original = image.copy()

    monkeypatch.setattr(
        pipeline,
        "recommend_treatment",
        lambda analysis: {
            "recommendations": [],
            "excluded_from_automatic": [],
            "summary": {
                "needs_treatment": False
            }
        }
    )

    monkeypatch.setattr(
        pipeline,
        "verify_preservation",
        lambda original, processed: (
            acceptable_preservation()
        )
    )

    result = pipeline.run_smart_pipeline(
        image,
        make_analysis()
    )

    assert np.array_equal(
        result["image"],
        original
    )

    assert (
        result["decision"]["status"]
        == "no_treatment"
    )

    assert np.array_equal(
        image,
        original
    )

    assert (
        result["image"]
        is not image
    )


def test_acceptable_candidate_is_accepted(
    monkeypatch
):
    image = make_image()

    monkeypatch.setattr(
        pipeline,
        "recommend_treatment",
        lambda analysis: {
            "recommendations": [
                {
                    "operation_id": "clahe",
                    "parameters": {},
                    "reason": "contrast",
                    "risk": "medium",
                    "mode": "enhancement"
                }
            ]
        }
    )

    monkeypatch.setattr(
        pipeline,
        "apply_operation",
        lambda operation_id, image, params: (
            np.clip(
                image.astype(np.int16) - 10,
                0,
                255
            ).astype(np.uint8)
        )
    )

    monkeypatch.setattr(
        pipeline,
        "verify_preservation",
        lambda original, processed: (
            acceptable_preservation()
        )
    )

    result = pipeline.run_smart_pipeline(
        image,
        make_analysis()
    )

    assert (
        result["steps"][0][
            "execution_status"
        ]
        == "accepted"
    )

    assert (
        result["decision"]["status"]
        == "accepted"
    )


def test_high_risk_candidate_is_rejected(
    monkeypatch
):
    image = make_image()
    original = image.copy()

    monkeypatch.setattr(
        pipeline,
        "recommend_treatment",
        lambda analysis: {
            "recommendations": [
                {
                    "operation_id": "clahe",
                    "parameters": {},
                    "reason": "contrast",
                    "risk": "medium",
                    "mode": "enhancement"
                }
            ]
        }
    )

    monkeypatch.setattr(
        pipeline,
        "apply_operation",
        lambda operation_id, image, params: (
            np.zeros_like(image)
        )
    )

    monkeypatch.setattr(
        pipeline,
        "verify_preservation",
        lambda original, processed: (
            high_risk_preservation()
        )
    )

    result = pipeline.run_smart_pipeline(
        image,
        make_analysis()
    )

    assert np.array_equal(
        result["image"],
        original
    )

    assert (
        result["steps"][0][
            "execution_status"
        ]
        == "rejected"
    )

    assert (
        result["decision"]["status"]
        == "unchanged_due_to_risk"
    )


def test_caution_is_accepted_for_low_sensitivity(
    monkeypatch
):
    image = make_image()

    monkeypatch.setattr(
        pipeline,
        "recommend_treatment",
        lambda analysis: {
            "recommendations": [
                {
                    "operation_id": "clahe",
                    "parameters": {},
                    "reason": "contrast",
                    "risk": "medium",
                    "mode": "enhancement"
                }
            ]
        }
    )

    monkeypatch.setattr(
        pipeline,
        "apply_operation",
        lambda operation_id, image, params: (
            image.copy()
        )
    )

    monkeypatch.setattr(
        pipeline,
        "verify_preservation",
        lambda original, processed: (
            caution_preservation()
        )
    )

    result = pipeline.run_smart_pipeline(
        image,
        make_analysis(
            preservation_level="low"
        )
    )

    assert (
        result["decision"]["status"]
        == "accepted_with_caution"
    )


def test_caution_is_rejected_for_high_sensitivity(
    monkeypatch
):
    image = make_image()
    original = image.copy()

    monkeypatch.setattr(
        pipeline,
        "recommend_treatment",
        lambda analysis: {
            "recommendations": [
                {
                    "operation_id": "clahe",
                    "parameters": {},
                    "reason": "contrast",
                    "risk": "medium",
                    "mode": "enhancement"
                }
            ]
        }
    )

    monkeypatch.setattr(
        pipeline,
        "apply_operation",
        lambda operation_id, image, params: (
            image.copy()
        )
    )

    monkeypatch.setattr(
        pipeline,
        "verify_preservation",
        lambda original, processed: (
            caution_preservation()
        )
    )

    result = pipeline.run_smart_pipeline(
        image,
        make_analysis(
            preservation_level="high"
        )
    )

    assert np.array_equal(
        result["image"],
        original
    )

    assert (
        result["steps"][0][
            "execution_status"
        ]
        == "rejected"
    )


def test_median_is_deferred_from_automatic_pipeline(
    monkeypatch
):
    image = make_image()

    monkeypatch.setattr(
        pipeline,
        "recommend_treatment",
        lambda analysis: {
            "recommendations": [
                {
                    "operation_id": (
                        "median_denoise"
                    ),
                    "parameters": {
                        "kernel_size": 3
                    },
                    "reason": "noise",
                    "risk": "medium-high",
                    "mode": "enhancement"
                }
            ]
        }
    )

    monkeypatch.setattr(
        pipeline,
        "verify_preservation",
        lambda original, processed: (
            acceptable_preservation()
        )
    )

    result = pipeline.run_smart_pipeline(
        image,
        make_analysis()
    )

    assert (
        result["steps"][0][
            "execution_status"
        ]
        == "deferred"
    )

    assert (
        result["decision"]["status"]
        == "review_required"
    )


def test_binarization_is_separate_from_enhancement(
    monkeypatch
):
    image = make_image()

    monkeypatch.setattr(
        pipeline,
        "recommend_treatment",
        lambda analysis: {
            "recommendations": [
                {
                    "operation_id": (
                        "adaptive_threshold"
                    ),
                    "parameters": {
                        "block_size": 35,
                        "c": 11
                    },
                    "reason": (
                        "uneven illumination"
                    ),
                    "risk": "medium-high",
                    "mode": "binarization"
                }
            ]
        }
    )

    def fake_apply(
        operation_id,
        image,
        params
    ):
        return np.where(
            image > 100,
            255,
            0
        ).astype(np.uint8)

    monkeypatch.setattr(
        pipeline,
        "apply_operation",
        fake_apply
    )

    monkeypatch.setattr(
        pipeline,
        "verify_preservation",
        lambda original, processed: (
            acceptable_preservation()
        )
    )

    result = pipeline.run_smart_pipeline(
        image,
        make_analysis()
    )

    assert np.array_equal(
        result["image"],
        image
    )

    assert len(
        result[
            "binarization_candidates"
        ]
    ) == 1

    assert (
        result[
            "binarization_candidates"
        ][0]["decision"]["status"]
        == "review_required"
    )


def test_verification_failure_rejects_candidate(
    monkeypatch
):
    image = make_image()
    original = image.copy()

    monkeypatch.setattr(
        pipeline,
        "recommend_treatment",
        lambda analysis: {
            "recommendations": [
                {
                    "operation_id": "clahe",
                    "parameters": {},
                    "reason": "contrast",
                    "risk": "medium",
                    "mode": "enhancement"
                }
            ]
        }
    )

    monkeypatch.setattr(
        pipeline,
        "apply_operation",
        lambda operation_id, image, params: (
            image.copy()
        )
    )

    def fail_verification(
        original,
        processed
    ):
        raise RuntimeError(
            "verification failed"
        )

    monkeypatch.setattr(
        pipeline,
        "verify_preservation",
        fail_verification
    )

    result = pipeline.run_smart_pipeline(
        image,
        make_analysis()
    )

    assert np.array_equal(
        result["image"],
        original
    )

    assert (
        result["steps"][0][
            "decision"
        ]["status"]
        == "verification_failed"
    )


def test_invalid_image_is_rejected():
    with pytest.raises(ValueError):
        pipeline.run_smart_pipeline(
            None,
            make_analysis()
        )

def test_final_verification_failure_prevents_automatic_acceptance(
    monkeypatch
):
    image = make_image()

    monkeypatch.setattr(
        pipeline,
        "recommend_treatment",
        lambda analysis: {
            "recommendations": [
                {
                    "operation_id": "clahe",
                    "parameters": {},
                    "reason": "contrast",
                    "risk": "medium",
                    "mode": "enhancement"
                }
            ],
            "excluded_from_automatic": [],
            "summary": {
                "needs_treatment": True
            }
        }
    )

    monkeypatch.setattr(
        pipeline,
        "apply_operation",
        lambda operation_id, image, params: (
            image.copy()
        )
    )

    calls = {
        "count": 0
    }

    def verification_behavior(
        original,
        processed
    ):
        calls["count"] += 1

        if calls["count"] == 1:
            return acceptable_preservation()

        raise RuntimeError(
            "final verification failed"
        )

    monkeypatch.setattr(
        pipeline,
        "verify_preservation",
        verification_behavior
    )

    result = pipeline.run_smart_pipeline(
        image,
        make_analysis()
    )

    assert (
        result["steps"][0][
            "execution_status"
        ]
        == "accepted"
    )

    assert (
        result["preservation"]
        is None
    )

    assert (
        result["decision"]["status"]
        == "review_required"
    )
    
