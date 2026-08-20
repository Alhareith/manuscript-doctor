import argparse
import os
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.document_boundary import detect_document_boundary
from processing.document_rectification import rectify_document
from processing.skew_detector import detect_skew


OUTPUT_DIR = Path("evaluation/output/known_skew")


def rotate_for_test(image, angle):
    height, width = image.shape[:2]
    center = (width / 2.0, height / 2.0)

    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

    if image.ndim == 2:
        border_value = 255
    else:
        border_value = (255, 255, 255)

    return cv2.warpAffine(
        image,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border_value
    )


def main():
    parser = argparse.ArgumentParser(description="Validate skew detection using a known rotation on a real document.")
    parser.add_argument("image", help="Path to the input document photo.")
    parser.add_argument("angle", type=float, help="Known test rotation angle in degrees.")
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
    print("Known Skew Validation")
    print("---------------------")
    print("boundary        :", boundary["detected"])

    if not boundary["detected"]:
        print("result          : skipped")
        print("reason          : boundary was not accepted")
        print()
        return

    rectified = rectify_document(image, boundary["corners"])
    rotated = rotate_for_test(rectified["image"], args.angle)
    skew = detect_skew(rotated)

    if not np.array_equal(image, original):
        raise RuntimeError("Validation modified the source image.")

    expected_angle = -args.angle
    error = abs(skew["angle"] - expected_angle)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = OUTPUT_DIR / f"{input_path.stem}_{args.angle:+.0f}_sk.jpg"

    if not cv2.imwrite(str(output_path), rotated):
        raise RuntimeError(f"Could not save: {output_path}")

    print("applied_angle   :", round(args.angle, 2))
    print("expected_angle  :", round(expected_angle, 2))
    print("detected_angle  :", skew["angle"])
    print("error           :", round(error, 2))
    print("confidence      :", skew["confidence"])
    print("line_count      :", skew["line_count"])
    print("dispersion      :", skew["dispersion"])
    print("reason          :", skew["reason"])
    print("preview         :", output_path)
    print()


if __name__ == "__main__":
    main()