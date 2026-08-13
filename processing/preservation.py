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

        return float("inf")

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


def _build_metrics(
    original_gray,
    processed_gray
):
    original_edges = _edge_map(
        original_gray
    )

    processed_edges = _edge_map(
        processed_gray
    )

    return {
        "edge_retention": round(
            _edge_retention(
                original_edges,
                processed_edges
            ),
            4
        ),

        "component_retention": round(
            _component_retention(
                original_gray,
                processed_gray
            ),
            4
        ),

        "structure_similarity": round(
            _structure_similarity(
                original_gray,
                processed_gray
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
    original_gray = _normalize(
        _to_gray(original)
    )

    processed_gray = _normalize(
        _to_gray(processed)
    )

    processed_gray = _match_size(
        original_gray,
        processed_gray
    )

    metrics = _build_metrics(
        original_gray,
        processed_gray
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
        "interpretation": "heuristic_structural_assessment"
    }
