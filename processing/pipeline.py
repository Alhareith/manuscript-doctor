# → Smart Pipeline (Phase C: Diagnose → Treat → Preserve → Verify)
#
# المعمارية:
#   Input → Recommend → [اختيار مرشح واحد → Apply → Re-analyze →
#   Benefit Gate → Preservation Gate → Accept OR Rollback] → Stop
#
# القواعد الصارمة:
#   * لا Filter Chains: خطوة واحدة مقبولة فقط لكل جلسة (MAX_ACCEPTED_STEPS).
#   * accepted_image و candidate_image منفصلان دائمًا؛
#     الرفض يعني تجاهل المرشح والبقاء على accepted_image (Rollback).
#   * بوابة المنفعة: قبول Preservation لا يكفي؛ يجب أن يتحسن المقياس
#     المستهدف للعملية نفسها (الضوضاء تنخفض، التباين يرتفع، ...).
#   * CAUTION بعد القبول = إيقاف فوري مع تحذير ظاهر.
#   * لا تكرار لنفس العملية أبدًا، وحد أقصى للمحاولات يفرض مراجعة يدوية.
#   * إعادة التحليل مبررة فقط بقياس المنفعة لكل مرشح.
#   * Binarization مسار مستقل من الأصل ولا يعتمد تلقائيًا أبدًا.

import numpy as np

from processing.analyzer import analyze_image
from processing.operations import apply_operation
from processing.preservation import verify_preservation
from processing.recommender import recommend_treatment


# العمليات المؤهلة للتنفيذ التلقائي (المصدر: سياسة Phase B المُثبتة).
# median_denoise مؤهل فقط عبر توصية impulse_noise المؤكدة من recommender،
# وتظل بوابتا المنفعة وPreservation حاجزَي أمان إضافيين.

AUTO_ELIGIBLE_OPERATIONS = {
    "clahe",
    "gamma_correct",
    "illumination_normalize",
    "median_denoise",
    "sharpen"
}

# عمليات تُعرض للمستخدم لكنها لا تدخل المسار التلقائي أبدًا.

MANUAL_ONLY_OPERATIONS = {
    "histogram_equalization",
    "global_threshold",
    "otsu_threshold",
    "adaptive_threshold",
    "bilateral_denoise",
    "non_local_means_denoise",
    "background_suppress",
    "weak_structure_suppress",
    "super_resolution",
    "faded_text_enhance",
    "morphological_opening",
    "morphological_closing",
    "morphological_top_hat",
    "morphological_black_hat",
    "deskew"
}

BINARIZATION_OPERATIONS = {
    "adaptive_threshold"
}

# حدود الحلقة (Loop Protection)

MAX_ACCEPTED_STEPS = 1
MAX_ATTEMPTS_PER_RUN = 4

# عتبات بوابة المنفعة (Benefit Gate)

BRIGHTNESS_LOW_BOUND = 85.0
BRIGHTNESS_HIGH_BOUND = 200.0
BRIGHTNESS_MIN_GAIN = 1.0

CONTRAST_MIN_GAIN = 1.0
SHARPNESS_MIN_GAIN_RATIO = 0.02
NOISE_MIN_DROP = 0.5
ILLUMINATION_MIN_DROP = 0.01


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


def _metric_value(analysis, key):
    item = analysis.get(
        "metrics",
        {}
    ).get(key)

    if isinstance(item, dict):
        item = item.get("value", 0.0)

    try:
        return float(item)

    except (TypeError, ValueError):
        return 0.0


def _noise_value(analysis):
    item = analysis.get(
        "metrics",
        {}
    ).get("noise", {})

    if isinstance(item, dict):
        item = item.get("value", 0.0)

    try:
        return float(item)

    except (TypeError, ValueError):
        return 0.0


def _brightness_band_distance(analysis):
    brightness = _metric_value(
        analysis,
        "brightness"
    )

    if brightness < BRIGHTNESS_LOW_BOUND:
        return BRIGHTNESS_LOW_BOUND - brightness

    if brightness > BRIGHTNESS_HIGH_BOUND:
        return brightness - BRIGHTNESS_HIGH_BOUND

    return 0.0


