"""Stable public compatibility surface for the original processing.operations module."""

from .ops.common import _apply_to_luminance, _to_gray, _validate_image, _validate_odd_kernel_size
from .ops.enhancement import clahe, gamma_correct, histogram_equalization, illumination_normalize, intensity_adjust, sharpen
from .ops.denoising import bilateral_denoise, median_denoise, non_local_means_denoise
from .ops.thresholding import adaptive_threshold, global_threshold, otsu_threshold
from .ops.morphology import morphological_closing, morphological_opening, morphological_black_hat, morphological_top_hat
from .ops.document import background_suppress, faded_text_enhance, weak_structure_suppress
from .ops.geometry import crop, deskew, flip_horizontal, flip_vertical, rotate_left, rotate_right
from .ops.super_resolution import super_resolution
from .ops.registry import OPERATIONS, apply_operation, get_operation, list_operations

__all__ = [
    "OPERATIONS", "apply_operation", "get_operation", "list_operations",
    "clahe", "histogram_equalization", "median_denoise", "sharpen",
    "global_threshold", "otsu_threshold", "adaptive_threshold",
    "morphological_opening", "morphological_closing", "bilateral_denoise",
    "non_local_means_denoise", "illumination_normalize", "gamma_correct",
    "intensity_adjust", "faded_text_enhance", "background_suppress",
    "weak_structure_suppress", "morphological_top_hat", "morphological_black_hat",
    "deskew", "crop", "rotate_right", "rotate_left", "flip_vertical", "flip_horizontal",
    "super_resolution",
]
