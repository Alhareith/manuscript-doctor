import cv2
import numpy as np
import pytest

from processing.recommender import (
    build_treatment_strategy,
    recommend_treatment,
    SHARPEN_PARAMS,
)
from processing.operations import apply_operation


IMPULSE_NOISE_METRICS = {
    "noise": {"value": 3.2, "impulse_ratio": 0.02}
}

GAUSSIAN_NOISE_METRICS = {
    "noise": {"value": 16.0, "impulse_ratio": 0.0008}
}


def make_analysis(
    diagnoses=None,
    preservation_level="moderate",
    metrics=None,
    noise=None
):
    diagnoses = diagnoses or []

    formatted_diagnoses = []

    for diag in diagnoses:
        if isinstance(diag, str):
            formatted_diagnoses.append(
                {"code": diag, "severity": "medium"}
            )

        elif isinstance(diag, dict):
            formatted_diagnoses.append(diag)

    merged_metrics = dict(metrics or {})

    if noise is not None:
        merged_metrics["noise"] = noise

    return {
        "diagnoses": formatted_diagnoses,
        "preservation_profile": {"level": preservation_level},
        "metrics": merged_metrics,
    }


def operation_ids(result):
    return {
        item["operation_id"] for item in result["recommendations"]
    }


def avoided_ids(result):
    return {
        item["operation_id"]
        for item in result["excluded_from_automatic"]
    }


def find_recommendation(result, operation_id):
    return next(
        item
        for item in result["recommendations"]
        if item["operation_id"] == operation_id
    )


# --- Strategy: base ordering rules ----------------------------------


def test_normal_document_requires_no_treatment():
    strategy = build_treatment_strategy(make_analysis())
    assert strategy["requires_treatment"] is False
    assert strategy["candidate_plan"] == []


def test_dark_document_starts_with_gamma():
    strategy = build_treatment_strategy(make_analysis(["dark"]))
    assert strategy["candidate_plan"][0]["operation_id"] == "gamma_correct"
    assert strategy["candidate_plan"][0]["requires_reanalysis"] is True


def test_uneven_illumination_precedes_clahe():
    strategy = build_treatment_strategy(
        make_analysis(["uneven_illumination", "low_contrast"])
    )
    assert (
        strategy["candidate_plan"][0]["operation_id"]
        == "illumination_normalize"
    )
    operations = [item["operation_id"] for item in strategy["candidate_plan"]]
    assert "clahe" in operations
    assert operations.index("illumination_normalize") < operations.index("clahe")
    assert "clahe" not in strategy["blocked_operations"]


def test_noise_blocks_sharpening():
    strategy = build_treatment_strategy(
        make_analysis(
            ["moderate_noise", "low_sharpness"],
            noise=GAUSSIAN_NOISE_METRICS["noise"],
        )
    )
    assert "sharpen" in strategy["blocked_operations"]
    assert not any(
        item.get("operation_id") == "sharpen"
        for item in strategy["candidate_plan"]
    )


def test_high_sensitivity_blocks_automatic_denoising():
    strategy = build_treatment_strategy(
        make_analysis(
            ["high_noise"],
            preservation_level="high",
            noise=GAUSSIAN_NOISE_METRICS["noise"],
        )
    )
    assert "median_denoise" in strategy["blocked_operations"]
    assert "bilateral_denoise" in strategy["blocked_operations"]
    assert "non_local_means_denoise" in strategy["blocked_operations"]


def test_uneven_illumination_has_priority_over_darkness():
    strategy = build_treatment_strategy(
        make_analysis(["dark", "uneven_illumination"])
    )
    operations = [
        item.get("operation_id")
        for item in strategy["candidate_plan"]
    ]
    assert operations[0] == "illumination_normalize"
    assert "gamma_correct" not in operations


def test_bright_document_uses_darkening_gamma_candidate():
    strategy = build_treatment_strategy(make_analysis(["bright"]))
    candidate = strategy["candidate_plan"][0]
    assert candidate["operation_id"] == "gamma_correct"
    assert candidate["parameters"]["gamma"] > 1.0


