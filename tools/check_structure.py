from pathlib import Path

import cv2
import numpy as np

from processing.analyzer import (
    analyze_image
)

from processing.operations import (
    morphological_opening,
    morphological_closing,
    morphological_top_hat,
    morphological_black_hat
)

from processing.preservation import (
    verify_preservation
)


INPUT = Path(
    "evaluation/input/06_fine_details.jpg"
)

OUTPUT = Path(
    "evaluation/output/structure"
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
    "opening_k3": (
        morphological_opening(
            image,
            kernel_size=3
        )
    ),

    "closing_k3": (
        morphological_closing(
            image,
            kernel_size=3
        )
    ),

    "top_hat_k3": (
        morphological_top_hat(
            image,
            kernel_size=3
        )
    ),

    "black_hat_k5": (
        morphological_black_hat(
            image,
            kernel_size=5
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
        "component_count",
        "small_component_ratio",
        "foreground_ratio",
        "thin_structure_ratio",
        "sharpness",
        "edge_density"
    ]:
        item = metrics.get(
            key
        )

        if item is None:
            continue

        if isinstance(
            item,
            dict
        ):
            item = item.get(
                "value"
            )

        print(
            f"  {key}:",
            round(
                float(item),
                4
            )
        )

    if name == "original":
        return

    preservation = verify_preservation(
        image,
        candidate
    )

    preservation_metrics = (
        preservation.get(
            "metrics",
            {}
        )
    )

    assessment = (
        preservation.get(
            "assessment",
            {}
        )
    )

    print(
        "  preservation:"
    )

    print(
        "    status:",
        assessment.get(
            "status",
            "unknown"
        )
    )

    print(
        "    edge_retention:",
        preservation_metrics.get(
            "edge_retention"
        )
    )

    print(
        "    component_retention:",
        preservation_metrics.get(
            "component_retention"
        )
    )

    print(
        "    structure_similarity:",
        preservation_metrics.get(
            "structure_similarity"
        )
    )

    print(
        "    edge_inflation:",
        preservation_metrics.get(
            "edge_inflation"
        )
    )

    warnings = preservation.get(
        "warnings",
        []
    )

    if warnings:
        print(
            "    warnings:",
            warnings
        )

    if (
        image.shape
        == candidate.shape
    ):
        difference = cv2.absdiff(
            image,
            candidate
        )
    
        changed_ratio = float(
            np.mean(
                difference > 3
            )
        )
    
        print(
            "  changed_ratio:",
            round(
                changed_ratio,
                4
            )
        )
    
    else:
        print(
            "  changed_ratio: N/A"
        )
    
        print(
            "  dimension_change:",
            image.shape,
            "->",
            candidate.shape
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