CLAHE_PARAMS = {
    "clip_limit": 1.5,
    "tile_grid_size": 8
}

MEDIAN_PARAMS = {
    "kernel_size": 3
}

SHARPEN_PARAMS = {
    "amount": 0.25,
    "kernel_size": 3
}

ADAPTIVE_THRESHOLD_PARAMS = {
    "block_size": 35,
    "c": 11
}


def _validate_analysis(analysis):
    if not isinstance(analysis, dict):
        raise ValueError(
            "Analysis must be a dictionary."
        )

    if "diagnoses" not in analysis:
        raise ValueError(
            "Analysis must contain diagnoses."
        )

    if "preservation_profile" not in analysis:
        raise ValueError(
            "Analysis must contain preservation_profile."
        )

    if not isinstance(
        analysis["diagnoses"],
        list
    ):
        raise ValueError(
            "diagnoses must be a list."
        )

    if not isinstance(
        analysis["preservation_profile"],
        dict
    ):
        raise ValueError(
            "preservation_profile must be a dictionary."
        )


def _diagnosis_codes(analysis):
    return {
        diagnosis["code"]
        for diagnosis in analysis["diagnoses"]
        if isinstance(diagnosis, dict)
        and "code" in diagnosis
    }


def _add_recommendation(
    recommendations,
    operation_id,
    priority,
    reason,
    parameters,
    mode,
    risk
):
    if any(
        item["operation_id"] == operation_id
        for item in recommendations
    ):
        return

    recommendations.append({
        "operation_id": operation_id,
        "priority": priority,
        "reason": reason,
        "parameters": parameters.copy(),
        "mode": mode,
        "risk": risk
    })


def _add_avoid(
    avoided,
    operation_id,
    reason,
    risk
):
    if any(
        item["operation_id"] == operation_id
        for item in avoided
    ):
        return

    avoided.append({
        "operation_id": operation_id,
        "reason": reason,
        "risk": risk
    })


def _recommend_contrast(
    codes,
    recommendations
):
    if {
        "low_contrast",
        "very_low_contrast"
    } & codes:
        _add_recommendation(
            recommendations,
            operation_id="clahe",
            priority=1,
            reason=(
                "تشير القياسات إلى انخفاض التباين، "
                "وCLAHE هو الخيار المحافظ المفضل "
                "لتحسين التباين المحلي."
            ),
            parameters=CLAHE_PARAMS,
            mode="enhancement",
            risk="medium"
        )


def _recommend_darkness(
    codes,
    recommendations
):
    if {
        "dark",
        "very_dark"
    } & codes:
        _add_recommendation(
            recommendations,
            operation_id="clahe",
            priority=1,
            reason=(
                "تشير القياسات إلى انخفاض الإضاءة، "
                "ويمكن استخدام CLAHE بصورة محافظة "
                "لتحسين وضوح البنية المحلية."
            ),
            parameters=CLAHE_PARAMS,
            mode="enhancement",
            risk="medium"
        )


def _recommend_noise(
    codes,
    preservation_level,
    recommendations,
    avoided
):
    has_noise = bool(
        {
            "moderate_noise",
            "high_noise"
        } & codes
    )

    if not has_noise:
        return

    if preservation_level == "high":
        _add_avoid(
            avoided,
            operation_id="median_denoise",
            reason=(
                "تم اكتشاف ضوضاء، لكن الصورة تحمل "
                "حساسية مرتفعة للمحافظة على التفاصيل. "
                "Median قد يزيل بنية دقيقة مع الضوضاء."
            ),
            risk="medium-high"
        )
        return

    _add_recommendation(
        recommendations,
        operation_id="median_denoise",
        priority=2,
        reason=(
            "تشير القياسات إلى وجود ضوضاء، "
            "وتم اعتماد Median kernel=3 كخيار "
            "أكثر تحفظًا من kernel الأكبر."
        ),
        parameters=MEDIAN_PARAMS,
        mode="enhancement",
        risk="medium-high"
    )


