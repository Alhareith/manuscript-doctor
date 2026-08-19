import argparse
import os
import sys
from pathlib import Path
from unittest import result

import cv2
import numpy as np

sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from processing.document_boundary import detect_document_boundary


OUTPUT_DIR = Path(
    "evaluation/output/document_boundary"
)


def draw_detection(image, result):
    preview = image.copy()

    if not result.get("corners"):
        return preview

    corners = np.asarray(
        result["corners"],
        dtype=np.int32
    )

    cv2.polylines(
        preview,
        [corners.reshape(-1, 1, 2)],
        True,
        (0, 255, 0),
        4,
        cv2.LINE_AA
    )

    labels = [
        "TL",
        "TR",
        "BR",
        "BL"
    ]

    for label, point in zip(
        labels,
        corners
    ):
        x = int(point[0])
        y = int(point[1])

        cv2.circle(
            preview,
            (x, y),
            8,
            (0, 0, 255),
            -1,
            cv2.LINE_AA
        )

        cv2.putText(
            preview,
            label,
            (
                min(
                    x + 10,
                    preview.shape[1] - 40
                ),
                max(
                    y - 10,
                    25
                )
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2,
            cv2.LINE_AA
        )

    return preview


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run Document Boundary Detection "
            "without cropping or modifying the source image."
        )
    )

    parser.add_argument(
        "image",
        help="Path to a document photo."
    )

    args = parser.parse_args()

    input_path = Path(
        args.image
    )

    if not input_path.is_file():
        raise FileNotFoundError(
            f"Input image not found: {input_path}"
        )

    image = cv2.imread(
        str(input_path),
        cv2.IMREAD_COLOR
    )

    if image is None:
        raise RuntimeError(
            f"OpenCV could not decode: {input_path}"
        )

    original = image.copy()

    result = detect_document_boundary(
        image
    )

    if not np.array_equal(
        image,
        original
    ):
        raise RuntimeError(
            "Boundary detector modified the input image."
        )

    print()
    print(
        "Document Boundary Detection"
    )
    print(
        "---------------------------"
    )
    print(
        "detected   :",
        result["detected"]
    )
    print(
        "confidence :",
        result["confidence"]
    )
    print(
        "area_ratio :",
        result["area_ratio"]
    )
    print(
        "corners    :",
        result["corners"]
    )
    print(
        "reason     :",
        result["reason"]
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = (
        OUTPUT_DIR
        / f"{input_path.stem}_bd.jpg"
    )

    preview = draw_detection(
        image,
        result
    )

    if not cv2.imwrite(
        str(output_path),
        preview
    ):
        raise RuntimeError(
            f"Could not save: {output_path}"
        )

    print(
        "preview    :",
        output_path
    )
    print()


if __name__ == "__main__":
    main()