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