def _benefit_result(
    metric,
    before,
    after,
    required,
    passed
):
    return {
        "metric": metric,
        "before": round(float(before), 4),
        "after": round(float(after), 4),
        "required_change": round(float(required), 4),
        "passed": bool(passed)
    }


def _measure_benefit(
    operation_id,
    before_analysis,
    after_analysis
):
    """قياس المنفعة الفعلية للعملية على مقياسها المستهدف.

    المقارنة دائمًا ضد حالة accepted الحالية (وليست الأصل)
    لأن المنفعة سؤال تجريبي تدريجي.
    """

    if operation_id == "gamma_correct":
        before = _brightness_band_distance(
            before_analysis
        )

        after = _brightness_band_distance(
            after_analysis
        )

        gain = before - after

        return _benefit_result(
            "brightness_band_distance",
            before,
            after,
            BRIGHTNESS_MIN_GAIN,
            gain >= BRIGHTNESS_MIN_GAIN
        )

    if operation_id == "clahe":
        before = _metric_value(
            before_analysis,
            "contrast"
        )

        after = _metric_value(
            after_analysis,
            "contrast"
        )

        gain = after - before

        return _benefit_result(
            "contrast",
            before,
            after,
            CONTRAST_MIN_GAIN,
            gain >= CONTRAST_MIN_GAIN
        )

    if operation_id == "sharpen":
        before = _metric_value(
            before_analysis,
            "sharpness"
        )

        after = _metric_value(
            after_analysis,
            "sharpness"
        )

        required = before * SHARPNESS_MIN_GAIN_RATIO

        gain = after - before

        return _benefit_result(
            "sharpness",
            before,
            after,
            required,
            gain >= required
        )

    if operation_id == "median_denoise":
        before = _noise_value(
            before_analysis
        )

        after = _noise_value(
            after_analysis
        )

        drop = before - after

        return _benefit_result(
            "noise_mean_residual",
            before,
            after,
            NOISE_MIN_DROP,
            drop >= NOISE_MIN_DROP
        )

    if operation_id == "illumination_normalize":
        before = _metric_value(
            before_analysis,
            "illumination_variation"
        )

        after = _metric_value(
            after_analysis,
            "illumination_variation"
        )

        drop = before - after

        return _benefit_result(
            "illumination_variation",
            before,
            after,
            ILLUMINATION_MIN_DROP,
            drop >= ILLUMINATION_MIN_DROP
        )

    # عملية غير معروفة في خريطة المنفعة: نرفض دائمًا (fail-closed).

    return {
        "metric": "unknown",
        "before": 0.0,
        "after": 0.0,
        "required_change": 0.0,
        "passed": False
    }


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
    note=None,
    benefit=None
):
    return {
        "operation_id": recommendation.get(
            "operation_id"
        ),
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
        "note": note,
        "benefit": benefit
    }


