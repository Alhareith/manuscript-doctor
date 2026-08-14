from pathlib import Path

import cv2

from processing.analyzer import (
    analyze_image
)


INPUT_DIR = Path(
    "evaluation/input"
)

images = [
    "01_normal.jpg",
    "02_dark.jpg",
    "03_low_contrast.jpg",
    "04_noisy.jpg",
    "05_uneven_lighting.jpg",
    "06_fine_details.jpg",
    "07_bleed_through.jpg"
]


for filename in images:
    path = INPUT_DIR / filename

    image = cv2.imread(
        str(path),
        cv2.IMREAD_UNCHANGED
    )

    if image is None:
        print(
            f"{filename}: NOT FOUND"
        )
        continue

    result = analyze_image(
        image
    )

    noise = result[
        "metrics"
    ]["noise"]

    print(
        filename
    )

    print(
        f"  value          = "
        f"{noise['value']:.4f}"
    )

    print(
        f"  p90            = "
        f"{noise['p90']:.4f}"
    )

    print(
        f"  affected_ratio = "
        f"{noise['affected_ratio']:.4f}"
    )

    print()