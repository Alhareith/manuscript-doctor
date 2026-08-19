from pathlib import Path

import cv2
import numpy as np

from processing.analyzer import (
    analyze_image
)

from processing.operations import (
    background_suppress,
    weak_structure_suppress,
    illumination_normalize,
    clahe
)

from processing.preservation import (
    verify_preservation
)


INPUT = Path(
    "evaluation/input/07_bleed_through.jpg"
)

OUTPUT = Path(
    "evaluation/output/bleed_through"
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
        "07_bleed_through.jpg not found."
    )


candidates = {
    "background_weak": (
        background_suppress(
            image,
            kernel_size=31,
            strength=0.30
        )
    ),

    "background_default": (
        background_suppress(
            image,
            kernel_size=31,
            strength=0.45
        )
    ),

    "weak_structure": (
        weak_structure_suppress(
            image,
            kernel_size=31,
            threshold=12,
            strength=0.35
        )
    ),

    "illumination_only": (
        illumination_normalize(
            image,
            kernel_size=51,
            strength=0.45
        )
    ),

    "clahe_only": (
        clahe(
            image,
            clip_limit=1.5,
            tile_grid_size=8
        )
    )
}


def metric(
    metrics,
    key
):
    item = metrics[key]

    if isinstance(
        item,
        dict
    ):
        return item["value"]

    return item


def evaluate(
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
        "contrast",
        "sharpness",
        "edge_density",
        "weak_structure_ratio",
        "strong_structure_ratio",
        "weak_to_strong_ratio"
    ]:
        print(
            f"  {key}:",
            round(
                metric(
                    metrics,
                    key
                ),
                4
            )
        )

    if name != "original":
        preservation = verify_preservation(
        image,
        candidate
    )

        print("  preservation:")

        if isinstance(preservation, dict):
            if "status" in preservation:
                print(
                    "    status:",
                    preservation["status"]
                )

            if "metrics" in preservation:
                for key, value in preservation["metrics"].items():
                    if isinstance(value, dict):
                        if "value" in value:
                            print(
                                f"    {key}:",
                                value["value"]
                            )
                        else:
                            print(
                                f"    {key}:",
                                value
                            )
                else:
                    print(
                        f"    {key}:",
                        value
                        )
              

        for key in [
            "severity",
            "warnings",
            "issues",
            "passed"
        ]:
            if key in preservation:
                print(
                    f"    {key}:",
                    preservation[key]
                )

    difference = cv2.absdiff(
        image,
        candidate
    )

    print(
        "  changed_ratio:",
        round(
            float(
                np.mean(
                    difference > 3
                )
            ),
            4
        )
    )

    print(
        "  mean_pixel_change:",
        round(
            float(
                np.mean(difference)
            ),
            4
        )
    )

evaluate(
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

    evaluate(
        name,
        candidate
    )