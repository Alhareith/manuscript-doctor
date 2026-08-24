from pathlib import Path

import cv2

from processing.analyzer import (
    analyze_image
)

from processing.operations import (
    deskew
)


INPUT = Path(
    "evaluation/input/11_skewed.jpg"
)

OUTPUT = Path(
    "evaluation/output/geometry"
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


analysis = analyze_image(
    image
)

metrics = analysis[
    "metrics"
]

angle = metrics[
    "skew_angle"
]["value"]

confidence = metrics[
    "skew_confidence"
]["value"]

line_count = metrics[
    "skew_line_count"
]["value"]


print(
    "Detected angle:",
    angle
)

print(
    "Confidence:",
    confidence
)

print(
    "Line count:",
    line_count
)

# tools/check_geometry.py

# خفض عتبة الزاوية لـ 0.2 وعتبة الثقة لـ 0.1
if abs(angle) >= 0.2 and confidence >= 0.1:
    result = deskew(image, angle=angle)
    out_file = OUTPUT / "deskewed.png"
    cv2.imwrite(str(out_file), result)
    print(f"Deskew candidate generated successfully at: {out_file}")
else:
    print("Deskew candidate not generated.")