def test_low_contrast_uses_clahe_when_not_blocked():
    strategy = build_treatment_strategy(make_analysis(["low_contrast"]))
    assert strategy["candidate_plan"][0]["operation_id"] == "clahe"


def test_unconfirmed_metrics_do_not_create_automatic_treatment():
    # Skew below confidence threshold is unconfirmed.
    analysis = make_analysis(
        metrics={
            "weak_to_strong_ratio": {"value": 5.0},
            "thin_structure_ratio": {"value": 0.9},
            "skew_angle": {"value": 8.0},
            "skew_confidence": {"value": 0.2},
        }
    )
    strategy = build_treatment_strategy(analysis)
    assert strategy["requires_treatment"] is False
    assert strategy["candidate_plan"] == []


# --- Strategy: noise-type differentiation ----------------------------


def test_impulse_noise_gets_median_candidate():
    strategy = build_treatment_strategy(
        make_analysis(
            ["moderate_noise"],
            noise=IMPULSE_NOISE_METRICS["noise"],
        )
    )
    candidates = [
        item for item in strategy["candidate_plan"]
        if item["operation_id"] == "median_denoise"
    ]
    assert len(candidates) == 1
    assert candidates[0]["parameters"] == {"kernel_size": 3}


def test_gaussian_noise_requires_manual_review():
    strategy = build_treatment_strategy(
        make_analysis(
            ["moderate_noise"],
            noise=GAUSSIAN_NOISE_METRICS["noise"],
        )
    )
    manual_steps = [
        item for item in strategy["candidate_plan"]
        if item["mode"] == "manual_review"
    ]
    assert len(manual_steps) == 1
    assert manual_steps[0]["operation_id"] is None


def test_gaussian_noise_conflict_is_reported():
    strategy = build_treatment_strategy(
        make_analysis(
            ["moderate_noise"],
            noise=GAUSSIAN_NOISE_METRICS["noise"],
        )
    )
    conflict_codes = {
        conflict["code"] for conflict in strategy["conflicts"]
    }
    assert "GAUSSIAN_NOISE_MANUAL_REVIEW" in conflict_codes


# --- Strategy: skew handling -----------------------------------------


def make_skew_analysis(angle, confidence):
    return make_analysis(
        metrics={
            "skew_angle": {"value": angle},
            "skew_confidence": {"value": confidence},
        }
    )


def test_confident_skew_gets_alignment_candidate():
    strategy = build_treatment_strategy(
        make_skew_analysis(angle=-3.2, confidence=0.9)
    )
    alignment = [
        item for item in strategy["candidate_plan"]
        if item["operation_id"] == "deskew"
    ]
    assert len(alignment) == 1
    assert alignment[0]["mode"] == "alignment"
    assert alignment[0]["parameters"]["angle"] == -3.2


def test_low_confidence_skew_is_ignored():
    strategy = build_treatment_strategy(
        make_skew_analysis(angle=-3.2, confidence=0.2)
    )
    assert strategy["requires_treatment"] is False
    assert strategy["candidate_plan"] == []


def test_small_skew_angle_is_ignored():
    strategy = build_treatment_strategy(
        make_skew_analysis(angle=0.3, confidence=0.9)
    )
    assert strategy["requires_treatment"] is False
    assert strategy["candidate_plan"] == []


# --- Recommendations: core paths --------------------------------------


def test_low_contrast_recommends_clahe():
    result = recommend_treatment(make_analysis(["low_contrast"]))
    assert "clahe" in operation_ids(result)


def test_dark_image_recommends_gamma_correction():
    result = recommend_treatment(make_analysis(["dark"]))
    assert "gamma_correct" in operation_ids(result)


def test_dark_and_low_contrast_recommend_gamma_then_clahe():
    result = recommend_treatment(
        make_analysis(["dark", "low_contrast"])
    )
    gamma = find_recommendation(result, "gamma_correct")
    clahe_rec = find_recommendation(result, "clahe")
    assert gamma["priority"] < clahe_rec["priority"]


