import cv2
import numpy as np
from numpy.strings import center

from .common import _apply_to_luminance, _to_gray, _validate_image, _validate_odd_kernel_size

def median_denoise(image, kernel_size=3):
    _validate_image(image)

    _validate_odd_kernel_size(kernel_size, "kernel_size")

    return cv2.medianBlur(image, kernel_size)

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

