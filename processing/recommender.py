# → محرك التوصيات المحافظ (Adaptive Rule-Based)
#
# التصميم:
#   * مصدر واحد للحقيقة: _condition_profile يستخرج شدة كل حالة
#     (none / medium / high) من التشخيصات والمقاييس.
#   * المعاملات تتكيف مع الشدة وحساسية المحافظة بدل قيم ثابتة.
#   * الضوضاء تُصنف إلى نبضية (Median مرشح تلقائي) وغاوسية
#     (مراجعة يدوية) عبر impulse_ratio القادم من analyzer.
#   * الترتيب يتبع التسلسل المُثبت في مرحلة Operation Validation:
#     Illumination → Exposure → Contrast → Noise → Sharpen → Deskew → Binarization.
#
# عقد الاستهلاك (يجب الحفاظ عليه):
#   * pipeline.py يقرأ recommendations[] بالحقول
#     operation_id / parameters / reason / risk / mode
#     حيث mode هو "enhancement" أو "binarization".
#   * الواجهة تعرض أيضًا priority و parameters و excluded_from_automatic.

# معاملات مُثبتة على مجموعة Operation Validation (seed = 20260817)

CLAHE_PARAMS = {"clip_limit": 1.5, "tile_grid_size": 8}
CLAHE_PARAMS_STRONG = {"clip_limit": 1.2, "tile_grid_size": 8}

GAMMA_DARK_PARAMS = {"gamma": 0.85}
GAMMA_DARK_STRONG_PARAMS = {"gamma": 0.65}
GAMMA_BRIGHT_PARAMS = {"gamma": 1.15}
GAMMA_BRIGHT_STRONG_PARAMS = {"gamma": 1.35}

SHARPEN_PARAMS = {"amount": 0.25, "sigma": 1.0}

MEDIAN_PARAMS = {"kernel_size": 3}

ILLUMINATION_PARAMS = {"kernel_size": 51, "strength": 0.65}
ILLUMINATION_CONSERVATIVE_PARAMS = {"kernel_size": 51, "strength": 0.45}

ADAPTIVE_THRESHOLD_PARAMS = {"block_size": 35, "c": 11}

# عتبات تكيف إضافية (مبنية على قياسات مرحلة التحقق)

IMPULSE_NOISE_AUTO_THRESHOLD = 0.012
SKEW_ACTION_ANGLE = 0.75
SKEW_ACTION_CONFIDENCE = 0.5

# سياسات الاستخدام التلقائي (إرشادية؛ pipeline يفرض سياسته بنفسه)

AUTO_ALLOWED = {
    "clahe",
    "gamma_correct",
    "illumination_normalize",
    "sharpen",
}

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
    "adaptive_threshold",
    "super_resolution"
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


def _noise_metric(analysis, key, default=0.0):
    item = analysis.get("metrics", {}).get("noise", {})

    if isinstance(item, dict):
        item = item.get(key, default)

    try:
        return float(item)

    except (TypeError, ValueError):
        return float(default)


def _preservation_level(analysis):
    profile = analysis.get("preservation_profile", {})

    level = profile.get("level") or profile.get("sensitivity") or "moderate"

    return str(level).lower()


def _severity(codes, medium_codes, high_codes):
    if bool(high_codes & codes):
        return "high"

    if bool(medium_codes & codes):
        return "medium"

    return "none"


