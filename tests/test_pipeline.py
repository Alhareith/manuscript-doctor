
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
    preservation_level="low",
    contrast=30.0,
    sharpness=100.0,
    brightness=120.0,
    illumination=0.05,
    noise=0.0
):
    return {
        "diagnoses": [],
        "preservation_profile": {
            "level": preservation_level
        },
        "metrics": {
            "contrast": {"value": contrast},
            "sharpness": {"value": sharpness},
            "brightness": {"value": brightness},
            "illumination_variation": {
                "value": illumination
            },
            "noise": {"value": noise}
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


def clahe_rec():
    return {
        "operation_id": "clahe",
        "parameters": {},
        "reason": "contrast",
        "risk": "medium",
        "mode": "enhancement"
    }


def sharpen_rec():
    return {
        "operation_id": "sharpen",
        "parameters": {},
        "reason": "sharpness",
        "risk": "medium",
        "mode": "enhancement"
    }


def gamma_rec():
    return {
        "operation_id": "gamma_correct",
        "parameters": {"gamma": 0.85},
        "reason": "dark",
        "risk": "low",
        "mode": "enhancement"
    }


def median_rec():
    return {
        "operation_id": "median_denoise",
        "parameters": {"kernel_size": 3},
        "reason": "noise",
        "risk": "medium-high",
        "mode": "enhancement"
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
            "recommendations": []
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

    assert (
        result["image"]
        is not image
    )


def test_acceptable_candidate_with_benefit_is_accepted(
    monkeypatch
):
    image = make_image()

    monkeypatch.setattr(
        pipeline,
        "recommend_treatment",
        lambda analysis: {
            "recommendations": [
                clahe_rec()
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
        "analyze_image",
        lambda image: make_analysis(
            contrast=45.0
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
        make_analysis(contrast=30.0)
    )

    assert (
        result["steps"][0][
            "execution_status"
        ]
        == "accepted"
    )

    assert (
        result["steps"][0]["benefit"][
            "passed"
        ]
        is True
    )

    assert (
        result["decision"]["status"]
        == "accepted"
    )


def test_candidate_without_benefit_is_rejected(
    monkeypatch
):
    image = make_image()
    original = image.copy()

    monkeypatch.setattr(
        pipeline,
        "recommend_treatment",
        lambda analysis: {
            "recommendations": [
                clahe_rec()
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
        "analyze_image",
        lambda image: make_analysis(
            contrast=30.5
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
        make_analysis(contrast=30.0)
    )

    assert np.array_equal(
        result["image"],
        original
    )

    assert (
        result["steps"][0]["decision"][
            "status"
        ]
        == "rejected_no_benefit"
    )

    assert (
        result["decision"]["status"]
        == "unchanged_due_to_risk"
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
                clahe_rec()
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
        "analyze_image",
        lambda image: make_analysis(
            contrast=60.0
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


def test_caution_is_accepted_for_low_sensitivity_then_stops(
    monkeypatch
):
    image = make_image()

    monkeypatch.setattr(
        pipeline,
        "recommend_treatment",
        lambda analysis: {
            "recommendations": [
                clahe_rec(),
                sharpen_rec()
            ]
        }
    )

    apply_calls = {
        "count": 0
    }

    def apply_behavior(
        operation_id,
        image,
        params
    ):
        apply_calls["count"] += 1

        return image.copy()

    monkeypatch.setattr(
        pipeline,
        "apply_operation",
        apply_behavior
    )

    monkeypatch.setattr(
        pipeline,
        "analyze_image",
        lambda image: make_analysis(
            contrast=50.0
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
            preservation_level="low",
            contrast=30.0
        )
    )

    assert (
        result["steps"][0][
            "execution_status"
        ]
        == "accepted"
    )

    assert (
        result["decision"]["status"]
        == "accepted_with_caution"
    )

    assert (
        apply_calls["count"] == 1
    )

    statuses = [
        step["execution_status"]
        for step in result["steps"]
    ]

    assert (
        statuses.count("accepted") == 1
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
                clahe_rec()
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
        "analyze_image",
        lambda image: make_analysis(
            contrast=50.0
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
            preservation_level="high",
            contrast=30.0
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


def test_two_accepted_steps_are_allowed_when_verified(
    monkeypatch
):
    image = make_image()

    monkeypatch.setattr(
        pipeline,
        "recommend_treatment",
        lambda analysis: {
            "recommendations": [
                clahe_rec(),
                sharpen_rec()
            ]
        }
    )

    apply_calls = {
        "count": 0
    }

    def apply_behavior(
        operation_id,
        image,
        params
    ):
        apply_calls["count"] += 1

        return image.copy()

    monkeypatch.setattr(
        pipeline,
        "apply_operation",
        apply_behavior
    )

    analysis_calls = {"count": 0}

    def analysis_behavior(image):
        analysis_calls["count"] += 1
        return make_analysis(
            contrast=50.0 + analysis_calls["count"] * 5.0,
            sharpness=150.0 + analysis_calls["count"] * 10.0
        )

    monkeypatch.setattr(
        pipeline,
        "analyze_image",
        analysis_behavior
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
        make_analysis(
            contrast=30.0,
            sharpness=100.0
        )
    )

    assert (
        apply_calls["count"] == 2
    )

    statuses = [
        step["execution_status"]
        for step in result["steps"]
    ]

    assert (
        statuses.count("accepted") == 2
    )

    assert (
        statuses.count("deferred") == 0
    )

    assert (
        result["decision"]["status"]
        == "accepted"
    )


def test_repeated_operation_is_not_retried(
    monkeypatch
):
    image = make_image()

    monkeypatch.setattr(
        pipeline,
        "recommend_treatment",
        lambda analysis: {
            "recommendations": [
                clahe_rec(),
                clahe_rec()
            ]
        }
    )

    apply_calls = {
        "count": 0
    }

    def apply_behavior(
        operation_id,
        image,
        params
    ):
        apply_calls["count"] += 1

        return image.copy()

    monkeypatch.setattr(
        pipeline,
        "apply_operation",
        apply_behavior
    )

    monkeypatch.setattr(
        pipeline,
        "analyze_image",
        lambda image: make_analysis(
            contrast=50.0
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
        make_analysis(contrast=30.0)
    )

    assert (
        apply_calls["count"] == 1
    )

    attempted_steps = [
        step
        for step in result["steps"]
        if step["execution_status"]
        == "rejected"
    ]

    assert len(attempted_steps) == 1


def test_max_attempts_triggers_manual_review(
    monkeypatch
):
    image = make_image()

    recommendations = [
        clahe_rec(),
        gamma_rec(),
        {
            "operation_id": (
                "illumination_normalize"
            ),
            "parameters": {},
            "reason": "illumination",
            "risk": "medium",
            "mode": "enhancement"
        },
        median_rec(),
        sharpen_rec()
    ]

    monkeypatch.setattr(
        pipeline,
        "recommend_treatment",
        lambda analysis: {
            "recommendations": recommendations
        }
    )

    monkeypatch.setattr(
        pipeline,
        "apply_operation",
        lambda operation_id, image, params: (
            image.copy()
        )
    )

    def analysis_behavior(image):
        return make_analysis(
            contrast=60.0,
            brightness=140.0,
            illumination=0.02,
            noise=2.0,
            sharpness=150.0
        )

    monkeypatch.setattr(
        pipeline,
        "analyze_image",
        analysis_behavior
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

    attempted_steps = [
        step
        for step in result["steps"]
        if step["execution_status"]
        == "rejected"
    ]

    assert len(attempted_steps) == (
        pipeline.MAX_ATTEMPTS_PER_RUN
    )

    assert (
        result["decision"]["status"]
        == "review_required"
    )

    assert (
        result["decision"][
            "reason_code"
        ]
        == "manual_review_required"
    )


def test_median_requires_noise_drop(
    monkeypatch
):
    image = make_image()

    monkeypatch.setattr(
        pipeline,
        "recommend_treatment",
        lambda analysis: {
            "recommendations": [
                median_rec()
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
        "analyze_image",
        lambda image: make_analysis(
            noise=2.0
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
        make_analysis(noise=15.0)
    )

    assert (
        result["steps"][0][
            "execution_status"
        ]
        == "accepted"
    )

    assert (
        result["steps"][0]["benefit"][
            "metric"
        ]
        == "noise_mean_residual"
    )


def test_median_without_noise_drop_is_rejected(
    monkeypatch
):
    image = make_image()

    monkeypatch.setattr(
        pipeline,
        "recommend_treatment",
        lambda analysis: {
            "recommendations": [
                median_rec()
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
        "analyze_image",
        lambda image: make_analysis(
            noise=14.8
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
        make_analysis(noise=15.0)
    )

    assert (
        result["steps"][0]["decision"][
            "status"
        ]
        == "rejected_no_benefit"
    )


def test_gamma_benefit_uses_brightness_band(
    monkeypatch
):
    image = make_image()

    monkeypatch.setattr(
        pipeline,
        "recommend_treatment",
        lambda analysis: {
            "recommendations": [
                gamma_rec()
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
        "analyze_image",
        lambda image: make_analysis(
            brightness=75.0
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
        make_analysis(brightness=60.0)
    )

    assert (
        result["steps"][0][
            "execution_status"
        ]
        == "accepted"
    )

    assert (
        result["steps"][0]["benefit"][
            "metric"
        ]
        == "brightness_band_distance"
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
                clahe_rec()
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
        "analyze_image",
        lambda image: make_analysis(
            contrast=50.0
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
        make_analysis(contrast=30.0)
    )

    assert np.array_equal(
        result["image"],
        original
    )

    assert (
        result["steps"][0]["decision"][
            "status"
        ]
        == "verification_failed"
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
                clahe_rec()
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
        "analyze_image",
        lambda image: make_analysis(
            contrast=50.0
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
        make_analysis(contrast=30.0)
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


def test_non_auto_operation_is_deferred(
    monkeypatch
):
    image = make_image()

    monkeypatch.setattr(
        pipeline,
        "recommend_treatment",
        lambda analysis: {
            "recommendations": [
                {
                    "operation_id": "deskew",
                    "parameters": {
                        "angle": 2.0
                    },
                    "reason": "skew",
                    "risk": "medium",
                    "mode": "alignment"
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

    assert np.array_equal(
        result["image"],
        image
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


def test_invalid_image_is_rejected():
    with pytest.raises(ValueError):
        pipeline.run_smart_pipeline(
            None,
            make_analysis()
        )
