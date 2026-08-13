# → تنظيم Smart Pipeline
import cv2
import numpy as np

from processing.operations import apply_operation
from processing.preservation import verify_preservation
from processing.recommender import recommend_treatment


AUTO_ENHANCEMENT_OPERATIONS = {
    "clahe",
    "sharpen"
}

DEFERRED_AUTOMATIC_OPERATIONS = {
    "median_denoise": (
        "Automatic median denoising is deferred because "
        "the current noise indicator is not reliable enough "
        "for automatic treatment decisions."
    )
}

BINARIZATION_OPERATIONS = {
    "adaptive_threshold"
}


def _validate_image(image):
    if image is None or not isinstance(image, np.ndarray):
        raise ValueError(
            "Image must be a valid NumPy array."
        )

    if image.size == 0:
        raise ValueError(
            "Image cannot be empty."
        )

    if image.dtype != np.uint8:
        raise ValueError(
            "Only 8-bit images are supported."
        )

    if image.ndim == 2:
        return

    if image.ndim != 3:
        raise ValueError(
            "Unsupported image shape."
        )

    if image.shape[2] not in {1, 3, 4}:
        raise ValueError(
            "Unsupported number of image channels."
        )


def _spatial_shape(image):
    return image.shape[:2]


def _preservation_level(analysis):
    profile = analysis.get(
        "preservation_profile",
        {}
    )

    level = profile.get(
        "level",
        "moderate"
    )

    if level not in {
        "low",
        "moderate",
        "high"
    }:
        return "moderate"

    return level


def _candidate_decision(
    preservation,
    preservation_level
):
    status = preservation[
        "assessment"
    ]["status"]

    if status == "high_risk":
        return {
            "accepted": False,
            "status": "rejected_high_risk",
            "message": (
                "تم رفض النتيجة تلقائيًا بسبب "
                "مؤشرات Preservation مرتفعة الخطورة."
            )
        }

    if (
        status == "caution"
        and preservation_level == "high"
    ):
        return {
            "accepted": False,
            "status": "rejected_sensitive_document",
            "message": (
                "تم رفض النتيجة تلقائيًا لأن "
                "الصورة عالية الحساسية وظهرت "
                "مؤشرات Preservation تستدعي الحذر."
            )
        }

    if status == "caution":
        return {
            "accepted": True,
            "status": "accepted_with_caution",
            "message": (
                "تم قبول الخطوة، مع وجود مؤشرات "
                "تستدعي المراجعة."
            )
        }

    return {
        "accepted": True,
        "status": "accepted",
        "message": (
            "لم تظهر مؤشرات Preservation الحالية "
            "خطورة مرتفعة تمنع قبول الخطوة."
        )
    }


def _verify_candidate(
    original,
    candidate,
    preservation_level
):
    if (
        _spatial_shape(candidate)
        != _spatial_shape(original)
    ):
        return {
            "accepted": False,
            "decision": {
                "accepted": False,
                "status": "rejected_dimension_change",
                "message": (
                    "تم رفض النتيجة لأن العملية "
                    "غيرت أبعاد الصورة."
                )
            },
            "preservation": None
        }

    try:
        preservation = verify_preservation(
            original,
            candidate
        )
    except Exception:
        return {
            "accepted": False,
            "decision": {
                "accepted": False,
                "status": "verification_failed",
                "message": (
                    "تعذر التحقق من Preservation، "
                    "ولذلك لم تعتمد النتيجة تلقائيًا."
                )
            },
            "preservation": None
        }

    decision = _candidate_decision(
        preservation,
        preservation_level
    )

    return {
        "accepted": decision["accepted"],
        "decision": decision,
        "preservation": preservation
    }


def _build_step(
    recommendation,
    execution_status,
    preservation=None,
    decision=None,
    note=None
):
    return {
        "operation_id": recommendation[
            "operation_id"
        ],
        "parameters": recommendation.get(
            "parameters",
            {}
        ),
        "reason": recommendation.get(
            "reason"
        ),
        "risk": recommendation.get(
            "risk"
        ),
        "mode": recommendation.get(
            "mode"
        ),
        "execution_status": execution_status,
        "preservation": preservation,
        "decision": decision,
        "note": note
    }


def _run_enhancement_steps(
    original,
    recommendations,
    preservation_level
):
    working = original.copy()
    steps = []

    accepted_count = 0
    caution_count = 0
    rejected_count = 0
    deferred_count = 0

    enhancement_recommendations = [
        item
        for item in recommendations
        if item.get("mode") == "enhancement"
    ]

    for recommendation in enhancement_recommendations:
        operation_id = recommendation[
            "operation_id"
        ]

        if (
            operation_id
            in DEFERRED_AUTOMATIC_OPERATIONS
        ):
            deferred_count += 1

            steps.append(
                _build_step(
                    recommendation,
                    execution_status="deferred",
                    note=(
                        DEFERRED_AUTOMATIC_OPERATIONS[
                            operation_id
                        ]
                    )
                )
            )

            continue

        if (
            operation_id
            not in AUTO_ENHANCEMENT_OPERATIONS
        ):
            deferred_count += 1

            steps.append(
                _build_step(
                    recommendation,
                    execution_status=(
                        "not_auto_eligible"
                    ),
                    note=(
                        "The operation is not eligible "
                        "for automatic enhancement."
                    )
                )
            )

            continue

        candidate = apply_operation(
            operation_id,
            working,
            recommendation.get(
                "parameters",
                {}
            )
        )

        verification = _verify_candidate(
            original,
            candidate,
            preservation_level
        )

        if verification["accepted"]:
            working = candidate

            accepted_count += 1

            if (
                verification["decision"][
                    "status"
                ]
                == "accepted_with_caution"
            ):
                caution_count += 1

            steps.append(
                _build_step(
                    recommendation,
                    execution_status="accepted",
                    preservation=verification[
                        "preservation"
                    ],
                    decision=verification[
                        "decision"
                    ]
                )
            )

        else:
            rejected_count += 1

            steps.append(
                _build_step(
                    recommendation,
                    execution_status="rejected",
                    preservation=verification[
                        "preservation"
                    ],
                    decision=verification[
                        "decision"
                    ]
                )
            )

    return {
        "image": working,
        "steps": steps,
        "accepted_count": accepted_count,
        "caution_count": caution_count,
        "rejected_count": rejected_count,
        "deferred_count": deferred_count
    }


