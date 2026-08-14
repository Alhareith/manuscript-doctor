# تحليل خصائص الصورة
import cv2
import numpy as np


BRIGHTNESS_VERY_LOW = 55.0
BRIGHTNESS_LOW = 85.0
BRIGHTNESS_HIGH = 200.0
BRIGHTNESS_VERY_HIGH = 220.0

CONTRAST_VERY_LOW = 20.0
CONTRAST_LOW = 35.0

SHARPNESS_VERY_LOW = 25.0
SHARPNESS_LOW = 60.0

NOISE_MODERATE = 12.0
NOISE_HIGH = 20.0

ILLUMINATION_VARIATION_MODERATE = 0.10
ILLUMINATION_VARIATION_HIGH = 0.18

EDGE_DENSITY_HIGH = 0.12


def _to_gray(image):
    if image is None or not isinstance(image, np.ndarray):
        raise ValueError("Image must be a valid NumPy array.")

    if image.size == 0:
        raise ValueError("Image cannot be empty.")

    if image.ndim == 2:
        return image

    if image.ndim != 3:
        raise ValueError("Unsupported image shape.")

    channels = image.shape[2]

    if channels == 1:
        return image[:, :, 0]

    if channels == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    if channels == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)

    raise ValueError("Unsupported number of image channels.")


def _get_dimensions(image):
    height, width = image.shape[:2]

    if image.ndim == 2:
        channels = 1
    else:
        channels = image.shape[2]

    return {
        "width": int(width),
        "height": int(height),
        "channels": int(channels)
    }


def _measure_brightness(gray):
    return float(np.mean(gray))


def _measure_contrast(gray):
    return float(np.std(gray))


def _measure_dynamic_range(gray):
    p5 = np.percentile(gray, 5)
    p95 = np.percentile(gray, 95)

    return float(p95 - p5)


def _measure_sharpness(gray):
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)

    return float(laplacian.var())


def _noise_metrics(gray):
    filtered = cv2.medianBlur(
        gray,
        3
    )

    residual = cv2.absdiff(
        gray,
        filtered
    ).astype(np.float32)

    mean_residual = float(
        np.mean(residual)
    )

    percentile_90 = float(
        np.percentile(
            residual,
            90
        )
    )

    affected_ratio = float(
        np.mean(
            residual >= 5.0
        )
    )

    return {
        "value": mean_residual,
        "unit": "mean_absolute_residual",
        "p90": percentile_90,
        "affected_ratio": affected_ratio,
        "interpretation": "heuristic"
    }



def _measure_illumination_variation(gray):
    height, width = gray.shape

    shortest_side = min(height, width)

    sigma = max(shortest_side / 30.0, 3.0)

    illumination = cv2.GaussianBlur(
        gray,
        (0, 0),
        sigmaX=sigma,
        sigmaY=sigma
    )

    mean_illumination = float(np.mean(illumination))

    if mean_illumination <= 1e-6:
        return 0.0

    variation = float(
        np.std(illumination) / mean_illumination
    )

    return variation


def _measure_edge_density(gray):
    median_intensity = float(np.median(gray))

    lower = int(max(0, 0.66 * median_intensity))
    upper = int(min(255, 1.33 * median_intensity))

    if lower == upper:
        lower = 50
        upper = 150

    edges = cv2.Canny(
        gray,
        lower,
        upper
    )

    edge_pixels = np.count_nonzero(edges)

    return float(edge_pixels / edges.size)


def _build_metrics(gray):
    return {
        "brightness": {
            "value": round(_measure_brightness(gray), 3),
            "unit": "gray_level"
        },
        "contrast": {
            "value": round(_measure_contrast(gray), 3),
            "unit": "gray_level_std"
        },
        "dynamic_range": {
            "value": round(_measure_dynamic_range(gray), 3),
            "unit": "gray_level"
        },
        "sharpness": {
            "value": round(_measure_sharpness(gray), 3),
            "unit": "laplacian_variance"
        },
        "noise": _noise_metrics(gray),
        "illumination_variation": {
            "value": round(
                _measure_illumination_variation(gray),
                4
            ),
            "unit": "coefficient"
        },
        "edge_density": {
            "value": round(_measure_edge_density(gray), 4),
            "unit": "ratio"
        }
    }