def _condition_profile(analysis):
    """مصدر واحد للحقيقة عن حالات الصورة وشدتها."""
    codes = _diagnosis_codes(analysis)

    noise_impulse = _noise_metric(analysis, "impulse_ratio")
    noise_level = _noise_metric(analysis, "value")

    conditions = {
        "dark": _severity(codes, {"dark"}, {"very_dark"}),
        "bright": _severity(codes, {"bright"}, {"very_bright"}),
        "low_contrast": _severity(
            codes, {"low_contrast"}, {"very_low_contrast"}
        ),
        "low_sharpness": _severity(
            codes, {"low_sharpness"}, {"very_low_sharpness"}
        ),
        "noise": _severity(codes, {"moderate_noise"}, {"high_noise"}),
        "uneven_illumination": _severity(
            codes,
            {"uneven_illumination"},
            {"strong_uneven_illumination"}
        ),
    }

    conditions["impulse_noise"] = bool(
        conditions["noise"] != "none"
        and noise_impulse >= IMPULSE_NOISE_AUTO_THRESHOLD
    )

    conditions["gaussian_noise"] = bool(
        conditions["noise"] != "none"
        and not conditions["impulse_noise"]
        and noise_level > 0.0
    )

    return conditions


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

    if conditions["noise"] != "none" and conditions["low_sharpness"] != "none":
        conflicts.append({"code": "NOISE_SHARPNESS_CONFLICT", "severity": "high", "message": "Denoising should be evaluated before sharpening; sharpening noisy structure may amplify noise."})

    if conditions["gaussian_noise"]:
        conflicts.append({"code": "GAUSSIAN_NOISE_MANUAL_REVIEW", "severity": "medium", "message": "Gaussian noise has no calibrated automatic denoiser yet; bilateral or NLM requires manual choice."})

    if conditions["uneven_illumination"] != "none" and conditions["low_contrast"] != "none":
        conflicts.append({"code": "ILLUMINATION_CONTRAST_ORDER", "severity": "medium", "message": "Correct uneven illumination before deciding whether local contrast enhancement is still required."})

    if conditions["uneven_illumination"] != "none" and conditions["dark"] != "none":
        conflicts.append({"code": "ILLUMINATION_DARKNESS_ORDER", "severity": "medium", "message": "Local illumination imbalance should be corrected before global exposure adjustment."})

    if conditions["dark"] != "none" and conditions["low_contrast"] != "none":
        conflicts.append({"code": "DARK_LOW_CONTRAST_SEQUENCE", "severity": "medium", "message": "Exposure correction should be evaluated before applying additional contrast enhancement."})

    if conditions["bright"] != "none" and conditions["low_contrast"] != "none":
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


def _blocked_operations(conditions, preservation_level):
    blocked = {}

    if conditions["noise"] != "none":
        blocked["sharpen"] = "Sharpening is deferred while significant noise is present."

    if conditions["gaussian_noise"]:
        blocked["bilateral_denoise"] = "Automatic gaussian denoising is uncalibrated."
        blocked["non_local_means_denoise"] = "Automatic gaussian denoising is uncalibrated."

    if preservation_level == "high":
        blocked["median_denoise"] = "Automatic median filtering is unsafe for high-sensitivity structure."
        blocked["bilateral_denoise"] = "Automatic denoising remains deferred for high-sensitivity structure."
        blocked["non_local_means_denoise"] = "Automatic denoising remains deferred for high-sensitivity structure."
        blocked["morphological_opening"] = "Opening may remove fine document structure."
        blocked["morphological_closing"] = "Closing may merge independent document structures."



    return blocked


def _clahe_parameters(conditions, preservation_level):
    if conditions["low_contrast"] == "high":
        parameters = CLAHE_PARAMS_STRONG.copy()
    else:
        parameters = CLAHE_PARAMS.copy()

    if preservation_level == "high" and parameters["clip_limit"] > 1.2:
        parameters["clip_limit"] = 1.2

    return parameters


def _illumination_parameters(preservation_level):
    if preservation_level == "high":
        return ILLUMINATION_CONSERVATIVE_PARAMS.copy()

    return ILLUMINATION_PARAMS.copy()


def _gamma_parameters(conditions):
    if conditions["dark"] == "high":
        return GAMMA_DARK_STRONG_PARAMS.copy()

    return GAMMA_DARK_PARAMS.copy()


def _bright_parameters(conditions):
    if conditions["bright"] == "high":
        return GAMMA_BRIGHT_STRONG_PARAMS.copy()

    return GAMMA_BRIGHT_PARAMS.copy()


def _skew_recommendation(analysis):
    angle = _metric_value(analysis, "skew_angle")
    confidence = _metric_value(analysis, "skew_confidence")

    if abs(angle) < SKEW_ACTION_ANGLE:
        return None

    if confidence < SKEW_ACTION_CONFIDENCE:
        return None

    return {
        "operation_id": "deskew",
        "parameters": {"angle": round(angle, 2)},
    }


