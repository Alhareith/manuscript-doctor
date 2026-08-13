import cv2
import numpy as np


def _validate_image(image):
    if image is None or not isinstance(image, np.ndarray):
        raise ValueError("Image must be a valid NumPy array.")

    if image.size == 0:
        raise ValueError("Image cannot be empty.")

    if image.dtype != np.uint8:
        raise ValueError("Only 8-bit images are supported.")

    if image.ndim == 2:
        return

    if image.ndim != 3:
        raise ValueError("Unsupported image shape.")

    if image.shape[2] not in {1, 3, 4}:
        raise ValueError("Unsupported number of image channels.")


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

    return cv2.cvtColor(
        image,
        cv2.COLOR_BGRA2GRAY
    )


def _validate_odd_kernel_size(value, name):
    if not isinstance(value, int):
        raise ValueError(f"{name} must be an integer.")

    if value < 3:
        raise ValueError(f"{name} must be at least 3.")

    if value % 2 == 0:
        raise ValueError(f"{name} must be odd.")


def _apply_to_luminance(image, operation):
    _validate_image(image)

    if image.ndim == 2:
        return operation(image.copy())

    if image.shape[2] == 1:
        gray = image[:, :, 0]

        result = operation(gray.copy())

        return result[:, :, np.newaxis]

    if image.shape[2] == 3:
        lab = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2LAB
        )

        lightness, a, b = cv2.split(lab)

        processed_lightness = operation(lightness)

        processed_lab = cv2.merge(
            (
                processed_lightness,
                a,
                b
            )
        )

        return cv2.cvtColor(
            processed_lab,
            cv2.COLOR_LAB2BGR
        )

    alpha = image[:, :, 3].copy()
    bgr = image[:, :, :3]

    processed_bgr = _apply_to_luminance(
        bgr,
        operation
    )

    return np.dstack(
        (
            processed_bgr,
            alpha
        )
    )


def clahe(
    image,
    clip_limit=2.0,
    tile_grid_size=8
):
    _validate_image(image)

    if not isinstance(clip_limit, (int, float)):
        raise ValueError("clip_limit must be numeric.")

    if clip_limit <= 0:
        raise ValueError("clip_limit must be greater than 0.")

    if not isinstance(tile_grid_size, int):
        raise ValueError("tile_grid_size must be an integer.")

    if tile_grid_size < 2:
        raise ValueError(
            "tile_grid_size must be at least 2."
        )

    clahe_filter = cv2.createCLAHE(
        clipLimit=float(clip_limit),
        tileGridSize=(
            tile_grid_size,
            tile_grid_size
        )
    )

    return _apply_to_luminance(
        image,
        clahe_filter.apply
    )


def histogram_equalization(image):
    _validate_image(image)

    return _apply_to_luminance(
        image,
        cv2.equalizeHist
    )


def median_denoise(
    image,
    kernel_size=3
):
    _validate_image(image)

    _validate_odd_kernel_size(
        kernel_size,
        "kernel_size"
    )

    return cv2.medianBlur(
        image,
        kernel_size
    )


def sharpen(
    image,
    amount=0.5,
    kernel_size=3
):
    _validate_image(image)

    if not isinstance(amount, (int, float)):
        raise ValueError("amount must be numeric.")

    if amount < 0 or amount > 2:
        raise ValueError(
            "amount must be between 0 and 2."
        )

    _validate_odd_kernel_size(
        kernel_size,
        "kernel_size"
    )

    blurred = cv2.GaussianBlur(
        image,
        (kernel_size, kernel_size),
        0
    )

    return cv2.addWeighted(
        image,
        1.0 + float(amount),
        blurred,
        -float(amount),
        0
    )


def global_threshold(
    image,
    threshold=127
):
    gray = _to_gray(image)

    if not isinstance(threshold, (int, float)):
        raise ValueError("threshold must be numeric.")

    if threshold < 0 or threshold > 255:
        raise ValueError(
            "threshold must be between 0 and 255."
        )

    _, result = cv2.threshold(
        gray,
        float(threshold),
        255,
        cv2.THRESH_BINARY
    )

    return result


def otsu_threshold(image):
    gray = _to_gray(image)

    _, result = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    return result


