import cv2
import numpy as np
from numpy.strings import center


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
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)


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
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

        lightness, a, b = cv2.split(lab)

        processed_lightness = operation(lightness)

        processed_lab = cv2.merge((processed_lightness, a, b))

        return cv2.cvtColor(processed_lab, cv2.COLOR_LAB2BGR)

    alpha = image[:, :, 3].copy()
    bgr = image[:, :, :3]

    processed_bgr = _apply_to_luminance(bgr, operation)

    return np.dstack((processed_bgr, alpha))


def clahe(image, clip_limit=1.5, tile_grid_size=8):
    _validate_image(image)

    if not isinstance(clip_limit, (int, float)):
        raise ValueError("clip_limit must be numeric.")

    if clip_limit <= 0:
        raise ValueError("clip_limit must be greater than 0.")

    if not isinstance(tile_grid_size, int):
        raise ValueError("tile_grid_size must be an integer.")

    if tile_grid_size < 2:
        raise ValueError("tile_grid_size must be at least 2.")

    clahe_filter = cv2.createCLAHE(
        clipLimit=float(clip_limit), tileGridSize=(tile_grid_size, tile_grid_size)
    )

    return _apply_to_luminance(image, clahe_filter.apply)


def histogram_equalization(image):
    _validate_image(image)

    return _apply_to_luminance(image, cv2.equalizeHist)


def median_denoise(image, kernel_size=3):
    _validate_image(image)

    _validate_odd_kernel_size(kernel_size, "kernel_size")

    return cv2.medianBlur(image, kernel_size)


def sharpen(image, amount=0.25, kernel_size=3):
    _validate_image(image)

    if not isinstance(amount, (int, float)):
        raise ValueError("amount must be numeric.")

    if amount < 0 or amount > 2:
        raise ValueError("amount must be between 0 and 2.")

    _validate_odd_kernel_size(kernel_size, "kernel_size")

    blurred = cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)

    return cv2.addWeighted(image, 1.0 + float(amount), blurred, -float(amount), 0)


def global_threshold(image, threshold=127):
    gray = _to_gray(image)

    if not isinstance(threshold, (int, float)):
        raise ValueError("threshold must be numeric.")

    if threshold < 0 or threshold > 255:
        raise ValueError("threshold must be between 0 and 255.")

    _, result = cv2.threshold(gray, float(threshold), 255, cv2.THRESH_BINARY)

    return result


def otsu_threshold(image):
    gray = _to_gray(image)

    _, result = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return result


def adaptive_threshold(image, block_size=35, c=11):
    gray = _to_gray(image)

    _validate_odd_kernel_size(block_size, "block_size")

    if not isinstance(c, (int, float)):
        raise ValueError("c must be numeric.")

    return cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        float(c),
    )


def morphological_opening(image, kernel_size=3):
    gray = _to_gray(image)

    _validate_odd_kernel_size(kernel_size, "kernel_size")

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))

    return cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)


def morphological_closing(image, kernel_size=3):
    gray = _to_gray(image)

    _validate_odd_kernel_size(kernel_size, "kernel_size")

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))

    return cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)


def bilateral_denoise(image, diameter=5, sigma_color=25, sigma_space=25):
    _validate_image(image)

    if diameter <= 0:
        raise ValueError("diameter must be greater than 0.")

    if sigma_color <= 0:
        raise ValueError("sigma_color must be greater than 0.")

    if sigma_space <= 0:
        raise ValueError("sigma_space must be greater than 0.")

    if image.ndim == 2:
        return cv2.bilateralFilter(image, diameter, sigma_color, sigma_space)

    if image.shape[2] == 3:
        return cv2.bilateralFilter(image, diameter, sigma_color, sigma_space)

    if image.shape[2] == 4:
        bgr = image[:, :, :3]
        alpha = image[:, :, 3]

        filtered = cv2.bilateralFilter(bgr, diameter, sigma_color, sigma_space)

        return np.dstack((filtered, alpha))

    raise ValueError("Unsupported image format.")