def _run_enhancement_attempt(
    original,
    accepted_image,
    accepted_analysis,
    recommendation,
    preservation_level
):
    """تنفيذ محاولة واحدة: Apply → Re-analyze → Benefit → Preservation."""

    operation_id = recommendation[
        "operation_id"
    ]

    try:
        candidate = apply_operation(
            operation_id,
            accepted_image,
            recommendation.get(
                "parameters",
                {}
            )
        )

    except Exception:
        return {
            "outcome": "rejected",
            "step": _build_step(
                recommendation,
                execution_status="rejected",
                decision={
                    "accepted": False,
                    "status": "execution_failed",
                    "message": (
                        "فشل تنفيذ العملية، "
                        "ولذلك استمرت الصورة كما هي."
                    )
                }
            ),
            "candidate": None,
            "candidate_analysis": None
        }

    if (
        _spatial_shape(candidate)
        != _spatial_shape(original)
    ):
        return {
            "outcome": "rejected",
            "step": _build_step(
                recommendation,
                execution_status="rejected",
                decision={
                    "accepted": False,
                    "status": "rejected_dimension_change",
                    "message": (
                        "تم رفض النتيجة لأن العملية "
                        "غيرت أبعاد الصورة."
                    )
                }
            ),
            "candidate": None,
            "candidate_analysis": None
        }

    try:
        candidate_analysis = analyze_image(
            candidate
        )

    except Exception:
        return {
            "outcome": "rejected",
            "step": _build_step(
                recommendation,
                execution_status="rejected",
                decision={
                    "accepted": False,
                    "status": "verification_failed",
                    "message": (
                        "تعذر إعادة تحليل المرشح لقياس "
                        "المنفعة، ولذلك لم يعتمد تلقائيًا."
                    )
                }
            ),
            "candidate": None,
            "candidate_analysis": None
        }

    benefit = _measure_benefit(
        operation_id,
        accepted_analysis,
        candidate_analysis
    )

    if not benefit["passed"]:
        return {
            "outcome": "rejected",
            "step": _build_step(
                recommendation,
                execution_status="rejected",
                decision={
                    "accepted": False,
                    "status": "rejected_no_benefit",
                    "message": (
                        "لم يتحسن المقياس المستهدف "
                        f"({benefit['metric']}) بالقدر "
                        "المطلوب، فتم التراجع عن الخطوة."
                    )
                },
                benefit=benefit
            ),
            "candidate": None,
            "candidate_analysis": None
        }

    verification = _verify_candidate(
        original,
        candidate,
        preservation_level
    )

    if verification["accepted"]:
        return {
            "outcome": "accepted",
            "step": _build_step(
                recommendation,
                execution_status="accepted",
                preservation=verification[
                    "preservation"
                ],
                decision=verification[
                    "decision"
                ],
                benefit=benefit
            ),
            "candidate": candidate,
            "candidate_analysis": candidate_analysis
        }

    return {
        "outcome": "rejected",
        "step": _build_step(
            recommendation,
            execution_status="rejected",
            preservation=verification[
                "preservation"
            ],
            decision=verification[
                "decision"
            ],
            benefit=benefit
        ),
        "candidate": None,
        "candidate_analysis": None
    }


