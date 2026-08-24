import cv2
import numpy as np
from numpy.strings import center

from .common import _apply_to_luminance, _to_gray, _validate_image, _validate_odd_kernel_size
from .enhancement import clahe, gamma_correct, histogram_equalization, illumination_normalize, intensity_adjust, sharpen
from .denoising import bilateral_denoise, median_denoise, non_local_means_denoise
from .thresholding import adaptive_threshold, global_threshold, otsu_threshold
from .morphology import morphological_closing, morphological_opening, morphological_black_hat, morphological_top_hat
from .document import background_suppress, faded_text_enhance, weak_structure_suppress
from .geometry import crop, deskew, flip_horizontal, flip_vertical, rotate_left, rotate_right
from .super_resolution import super_resolution

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
        "purpose": "زيادة وضوح التفاصيل",
        "description": "يعزز التفاصيل باستخدام Unsharp Masking بدرجة قابلة للتحكم.",
    },
    "super_resolution": {
        "function": super_resolution,
        "name": "Super Resolution",
        "category": "detail",
        "purpose": "تكبير الصورة وتحسين قابلية قراءة النص",
        "description": "يكبر الصورة بتدخل Lanczos ثم يطبق Unsharp Masking محافظاً على luminance دون اختلاق حروف مفقودة.",
        "risk": "medium-high",
        "automatic": False,
        "default_parameters": {"scale": 2, "amount": 0.35, "sigma": 1.0},
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
    "crop": {
        "function": crop,
        "name": "Document Crop",
        "category": "geometry",
        "purpose": "اقتصاص جزء محدد من الوثيقة مع الحفاظ على البكسلات داخل الإطار.",
        "description": "يقتص مستطيلاً يحدده المستخدم يدوياً بعد مراجعته في المعاينة.",
        "risk": "medium",
        "automatic": False,
        "default_parameters": {"x": 0, "y": 0, "width": 1, "height": 1},
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
    "rotate_right": {
        "function": rotate_right,
        "name": "Rotate Right",
        "category": "orientation",
        "purpose": "Rotate the document 90 degrees clockwise.",
        "description": "Turns the document to the right while preserving all pixels.",
        "risk": "low",
        "automatic": False,
        "default_parameters": {},
    },
    "rotate_left": {
        "function": rotate_left,
        "name": "Rotate Left",
        "category": "orientation",
        "purpose": "Rotate the document 90 degrees counter-clockwise.",
        "description": "Turns the document to the left while preserving all pixels.",
        "risk": "low",
        "automatic": False,
        "default_parameters": {},
    },
    "flip_vertical": {
        "function": flip_vertical,
        "name": "Flip Vertical",
        "category": "orientation",
        "purpose": "Flip the document along the horizontal axis.",
        "description": "Mirrors the document from top to bottom.",
        "risk": "low",
        "automatic": False,
        "default_parameters": {},
    },
    "flip_horizontal": {
        "function": flip_horizontal,
        "name": "Flip Horizontal",
        "category": "orientation",
        "purpose": "Flip the document along the vertical axis.",
        "description": "Mirrors the document from right to left.",
        "risk": "low",
        "automatic": False,
        "default_parameters": {},
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

