CLAHE_PARAMS = {"clip_limit": 1.5, "tile_grid_size": 8}

MEDIAN_PARAMS = {"kernel_size": 3}

SHARPEN_PARAMS = {"amount": 0.25, "kernel_size": 3}

ADAPTIVE_THRESHOLD_PARAMS = {"block_size": 35, "c": 11}

AUTO_ALLOWED = {"clahe", "gamma_correct", "illumination_normalize", "sharpen"}

AUTO_DEFERRED = {
    "median_denoise",
    "bilateral_denoise",
    "non_local_means_denoise",
    "background_suppress",
    "weak_structure_suppress",
    "morphological_opening",
    "morphological_closing",
    "morphological_top_hat",
    "morphological_black_hat",
    "deskew"
}

MANUAL_ONLY = {
    "histogram_equalization",
    "global_threshold",
    "otsu_threshold",
    "adaptive_threshold"
}

def _diagnosis_codes(analysis):
    codes = set()
    for item in analysis.get("diagnoses", []):
        if isinstance(item, str):
            codes.add(item)
        elif isinstance(item, dict):
            code = item.get("code") or item.get("id") or item.get("diagnosis")
            if code:
                codes.add(str(code))
    return codes

def _metric_value(analysis, key, default=0.0):
    item = analysis.get("metrics", {}).get(key, default)
    if isinstance(item, dict):
        item = item.get("value", default)
    try:
        return float(item)
    except (TypeError, ValueError):
        return float(default)

def _preservation_level(analysis):
    profile = analysis.get("preservation_profile", {})
    level = profile.get("level") or profile.get("sensitivity") or "moderate"
    return str(level).lower()

def _extract_condition_profile(analysis):
    codes = _diagnosis_codes(analysis)
    preservation = _preservation_level(analysis)

    dark = bool({"dark", "very_dark"} & codes)
    bright = bool({"bright", "very_bright"} & codes)
    low_contrast = bool({"low_contrast", "very_low_contrast"} & codes)
    low_sharpness = bool({"low_sharpness", "very_low_sharpness"} & codes)
    noise = bool({"moderate_noise", "high_noise"} & codes)
    uneven = bool({"uneven_illumination", "strong_uneven_illumination"} & codes)

    return {
        "dark": dark,
        "bright": bright,
        "low_contrast": low_contrast,
        "low_sharpness": low_sharpness,
        "noise": noise,
        "uneven_illumination": uneven,
        "high_preservation_sensitivity": preservation == "high",
        "moderate_preservation_sensitivity": preservation == "moderate"
    }

def _extract_unconfirmed_evidence(analysis):
    return {
        "weak_to_strong_ratio": _metric_value(analysis, "weak_to_strong_ratio"),
        "thin_structure_ratio": _metric_value(analysis, "thin_structure_ratio"),
        "small_component_ratio": _metric_value(analysis, "small_component_ratio"),
        "skew_angle": _metric_value(analysis, "skew_angle"),
        "skew_confidence": _metric_value(analysis, "skew_confidence")
    }

def _detect_conflicts(conditions):
    conflicts = []

    if conditions["noise"] and conditions["low_sharpness"]:
        conflicts.append({"code": "NOISE_SHARPNESS_CONFLICT", "severity": "high", "message": "Denoising should be evaluated before sharpening; sharpening noisy structure may amplify noise."})

    if conditions["noise"] and conditions["high_preservation_sensitivity"]:
        conflicts.append({"code": "NOISE_FINE_DETAIL_CONFLICT", "severity": "high", "message": "Automatic denoising remains disabled because fine structural details may be removed."})

    if conditions["uneven_illumination"] and conditions["low_contrast"]:
        conflicts.append({"code": "ILLUMINATION_CONTRAST_ORDER", "severity": "medium", "message": "Correct uneven illumination before deciding whether local contrast enhancement is still required."})

    if conditions["uneven_illumination"] and conditions["dark"]:
        conflicts.append({"code": "ILLUMINATION_DARKNESS_ORDER", "severity": "medium", "message": "Local illumination imbalance should be corrected before global exposure adjustment."})

    if conditions["dark"] and conditions["low_contrast"]:
        conflicts.append({"code": "DARK_LOW_CONTRAST_SEQUENCE", "severity": "medium", "message": "Exposure correction should be evaluated before applying additional contrast enhancement."})

    if conditions["bright"] and conditions["low_contrast"]:
        conflicts.append({"code": "BRIGHT_LOW_CONTRAST_SEQUENCE", "severity": "medium", "message": "Brightness correction should precede additional local contrast enhancement."})

    return conflicts