def _run_binarization_candidates(
    original,
    recommendations
):
    candidates = []

    binarization_recommendations = [
        item
        for item in recommendations
        if (
            item.get("mode")
            == "binarization"
            and item.get("operation_id")
            in BINARIZATION_OPERATIONS
        )
    ]

    for recommendation in (
        binarization_recommendations
    ):
        operation_id = recommendation[
            "operation_id"
        ]

        candidate = apply_operation(
            operation_id,
            original,
            recommendation.get(
                "parameters",
                {}
            )
        )

        try:
            preservation = (
                verify_preservation(
                    original,
                    candidate
                )
            )

        except Exception:
            preservation = None

        candidates.append({
            "operation_id": operation_id,
            "parameters": recommendation.get(
                "parameters",
                {}
            ),
            "reason": recommendation.get(
                "reason"
            ),
            "risk": recommendation.get(
                "risk"
            ),
            "image": candidate,
            "preservation": preservation,
            "decision": {
                "status": "review_required",
                "message": (
                    "هذه نتيجة Binarization مستقلة. "
                    "لا يتم اعتمادها تلقائيًا كبديل "
                    "للصورة المحسنة لأن تفسير "
                    "Preservation لنتائج Binary "
                    "ما يزال محدودًا."
                )
            }
        })

    return candidates


def _final_decision(
    recommendation_result,
    enhancement_result,
    binarization_candidates
):
    recommendations = recommendation_result[
        "recommendations"
    ]

    if not recommendations:
        return {
            "status": "no_treatment",
            "message": (
                "لم تظهر حاجة واضحة إلى معالجة "
                "تلقائية، لذلك بقيت الصورة كما هي."
            )
        }

    if enhancement_result[
        "accepted_count"
    ] > 0:
        if enhancement_result[
            "caution_count"
        ] > 0:
            return {
                "status": (
                    "accepted_with_caution"
                ),
                "message": (
                    "تم اعتماد نتيجة Enhancement "
                    "مع وجود مؤشرات تستدعي المراجعة."
                )
            }

        return {
            "status": "accepted",
            "message": (
                "تم اعتماد نتيجة Enhancement "
                "ولم تظهر مؤشرات عالية الخطورة "
                "في الخطوات المقبولة."
            )
        }

    if enhancement_result[
        "rejected_count"
    ] > 0:
        return {
            "status": "unchanged_due_to_risk",
            "message": (
                "لم تعتمد المعالجة التلقائية لأن "
                "المرشحات المنفذة تجاوزت سياسة "
                "Preservation الحالية."
            )
        }

    if (
        enhancement_result[
            "deferred_count"
        ] > 0
        or binarization_candidates
    ):
        return {
            "status": "review_required",
            "message": (
                "توجد توصيات تحتاج معالجة يدوية "
                "أو مراجعة منفصلة قبل اعتمادها."
            )
        }

    return {
        "status": "no_treatment",
        "message": (
            "لم يتم تحديد معالجة تلقائية مناسبة."
        )
    }


def run_smart_pipeline(
    image,
    analysis
):
    _validate_image(image)

    original = image.copy()

    recommendation_result = (
        recommend_treatment(
            analysis
        )
    )

    preservation_level = (
        _preservation_level(
            analysis
        )
    )

    enhancement_result = (
        _run_enhancement_steps(
            original,
            recommendation_result[
                "recommendations"
            ],
            preservation_level
        )
    )

    binarization_candidates = (
        _run_binarization_candidates(
            original,
            recommendation_result[
                "recommendations"
            ]
        )
    )

    final_image = enhancement_result[
        "image"
    ]

    final_verification_available = True

    try:
        final_preservation = (
            verify_preservation(
                original,
                final_image
        )
    )
    except Exception:
        final_preservation = None
        final_verification_available = False

    decision = _final_decision(
        recommendation_result,
        enhancement_result,
        binarization_candidates
    )   

    if (not final_verification_available and decision["status"] in { "accepted","accepted_with_caution"}):
        decision = {
            "status": "review_required",
            "message": (
                "تم تنفيذ المعالجة، لكن تعذر إجراء "
                "Final Preservation Verification، "
                "لذلك لا يمكن اعتماد النتيجة تلقائيًا."
            )
        }

    return {
        "image": final_image,
        "decision": decision,
        "steps": enhancement_result[
            "steps"
        ],
        "preservation": final_preservation,
        "binarization_candidates": (
            binarization_candidates
        ),
        "recommendation": (
            recommendation_result
        ),
        "policy": {
            "type": "rule_based",
            "preservation_aware": True,
            "automatic_enhancement_operations": (
                sorted(
                    AUTO_ENHANCEMENT_OPERATIONS
                )
            ),
            "deferred_automatic_operations": (
                sorted(
                    DEFERRED_AUTOMATIC_OPERATIONS
                )
            )
        }
    }
