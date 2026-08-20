import argparse
import os
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.auto_deskew import apply_auto_deskew
from processing.document_boundary import detect_document_boundary
from processing.document_rectification import rectify_document
from processing.skew_detector import detect_skew


OUTPUT_DIR = Path("evaluation/output/auto_deskew")


def rotate_for_test(image, angle):
    height, width = image.shape[:2]
    center = (width / 2.0, height / 2.0)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

    if image.ndim == 2:
        border_value = 255
    else:
        border_value = (255, 255, 255)

    return cv2.warpAffine(image, matrix, (width, height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=border_value)


def main():
    parser = argparse.ArgumentParser(description="Validate automatic deskew application on a real document.")
    parser.add_argument("image", help="Path to the input document photo.")
    parser.add_argument("test_angle", type=float, help="Known rotation applied only for validation.")
    args = parser.parse_args()

    input_path = Path(args.image)

    if not input_path.is_file():
        raise FileNotFoundError(f"Input image not found: {input_path}")

    image = cv2.imread(str(input_path), cv2.IMREAD_COLOR)

    if image is None:
        raise RuntimeError(f"OpenCV could not decode: {input_path}")

    original = image.copy()
    boundary = detect_document_boundary(image)

    print()
    print("Auto Deskew Application")
    print("-----------------------")
    print("boundary          :", boundary["detected"])

    if not boundary["detected"]:
        print("result            : skipped")
        print("reason            : boundary was not accepted")
        print()
        return

    rectified = rectify_document(image, boundary["corners"])
    tilted = rotate_for_test(rectified["image"], args.test_angle)

    before = detect_skew(tilted)
    correction = apply_auto_deskew(tilted, before)
    after = detect_skew(correction["image"])

    if not np.array_equal(image, original):
        raise RuntimeError("Validation modified the original image.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    tilted_path = OUTPUT_DIR / f"{input_path.stem}_before.jpg"
    corrected_path = OUTPUT_DIR / f"{input_path.stem}_after.jpg"

    if not cv2.imwrite(str(tilted_path), tilted):
        raise RuntimeError(f"Could not save: {tilted_path}")

    if not cv2.imwrite(str(corrected_path), correction["image"]):
        raise RuntimeError(f"Could not save: {corrected_path}")

    print("test_angle        :", round(args.test_angle, 2))
    print("detected_before   :", before["angle"])
    print("confidence_before :", before["confidence"])
    print("line_count        :", before["line_count"])
    print("dispersion_before :", before["dispersion"])
    print("applied           :", correction["applied"])
    print("correction_angle  :", correction["angle"])
    print("detected_after    :", after["angle"])
    print("confidence_after  :", after["confidence"])
    print("dispersion_after  :", after["dispersion"])
    print("before_preview    :", tilted_path)
    print("after_preview     :", corrected_path)
    print()


if __name__ == "__main__":
    main()