def _validate_analysis(analysis):
    if not isinstance(analysis, dict):
        raise ValueError("Analysis must be a dictionary.")

    if "diagnoses" not in analysis:
        raise ValueError("Analysis must contain diagnoses.")

    if "preservation_profile" not in analysis:
        raise ValueError("Analysis must contain preservation_profile.")

    if not isinstance(analysis["diagnoses"], list):
        raise ValueError("diagnoses must be a list.")

    if not isinstance(analysis["preservation_profile"], dict):
        raise ValueError("preservation_profile must be a dictionary.")


def _diagnosis_codes(analysis):
    return {
        diagnosis["code"]
        for diagnosis in analysis["diagnoses"]
        if isinstance(diagnosis, dict) and "code" in diagnosis
    }

def _blocked_operations(conditions):
    blocked = {}

    if conditions["noise"]:
        blocked["sharpen"] = "Sharpening is deferred while significant noise is present."

    if conditions["high_preservation_sensitivity"]:
        blocked["median_denoise"] = "Automatic median filtering is unsafe for high-sensitivity structure."
        blocked["bilateral_denoise"] = "Automatic denoising remains deferred for high-sensitivity structure."
        blocked["non_local_means_denoise"] = "Automatic denoising remains deferred for high-sensitivity structure."
        blocked["morphological_opening"] = "Opening may remove fine document structure."
        blocked["morphological_closing"] = "Closing may merge independent document structures."

    if conditions["uneven_illumination"]:
        blocked["clahe"] = "CLAHE is deferred until illumination normalization is evaluated."

    return blocked

def _build_candidate_plan(conditions, blocked):
    plan = []

    if conditions["uneven_illumination"]:
        plan.append({"priority": 10, "operation_id": "illumination_normalize", "parameters": {"kernel_size": 51, "strength": 0.65}, "mode": "candidate", "automatic_eligible": True, "requires_reanalysis": True, "reason": "Uneven illumination should be corrected before dependent tonal processing."})

    elif conditions["dark"]:
        plan.append({"priority": 20, "operation_id": "gamma_correct", "parameters": {"gamma": 0.85}, "mode": "candidate", "automatic_eligible": True, "requires_reanalysis": True, "reason": "Global darkness is present without priority illumination correction."})

    elif conditions["bright"]:
        plan.append({"priority": 20, "operation_id": "gamma_correct", "parameters": {"gamma": 1.15}, "mode": "candidate", "automatic_eligible": True, "requires_reanalysis": True, "reason": "Global brightness requires conservative tonal correction."})

    if conditions["low_contrast"] and "clahe" not in blocked:
        plan.append({"priority": 30, "operation_id": "clahe", "parameters": {"clip_limit": 1.5, "tile_grid_size": 8}, "mode": "candidate", "automatic_eligible": True, "requires_reanalysis": True, "reason": "Low contrast remains eligible for conservative CLAHE."})

    if conditions["noise"]:
        plan.append({"priority": 40, "operation_id": None, "parameters": {}, "mode": "manual_review", "automatic_eligible": False, "requires_reanalysis": False, "reason": "Noise is present, but automatic denoiser selection remains uncalibrated."})

    if conditions["low_sharpness"] and "sharpen" not in blocked:
        plan.append({"priority": 50, "operation_id": "sharpen", "parameters": {"amount": 0.25, "kernel_size": 3}, "mode": "candidate", "automatic_eligible": True, "requires_reanalysis": True, "reason": "Low sharpness is present and no active conflict blocks conservative sharpening."})

    return sorted(plan, key=lambda item: item["priority"])

def _requires_treatment(conditions):
    return any(conditions[key] for key in ["dark", "bright", "low_contrast", "low_sharpness", "noise", "uneven_illumination"])

def build_treatment_strategy(analysis):
    conditions = _extract_condition_profile(analysis)
    evidence = _extract_unconfirmed_evidence(analysis)
    conflicts = _detect_conflicts(conditions)
    blocked = _blocked_operations(conditions)
    plan = _build_candidate_plan(conditions, blocked)

    return {
        "requires_treatment": _requires_treatment(conditions),
        "conditions": conditions,
        "unconfirmed_evidence": evidence,
        "conflicts": conflicts,
        "blocked_operations": blocked,
        "candidate_plan": plan
    }