def test_clahe_is_not_duplicated():
    result = recommend_treatment(
        make_analysis(["dark", "low_contrast"])
    )
    clahe_count = sum(
        item["operation_id"] == "clahe"
        for item in result["recommendations"]
    )
    assert clahe_count == 1


def test_impulse_noise_recommends_median():
    result = recommend_treatment(
        make_analysis(
            ["moderate_noise"],
            noise=IMPULSE_NOISE_METRICS["noise"],
        )
    )
    assert "median_denoise" in operation_ids(result)


def test_gaussian_noise_does_not_recommend_median():
    result = recommend_treatment(
        make_analysis(
            ["moderate_noise"],
            noise=GAUSSIAN_NOISE_METRICS["noise"],
        )
    )
    assert "median_denoise" not in operation_ids(result)
    assert "bilateral_denoise" in avoided_ids(result)
    assert "non_local_means_denoise" in avoided_ids(result)


def test_high_preservation_avoids_median():
    result = recommend_treatment(
        make_analysis(
            ["high_noise"],
            preservation_level="high",
            noise=IMPULSE_NOISE_METRICS["noise"],
        )
    )
    assert "median_denoise" not in operation_ids(result)
    assert "median_denoise" in avoided_ids(result)


def test_low_sharpness_recommends_sharpen():
    result = recommend_treatment(make_analysis(["low_sharpness"]))
    assert "sharpen" in operation_ids(result)


def test_sharpen_parameters_use_sigma_not_kernel_size():
    result = recommend_treatment(make_analysis(["low_sharpness"]))
    sharpen = find_recommendation(result, "sharpen")
    assert "sigma" in sharpen["parameters"]
    assert "kernel_size" not in sharpen["parameters"]


def test_noise_prevents_sharpen():
    result = recommend_treatment(
        make_analysis(
            ["low_sharpness", "high_noise"],
            noise=GAUSSIAN_NOISE_METRICS["noise"],
        )
    )
    assert "sharpen" not in operation_ids(result)
    assert "sharpen" in avoided_ids(result)


def test_high_preservation_prevents_sharpen():
    result = recommend_treatment(
        make_analysis(
            ["low_sharpness"], preservation_level="high"
        )
    )
    assert "sharpen" not in operation_ids(result)


def test_uneven_illumination_recommends_normalization_and_binarization():
    result = recommend_treatment(
        make_analysis(["uneven_illumination"])
    )
    normalization = find_recommendation(
        result, "illumination_normalize"
    )
    assert normalization["mode"] == "enhancement"
    assert normalization["priority"] == 10

    binarization = find_recommendation(
        result, "adaptive_threshold"
    )
    assert binarization["mode"] == "binarization"


def test_confident_skew_recommends_deskew():
    result = recommend_treatment(
        make_skew_analysis(angle=2.4, confidence=0.8)
    )
    deskew = find_recommendation(result, "deskew")
    assert deskew["mode"] == "alignment"
    assert deskew["parameters"] == {"angle": 2.4}


def test_manual_only_operations_are_not_recommended():
    result = recommend_treatment(
        make_analysis(["low_contrast", "moderate_noise", "low_sharpness"])
    )
    recommended = operation_ids(result)
    assert "histogram_equalization" not in recommended
    assert "global_threshold" not in recommended
    assert "morphological_opening" not in recommended
    assert "morphological_closing" not in recommended


def test_manual_only_operations_are_in_avoid_list():
    result = recommend_treatment(make_analysis([]))
    avoided = avoided_ids(result)
    assert "histogram_equalization" in avoided
    assert "global_threshold" in avoided
    assert "morphological_opening" in avoided
    assert "morphological_closing" in avoided


def test_normal_image_needs_no_automatic_treatment():
    result = recommend_treatment(make_analysis([]))
    assert result["recommendations"] == []
    assert result["summary"]["needs_treatment"] is False


def test_recommendations_are_sorted_by_priority():
    result = recommend_treatment(
        make_analysis(
            ["low_contrast", "moderate_noise", "uneven_illumination"]
        )
    )
    priorities = [
        item["priority"] for item in result["recommendations"]
    ]
    assert priorities == sorted(priorities)


# --- Adaptive parameters ----------------------------------------------


