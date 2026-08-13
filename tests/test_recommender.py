import pytest

from processing.recommender import (
    recommend_treatment
)


def make_analysis(
    diagnosis_codes=None,
    preservation_level="low"
):
    diagnosis_codes = (
        diagnosis_codes or []
    )

    return {
        "diagnoses": [
            {
                "code": code,
                "severity": "medium"
            }
            for code in diagnosis_codes
        ],
        "preservation_profile": {
            "level": preservation_level
        }
    }


def operation_ids(result):
    return {
        item["operation_id"]
        for item in result["recommendations"]
    }


def avoided_ids(result):
    return {
        item["operation_id"]
        for item in result["avoid"]
    }


def test_low_contrast_recommends_clahe():
    analysis = make_analysis(
        ["low_contrast"]
    )

    result = recommend_treatment(
        analysis
    )

    assert "clahe" in operation_ids(
        result
    )


def test_dark_image_recommends_clahe():
    analysis = make_analysis(
        ["dark"]
    )

    result = recommend_treatment(
        analysis
    )

    assert "clahe" in operation_ids(
        result
    )


def test_clahe_is_not_duplicated():
    analysis = make_analysis(
        [
            "dark",
            "low_contrast"
        ]
    )

    result = recommend_treatment(
        analysis
    )

    clahe_count = sum(
        item["operation_id"] == "clahe"
        for item in result[
            "recommendations"
        ]
    )

    assert clahe_count == 1


def test_noise_recommends_median():
    analysis = make_analysis(
        ["moderate_noise"]
    )

    result = recommend_treatment(
        analysis
    )

    assert (
        "median_denoise"
        in operation_ids(result)
    )


def test_high_preservation_avoids_median():
    analysis = make_analysis(
        ["high_noise"],
        preservation_level="high"
    )

    result = recommend_treatment(
        analysis
    )

    assert (
        "median_denoise"
        not in operation_ids(result)
    )

    assert (
        "median_denoise"
        in avoided_ids(result)
    )


def test_low_sharpness_recommends_sharpen():
    analysis = make_analysis(
        ["low_sharpness"]
    )

    result = recommend_treatment(
        analysis
    )

    assert (
        "sharpen"
        in operation_ids(result)
    )


def test_noise_prevents_sharpen():
    analysis = make_analysis(
        [
            "low_sharpness",
            "high_noise"
        ]
    )

    result = recommend_treatment(
        analysis
    )

    assert (
        "sharpen"
        not in operation_ids(result)
    )

    assert (
        "sharpen"
        in avoided_ids(result)
    )


def test_high_preservation_prevents_sharpen():
    analysis = make_analysis(
        ["low_sharpness"],
        preservation_level="high"
    )

    result = recommend_treatment(
        analysis
    )

    assert (
        "sharpen"
        not in operation_ids(result)
    )


def test_uneven_illumination_recommends_adaptive_threshold():
    analysis = make_analysis(
        ["uneven_illumination"]
    )

    result = recommend_treatment(
        analysis
    )

    assert (
        "adaptive_threshold"
        in operation_ids(result)
    )


def test_adaptive_threshold_is_binarization():
    analysis = make_analysis(
        ["uneven_illumination"]
    )

    result = recommend_treatment(
        analysis
    )

    recommendation = next(
        item
        for item in result[
            "recommendations"
        ]
        if item["operation_id"]
        == "adaptive_threshold"
    )

    assert (
        recommendation["mode"]
        == "binarization"
    )


def test_manual_only_operations_are_not_recommended():
    analysis = make_analysis(
        [
            "low_contrast",
            "moderate_noise",
            "low_sharpness"
        ]
    )

    result = recommend_treatment(
        analysis
    )

    recommended = operation_ids(
        result
    )

    assert (
        "histogram_equalization"
        not in recommended
    )

    assert (
        "global_threshold"
        not in recommended
    )

    assert (
        "morphological_opening"
        not in recommended
    )

    assert (
        "morphological_closing"
        not in recommended
    )


def test_manual_only_operations_are_in_avoid_list():
    analysis = make_analysis([])

    result = recommend_treatment(
        analysis
    )

    avoided = avoided_ids(
        result
    )

    assert (
        "histogram_equalization"
        in avoided
    )

    assert (
        "global_threshold"
        in avoided
    )

    assert (
        "morphological_opening"
        in avoided
    )

    assert (
        "morphological_closing"
        in avoided
    )


def test_normal_image_needs_no_automatic_treatment():
    analysis = make_analysis([])

    result = recommend_treatment(
        analysis
    )

    assert (
        result["recommendations"]
        == []
    )

    assert (
        result["summary"][
            "needs_treatment"
        ]
        is False
    )


def test_recommendations_are_sorted_by_priority():
    analysis = make_analysis(
        [
            "low_contrast",
            "moderate_noise",
            "uneven_illumination"
        ]
    )

    result = recommend_treatment(
        analysis
    )

    priorities = [
        item["priority"]
        for item in result[
            "recommendations"
        ]
    ]

    assert priorities == sorted(
        priorities
    )


def test_invalid_analysis_is_rejected():
    with pytest.raises(ValueError):
        recommend_treatment(None)


def test_missing_diagnoses_is_rejected():
    with pytest.raises(ValueError):
        recommend_treatment({
            "preservation_profile": {
                "level": "low"
            }
        })


def test_missing_preservation_profile_is_rejected():
    with pytest.raises(ValueError):
        recommend_treatment({
            "diagnoses": []
        })