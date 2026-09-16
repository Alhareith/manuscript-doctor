"""Core course image-processing operations kept separate from the production smart pipeline.

These operations are manual-only. They validate inputs, preserve alpha where appropriate,
and use the project's luminance helpers for colour documents.
"""

import cv2
import numpy as np

from .common import _apply_to_luminance, _to_gray, _validate_image, _validate_odd_kernel_size


def gaussian_blur(image, kernel_size=5, sigma=0.0):
    """Apply standard Gaussian smoothing."""
    _validate_image(image)
    _validate_odd_kernel_size(kernel_size, "kernel_size")

    if not isinstance(sigma, (int, float)) or sigma < 0:
        raise ValueError("sigma must be a non-negative number.")

    sigma = float(sigma)

    if image.ndim == 3 and image.shape[2] == 4:
        alpha = image[:, :, 3]
        smoothed = cv2.GaussianBlur(image[:, :, :3], (kernel_size, kernel_size), sigma)
        return np.dstack((smoothed, alpha))

    return cv2.GaussianBlur(image, (kernel_size, kernel_size), sigma)


def laplacian_sharpen(image, amount=0.5, kernel_size=3):
    """Sharpen luminance using the magnitude of the Laplacian response."""
    _validate_image(image)

    if not isinstance(amount, (int, float)) or amount < 0:
        raise ValueError("amount must be a non-negative number.")

    if kernel_size not in (1, 3, 5, 7):
        raise ValueError("kernel_size must be one of 1, 3, 5, 7.")

    amount = float(amount)

    def _sharpen(gray):
        laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=kernel_size)
        boosted = gray.astype(np.float64) + amount * np.abs(laplacian)
        return np.clip(boosted, 0, 255).astype(np.uint8)

    return _apply_to_luminance(image, _sharpen)


def sobel_edges(image, kernel_size=3):
    """Return a normalized Sobel gradient-magnitude map."""
    _validate_image(image)

    if kernel_size not in (1, 3, 5, 7):
        raise ValueError("kernel_size must be one of 1, 3, 5, 7.")

    gray = _to_gray(image)
    grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=kernel_size)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=kernel_size)
    magnitude = cv2.magnitude(grad_x, grad_y)

    maximum = float(magnitude.max())
    if maximum > 0:
        magnitude = magnitude * (255.0 / maximum)

    return magnitude.astype(np.uint8)


def contrast_stretch(image, low_percentile=2, high_percentile=98):
    """Linearly stretch the selected percentile range to 0..255."""
    _validate_image(image)

    for name, value in (("low_percentile", low_percentile), ("high_percentile", high_percentile)):
        if not isinstance(value, (int, float)) or not 0 <= value <= 100:
            raise ValueError(f"{name} must be between 0 and 100.")

    if float(low_percentile) >= float(high_percentile):
        raise ValueError("low_percentile must be smaller than high_percentile.")

    def _stretch(gray):
        low, high = np.percentile(gray, [float(low_percentile), float(high_percentile)])
        if high - low < 1e-6:
            return gray.copy()
        stretched = (gray.astype(np.float64) - low) * (255.0 / (high - low))
        return np.clip(stretched, 0, 255).astype(np.uint8)

    return _apply_to_luminance(image, _stretch)


def log_transform(image, strength=1.0):
    """Apply a normalized logarithmic intensity transform."""
    _validate_image(image)

    if not isinstance(strength, (int, float)) or strength <= 0:
        raise ValueError("strength must be a positive number.")

    strength = float(strength)

    def _log_map(gray):
        logged = np.log1p(gray.astype(np.float64))
        maximum = float(logged.max())
        if maximum < 1e-6:
            return gray.copy()
        scaled = (logged / maximum) * 255.0 * strength
        return np.clip(scaled, 0, 255).astype(np.uint8)

    return _apply_to_luminance(image, _log_map)