def non_local_means_denoise(
    image, strength=5, template_window_size=7, search_window_size=21
):
    _validate_image(image)

    if strength <= 0:
        raise ValueError("strength must be greater than 0.")

    if template_window_size < 3 or template_window_size % 2 == 0:
        raise ValueError("template_window_size must be odd and >= 3.")

    if search_window_size < 3 or search_window_size % 2 == 0:
        raise ValueError("search_window_size must be odd and >= 3.")

    if image.ndim == 2:
        return cv2.fastNlMeansDenoising(
            image, None, float(strength), template_window_size, search_window_size
        )

    if image.shape[2] == 3:
        return cv2.fastNlMeansDenoisingColored(
            image,
            None,
            float(strength),
            float(strength),
            template_window_size,
            search_window_size,
        )

    if image.shape[2] == 4:
        bgr = image[:, :, :3]
        alpha = image[:, :, 3]

        filtered = cv2.fastNlMeansDenoisingColored(
            bgr,
            None,
            float(strength),
            float(strength),
            template_window_size,
            search_window_size,
        )

        return np.dstack((filtered, alpha))

    raise ValueError("Unsupported image format.")


def illumination_normalize(image, kernel_size=51, strength=0.65):
    _validate_image(image)

    if kernel_size < 15 or kernel_size % 2 == 0:
        raise ValueError("kernel_size must be odd and >= 15.")

    if not 0 < strength <= 1:
        raise ValueError("strength must be > 0 and <= 1.")

    def normalize_channel(channel):
        source = channel.astype(np.float32)

        background = cv2.GaussianBlur(source, (kernel_size, kernel_size), 0)

        background_mean = float(np.mean(background))

        background = np.maximum(background, 1.0)

        corrected = source / background * background_mean

        corrected = np.clip(corrected, 0, 255)

        blended = source * (1.0 - strength) + corrected * strength

        return np.clip(blended, 0, 255).astype(np.uint8)

    if image.ndim == 2:
        return normalize_channel(image)

    if image.shape[2] == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

        l_channel, a_channel, b_channel = cv2.split(lab)

        normalized_l = normalize_channel(l_channel)

        result_lab = cv2.merge((normalized_l, a_channel, b_channel))

        return cv2.cvtColor(result_lab, cv2.COLOR_LAB2BGR)

    if image.shape[2] == 4:
        bgr = image[:, :, :3]
        alpha = image[:, :, 3]

        normalized_bgr = illumination_normalize(
            bgr, kernel_size=kernel_size, strength=strength
        )

        return np.dstack((normalized_bgr, alpha))

    raise ValueError("Unsupported image format.")


def gamma_correct(image, gamma=1.0):
    _validate_image(image)

    if gamma <= 0:
        raise ValueError("gamma must be greater than 0.")

    inverse_gamma = gamma

    table = np.array(
        [((i / 255.0) ** inverse_gamma) * 255 for i in range(256)], dtype=np.uint8
    )

    if image.ndim == 2:
        return cv2.LUT(image, table)

    if image.shape[2] == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

        l_channel, a_channel, b_channel = cv2.split(lab)

        corrected_l = cv2.LUT(l_channel, table)

        corrected_lab = cv2.merge((corrected_l, a_channel, b_channel))

        return cv2.cvtColor(corrected_lab, cv2.COLOR_LAB2BGR)

    if image.shape[2] == 4:
        bgr = image[:, :, :3]
        alpha = image[:, :, 3]

        corrected = gamma_correct(bgr, gamma=gamma)

        return np.dstack((corrected, alpha))

    raise ValueError("Unsupported image format.")


def intensity_adjust(image, alpha=1.0, beta=0):
    _validate_image(image)

    if alpha <= 0:
        raise ValueError("alpha must be greater than 0.")

    if beta < -100 or beta > 100:
        raise ValueError("beta must be between -100 and 100.")

    if image.ndim == 2:
        return cv2.convertScaleAbs(image, alpha=float(alpha), beta=float(beta))

    if image.shape[2] == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

        l_channel, a_channel, b_channel = cv2.split(lab)

        adjusted_l = cv2.convertScaleAbs(
            l_channel, alpha=float(alpha), beta=float(beta)
        )

        adjusted_lab = cv2.merge((adjusted_l, a_channel, b_channel))

        return cv2.cvtColor(adjusted_lab, cv2.COLOR_LAB2BGR)

    if image.shape[2] == 4:
        bgr = image[:, :, :3]
        alpha_channel = image[:, :, 3]

        adjusted = intensity_adjust(bgr, alpha=alpha, beta=beta)

        return np.dstack((adjusted, alpha_channel))


