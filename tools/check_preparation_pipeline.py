import argparse
import os
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.preparation_pipeline import prepare_document


OUTPUT_DIR = Path("evaluation/output/preparation")


def main():
    parser = argparse.ArgumentParser(description="Run the complete document preparation pipeline.")
    parser.add_argument("image", help="Path to the input document image.")
    args = parser.parse_args()

    input_path = Path(args.image)

    if not input_path.is_file():
        raise FileNotFoundError(f"Input image not found: {input_path}")

    image = cv2.imread(str(input_path), cv2.IMREAD_COLOR)

    if image is None:
        raise RuntimeError(f"OpenCV could not decode: {input_path}")

    original = image.copy()
    result = prepare_document(image)

    if not np.array_equal(image, original):
        raise RuntimeError("Preparation pipeline modified the original image.")

    print()
    print("Document Preparation")
    print("--------------------")
    print("prepared   :", result["prepared"])
    print("reason     :", result["reason"])

    for step in result["steps"]:
        print()
        print("step       :", step["step"])
        print("status     :", step["status"])

        for key, value in step.items():
            if key not in {"step", "status"}:
                print(f"{key:<11}:", value)

    if not result["prepared"]:
        print()
        print("output     : not created")
        print()
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = OUTPUT_DIR / f"{input_path.stem}_prep.jpg"

    if not cv2.imwrite(str(output_path), result["image"]):
        raise RuntimeError(f"Could not save: {output_path}")

    print()
    print("final_size :", f'{result["image"].shape[1]}x{result["image"].shape[0]}')
    print("output     :", output_path)
    print()


if __name__ == "__main__":
    main()