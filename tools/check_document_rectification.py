import argparse
import os
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.document_boundary import detect_document_boundary
from processing.document_rectification import rectify_document


OUTPUT_DIR = Path("evaluation/output/document_rectification")


def main():
    parser = argparse.ArgumentParser(description="Detect and rectify a document without modifying the pipeline.")
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
    print("Document Rectification Check")
    print("----------------------------")
    print("detected   :", boundary["detected"])
    print("confidence :", boundary["confidence"])
    print("area_ratio :", boundary["area_ratio"])
    print("corners    :", boundary["corners"])
    print("reason     :", boundary["reason"])

    if not np.array_equal(image, original):
        raise RuntimeError("Boundary detection modified the source image.")

    if not boundary["detected"]:
        print("rectified  : False")
        print("reason     : stopped safely because the boundary was not accepted")
        print()
        return

    if len(boundary["corners"]) != 4:
        raise RuntimeError("Accepted boundary does not contain exactly four corners.")

    result = rectify_document(image, boundary["corners"])

    if not np.array_equal(image, original):
        raise RuntimeError("Rectification modified the source image.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = OUTPUT_DIR / f"{input_path.stem}_pr.jpg"

    if not cv2.imwrite(str(output_path), result["image"]):
        raise RuntimeError(f"Could not save: {output_path}")

    print("rectified  : True")
    print("size       :", f'{result["width"]}x{result["height"]}')
    print("output     :", output_path)
    print()


if __name__ == "__main__":
    main()