def _build_candidate_plan(analysis, conditions, blocked):
    """خطة مرتبة حسب التسلسل المُثبت، بمعاملات متكيفة."""
    preservation = _preservation_level(analysis)

    plan = []

    if conditions["uneven_illumination"] != "none":
        plan.append({
            "priority": 10,
            "operation_id": "illumination_normalize",
            "parameters": _illumination_parameters(preservation),
            "mode": "candidate",
            "automatic_eligible": True,
            "requires_reanalysis": True,
            "reason": "Uneven illumination should be corrected before dependent tonal processing."
        })

    elif conditions["dark"] != "none":
        plan.append({
            "priority": 20,
            "operation_id": "gamma_correct",
            "parameters": _gamma_parameters(conditions),
            "mode": "candidate",
            "automatic_eligible": True,
            "requires_reanalysis": True,
            "reason": "Global darkness is present without priority illumination correction."
        })

    elif conditions["bright"] != "none":
        plan.append({
            "priority": 25,
            "operation_id": "gamma_correct",
            "parameters": _bright_parameters(conditions),
            "mode": "candidate",
            "automatic_eligible": True,
            "requires_reanalysis": True,
            "reason": "Global brightness requires conservative tonal correction."
        })

    if conditions["low_contrast"] != "none" and "clahe" not in blocked:
        plan.append({
            "priority": 30,
            "operation_id": "clahe",
            "parameters": _clahe_parameters(conditions, preservation),
            "mode": "candidate",
            "automatic_eligible": True,
            "requires_reanalysis": True,
                        "reason": (
                "Low contrast is evaluated after any higher-priority "
                "illumination or exposure correction."
            )

        })

    if conditions["impulse_noise"]:
        plan.append({
            "priority": 40,
            "operation_id": "median_denoise",
            "parameters": MEDIAN_PARAMS.copy(),
            "mode": "candidate",
            "automatic_eligible": False,
            "requires_reanalysis": True,
            "reason": "Impulse (salt-and-pepper) noise is confirmed by impulse_ratio; median kernel=3 is the validated conservative choice."
        })

    elif conditions["noise"] != "none":
        plan.append({
            "priority": 40,
            "operation_id": None,
            "parameters": {},
            "mode": "manual_review",
            "automatic_eligible": False,
            "requires_reanalysis": False,
            "reason": "Noise is present without a calibrated automatic denoiser for its type."
        })

    if conditions["low_sharpness"] != "none" and "sharpen" not in blocked:
        plan.append({
            "priority": 50,
            "operation_id": "sharpen",
            "parameters": SHARPEN_PARAMS.copy(),
            "mode": "candidate",
            "automatic_eligible": True,
            "requires_reanalysis": True,
            "reason": "Low sharpness is present and no active conflict blocks conservative sharpening."
        })

    skew = _skew_recommendation(analysis)

    if skew is not None:
        plan.append({
            "priority": 60,
            "operation_id": "deskew",
            "parameters": skew["parameters"],
            "mode": "alignment",
            "automatic_eligible": False,
            "requires_reanalysis": True,
            "reason": "Detected skew exceeds the action threshold with sufficient confidence."
        })

    return sorted(plan, key=lambda item: item["priority"])


def _requires_treatment(conditions):
    active = [
        "dark", "bright", "low_contrast",
        "low_sharpness", "noise", "uneven_illumination"
    ]

    return any(conditions[key] != "none" for key in active)


def build_treatment_strategy(analysis):
    _validate_analysis(analysis)

    conditions = _condition_profile(analysis)
    evidence = _extract_unconfirmed_evidence(analysis)
    conflicts = _detect_conflicts(conditions)
    blocked = _blocked_operations(
        conditions, _preservation_level(analysis)
    )
    plan = _build_candidate_plan(analysis, conditions, blocked)

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


def _recommend_illumination(conditions, preservation_level, recommendations):
    if conditions["uneven_illumination"] == "none":
        return

    parameters = _illumination_parameters(preservation_level)

    _add_recommendation(
        recommendations,
        operation_id="illumination_normalize",
        priority=10,
        reason=(
            "توجد إضاءة غير متجانسة، والمعالجة المحافظة "
            "للإضاءة يجب أن تسبق أي تعديل لوني أو تبايني."
        ),
        parameters=parameters,
        mode="enhancement",
        risk="medium",
    )


def _recommend_exposure(conditions, recommendations):
    if conditions["dark"] != "none":
        _add_recommendation(
            recommendations,
            operation_id="gamma_correct",
            priority=20,
            reason=(
                "تشير القياسات إلى انخفاض الإضاءة، وGamma "
                "هو التصحيح اللوني المحافظ المُثبت للحالة."
            ),
            parameters=_gamma_parameters(conditions),
            mode="enhancement",
            risk="low",
        )

    elif conditions["bright"] != "none":
        _add_recommendation(
            recommendations,
            operation_id="gamma_correct",
            priority=25,
            reason=(
                "تشير القياسات إلى ارتفاع الإضاءة، ويستخدم "
                "Gamma بقيمة معاكسة لتقليل السطوع."
            ),
            parameters=_bright_parameters(conditions),
            mode="enhancement",
            risk="low",
        )


