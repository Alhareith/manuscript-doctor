import cv2
import numpy as np

MIN_OUTPUT_SIDE = 40
MIN_QUAD_AREA_RATIO = 0.01


def _validate_image(image):
    if image is None or not isinstance(image, np.ndarray):
        raise ValueError("Image must be a valid NumPy array.")

    if image.size == 0:
        raise ValueError("Image cannot be empty.")

    if image.dtype != np.uint8:
        raise ValueError("Only 8-bit images are supported.")

    if image.ndim == 2:
        return

    if image.ndim != 3 or image.shape[2] not in {1, 3, 4}:
        raise ValueError("Unsupported image format.")


def _normalize_corners(corners):
    points = np.asarray(corners, dtype=np.float32)

    if points.shape != (4, 2):
        raise ValueError("corners must contain exactly four [x, y] points.")

    if not np.all(np.isfinite(points)):
        raise ValueError("corners contain invalid numeric values.")

    return points


def _validate_corners(corners, width, height):
    points = _normalize_corners(corners)

    if np.any(points[:, 0] < 0) or np.any(points[:, 0] > width - 1):
        raise ValueError("One or more corner x-coordinates are outside the image.")

    if np.any(points[:, 1] < 0) or np.any(points[:, 1] > height - 1):
        raise ValueError("One or more corner y-coordinates are outside the image.")

    contour = points.reshape(-1, 1, 2)

    if not cv2.isContourConvex(contour.astype(np.int32)):
        raise ValueError("Document corners must form a convex quadrilateral.")

    area = abs(float(cv2.contourArea(contour)))

    image_area = float(width * height)

    area_ratio = area / image_area

    if area_ratio < MIN_QUAD_AREA_RATIO:
        raise ValueError(
            "Document quadrilateral is too small for reliable rectification."
        )

    return points


def _calculate_output_size(corners):
    top_left, top_right, bottom_right, bottom_left = corners

    top_width = float(np.linalg.norm(top_right - top_left))

    bottom_width = float(np.linalg.norm(bottom_right - bottom_left))

    left_height = float(np.linalg.norm(bottom_left - top_left))

    right_height = float(np.linalg.norm(bottom_right - top_right))

    output_width = int(round(max(top_width, bottom_width)))

    output_height = int(round(max(left_height, right_height)))

    if output_width < MIN_OUTPUT_SIDE or output_height < MIN_OUTPUT_SIDE:
        raise ValueError("Calculated rectified image size is too small.")

    return (output_width, output_height)


def rectify_document(image, corners):
    _validate_image(image)

    height, width = image.shape[:2]

    source = _validate_corners(corners, width, height)

    output_width, output_height = _calculate_output_size(source)

    destination = np.array(
        [
            [0, 0],
            [output_width - 1, 0],
            [output_width - 1, output_height - 1],
            [0, output_height - 1],
        ],
        dtype=np.float32,
    )

    transform = cv2.getPerspectiveTransform(source, destination)

    if (
        transform is None
        or transform.shape != (3, 3)
        or not np.all(np.isfinite(transform))
    ):
        raise ValueError("Could not calculate a valid perspective transform.")

    rectified = cv2.warpPerspective(
        image,
        transform,
        (output_width, output_height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )

    if rectified is None or rectified.size == 0:
        raise RuntimeError("Perspective rectification produced an empty image.")

    return {
        "image": rectified,
        "width": int(output_width),
        "height": int(output_height),
        "source_corners": [[int(round(x)), int(round(y))] for x, y in source],
        "transform": transform.copy(),
    }