def _recommend_sharpness(
    codes,
    preservation_level,
    recommendations,
    avoided
):
    has_low_sharpness = bool(
        {
            "low_sharpness",
            "very_low_sharpness"
        } & codes
    )

    has_noise = bool(
        {
            "moderate_noise",
            "high_noise"
        } & codes
    )

    if not has_low_sharpness:
        return

    if has_noise:
        _add_avoid(
            avoided,
            operation_id="sharpen",
            reason=(
                "الصورة منخفضة الحدة لكنها تحتوي "
                "أيضًا على ضوضاء، وقد يؤدي Sharpen "
                "إلى تضخيم الضوضاء."
            ),
            risk="medium"
        )
        return

    if preservation_level == "high":
        _add_avoid(
            avoided,
            operation_id="sharpen",
            reason=(
                "الحساسية البنيوية مرتفعة، لذلك "
                "لا يوصى بالتوضيح التلقائي قبل "
                "التحقق المحافظ من التفاصيل."
            ),
            risk="medium"
        )
        return

    _add_recommendation(
        recommendations,
        operation_id="sharpen",
        priority=3,
        reason=(
            "تشير القياسات إلى انخفاض الحدة، "
            "ويستخدم Sharpen بإعداد محافظ."
        ),
        parameters=SHARPEN_PARAMS,
        mode="enhancement",
        risk="medium"
    )


def _recommend_illumination(
    codes,
    recommendations
):
    if not (
        {
            "uneven_illumination",
            "strong_uneven_illumination"
        } & codes
    ):
        return

    _add_recommendation(
        recommendations,
        operation_id="adaptive_threshold",
        priority=4,
        reason=(
            "توجد إضاءة غير متجانسة، "
            "ولذلك يعتبر Adaptive Threshold "
            "خيارًا مناسبًا لمسار فصل النص "
            "عن الخلفية."
        ),
        parameters=ADAPTIVE_THRESHOLD_PARAMS,
        mode="binarization",
        risk="medium-high"
    )


def _build_default_avoid_list(
    avoided
):
    defaults = [
        (
            "histogram_equalization",
            (
                "لم يعتمد Histogram Equalization "
                "للاستخدام التلقائي بسبب قوته "
                "واحتمال تضخيم الخلفية والضوضاء."
            ),
            "high"
        ),
        (
            "global_threshold",
            (
                "القيمة الثابتة للThreshold لم تعمم "
                "جيدًا عبر مجموعة التقييم."
            ),
            "high"
        ),
        (
            "morphological_opening",
            (
                "Opening قد يزيل تفاصيل بنيوية صغيرة "
                "ولذلك بقي للاستخدام اليدوي."
            ),
            "high"
        ),
        (
            "morphological_closing",
            (
                "Closing قد يدمج تفاصيل متجاورة "
                "ولذلك بقي للاستخدام اليدوي."
            ),
            "high"
        )
    ]

    for operation_id, reason, risk in defaults:
        _add_avoid(
            avoided,
            operation_id,
            reason,
            risk
        )


def _build_summary(
    recommendations,
    avoided
):
    if not recommendations:
        return {
            "needs_treatment": False,
            "message": (
                "لم تظهر التشخيصات الحالية حاجة "
                "واضحة إلى معالجة تلقائية."
            )
        }

    return {
        "needs_treatment": True,
        "message": (
            f"تم تحديد {len(recommendations)} "
            "توصية معالجة مبدئية قابلة للتفسير."
        )
    }


def recommend_treatment(analysis):
    _validate_analysis(analysis)

    codes = _diagnosis_codes(
        analysis
    )

    preservation_level = (
        analysis[
            "preservation_profile"
        ].get(
            "level",
            "moderate"
        )
    )

    recommendations = []
    avoided = []

    _recommend_contrast(
        codes,
        recommendations
    )

    _recommend_darkness(
        codes,
        recommendations
    )

    _recommend_noise(
        codes,
        preservation_level,
        recommendations,
        avoided
    )

    _recommend_sharpness(
        codes,
        preservation_level,
        recommendations,
        avoided
    )

    _recommend_illumination(
        codes,
        recommendations
    )

    _build_default_avoid_list(
        avoided
    )

    recommendations.sort(
        key=lambda item: item["priority"]
    )

    return {
        "recommendations": recommendations,
        "avoid": avoided,
        "summary": _build_summary(
            recommendations,
            avoided
        ),
        "basis": {
            "diagnoses": sorted(codes),
            "preservation_level": preservation_level,
            "policy": "rule_based"
        }
    }