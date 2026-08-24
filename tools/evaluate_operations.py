import csv
import json
import sys
from pathlib import Path

import cv2


BASE_DIR = Path(__file__).resolve().parents[1]

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


from processing.analyzer import analyze_image
from processing.operations import apply_operation


INPUT_DIR = BASE_DIR / "evaluation" / "input"
OUTPUT_DIR = BASE_DIR / "evaluation" / "output"
RESULTS_FILE = BASE_DIR / "evaluation" / "results.csv"

SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png"
}


OPERATION_CASES = {
    "clahe": [
        {"clip_limit": 1.5, "tile_grid_size": 8},
        {"clip_limit": 2.0, "tile_grid_size": 8},
        {"clip_limit": 2.5, "tile_grid_size": 8},
    ],

    "histogram_equalization": [
        {}
    ],

    "median_denoise": [
        {"kernel_size": 3},
        {"kernel_size": 5},
    ],

    "sharpen": [
        {"amount": 0.25, "kernel_size": 3},
        {"amount": 0.5, "kernel_size": 3},
        {"amount": 0.75, "kernel_size": 3},
    ],

    "global_threshold": [
        {"threshold": 100},
        {"threshold": 127},
        {"threshold": 160},
    ],

    "otsu_threshold": [
        {}
    ],

    "adaptive_threshold": [
        {"block_size": 25, "c": 7},
        {"block_size": 35, "c": 11},
        {"block_size": 51, "c": 15},
    ],

    "morphological_opening": [
        {"kernel_size": 3},
        {"kernel_size": 5},
    ],

    "morphological_closing": [
        {"kernel_size": 3},
        {"kernel_size": 5},
    ],
}


def find_images():
    if not INPUT_DIR.exists():
        return []

    return sorted(
        path
        for path in INPUT_DIR.iterdir()
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def read_image(path):
    image = cv2.imread(
        str(path),
        cv2.IMREAD_UNCHANGED
    )

    if image is None:
        raise ValueError(
            f"Cannot read image: {path.name}"
        )

    return image


def safe_filename(value):
    return (
        value
        .replace(" ", "_")
        .replace(".", "_")
        .replace("-", "_")
    )


def parameter_label(params):
    if not params:
        return "default"

    parts = []

    for key, value in params.items():
        parts.append(
            f"{safe_filename(str(key))}_{safe_filename(str(value))}"
        )

    return "__".join(parts)


def metric_value(analysis, metric):
    return analysis["metrics"][metric]["value"]


def evaluate_case(
    image_path,
    image,
    operation_id,
    params
):
    original_analysis = analyze_image(image)

    processed = apply_operation(
        operation_id,
        image,
        params
    )

    processed_analysis = analyze_image(processed)

    image_output_dir = (
        OUTPUT_DIR
        / image_path.stem
        / operation_id
    )

    image_output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    label = parameter_label(params)

    output_path = (
        image_output_dir
        / f"{label}.png"
    )

    success = cv2.imwrite(
        str(output_path),
        processed
    )

    if not success:
        raise RuntimeError(
            f"Cannot save result: {output_path}"
        )

    return {
        "image": image_path.name,
        "operation": operation_id,
        "parameters": json.dumps(
            params,
            ensure_ascii=False,
            sort_keys=True
        ),
        "output": str(
            output_path.relative_to(BASE_DIR)
        ),

        "brightness_before": metric_value(
            original_analysis,
            "brightness"
        ),
        "brightness_after": metric_value(
            processed_analysis,
            "brightness"
        ),

        "contrast_before": metric_value(
            original_analysis,
            "contrast"
        ),
        "contrast_after": metric_value(
            processed_analysis,
            "contrast"
        ),

        "sharpness_before": metric_value(
            original_analysis,
            "sharpness"
        ),
        "sharpness_after": metric_value(
            processed_analysis,
            "sharpness"
        ),

        "noise_before": metric_value(
            original_analysis,
            "noise"
        ),
        "noise_after": metric_value(
            processed_analysis,
            "noise"
        ),

        "illumination_before": metric_value(
            original_analysis,
            "illumination_variation"
        ),
        "illumination_after": metric_value(
            processed_analysis,
            "illumination_variation"
        ),

        "edge_density_before": metric_value(
            original_analysis,
            "edge_density"
        ),
        "edge_density_after": metric_value(
            processed_analysis,
            "edge_density"
        ),
    }


def write_results(rows):
    RESULTS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if not rows:
        return

    with RESULTS_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0].keys())
        )

        writer.writeheader()
        writer.writerows(rows)


def main():
    images = find_images()

    if not images:
        print(
            "No evaluation images found in:"
        )
        print(INPUT_DIR)
        return

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    rows = []

    for image_path in images:
        print(
            f"\nEvaluating: {image_path.name}"
        )

        image = read_image(image_path)

        for operation_id, cases in OPERATION_CASES.items():
            for params in cases:
                print(
                    f"  {operation_id}: {params or 'default'}"
                )

                row = evaluate_case(
                    image_path,
                    image,
                    operation_id,
                    params
                )

                rows.append(row)

    write_results(rows)

    print("\nEvaluation completed.")
    print(f"Results: {RESULTS_FILE}")
    print(f"Images:  {OUTPUT_DIR}")


if __name__ == "__main__":
    main()