import cv2
import numpy as np
from numpy.strings import center

from .common import _apply_to_luminance, _validate_image

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

def sharpen(image, amount=0.5, sigma=1.0):
    _validate_image(image)

    if not isinstance(amount, (int, float)):
        raise ValueError("amount must be numeric.")

    if amount < 0 or amount > 2:
        raise ValueError("amount must be between 0 and 2.")

    if not isinstance(sigma, (int, float)):
        raise ValueError("sigma must be numeric.")

    if sigma <= 0 or sigma > 5:
        raise ValueError("sigma must be greater than 0 and at most 5.")

    blurred = cv2.GaussianBlur(image, (0, 0), sigmaX=float(sigma), sigmaY=float(sigma))

    return cv2.addWeighted(image, 1.0 + float(amount), blurred, -float(amount), 0)

