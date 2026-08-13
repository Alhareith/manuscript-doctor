from pathlib import Path

import cv2

from processing.analyzer import (
    analyze_image
)

from processing.operations import (
    median_denoise
)


INPUT = Path(
    "evaluation/input/04_noisy.jpg"
)

OUTPUT = Path(
    "evaluation/output"
)

OUTPUT.mkdir(
    parents=True,
    exist_ok=True
)


image = cv2.imread(
    str(INPUT),
    cv2.IMREAD_UNCHANGED
)

if image is None:
    raise RuntimeError(
        "04_noisy.jpg not found."
    )


original_analysis = (
    analyze_image(
        image
    )
)


median3 = median_denoise(
    image,
    kernel_size=3
)

median5 = median_denoise(
    image,
    kernel_size=5
)


cv2.imwrite(
    str(
        OUTPUT
        / "04_noisy_median_k3.png"
    ),
    median3
)

cv2.imwrite(
    str(
        OUTPUT
        / "04_noisy_median_k5.png"
    ),
    median5
)


for name, candidate in [
    ("original", image),
    ("median_k3", median3),
    ("median_k5", median5)
]:
    result = analyze_image(
        candidate
    )

    noise = result[
        "metrics"
    ]["noise"]

    metrics = result[
        "metrics"
    ]

    print(name)

    print(
        " noise =",
        round(
            noise["value"],
            4
        )
    )

    print(
        " p90 =",
        round(
            noise["p90"],
            4
        )
    )

    print(
        " affected_ratio =",
        round(
            noise[
                "affected_ratio"
            ],
            4
        )
    )

    print(
        " sharpness =",
        metrics[
            "sharpness"
        ]["value"]
    )

    print(
        " edge_density =",
        metrics[
            "edge_density"
        ]["value"]
    )

    print()