def adaptive_threshold(
    image,
    block_size=35,
    c=11
):
    gray = _to_gray(image)

    _validate_odd_kernel_size(
        block_size,
        "block_size"
    )

    if not isinstance(c, (int, float)):
        raise ValueError("c must be numeric.")

    return cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        float(c)
    )


def morphological_opening(
    image,
    kernel_size=3
):
    gray = _to_gray(image)

    _validate_odd_kernel_size(
        kernel_size,
        "kernel_size"
    )

    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (kernel_size, kernel_size)
    )

    return cv2.morphologyEx(
        gray,
        cv2.MORPH_OPEN,
        kernel
    )


def morphological_closing(
    image,
    kernel_size=3
):
    gray = _to_gray(image)

    _validate_odd_kernel_size(
        kernel_size,
        "kernel_size"
    )

    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (kernel_size, kernel_size)
    )

    return cv2.morphologyEx(
        gray,
        cv2.MORPH_CLOSE,
        kernel
    )


OPERATIONS = {
    "clahe": {
        "function": clahe,
        "name": "CLAHE",
        "category": "contrast",
        "purpose": "تحسين التباين المحلي",
        "description": "يحسن التباين في المناطق المحلية مع الحد من التضخيم المفرط."
    },

    "histogram_equalization": {
        "function": histogram_equalization,
        "name": "Histogram Equalization",
        "category": "contrast",
        "purpose": "إعادة توزيع درجات السطوع",
        "description": "يعيد توزيع شدة الإضاءة عالميًا لزيادة التباين."
    },

    "median_denoise": {
        "function": median_denoise,
        "name": "Median Denoising",
        "category": "noise",
        "purpose": "تقليل بعض أنواع الضوضاء",
        "description": "يقلل التغيرات النقطية مع محافظة نسبية على الحواف."
    },

    "sharpen": {
        "function": sharpen,
        "name": "Sharpen",
        "category": "detail",
        "purpose": "تعزيز وضوح التفاصيل",
        "description": "يعزز التفاصيل باستخدام Unsharp Masking بدرجة قابلة للتحكم."
    },

    "global_threshold": {
        "function": global_threshold,
        "name": "Global Threshold",
        "category": "text_separation",
        "purpose": "فصل المناطق الداكنة والفاتحة",
        "description": "يحول الصورة إلى تمثيل ثنائي باستخدام عتبة ثابتة."
    },

    "otsu_threshold": {
        "function": otsu_threshold,
        "name": "Otsu Threshold",
        "category": "text_separation",
        "purpose": "اختيار عتبة ثنائية تلقائيًا",
        "description": "يستخدم طريقة Otsu لاختيار عتبة عالمية من توزيع الشدة."
    },

    "adaptive_threshold": {
        "function": adaptive_threshold,
        "name": "Adaptive Threshold",
        "category": "text_separation",
        "purpose": "فصل النص مع تغير الإضاءة",
        "description": "يحسب عتبات محلية للمناطق المختلفة بدل استخدام عتبة واحدة للصورة."
    },

    "morphological_opening": {
        "function": morphological_opening,
        "name": "Morphological Opening",
        "category": "structure",
        "purpose": "إزالة تفاصيل صغيرة من البنية",
        "description": "عملية بنيوية يجب استخدامها بحذر لأنها قد تزيل تفاصيل دقيقة."
    },

    "morphological_closing": {
        "function": morphological_closing,
        "name": "Morphological Closing",
        "category": "structure",
        "purpose": "سد فجوات بنيوية صغيرة",
        "description": "عملية بنيوية قد تربط تفاصيل متجاورة ولذلك تحتاج تقييمًا محافظًا."
    }
}


def get_operation(operation_id):
    if not isinstance(operation_id, str):
        raise ValueError(
            "operation_id must be a string."
        )

    operation = OPERATIONS.get(operation_id)

    if operation is None:
        raise ValueError(
            f"Unknown operation: {operation_id}"
        )

    return operation


def list_operations():
    return [
        {
            "id": operation_id,
            "name": data["name"],
            "category": data["category"],
            "purpose": data["purpose"],
            "description": data["description"]
        }
        for operation_id, data in OPERATIONS.items()
    ]


def apply_operation(
    operation_id,
    image,
    params=None
):
    operation = get_operation(operation_id)

    if params is None:
        params = {}

    if not isinstance(params, dict):
        raise ValueError(
            "params must be a dictionary."
        )

    return operation["function"](
        image,
        **params
    )

