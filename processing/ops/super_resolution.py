"""Deterministic document upscaling with conservative edge recovery.

This operation is intentionally not marketed as neural super-resolution. It
enlarges the existing pixels, improves local luminance contrast gently, and
recovers existing edge contrast without inventing missing character strokes.
"""

import cv2
import numpy as np

from .common import _apply_to_luminance, _validate_image

MAX_OUTPUT_PIXELS = 60_000_000


def _integer_scale(value):
    if isinstance(value, bool):
        raise ValueError("scale must be an integer of 2 or 3.")
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        raise ValueError("scale must be an integer of 2 or 3.") from None
    if not numeric.is_integer() or int(numeric) not in {2, 3}:
        raise ValueError("scale must be an integer of 2 or 3.")
    return int(numeric)


def _enhance_luminance(channel, amount, sigma):
    """Improve existing document detail while limiting artificial halos."""
    clahe = cv2.createCLAHE(clipLimit=1.35, tileGridSize=(8, 8))
    local = clahe.apply(channel)
    base = cv2.addWeighted(channel, 0.82, local, 0.18, 0)

    blurred = cv2.GaussianBlur(
        base,
        (0, 0),
        sigmaX=float(sigma),
        sigmaY=float(sigma),
    )

    base_f = base.astype(np.float32)
    high = base_f - blurred.astype(np.float32)
    high = np.clip(high, -24.0, 24.0)
    enhanced = base_f + (float(amount) * high)

    return np.clip(np.rint(enhanced), 0, 255).astype(np.uint8)


def super_resolution(image, scale=2, amount=0.45, sigma=0.9):
    """Upscale a document and improve readability of detail already present.

    Despite the historical operation id, this is a deterministic document
    upscaler, not an AI reconstruction model. It cannot recover character
    information that is absent from the source image.
    """
    _validate_image(image)
    scale = _integer_scale(scale)

    if not isinstance(amount, (int, float)) or isinstance(amount, bool):
        raise ValueError("amount must be numeric.")
    if not 0 <= float(amount) <= 1:
        raise ValueError("amount must be between 0 and 1.")

    if not isinstance(sigma, (int, float)) or isinstance(sigma, bool):
        raise ValueError("sigma must be numeric.")
    if not 0.5 <= float(sigma) <= 3:
        raise ValueError("sigma must be between 0.5 and 3.")

    height, width = image.shape[:2]
    output_pixels = int(height) * int(width) * scale * scale
    if output_pixels > MAX_OUTPUT_PIXELS:
        raise ValueError(
            f"scaled image exceeds the safe limit of {MAX_OUTPUT_PIXELS} pixels."
        )

    output_size = (int(width) * scale, int(height) * scale)
    upscaled = cv2.resize(image, output_size, interpolation=cv2.INTER_LANCZOS4)

    return _apply_to_luminance(
        upscaled,
        lambda channel: _enhance_luminance(channel, amount, sigma),
    )
