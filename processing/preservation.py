import cv2
import numpy as np


EDGE_RETENTION_CAUTION = 0.75
EDGE_RETENTION_HIGH_RISK = 0.55

COMPONENT_RETENTION_CAUTION = 0.70
COMPONENT_RETENTION_HIGH_RISK = 0.50

STRUCTURE_SIMILARITY_CAUTION = 0.75
STRUCTURE_SIMILARITY_HIGH_RISK = 0.55

EDGE_INFLATION_CAUTION = 1.60
EDGE_INFLATION_HIGH_RISK = 2.20

CLIPPING_NEW_CAUTION = 0.02
CLIPPING_NEW_HIGH_RISK = 0.10

SMOOTHING_CAUTION = 0.50
SMOOTHING_HIGH_RISK = 0.25

INK_RETENTION_CAUTION = 0.80
INK_RETENTION_HIGH_RISK = 0.60
INK_INFLATION_CAUTION = 1.80

# Matches the analyzer's high impulse rating. Below this, tiny genuine
# marks (diacritics) may look like impulses and keep strict protection.
IMPULSE_NOISE_REFERENCE_THRESHOLD = 0.012

# Isolated impulse pixels separate salt-and-pepper noise from dense
# thin text, whose residual pixels cluster along strokes. Calibrated
# on the validation dataset: clean/gaussian sources stay below 0.004
# while salt-and-pepper cases measure at least 0.006 across sources.
ISOLATED_IMPULSE_REFERENCE_THRESHOLD = 0.005


def _validate_image(image):
    if image is None or not isinstance(image, np.ndarray):
        raise ValueError("Image must be a valid NumPy array.")

    if image.size == 0:
        raise ValueError("Image cannot be empty.")

    if image.dtype != np.uint8:
        raise ValueError("Only 8-bit images are supported.")

    if image.ndim not in {2, 3}:
        raise ValueError("Unsupported image shape.")


def _to_gray(image):
    _validate_image(image)

    if image.ndim == 2:
        return image.copy()

    channels = image.shape[2]

    if channels == 1:
        return image[:, :, 0].copy()

    if channels == 3:
        return cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

    if channels == 4:
        return cv2.cvtColor(
            image,
            cv2.COLOR_BGRA2GRAY
        )

    raise ValueError(
        "Unsupported number of image channels."
    )


def _match_size(reference, target):
    if reference.shape == target.shape:
        return target

    return cv2.resize(
        target,
        (
            reference.shape[1],
            reference.shape[0]
        ),
        interpolation=cv2.INTER_AREA
    )


def _normalize(gray):
    return cv2.normalize(
        gray,
        None,
        0,
        255,
        cv2.NORM_MINMAX
    )


def _edge_map(gray):
    median_intensity = float(
        np.median(gray)
    )

    lower = int(
        max(
            0,
            0.66 * median_intensity
        )
    )

    upper = int(
        min(
            255,
            1.33 * median_intensity
        )
    )

    if lower == upper:
        lower = 50
        upper = 150

    return cv2.Canny(
        gray,
        lower,
        upper
    )


def _edge_retention(
    original_edges,
    processed_edges
):
    original_mask = (
        original_edges > 0
    )

    original_count = np.count_nonzero(
        original_mask
    )

    if original_count == 0:
        return 1.0

    dilation_kernel = np.ones(
        (3, 3),
        dtype=np.uint8
    )

    processed_dilated = cv2.dilate(
        processed_edges,
        dilation_kernel,
        iterations=1
    )

    retained = (
        original_mask
        & (processed_dilated > 0)
    )

    retained_count = np.count_nonzero(
        retained
    )

    return float(
        retained_count / original_count
    )


def _edge_inflation(
    original_edges,
    processed_edges
):
    original_count = np.count_nonzero(
        original_edges
    )

    processed_count = np.count_nonzero(
        processed_edges
    )

    if original_count == 0:
        if processed_count == 0:
            return 1.0

        return float(processed_count)

    return float(
        processed_count / original_count
    )


def _binary_structure(gray):
    blurred = cv2.GaussianBlur(
        gray,
        (3, 3),
        0
    )

    _, binary = cv2.threshold(
        blurred,
        0,
        255,
        cv2.THRESH_BINARY_INV
        + cv2.THRESH_OTSU
    )

    return binary