def faded_text_enhance(image, clip_limit=1.4, gamma=0.95):
    _validate_image(image)

    if clip_limit <= 0:
        raise ValueError("clip_limit must be greater than 0.")

    if gamma <= 0:
        raise ValueError("gamma must be greater than 0.")

    corrected = gamma_correct(image, gamma=gamma)

    return clahe(corrected, clip_limit=clip_limit, tile_grid_size=8)

    raise ValueError("Unsupported image format.")


def background_suppress(image, kernel_size=31, strength=0.45):
    _validate_image(image)

    if kernel_size < 15 or kernel_size % 2 == 0:
        raise ValueError("kernel_size must be odd and >= 15.")

    if not 0 < strength <= 1:
        raise ValueError("strength must be > 0 and <= 1.")

    def suppress_channel(channel):
        source = channel.astype(np.float32)

        background = cv2.GaussianBlur(source, (kernel_size, kernel_size), 0)

        difference = source - background

        corrected = source + difference * strength

        return np.clip(corrected, 0, 255).astype(np.uint8)

    if image.ndim == 2:
        return suppress_channel(image)

    if image.shape[2] == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

        l_channel, a_channel, b_channel = cv2.split(lab)

        corrected_l = suppress_channel(l_channel)

        corrected_lab = cv2.merge((corrected_l, a_channel, b_channel))

        return cv2.cvtColor(corrected_lab, cv2.COLOR_LAB2BGR)

    if image.shape[2] == 4:
        bgr = image[:, :, :3]
        alpha = image[:, :, 3]

        corrected = background_suppress(bgr, kernel_size=kernel_size, strength=strength)

        return np.dstack((corrected, alpha))

    raise ValueError("Unsupported image format.")


def weak_structure_suppress(image, kernel_size=31, threshold=12, strength=0.35):
    _validate_image(image)

    if kernel_size < 15 or kernel_size % 2 == 0:
        raise ValueError("kernel_size must be odd and >= 15.")

    if threshold <= 0:
        raise ValueError("threshold must be greater than 0.")

    if not 0 < strength <= 1:
        raise ValueError("strength must be > 0 and <= 1.")

    def suppress(channel):
        source = channel.astype(np.float32)

        background = cv2.GaussianBlur(source, (kernel_size, kernel_size), 0)

        residual = source - background

        weak_mask = (np.abs(residual) <= float(threshold)).astype(np.float32)

        corrected = source - residual * weak_mask * strength

        return np.clip(corrected, 0, 255).astype(np.uint8)

    if image.ndim == 2:
        return suppress(image)

    if image.shape[2] == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

        l_channel, a_channel, b_channel = cv2.split(lab)

        corrected_l = suppress(l_channel)

        corrected_lab = cv2.merge((corrected_l, a_channel, b_channel))

        return cv2.cvtColor(corrected_lab, cv2.COLOR_LAB2BGR)

    if image.shape[2] == 4:
        bgr = image[:, :, :3]
        alpha = image[:, :, 3]

        corrected = weak_structure_suppress(
            bgr, kernel_size=kernel_size, threshold=threshold, strength=strength
        )

        return np.dstack((corrected, alpha))

    raise ValueError("Unsupported image format.")


def morphological_top_hat(image, kernel_size=3):
    _validate_image(image)

    if kernel_size < 3 or kernel_size % 2 == 0:
        raise ValueError("kernel_size must be odd and >= 3.")

    gray = _to_gray(image)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))

    return cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)


def morphological_black_hat(image, kernel_size=5):
    _validate_image(image)

    if kernel_size < 3 or kernel_size % 2 == 0:
        raise ValueError("kernel_size must be odd and >= 3.")

    gray = _to_gray(image)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))

    return cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)