def _diagnose(metrics):
    diagnoses = []

    brightness = metrics["brightness"]["value"]
    contrast = metrics["contrast"]["value"]
    sharpness = metrics["sharpness"]["value"]
    noise = metrics["noise"]["value"]
    illumination = metrics["illumination_variation"]["value"]

    if brightness < BRIGHTNESS_VERY_LOW:
        diagnoses.append({
            "code": "very_dark",
            "label": "إضاءة منخفضة جدًا",
            "severity": "high",
            "message": "تشير القياسات إلى أن الصورة مظلمة بدرجة واضحة."
        })

    elif brightness < BRIGHTNESS_LOW:
        diagnoses.append({
            "code": "dark",
            "label": "إضاءة منخفضة",
            "severity": "medium",
            "message": "تشير القياسات إلى انخفاض مستوى الإضاءة."
        })

    if brightness > BRIGHTNESS_VERY_HIGH:
        diagnoses.append({
            "code": "very_bright",
            "label": "إضاءة مرتفعة جدًا",
            "severity": "high",
            "message": "تشير القياسات إلى سطوع مرتفع قد يخفي بعض التفاصيل."
        })

    elif brightness > BRIGHTNESS_HIGH:
        diagnoses.append({
            "code": "bright",
            "label": "إضاءة مرتفعة",
            "severity": "medium",
            "message": "تشير القياسات إلى ارتفاع مستوى الإضاءة."
        })

    if contrast < CONTRAST_VERY_LOW:
        diagnoses.append({
            "code": "very_low_contrast",
            "label": "تباين منخفض جدًا",
            "severity": "high",
            "message": "تظهر الصورة فرقًا محدودًا جدًا بين درجاتها البصرية."
        })

    elif contrast < CONTRAST_LOW:
        diagnoses.append({
            "code": "low_contrast",
            "label": "تباين منخفض",
            "severity": "medium",
            "message": "تشير القياسات إلى انخفاض التباين في الصورة."
        })

    if sharpness < SHARPNESS_VERY_LOW:
        diagnoses.append({
            "code": "very_low_sharpness",
            "label": "حدة منخفضة جدًا",
            "severity": "high",
            "message": "تشير القياسات إلى ضعف واضح في الحواف والتفاصيل."
        })

    elif sharpness < SHARPNESS_LOW:
        diagnoses.append({
            "code": "low_sharpness",
            "label": "حدة منخفضة",
            "severity": "medium",
            "message": "تشير القياسات إلى انخفاض نسبي في حدة التفاصيل."
        })

    if noise > NOISE_HIGH:
        diagnoses.append({
            "code": "high_noise",
            "label": "ضوضاء مرتفعة",
            "severity": "high",
            "message": "تشير القياسات إلى تغيرات محلية قوية قد تمثل ضوضاء."
        })

    elif noise > NOISE_MODERATE:
        diagnoses.append({
            "code": "moderate_noise",
            "label": "ضوضاء متوسطة",
            "severity": "medium",
            "message": "تشير القياسات إلى وجود قدر متوسط من التغيرات المحلية."
        })

    if illumination > ILLUMINATION_VARIATION_HIGH:
        diagnoses.append({
            "code": "strong_uneven_illumination",
            "label": "إضاءة غير متجانسة بوضوح",
            "severity": "high",
            "message": "توجد فروق واضحة في توزيع الإضاءة عبر الصورة."
        })

    elif illumination > ILLUMINATION_VARIATION_MODERATE:
        diagnoses.append({
            "code": "uneven_illumination",
            "label": "إضاءة غير متجانسة",
            "severity": "medium",
            "message": "تشير القياسات إلى تفاوت في توزيع الإضاءة عبر الصورة."
        })

    return diagnoses