def test_very_dark_gets_stronger_gamma():
    result = recommend_treatment(make_analysis(["very_dark"]))
    gamma = find_recommendation(result, "gamma_correct")
    assert gamma["parameters"]["gamma"] == 0.65


def test_moderate_dark_gets_conservative_gamma():
    result = recommend_treatment(make_analysis(["dark"]))
    gamma = find_recommendation(result, "gamma_correct")
    assert gamma["parameters"]["gamma"] == 0.85


def test_very_bright_gets_stronger_gamma():
    result = recommend_treatment(make_analysis(["very_bright"]))
    gamma = find_recommendation(result, "gamma_correct")
    assert gamma["parameters"]["gamma"] == 1.35


def test_moderate_bright_gets_conservative_gamma():
    result = recommend_treatment(make_analysis(["bright"]))
    gamma = find_recommendation(result, "gamma_correct")
    assert gamma["parameters"]["gamma"] == 1.15


def test_very_low_contrast_gets_stronger_clahe():
    result = recommend_treatment(
        make_analysis(["very_low_contrast"])
    )
    clahe_rec = find_recommendation(result, "clahe")
    assert clahe_rec["parameters"]["clip_limit"] == 1.2


def test_moderate_low_contrast_gets_default_clahe():
    result = recommend_treatment(make_analysis(["low_contrast"]))
    clahe_rec = find_recommendation(result, "clahe")
    assert clahe_rec["parameters"]["clip_limit"] == 1.5


def test_high_preservation_reduces_clahe_strength():
    result = recommend_treatment(
        make_analysis(
            ["very_low_contrast"], preservation_level="high"
        )
    )
    clahe_rec = find_recommendation(result, "clahe")
    assert clahe_rec["parameters"]["clip_limit"] == 1.2


def test_high_preservation_reduces_illumination_strength():
    result = recommend_treatment(
        make_analysis(
            ["uneven_illumination"], preservation_level="high"
        )
    )
    normalization = find_recommendation(
        result, "illumination_normalize"
    )
    assert normalization["parameters"]["strength"] == 0.45


def test_moderate_preservation_keeps_illumination_strength():
    result = recommend_treatment(
        make_analysis(["uneven_illumination"])
    )
    normalization = find_recommendation(
        result, "illumination_normalize"
    )
    assert normalization["parameters"]["strength"] == 0.65


# --- Parameter executability (regression: pipeline crash fix) --------


def test_sharpen_params_module_constant_matches_operation_signature():
    assert set(SHARPEN_PARAMS) == {"amount", "sigma"}


def make_small_image():
    image = np.full((120, 160, 3), 200, dtype=np.uint8)
    cv2.putText(
        image,
        "TEXT",
        (20, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        40,
        2,
        cv2.LINE_AA,
    )
    return image


@pytest.mark.parametrize(
    "diagnoses,noise,operation_id",
    [
        (["dark"], None, "gamma_correct"),
        (["bright"], None, "gamma_correct"),
        (["low_contrast"], None, "clahe"),
        (["low_sharpness"], None, "sharpen"),
        (["uneven_illumination"], None, "illumination_normalize"),
        (
            ["moderate_noise"],
            IMPULSE_NOISE_METRICS["noise"],
            "median_denoise",
        ),
    ],
)
def test_recommended_parameters_execute(
    diagnoses, noise, operation_id
):
    result = recommend_treatment(
        make_analysis(diagnoses, noise=noise)
    )

    recommendation = find_recommendation(result, operation_id)

    processed = apply_operation(
        operation_id,
        make_small_image(),
        recommendation["parameters"],
    )

    assert processed is not None
    assert processed.shape[0] > 0


# --- Validation --------------------------------------------------------


def test_invalid_analysis_is_rejected():
    with pytest.raises(ValueError):
        recommend_treatment(None)


def test_missing_diagnoses_is_rejected():
    with pytest.raises(ValueError):
        recommend_treatment(
            {"preservation_profile": {"level": "low"}}
        )


def test_missing_preservation_profile_is_rejected():
    with pytest.raises(ValueError):
        recommend_treatment({"diagnoses": []})
