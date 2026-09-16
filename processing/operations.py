"""Stable public compatibility surface for the original processing.operations module."""

from .ops.common import _apply_to_luminance, _to_gray, _validate_image, _validate_odd_kernel_size
from .ops.enhancement import clahe, gamma_correct, histogram_equalization, illumination_normalize, intensity_adjust, sharpen
from .ops.denoising import bilateral_denoise, median_denoise, non_local_means_denoise
from .ops.thresholding import adaptive_threshold, global_threshold, otsu_threshold
from .ops.morphology import (
    dilation,
    erosion,
    morphological_black_hat,
    morphological_closing,
    morphological_gradient,
    morphological_opening,
    morphological_top_hat,
)
from .ops.course_ops import contrast_stretch, gaussian_blur, laplacian_sharpen, log_transform, sobel_edges
from .ops.document import background_suppress, faded_text_enhance, weak_structure_suppress
from .ops.geometry import crop, deskew, flip_horizontal, flip_vertical, rotate_left, rotate_right
from .ops.super_resolution import super_resolution
from .ops.registry import OPERATIONS, apply_operation, get_operation, list_operations


# Course operations are deliberately registered here as manual-only additions.
# Keeping this overlay outside registry.py avoids disturbing the proven production registry
# and keeps the smart pipeline unchanged.
OPERATIONS.update(
    {
        "erosion": {
            "function": erosion,
            "name": "Erosion",
            "category": "morphology",
            "purpose": "تقليص المناطق الفاتحة وإزالة النقاط الرقيقة",
            "description": "تآكل بنيوي قياسي على الصورة الرمادية بنواة مستطيلة.",
            "risk": "high",
            "automatic": False,
            "default_parameters": {"kernel_size": 3, "iterations": 1},
        },
        "dilation": {
            "function": dilation,
            "name": "Dilation",
            "category": "morphology",
            "purpose": "توسيع المناطق الفاتحة وسد الفجوات الرقيقة",
            "description": "توسيع بنيوي قياسي على الصورة الرمادية بنواة مستطيلة.",
            "risk": "high",
            "automatic": False,
            "default_parameters": {"kernel_size": 3, "iterations": 1},
        },
        "morphological_gradient": {
            "function": morphological_gradient,
            "name": "Morphological Gradient",
            "category": "morphology",
            "purpose": "إبراز حدود البنى بالتوسيع ناقص التآكل",
            "description": "التعريف القياسي للتدرج المورفولوجي كمخرج مرئي للحدود.",
            "risk": "high",
            "automatic": False,
            "default_parameters": {"kernel_size": 3},
        },
        "gaussian_blur": {
            "function": gaussian_blur,
            "name": "Gaussian Blur",
            "category": "noise",
            "purpose": "تمهيد غاوسي يخفف الضوضاء الناعمة",
            "description": "ترشيح مكاني غاوسي قياسي مع سيجما قابلة للضبط.",
            "risk": "medium",
            "automatic": False,
            "default_parameters": {"kernel_size": 5, "sigma": 0.0},
        },
        "laplacian_sharpen": {
            "function": laplacian_sharpen,
            "name": "Laplacian Sharpen",
            "category": "detail",
            "purpose": "تعزيز التفاصيل بالمشتقة الثانية",
            "description": "حدّة لابلاسيان محافظة على قناة الإضاءة.",
            "risk": "medium",
            "automatic": False,
            "default_parameters": {"amount": 0.5, "kernel_size": 3},
        },
        "sobel_edges": {
            "function": sobel_edges,
            "name": "Sobel Edges",
            "category": "detail",
            "purpose": "إظهار مقدار التدرج باستخدام سوبل",
            "description": "خريطة حواف مرئية مبنية على مركبتي التدرج Gx وGy.",
            "risk": "high",
            "automatic": False,
            "default_parameters": {"kernel_size": 3},
        },
        "contrast_stretch": {
            "function": contrast_stretch,
            "name": "Contrast Stretch",
            "category": "contrast",
            "purpose": "تمدد تباين خطي مئيني إلى النطاق الكامل",
            "description": "يمدد المجال بين المئينين المحددين خطيًا إلى 0..255.",
            "risk": "low",
            "automatic": False,
            "default_parameters": {"low_percentile": 2, "high_percentile": 98},
        },
        "log_transform": {
            "function": log_transform,
            "name": "Log Transform",
            "category": "exposure",
            "purpose": "إظهار تفاصيل الظلال بتحويل لوغاريتمي",
            "description": "تحويل لوغاريتمي مطبّع مع معامل شدة يدوي.",
            "risk": "low",
            "automatic": False,
            "default_parameters": {"strength": 1.0},
        },
    }
)


__all__ = [
    "OPERATIONS", "apply_operation", "get_operation", "list_operations",
    "clahe", "histogram_equalization", "median_denoise", "sharpen",
    "global_threshold", "otsu_threshold", "adaptive_threshold",
    "morphological_opening", "morphological_closing", "bilateral_denoise",
    "non_local_means_denoise", "illumination_normalize", "gamma_correct",
    "intensity_adjust", "faded_text_enhance", "background_suppress",
    "weak_structure_suppress", "morphological_top_hat", "morphological_black_hat",
    "erosion", "dilation", "morphological_gradient", "gaussian_blur",
    "laplacian_sharpen", "sobel_edges", "contrast_stretch", "log_transform",
    "deskew", "crop", "rotate_right", "rotate_left", "flip_vertical", "flip_horizontal",
    "super_resolution",
]
