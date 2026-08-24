import cv2
import numpy as np
from numpy.strings import center

from .common import _to_gray, _validate_image, _validate_odd_kernel_size

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

