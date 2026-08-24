from pathlib import Path

import cv2
import numpy as np

from processing import preservation
from processing.analyzer import (
    analyze_image
)

from processing.operations import (
    gamma_correct,
    intensity_adjust,
    faded_text_enhance,
    clahe
)

from processing.preservation import (
    verify_preservation
)


INPUT = Path(
    "evaluation/input/02_dark.jpg"
)

OUTPUT = Path(
    "evaluation/output/exposure"
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
        f"{INPUT} not found."
    )


candidates = {
    "gamma_085": gamma_correct(
        image,
        gamma=0.85
    ),

    "gamma_070": gamma_correct(
        image,
        gamma=0.70
    ),

    "intensity_weak": intensity_adjust(
        image,
        alpha=1.05,
        beta=5
    ),

    "clahe": clahe(
        image,
        clip_limit=1.5,
        tile_grid_size=8
    ),

    "faded_candidate": (
        faded_text_enhance(
            image,
            clip_limit=1.4,
            gamma=0.95
        )
    )
}


def value(
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

def show(
    name,
    candidate
):
    result = analyze_image(
        candidate
    )

    metrics = result["metrics"]

    print()
    print(name)

    for key in [
        "brightness",
        "contrast",
        "sharpness",
        "dark_clipped_ratio",
        "bright_clipped_ratio",
        "edge_density"
    ]:
        print(
            f"  {key}:",
            round(
                value(
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

        print(
            "  preservation:"
        )

        if "status" in preservation:
            print(
                "    status:",
                preservation["status"]
            )

        if "metrics" in preservation:
            for metric_key, metric_value in preservation["metrics"].items():

                if (
                    isinstance(
                        metric_value,
                        dict
                    )
                    and "value" in metric_value
                ):
                    metric_value = metric_value["value"]

                if isinstance(
                    metric_value,
                    (int, float)
                ):
                    print(
                        f"    {metric_key}:",
                        round(
                            float(metric_value),
                            4
                        )
                    )
                else:
                    print(
                        f"    {metric_key}:",
                        metric_value
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

show(
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

    show(
        name,
        candidate
    )