def _add_recommendation(
    recommendations, operation_id, priority, reason, parameters, mode, risk
):
    if any(item["operation_id"] == operation_id for item in recommendations):
        return

    recommendations.append(
        {
            "operation_id": operation_id,
            "priority": priority,
            "reason": reason,
            "parameters": parameters.copy(),
            "mode": mode,
            "risk": risk,
        }
    )


def _add_avoid(avoided, operation_id, reason, risk):
    if any(item["operation_id"] == operation_id for item in avoided):
        return

    avoided.append({"operation_id": operation_id, "reason": reason, "risk": risk})


def _recommend_contrast(codes, recommendations):
    if {"low_contrast", "very_low_contrast"} & codes:
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
            risk="medium",
        )


def _recommend_darkness(codes, recommendations):
    if {"dark", "very_dark"} & codes:
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
            risk="medium",
        )


def _recommend_noise(codes, preservation_level, recommendations, avoided):
    has_noise = bool({"moderate_noise", "high_noise"} & codes)

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
            risk="medium-high",
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
        risk="medium-high",
    )


def _recommend_sharpness(codes, preservation_level, recommendations, avoided):
    has_low_sharpness = bool({"low_sharpness", "very_low_sharpness"} & codes)

    has_noise = bool({"moderate_noise", "high_noise"} & codes)

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
            risk="medium",
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
            risk="medium",
        )
        return

    _add_recommendation(
        recommendations,
        operation_id="sharpen",
        priority=3,
        reason=("تشير القياسات إلى انخفاض الحدة، " "ويستخدم Sharpen بإعداد محافظ."),
        parameters=SHARPEN_PARAMS,
        mode="enhancement",
        risk="medium",
    )


def _recommend_illumination(codes, recommendations):
    if not ({"uneven_illumination", "strong_uneven_illumination"} & codes):
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
        risk="medium-high",
    )


def _build_default_avoid_list(avoided):
    defaults = [
        (
            "histogram_equalization",
            (
                "لم يعتمد Histogram Equalization "
                "للاستخدام التلقائي بسبب قوته "
                "واحتمال تضخيم الخلفية والضوضاء."
            ),
            "high",
        ),
        (
            "global_threshold",
            ("القيمة الثابتة للThreshold لم تعمم " "جيدًا عبر مجموعة التقييم."),
            "high",
        ),
        (
            "morphological_opening",
            ("Opening قد يزيل تفاصيل بنيوية صغيرة " "ولذلك بقي للاستخدام اليدوي."),
            "high",
        ),
        (
            "morphological_closing",
            ("Closing قد يدمج تفاصيل متجاورة " "ولذلك بقي للاستخدام اليدوي."),
            "high",
        ),
    ]

    for operation_id, reason, risk in defaults:
        _add_avoid(avoided, operation_id, reason, risk)


def _build_summary(recommendations, avoided):
    if not recommendations:
        return {
            "needs_treatment": False,
            "message": ("لم تظهر التشخيصات الحالية حاجة " "واضحة إلى معالجة تلقائية."),
        }

    return {
        "needs_treatment": True,
        "message": (
            f"تم تحديد {len(recommendations)} " "توصية معالجة مبدئية قابلة للتفسير."
        ),
    }


def recommend_treatment(analysis):
    _validate_analysis(analysis)

    codes = _diagnosis_codes(analysis)

    preservation_level = analysis["preservation_profile"].get("level", "moderate")

    recommendations = []
    avoided = []
    strategy = build_treatment_strategy(analysis)
    _recommend_contrast(codes, recommendations)

    _recommend_darkness(codes, recommendations)

    _recommend_noise(codes, preservation_level, recommendations, avoided)

    _recommend_sharpness(codes, preservation_level, recommendations, avoided)

    _recommend_illumination(codes, recommendations)

    _build_default_avoid_list(avoided)

    recommendations.sort(key=lambda item: item["priority"])

    return {
        "recommendations": recommendations,
        "excluded_from_automatic": avoided,
        "summary": _build_summary(recommendations, avoided),
        "basis": {
            "diagnoses": sorted(codes),
            "preservation_level": preservation_level,
            "policy": "rule_based",
        },
        "treatment_strategy": strategy,

    }
