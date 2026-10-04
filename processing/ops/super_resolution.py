"""Conservative single-image super-resolution for document previews.

This module intentionally avoids hallucinating missing characters. It enlarges the
source with Lanczos interpolation and applies a restrained luminance-only unsharp
mask so small text can become easier to inspect without changing its colors.
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


def super_resolution(image, scale=2, amount=0.35, sigma=1.0):
    """Enlarge a document image and recover readable edge contrast conservatively.

    This is a deterministic OpenCV fallback: it does not invent character strokes.
    ``scale`` is limited to 2x/3x and the output pixel count is bounded to keep the
    Flask process safe for large uploads.
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

    def sharpen_luminance(channel):
        blurred = cv2.GaussianBlur(
            channel,
            (0, 0),
            sigmaX=float(sigma),
            sigmaY=float(sigma),
        )
        return cv2.addWeighted(
            channel,
            1.0 + float(amount),
            blurred,
            -float(amount),
            0,
        )

    return _apply_to_luminance(upscaled, sharpen_luminance)