def _meaningful_components(binary):
    count, labels, stats, _ = (
        cv2.connectedComponentsWithStats(
            binary,
            connectivity=8
        )
    )

    areas = []

    for index in range(1, count):
        area = int(
            stats[
                index,
                cv2.CC_STAT_AREA
            ]
        )

        if 3 <= area <= 5000:
            areas.append(area)

    return areas


def _component_retention(
    original_gray,
    processed_gray
):
    original_binary = _binary_structure(
        original_gray
    )

    processed_binary = _binary_structure(
        processed_gray
    )

    original_components = (
        _meaningful_components(
            original_binary
        )
    )

    processed_components = (
        _meaningful_components(
            processed_binary
        )
    )

    original_count = len(
        original_components
    )

    processed_count = len(
        processed_components
    )

    if original_count == 0:
        return 1.0

    ratio = (
        processed_count
        / original_count
    )

    return float(
        min(ratio, 1.0)
    )


def _structure_similarity(
    original_gray,
    processed_gray
):
    original_float = (
        original_gray.astype(
            np.float32
        )
        / 255.0
    )

    processed_float = (
        processed_gray.astype(
            np.float32
        )
        / 255.0
    )

    difference = cv2.absdiff(
        original_float,
        processed_float
    )

    mean_difference = float(
        np.mean(difference)
    )

    similarity = (
        1.0 - mean_difference
    )

    return float(
        np.clip(
            similarity,
            0.0,
            1.0
        )
    )


def _clipping_change(
    original_gray,
    processed_gray
):
    orig_dark = float(
        np.mean(original_gray <= 5)
    )

    orig_bright = float(
        np.mean(original_gray >= 250)
    )

    proc_dark = float(
        np.mean(processed_gray <= 5)
    )

    proc_bright = float(
        np.mean(processed_gray >= 250)
    )

    new_dark = max(0.0, proc_dark - orig_dark)
    new_bright = max(
        0.0, proc_bright - orig_bright
    )

    return {
        "new_dark_clipped_ratio": round(
            new_dark, 4
        ),
        "new_bright_clipped_ratio": round(
            new_bright, 4
        ),
        "total_new_clipping": round(
            new_dark + new_bright, 4
        ),
    }


def _smoothing_ratio(
    original_gray,
    processed_gray
):
    # Impulse noise inflates Laplacian variance like real structure,
    # so sharpness is compared on median-suppressed proxies. This keeps
    # denoisers from being penalized for removing noise pixels.
    orig_sharpness = cv2.Laplacian(
        cv2.medianBlur(original_gray, 3),
        cv2.CV_64F
    ).var()

    proc_sharpness = cv2.Laplacian(
        cv2.medianBlur(processed_gray, 3),
        cv2.CV_64F
    ).var()

    if orig_sharpness < 1e-6:
        return 1.0

    return float(
        np.clip(proc_sharpness / orig_sharpness, 0.0, 2.0)
    )


def _is_near_binary(gray):
    extreme_ratio = float(
        np.mean(
            (gray <= 10) | (gray >= 245)
        )
    )

    return extreme_ratio > 0.90