def _run_enhancement_loop(
    original,
    analysis,
    recommendations,
    preservation_level
):
    accepted_image = original.copy()
    accepted_analysis = analysis

    steps = []

    attempted = set()

    attempts = 0
    accepted_count = 0
    caution_count = 0
    rejected_count = 0

    step_limit_hit = False
    stopped_after_caution = False
    stopped_after_accept = False

    deferred_ids = set()

    for recommendation in recommendations:
        mode = recommendation.get("mode")

        if mode != "enhancement":
            continue

        operation_id = recommendation.get(
            "operation_id"
        )

        if accepted_count >= MAX_ACCEPTED_STEPS:
            stopped_after_accept = True

            deferred_ids.add(operation_id)

            continue

        if operation_id in attempted:
            continue

        if (
            operation_id
            not in AUTO_ELIGIBLE_OPERATIONS
        ):
            attempted.add(operation_id)
            deferred_ids.add(operation_id)

            steps.append(
                _build_step(
                    recommendation,
                    execution_status="deferred",
                    note=(
                        "العملية غير مؤهلة للتنفيذ "
                        "التلقائي الآمن وفق السياسة الحالية."
                    )
                )
            )

            continue

        if attempts >= MAX_ATTEMPTS_PER_RUN:
            step_limit_hit = True

            deferred_ids.add(operation_id)

            continue

        attempted.add(operation_id)
        attempts += 1

        attempt = _run_enhancement_attempt(
            original,
            accepted_image,
            accepted_analysis,
            recommendation,
            preservation_level
        )

        steps.append(attempt["step"])

        if attempt["outcome"] == "accepted":
            accepted_image = attempt["candidate"]
            accepted_analysis = (
                attempt["candidate_analysis"]
            )

            accepted_count += 1

            if (
                attempt["step"]["decision"][
                    "status"
                ]
                == "accepted_with_caution"
            ):
                caution_count += 1
                stopped_after_caution = True

        else:
            rejected_count += 1

    deferred_count = 0

    for recommendation in recommendations:
        mode = recommendation.get("mode")

        if mode == "enhancement":
            continue

        operation_id = recommendation.get(
            "operation_id"
        )

        if operation_id in attempted:
            continue

        attempted.add(operation_id)
        deferred_count += 1

        steps.append(
            _build_step(
                recommendation,
                execution_status="deferred",
                note=(
                    "التصحيح الهندسي والمسارات غير "
                    "التحسينية تبقى للتشغيل اليدوي."
                )
            )
        )

    if stopped_after_accept or stopped_after_caution:
        for recommendation in recommendations:
            if (
                recommendation.get("mode")
                != "enhancement"
            ):
                continue

            operation_id = recommendation.get(
                "operation_id"
            )

            if operation_id in attempted:
                continue

            if (
                operation_id
                not in AUTO_ELIGIBLE_OPERATIONS
            ):
                continue

            attempted.add(operation_id)
            deferred_count += 1

            steps.append(
                _build_step(
                    recommendation,
                    execution_status="deferred",
                    note=(
                        "توقفت الجلسة بعد قبول خطوة "
                        "واحدة وفق سياسة عدم تسلسل "
                        "الفلاتر (No Filter Chains)."
                    )
                )
            )

    return {
        "image": accepted_image,
        "steps": steps,
        "accepted_count": accepted_count,
        "caution_count": caution_count,
        "rejected_count": rejected_count,
        "deferred_count": deferred_count,
        "step_limit_hit": step_limit_hit,
        "stopped_after_caution": (
            stopped_after_caution
        )
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
            message = (
                "تم اعتماد خطوة معالجة واحدة مع "
                "مؤشرات تستدعي المراجعة، وتوقفت "
                "الجلسة تلقائيًا عندها."
            )

            if enhancement_result[
                "stopped_after_caution"
            ]:
                message += (
                    " لا تُنفذ خطوات تلقائية "
                    "إضافية من هذه النتيجة."
                )

            return {
                "status": (
                    "accepted_with_caution"
                ),
                "message": message
            }

        return {
            "status": "accepted",
            "message": (
                "تم اعتماد خطوة معالجة واحدة "
                "محققة للمنفعة وسليمة أمام "
                "Preservation، ثم توقفت الجلسة."
            )
        }

    if enhancement_result[
        "step_limit_hit"
    ]:
        return {
            "status": "review_required",
            "reason_code": (
                "manual_review_required"
            ),
            "message": (
                "بلغت المحاولات التلقائية الحد "
                "الأقصى دون قبول آمن؛ مطلوبة "
                "مراجعة يدوية قبل أي معالجة أخرى."
            )
        }

    if enhancement_result[
        "rejected_count"
    ] > 0:
        return {
            "status": "unchanged_due_to_risk",
            "message": (
                "لم تعتمد المعالجة التلقائية لأن "
                "المرشحين المجربين تجاوزوا سياسة "
                "المنفعة أو Preservation."
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
        _run_enhancement_loop(
            original,
            analysis,
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

    if (
        not final_verification_available
        and decision["status"] in {
            "accepted",
            "accepted_with_caution"
        }
    ):
        decision = {
            "status": "review_required",
            "message": (
                "تم تنفيذ المعالجة، لكن تعذر إجراء "
                "Final Preservation Verification، "
                "ولذلك لا يمكن اعتماد النتيجة تلقائيًا."
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
            "philosophy": (
                "diagnose_treat_preserve_verify"
            ),
            "single_accepted_step_per_run": (
                MAX_ACCEPTED_STEPS == 1
            ),
            "max_attempts_per_run": (
                MAX_ATTEMPTS_PER_RUN
            ),
            "benefit_gate": True,
            "automatic_enhancement_operations": (
                sorted(
                    AUTO_ELIGIBLE_OPERATIONS
                )
            ),
            "manual_only_operations": (
                sorted(
                    MANUAL_ONLY_OPERATIONS
                )
            )
        }
    }
