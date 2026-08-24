import cv2
import numpy as np
from numpy.strings import center

from .common import _validate_image
from .enhancement import clahe, gamma_correct

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

        corrected = source - difference * strength

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

