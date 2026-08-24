from pathlib import Path

import cv2
import numpy as np

from processing.analyzer import (
    analyze_image
)

from processing.operations import (
    illumination_normalize
)

from processing.preservation import (
    verify_preservation
)


INPUT = Path(
    "evaluation/input/06_fine_details.jpg"
)

OUTPUT = Path(
    "evaluation/output/illumination"
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
        "05_uneven_lighting.jpg not found."
    )


candidates = {
    "weak": illumination_normalize(
        image,
        kernel_size=51,
        strength=0.45
    ),

    "default": illumination_normalize(
        image,
        kernel_size=51,
        strength=0.65
    ),

    "wide": illumination_normalize(
        image,
        kernel_size=81,
        strength=0.65
    ),

    "strong": illumination_normalize(
        image,
        kernel_size=81,
        strength=0.85
    )
}


def metric_value(
    metrics,
    key
):
    value = metrics[key]

    if isinstance(
        value,
        dict
    ):
        return value["value"]

    return value


def print_analysis(
    name,
    candidate
):
    analysis = analyze_image(
        candidate
    )

    metrics = analysis[
        "metrics"
    ]

    print()
    print(name)

    for key in [
        "brightness",
        "contrast",
        "sharpness",
        "illumination_variation",
        "edge_density"
    ]:
        print(
            f"  {key}:",
            round(
                metric_value(
                    metrics,
                    key
                ),
                4
            )
        )


print()
print(
    "ORIGINAL"
)

print_analysis(
    "original",
    image
)


for name, candidate in candidates.items():
    cv2.imwrite(
        str(
            OUTPUT
            / f"{name}.png"
        ),
        candidate
    )

    print_analysis(
        name,
        candidate
    )

    preservation = (
        verify_preservation(
            image,
            candidate
        )
    )

    print("  preservation:")

    if "status" in preservation:
        print(
            "    status:",
            preservation["status"]
        )

    if "metrics" in preservation:
        for key, value in preservation["metrics"].items():
            if isinstance(value, dict) and "value" in value:
                value = value["value"]

            if isinstance(value, (int, float)):
                print(
                    f"    {key}:",
                    round(float(value), 4)
                )
            else:
                print(
                    f"    {key}:",
                    value
                )

    difference = cv2.absdiff(
        image,
        candidate
    )

    changed_ratio = float(
        np.mean(
            difference > 3
        )
    )

    mean_change = float(
        np.mean(
            difference
        )
    )

    print(
        "  changed_ratio:",
        round(
            changed_ratio,
            4
        )
    )

    print(
        "  mean_pixel_change:",
        round(
            mean_change,
            4
        )
    )


print()
print(
    "Results saved to:",
    OUTPUT
)