def _ink_metrics(
    original_raw,
    original_reference,
    processed_gray
):
    # Ink coverage is only comparable when the output is binarized;
    # enhancement outputs keep grayscale gradation and return 1.0.
    if not _is_near_binary(processed_gray):
        return {
            "ink_retention": 1.0,
            "ink_inflation_ratio": 1.0,
        }

    otsu_threshold, _ = cv2.threshold(
        original_raw,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    reference_ink = float(
        np.mean(original_reference < otsu_threshold)
    )

    raw_ink = float(
        np.mean(original_raw < otsu_threshold)
    )

    processed_reference_ink = float(
        np.mean(processed_gray < otsu_threshold)
    )

    if reference_ink <= 1e-6 or raw_ink <= 1e-6:
        return {
            "ink_retention": 1.0,
            "ink_inflation_ratio": 1.0,
        }

    # Loss is judged against the impulse-suppressed reference so
    # denoising pepper noise is not read as lost text, while
    # inflation is judged against the raw original so an untouched
    # noisy image measures exactly 1.0.
    return {
        "ink_retention": float(
            np.clip(
                processed_reference_ink / reference_ink,
                0.0,
                5.0
            )
        ),
        "ink_inflation_ratio": float(
            np.clip(
                processed_reference_ink / raw_ink,
                0.0,
                5.0
            )
        ),
    }


def _isolated_impulse_ratio(gray):
    residual = cv2.absdiff(
        gray,
        cv2.medianBlur(gray, 3)
    )

    mask = (residual >= 100.0).astype(np.float32)

    neighbor_count = (
        cv2.filter2D(
            mask,
            -1,
            np.ones((3, 3), dtype=np.float32)
        )
        - mask
    )

    isolated = (mask == 1) & (neighbor_count == 0)

    return float(np.mean(isolated))


def _reference_gray(original_gray):
    # Isolated impulse pixels are noise; clustered residual pixels
    # belong to dense thin strokes. Only truly impulsive originals
    # get a suppressed reference so removing noise is not reported
    # as structure loss.
    if (
        _isolated_impulse_ratio(original_gray)
        >= ISOLATED_IMPULSE_REFERENCE_THRESHOLD
    ):
        return cv2.medianBlur(original_gray, 3)

    return original_gray


def _build_metrics(
    original_norm,
    processed_norm,
    original_raw,
    processed_raw,
    original_reference
):
    # Retention metrics are judged against the (impulse-suppressed)
    # reference so noise removal is not structure loss.
    reference_edges = _edge_map(original_norm)

    processed_edges = _edge_map(processed_norm)

    # Inflation is judged against the untouched original so an
    # identical noisy image still measures 1.0.
    original_edges = _edge_map(original_raw)

    binary_output = _is_near_binary(processed_raw)

    clipping = _clipping_change(
        original_raw,
        processed_raw
    )

    if binary_output:
        # Binarization saturates pixels by design; ink metrics
        # govern its interpretation instead of clipping.
        clipping = {
            "new_dark_clipped_ratio": 0.0,
            "new_bright_clipped_ratio": 0.0,
            "total_new_clipping": 0.0,
        }

    clipping["binary_output"] = binary_output

    return {
        "edge_retention": round(
            _edge_retention(
                reference_edges,
                processed_edges
            ),
            4
        ),

        "component_retention": round(
            _component_retention(
                original_norm,
                processed_norm
            ),
            4
        ),

        "structure_similarity": round(
            _structure_similarity(
                original_raw,
                processed_raw
            ),
            4
        ),

        "edge_inflation": round(
            _edge_inflation(
                original_edges,
                processed_edges
            ),
            4
        ),

        "clipping_change": clipping,

        "smoothing_ratio": round(
            _smoothing_ratio(
                original_reference,
                processed_raw
            ),
            4
        ),
        **{
            key: round(value, 4)
            for key, value in _ink_metrics(
                original_raw,
                original_reference,
                processed_raw
            ).items()
        },
    }


def _build_warnings(metrics):
    warnings = []

    edge_retention = (
        metrics["edge_retention"]
    )

    component_retention = (
        metrics["component_retention"]
    )

    structure_similarity = (
        metrics["structure_similarity"]
    )

    edge_inflation = (
        metrics["edge_inflation"]
    )

    clipping_total = metrics["clipping_change"]["total_new_clipping"]

    smoothing = metrics["smoothing_ratio"]

    if (
        edge_retention
        < EDGE_RETENTION_HIGH_RISK
    ):
        warnings.append({
            "code": "major_edge_loss",
            "severity": "high",
            "message": "توجد مؤشرات قوية على فقد جزء من البنية الحافية الأصلية."
        })

    elif (
        edge_retention
        < EDGE_RETENTION_CAUTION
    ):
        warnings.append({
            "code": "edge_loss",
            "severity": "medium",
            "message": "توجد مؤشرات على انخفاض في بعض الحواف الأصلية."
        })

    if (
        component_retention
        < COMPONENT_RETENTION_HIGH_RISK
    ):
        warnings.append({
            "code": "major_component_loss",
            "severity": "high",
            "message": "انخفض عدد المكونات البنيوية الصغيرة بدرجة كبيرة بعد المعالجة."
        })

    elif (
        component_retention
        < COMPONENT_RETENTION_CAUTION
    ):
        warnings.append({
            "code": "component_loss",
            "severity": "medium",
            "message": "توجد مؤشرات على اختفاء بعض المكونات البنيوية بعد المعالجة."
        })

    if (
        structure_similarity
        < STRUCTURE_SIMILARITY_HIGH_RISK
    ):
        warnings.append({
            "code": "major_structural_change",
            "severity": "high",
            "message": "تغيرت البنية البصرية العامة بدرجة كبيرة مقارنة بالأصل."
        })

    elif (
        structure_similarity
        < STRUCTURE_SIMILARITY_CAUTION
    ):
        warnings.append({
            "code": "structural_change",
            "severity": "medium",
            "message": "ظهرت تغيرات بنيوية ملحوظة مقارنة بالصورة الأصلية."
        })

    if (
        edge_inflation
        > EDGE_INFLATION_HIGH_RISK
    ):
        warnings.append({
            "code": "major_edge_inflation",
            "severity": "high",
            "message": "ازدادت الحواف بدرجة كبيرة، وقد يشير ذلك إلى تضخيم الضوضاء أو التفاصيل."
        })

    elif (
        edge_inflation
        > EDGE_INFLATION_CAUTION
    ):
        warnings.append({
            "code": "edge_inflation",
            "severity": "medium",
            "message": "ازدادت كثافة الحواف بعد المعالجة بدرجة تستدعي المراجعة."
        })

    if clipping_total > CLIPPING_NEW_HIGH_RISK:
        warnings.append({
            "code": "major_clipping",
            "severity": "high",
            "message": "المعالجة تسببت في فقدان عدد كبير من درجات السطوع بسبب التشبع."
        })

    elif clipping_total > CLIPPING_NEW_CAUTION:
        warnings.append({
            "code": "clipping",
            "severity": "medium",
            "message": "ظهر بعض التشبع الجديد في درجات السطوع بعد المعالجة."
        })

    if smoothing < SMOOTHING_HIGH_RISK:
        warnings.append({
            "code": "major_smoothing",
            "severity": "high",
            "message": "انخفضت حدة الصورة بدرجة كبيرة مما يشير إلى تجانس مفرط قد يفقد تفاصيل."
        })

    elif smoothing < SMOOTHING_CAUTION:
        warnings.append({
            "code": "smoothing",
            "severity": "medium",
            "message": "انخفضت حدة الصورة بشكل ملحوظ بعد المعالجة."
        })

    ink_retention = metrics["ink_retention"]

    if ink_retention < INK_RETENTION_HIGH_RISK:
        warnings.append({
            "code": "major_ink_loss",
            "severity": "high",
            "message": "فقدت النتيجة جزءًا كبيرًا من تغطية الحبر الأصلية، وقد يشير ذلك إلى فقد حروف أو أجزاء باهتة."
        })

    elif ink_retention < INK_RETENTION_CAUTION:
        warnings.append({
            "code": "ink_loss",
            "severity": "medium",
            "message": "انخفضت تغطية الحبر بعد المعالجة بما يستدعي مراجعة فقد أجزاء دقيقة."
        })

    ink_inflation = metrics["ink_inflation_ratio"]

    if ink_inflation > INK_INFLATION_CAUTION:
        warnings.append({
            "code": "ink_inflation",
            "severity": "medium",
            "message": "ازدادت تغطية الحبر بدرجة كبيرة، وقد يشير ذلك إلى تحويل خلفية أو نسيج إلى حبر."
        })

    return warnings


def _build_assessment(warnings):
    if any(
        warning["severity"] == "high"
        for warning in warnings
    ):
        return {
            "status": "high_risk",
            "message": "توجد مؤشرات قوية على تغير بنيوي قد يجعل النتيجة غير مناسبة للاعتماد دون مراجعة."
        }

    if warnings:
        return {
            "status": "caution",
            "message": "تحققت المعالجة، لكن توجد تغيرات بنيوية تستدعي مراجعة النتيجة."
        }

    return {
        "status": "acceptable",
        "message": "لم تظهر المؤشرات الحالية تغيرات بنيوية قوية تستدعي التحذير."
    }


def verify_preservation(
    original,
    processed
):
    original_raw = _to_gray(original)
    processed_raw = _to_gray(processed)

    if original_raw.shape != processed_raw.shape:
        processed_raw = _match_size(
            original_raw, processed_raw
        )

    original_reference = _reference_gray(
        original_raw
    )

    original_norm = _normalize(original_reference)
    processed_norm = _normalize(processed_raw)

    metrics = _build_metrics(
        original_norm,
        processed_norm,
        original_raw,
        processed_raw,
        original_reference
    )

    warnings = _build_warnings(
        metrics
    )

    assessment = _build_assessment(
        warnings
    )

    return {
    "metrics": metrics,
    "warnings": warnings,
    "assessment": assessment,
    "interpretation": "heuristic_structural_assessment",
    "limitations": [
        "The assessment measures visual structure, not textual meaning.",
        "Large appearance changes such as binarization may reduce similarity even when the result is useful.",
        "Thresholds are provisional and require evaluation on real manuscript images.",
        "Component counting may treat noise pixels as structure to preserve."
    ]
}