def _recommend_contrast(conditions, blocked, preservation_level, recommendations):
    if conditions["low_contrast"] == "none":
        return

    if "clahe" in blocked:
        return

    _add_recommendation(
        recommendations,
        operation_id="clahe",
        priority=30,
        reason=(
            "تشير القياسات إلى انخفاض التباين، "
            "وCLAHE بإعداد متكيف هو الخيار المحافظ المفضل."
        ),
        parameters=_clahe_parameters(conditions, preservation_level),
        mode="enhancement",
        risk="medium",
    )


def _recommend_noise(conditions, preservation_level, recommendations, avoided):
    if conditions["noise"] == "none":
        return

    if conditions["impulse_noise"]:
        if preservation_level == "high":
            _add_avoid(
                avoided,
                operation_id="median_denoise",
                reason=(
                    "الضوضاء نبضية لكن الصورة عالية الحساسية، "
                    "وقد يزيل Median بنية دقيقة مع الضوضاء."
                ),
                risk="medium-high",
            )

            return

        _add_recommendation(
            recommendations,
            operation_id="median_denoise",
            priority=40,
            reason=(
                "أكد impulse_ratio وجود ضوضاء نبضية "
                "من نوع Salt-and-Pepper، وMedian kernel=3 "
                "هو الخيار المُثبت والمحافظ لهذه الحالة."
            ),
            parameters=MEDIAN_PARAMS.copy(),
            mode="enhancement",
            risk="medium-high",
        )

        return

    _add_avoid(
        avoided,
        operation_id="bilateral_denoise",
        reason=(
            "الضوضاء الحالية ليست نبضية، واختيار مرشح "
            "الضوضاء الغاوسية يحتاج قرارًا يدويًا بعد المعايرة."
        ),
        risk="medium-high",
    )

    _add_avoid(
        avoided,
        operation_id="non_local_means_denoise",
        reason=(
            "الضوضاء الحالية ليست نبضية، واختيار قوة "
            "NLM يحتاج مراجعة يدوية لتجنب التجانس المفرط."
        ),
        risk="medium-high",
    )


def _recommend_sharpness(conditions, blocked, preservation_level, recommendations, avoided):
    if conditions["low_sharpness"] == "none":
        return

    if "sharpen" in blocked:
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
        priority=50,
        reason=("تشير القياسات إلى انخفاض الحدة، " "ويستخدم Sharpen بإعداد محافظ."),
        parameters=SHARPEN_PARAMS.copy(),
        mode="enhancement",
        risk="medium",
    )


def _recommend_alignment(analysis, recommendations):
    skew = _skew_recommendation(analysis)

    if skew is None:
        return

    _add_recommendation(
        recommendations,
        operation_id="deskew",
        priority=60,
        reason=(
            "اكتُشف ميلان في أسطر الوثيقة بثقة كافية، "
            "والتصحيح الهندسي يُنفذ يدويًا بالزاوية المكتشفة."
        ),
        parameters=skew["parameters"],
        mode="alignment",
        risk="medium",
    )


def _recommend_binarization(conditions, recommendations):
    if conditions["uneven_illumination"] == "none":
        return

    _add_recommendation(
        recommendations,
        operation_id="adaptive_threshold",
        priority=70,
        reason=(
            "توجد إضاءة غير متجانسة، ولذلك يعتبر Adaptive Threshold "
            "خيارًا مناسبًا لمسار فصل النص عن الخلفية."
        ),
        parameters=ADAPTIVE_THRESHOLD_PARAMS.copy(),
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

    conditions = _condition_profile(analysis)

    blocked = _blocked_operations(
        conditions, _preservation_level(analysis)
    )

    recommendations = []
    avoided = []

    _recommend_illumination(conditions, preservation_level, recommendations)

    _recommend_exposure(conditions, recommendations)

    _recommend_contrast(conditions, blocked, preservation_level, recommendations)

    _recommend_noise(conditions, preservation_level, recommendations, avoided)

    _recommend_sharpness(conditions, blocked, preservation_level, recommendations, avoided)

    _recommend_alignment(analysis, recommendations)

    _recommend_binarization(conditions, recommendations)

    _build_default_avoid_list(avoided)

    recommendations.sort(key=lambda item: item["priority"])

    strategy = build_treatment_strategy(analysis)

    return {
        "recommendations": recommendations,
        "excluded_from_automatic": avoided,
        "summary": _build_summary(recommendations, avoided),
        "basis": {
            "diagnoses": sorted(codes),
            "preservation_level": preservation_level,
            "policy": "rule_based_adaptive",
        },
        "treatment_strategy": strategy,
    }
