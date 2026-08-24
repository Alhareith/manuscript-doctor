from pathlib import Path

import cv2
import numpy as np

from processing.analyzer import (
    analyze_image
)

from processing.operations import (
    median_denoise,
    bilateral_denoise,
    non_local_means_denoise
)

from processing.preservation import (
    verify_preservation
)


INPUT = Path(
    "evaluation/input/04_noisy.jpg"
)

OUTPUT = Path(
    "evaluation/output/denoising"
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


candidates = {
    "original": image,

    "median_k3": median_denoise(
        image,
        kernel_size=3
    ),

    "median_k5": median_denoise(
        image,
        kernel_size=5
    ),

    "bilateral_weak": bilateral_denoise(
        image,
        diameter=5,
        sigma_color=20,
        sigma_space=20
    ),

    "bilateral_default": bilateral_denoise(
        image,
        diameter=5,
        sigma_color=25,
        sigma_space=25
    ),

    "nlm_weak": non_local_means_denoise(
        image,
        strength=3,
        template_window_size=7,
        search_window_size=21
    ),

    "nlm_default": non_local_means_denoise(
        image,
        strength=5,
        template_window_size=7,
        search_window_size=21
    )
}


def metric_value(
    metrics,
    name
):
    value = metrics[name]

    if isinstance(
        value,
        dict
    ):
        return value["value"]

    return value


original_analysis = analyze_image(
    image
)


print()
print(
    "DENOISING COMPARISON"
)
print(
    "=" * 72
)


for name, candidate in candidates.items():
    if name != "original":
        cv2.imwrite(
            str(
                OUTPUT
                / f"{name}.png"
            ),
            candidate
        )

    analysis = analyze_image(
        candidate
    )

    metrics = analysis[
        "metrics"
    ]

    noise = metrics[
        "noise"
    ]

    if name == "original":
        preservation = None
    else:
        preservation = verify_preservation(
            image,
            candidate
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

    print()
    print(name)

    print(
        "  noise:",
        round(
            noise["value"],
            4
        )
    )

    print(
        "  noise_p90:",
        round(
            noise["p90"],
            4
        )
    )

    print(
        "  affected_ratio:",
        round(
            noise["affected_ratio"],
            4
        )
    )

    print(
        "  sharpness:",
        round(
            metric_value(
                metrics,
                "sharpness"
            ),
            4
        )
    )

    print(
        "  edge_density:",
        round(
            metric_value(
                metrics,
                "edge_density"
            ),
            4
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

    if name == "original":
        preservation = None
    else:
        preservation = verify_preservation(
            image,
            candidate
        )

        assessment = preservation.get(
            "assessment",
            {}
        )

        print(
            "  preservation:",
            assessment.get(
                "status",
                "unknown"
        )
    )


print()
print("=" * 72)