def _build_preservation_profile(metrics):
    indicators = []
    sensitivity_points = 0

    contrast = metrics["contrast"]["value"]
    sharpness = metrics["sharpness"]["value"]
    dynamic_range = metrics["dynamic_range"]["value"]
    edge_density = metrics["edge_density"]["value"]

    if edge_density >= EDGE_DENSITY_HIGH:
        sensitivity_points += 2

        indicators.append({
            "code": "dense_edge_structure",
            "message": "تحتوي الصورة على كثافة حواف مرتفعة نسبيًا، لذلك يفضل تجنب المعالجة العدوانية."
        })

    if contrast < CONTRAST_LOW:
        sensitivity_points += 1

        indicators.append({
            "code": "weak_contrast_details",
            "message": "قد تكون بعض التفاصيل ضعيفة التباين وأكثر عرضة للاختفاء أثناء المعالجة القوية."
        })

    if sharpness < SHARPNESS_LOW:
        sensitivity_points += 1

        indicators.append({
            "code": "weak_edge_definition",
            "message": "الحواف الحالية ضعيفة نسبيًا، لذلك ينبغي التعامل بحذر مع العمليات التي قد تزيل التفاصيل."
        })

    if dynamic_range < 60:
        sensitivity_points += 1

        indicators.append({
            "code": "limited_dynamic_range",
            "message": "النطاق البصري محدود نسبيًا، وقد توجد تفاصيل متقاربة في الشدة."
        })

    if sensitivity_points >= 3:
        level = "high"

    elif sensitivity_points >= 1:
        level = "moderate"

    else:
        level = "low"

    messages = {
        "low": "لا تظهر المؤشرات الحالية حساسية مرتفعة للمعالجة، مع بقاء التحقق بعد المعالجة ضروريًا.",
        "moderate": "توجد مؤشرات تستدعي استخدام معالجة متوازنة ومراقبة أثرها على التفاصيل.",
        "high": "توجد مؤشرات تستدعي معالجة محافظة وتجنب العمليات القوية دون تحقق."
    }

    return {
        "level": level,
        "indicators": indicators,
        "message": messages[level],
        "interpretation": "heuristic"
    }
def _clipping_metrics(
    gray
):
    dark_clipped_ratio = float(
        np.mean(
            gray <= 5
        )
    )

    bright_clipped_ratio = float(
        np.mean(
            gray >= 250
        )
    )

    return {
        "dark_clipped_ratio": (
            dark_clipped_ratio
        ),
        "bright_clipped_ratio": (
            bright_clipped_ratio
        )
    }

def _bleed_through_indicators(gray):
    source = gray.astype(
        np.float32
    )

    background = cv2.GaussianBlur(
        source,
        (31, 31),
        0
    )

    residual = np.abs(
        source - background
    )

    weak_structure_ratio = float(
        np.mean(
            (residual >= 4.0)
            & (residual <= 18.0)
        )
    )

    strong_structure_ratio = float(
        np.mean(
            residual > 18.0
        )
    )

    weak_to_strong_ratio = float(
        weak_structure_ratio
        / max(
            strong_structure_ratio,
            1e-6
        )
    )

    return {
        "weak_structure_ratio": (
            weak_structure_ratio
        ),
        "strong_structure_ratio": (
            strong_structure_ratio
        ),
        "weak_to_strong_ratio": (
            weak_to_strong_ratio
        )
    }

def analyze_image(image):
    gray = _to_gray(image)

    dimensions = _get_dimensions(image)

    metrics = _build_metrics(gray)

    clipping = _clipping_metrics(gray)
    bleed_indicators = (
        _bleed_through_indicators(
            gray
        )
    )

    metrics["dark_clipped_ratio"] = {
        "value": round(
            clipping["dark_clipped_ratio"],
            4
        ),
        "unit": "ratio"
    }

    metrics["bright_clipped_ratio"] = {
        "value": round(
            clipping["bright_clipped_ratio"],
            4
        ),
        "unit": "ratio"
    }

    metrics["weak_structure_ratio"] = {
        "value": round(
            bleed_indicators["weak_structure_ratio"],
            4
        ),
        "unit": "ratio"
    }

    metrics["strong_structure_ratio"] = {
        "value": round(
            bleed_indicators["strong_structure_ratio"],
            4
        ),
        "unit": "ratio"
    }

    metrics["weak_to_strong_ratio"] = {
        "value": round(
            bleed_indicators["weak_to_strong_ratio"],
            4
        ),
        "unit": "ratio"
    }

    diagnoses = _diagnose(metrics)

    preservation_profile = _build_preservation_profile(
        metrics
    )

    return {
        "dimensions": dimensions,
        "metrics": metrics,
        "diagnoses": diagnoses,
        "preservation_profile": preservation_profile,
        "clipping": clipping
    }

