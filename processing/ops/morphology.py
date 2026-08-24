import cv2
import numpy as np
from numpy.strings import center

from .common import _to_gray, _validate_image, _validate_odd_kernel_size

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

