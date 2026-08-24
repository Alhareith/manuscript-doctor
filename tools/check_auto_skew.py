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


OUTPUT_DIR = Path("evaluation/output/auto_skew")


def main():
    parser = argparse.ArgumentParser(description="Check automatic skew detection after document rectification.")
    parser.add_argument("image", help="Path to the input document photo.")
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
    print("Auto Skew Detection")
    print("-------------------")
    print("boundary    :", boundary["detected"])
    print("confidence  :", boundary["confidence"])
    print("corners     :", boundary["corners"])

    if not boundary["detected"]:
        print("skew        : skipped")
        print("reason      : boundary was not accepted")
        print()
        return

    rectified = rectify_document(image, boundary["corners"])
    skew = detect_skew(rectified["image"])

    if not np.array_equal(image, original):
        raise RuntimeError("Preparation modified the source image.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = OUTPUT_DIR / f"{input_path.stem}_sk.jpg"

    if not cv2.imwrite(str(output_path), rectified["image"]):
        raise RuntimeError(f"Could not save: {output_path}")

    print("angle       :", skew["angle"])
    print("confidence  :", skew["confidence"])
    print("line_count  :", skew["line_count"])
    print("dispersion  :", skew["dispersion"])
    print("reason      :", skew["reason"])
    print("preview     :", output_path)
    print()


if __name__ == "__main__":
    main()
    