def deskew(image, angle):
    _validate_image(image)

    angle = float(angle)

    if abs(angle) > 45:
        raise ValueError("angle must be between -45 and 45 degrees.")

    h, w = image.shape[:2]
    # مركز الصورة الأصلية
    center = (w / 2.0, h / 2.0)

    # حساب مصفوفة الدوران
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

    # حساب الأبعاد الجديدة لتستوعب الصورة كاملة بعد الدوران
    cos_val = np.abs(matrix[0, 0])
    sin_val = np.abs(matrix[0, 1])

    new_w = int((h * sin_val) + (w * cos_val))
    new_h = int((h * cos_val) + (w * sin_val))

    # تعديل الإزاحة لتكون نقطة الدوران في مركز الصورة الجديد تماماً
    matrix[0, 2] += (new_w / 2.0) - center[0]
    matrix[1, 2] += (new_h / 2.0) - center[1]

    # تحديد لون الخلفية للفراغات الناتجة
    if image.ndim == 2:
        border_value = 255
    elif image.shape[2] == 3:
        border_value = (255, 255, 255)
    else:
        border_value = (255, 255, 255, 0)

    # تطبيق التحويل
    return cv2.warpAffine(
        image,
        matrix,
        (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border_value,
    )

OPERATIONS = {
    "clahe": {
        "function": clahe,
        "name": "CLAHE",
        "category": "contrast",
        "purpose": "تحسين التباين المحلي",
        "description": "يحسن التباين في المناطق المحلية مع الحد من التضخيم المفرط.",
    },
    "histogram_equalization": {
        "function": histogram_equalization,
        "name": "Histogram Equalization",
        "category": "contrast",
        "purpose": "إعادة توزيع درجات السطوع",
        "description": "يعيد توزيع شدة الإضاءة عالميًا لزيادة التباين.",
    },
    "median_denoise": {
        "function": median_denoise,
        "name": "Median Denoising",
        "category": "noise",
        "purpose": "تقليل بعض أنواع الضوضاء",
        "description": "يقلل التغيرات النقطية مع محافظة نسبية على الحواف.",
    },
    "sharpen": {
        "function": sharpen,
        "name": "Sharpen",
        "category": "detail",
        "purpose": "تعزيز وضوح التفاصيل",
        "description": "يعزز التفاصيل باستخدام Unsharp Masking بدرجة قابلة للتحكم.",
    },
    "global_threshold": {
        "function": global_threshold,
        "name": "Global Threshold",
        "category": "text_separation",
        "purpose": "فصل المناطق الداكنة والفاتحة",
        "description": "يحول الصورة إلى تمثيل ثنائي باستخدام عتبة ثابتة.",
    },
    "otsu_threshold": {
        "function": otsu_threshold,
        "name": "Otsu Threshold",
        "category": "text_separation",
        "purpose": "اختيار عتبة ثنائية تلقائيًا",
        "description": "يستخدم طريقة Otsu لاختيار عتبة عالمية من توزيع الشدة.",
    },
    "adaptive_threshold": {
        "function": adaptive_threshold,
        "name": "Adaptive Threshold",
        "category": "text_separation",
        "purpose": "فصل النص مع تغير الإضاءة",
        "description": "يحسب عتبات محلية للمناطق المختلفة بدل استخدام عتبة واحدة للصورة.",
    },
    "morphological_opening": {
        "function": morphological_opening,
        "name": "Morphological Opening",
        "category": "structure",
        "purpose": "إزالة تفاصيل صغيرة من البنية",
        "description": "عملية بنيوية يجب استخدامها بحذر لأنها قد تزيل تفاصيل دقيقة.",
    },
    "morphological_closing": {
        "function": morphological_closing,
        "name": "Morphological Closing",
        "category": "structure",
        "purpose": "سد فجوات بنيوية صغيرة",
        "description": "عملية بنيوية قد تربط تفاصيل متجاورة ولذلك تحتاج تقييمًا محافظًا.",
    },
    "bilateral_denoise": {
        "function": bilateral_denoise,
        "name": "Bilateral Denoising",
        "category": "denoising",
        "purpose": "Reduce noise while preserving important image edges.",
        "description": "Applies bilateral filtering to reduce noise while preserving edges.",
        "risk": "medium",
        "automatic": False,
        "default_parameters": {"diameter": 5, "sigma_color": 25, "sigma_space": 25},
    },
    "non_local_means_denoise": {
        "function": non_local_means_denoise,
        "name": "Non-Local Means Denoising",
        "category": "denoising",
        "purpose": "Reduce image noise while preserving fine image structures.",
        "description": "Uses Non-Local Means filtering to reduce noise while preserving similar local structures.",
        "risk": "medium",
        "automatic": False,
        "default_parameters": {
            "strength": 5,
            "template_window_size": 7,
            "search_window_size": 21,
        },
    },
    "illumination_normalize": {
        "function": illumination_normalize,
        "name": "Illumination Normalization",
        "category": "illumination",
        "purpose": "Reduce uneven spatial illumination across a document image.",
        "description": "Conservatively normalizes gradual brightness variations while preserving document structure.",
        "risk": "medium",
        "automatic": False,
        "default_parameters": {"kernel_size": 51, "strength": 0.65},
    },
    "gamma_correct": {
        "function": gamma_correct,
        "name": "Gamma Correction",
        "category": "exposure",
        "purpose": "Adjust image brightness using a gamma curve.",
        "description": "Applies gamma correction to adjust image brightness and contrast.",
        "risk": "low",
        "automatic": False,
        "default_parameters": {"gamma": 1.0},
    },
    "intensity_adjust": {
        "function": intensity_adjust,
        "name": "Intensity Adjustment",
        "category": "exposure",
        "purpose": "Adjust image brightness and contrast linearly.",
        "description": "Linearly adjusts image intensity using alpha (contrast) and beta (brightness) parameters.",
        "risk": "medium",
        "automatic": False,
        "default_parameters": {"alpha": 1.0, "beta": 0},
    },
    "faded_text_enhance": {
        "function": faded_text_enhance,
        "name": "Faded Text Enhancement",
        "category": "contrast",
        "purpose": "Enhance faded text in document images.",
        "description": "Applies gamma correction followed by CLAHE to enhance faded text while preserving overall image quality.",
        "risk": "medium",
        "automatic": False,
        "default_parameters": {"clip_limit": 1.4, "gamma": 0.95},
    },
    "background_suppress": {
        "function": background_suppress,
        "name": "Background Suppression",
        "category": "background",
        "purpose": "Suppress uneven background illumination in document images.",
        "description": "Reduces uneven background illumination while preserving text and important structures.",
        "risk": "medium-high",
        "automatic": False,
        "default_parameters": {"kernel_size": 31, "strength": 0.45},
    },
    "weak_structure_suppress": {
        "function": weak_structure_suppress,
        "name": "Weak Structure Suppression",
        "category": "background",
        "purpose": "Suppress weak structures in document images.",
        "description": "Reduces the visibility of weak structures while preserving important text and details.",
        "risk": "high",
        "automatic": False,
        "default_parameters": {"kernel_size": 31, "threshold": 12, "strength": 0.35},
    },
    "morphological_top_hat": {
        "function": morphological_top_hat,
        "name": "Morphological Top-hat",
        "category": "morphology",
        "purpose": "Extract small bright structures from a dark background.",
        "description": "Highlights small bright structures in the image using morphological top-hat transformation.",
        "risk": "high",
        "automatic": False,
        "default_parameters": {"kernel_size": 3},
    },
    "morphological_black_hat": {
        "function": morphological_black_hat,
        "name": "Morphological Black-hat",
        "category": "morphology",
        "purpose": "Extract small dark structures from a bright background.",
        "description": "Highlights small dark structures in the image using morphological black-hat transformation.",
        "risk": "high",
        "automatic": False,
        "default_parameters": {"kernel_size": 5},
    },
    "deskew": {
        "function": deskew,
        "name": "Deskew",
        "category": "alignment",
        "purpose": "Correct skew in document images.",
        "description": "Rotates the image to correct skew based on the provided angle.",
        "risk": "medium",
        "automatic": False,
        "default_parameters": {"angle": 0.0},
    },
}


def get_operation(operation_id):
    if not isinstance(operation_id, str):
        raise ValueError("operation_id must be a string.")

    operation = OPERATIONS.get(operation_id)

    if operation is None:
        raise ValueError(f"Unknown operation: {operation_id}")

    return operation


def list_operations():
    return [
        {
            "id": operation_id,
            "name": data["name"],
            "category": data["category"],
            "purpose": data["purpose"],
            "description": data["description"],
        }
        for operation_id, data in OPERATIONS.items()
    ]


def apply_operation(operation_id, image, params=None):
    operation = get_operation(operation_id)

    if params is None:
        params = {}

    if not isinstance(params, dict):
        raise ValueError("params must be a dictionary.")

    return operation["function"](image, **params)
