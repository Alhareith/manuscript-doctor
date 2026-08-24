import cv2
import numpy as np


INPUT = (
    r"evaluation\input\11_skewed.jpg"
)


image = cv2.imread(
    INPUT,
    cv2.IMREAD_GRAYSCALE
)

if image is None:
    raise RuntimeError(
        f"Could not read: {INPUT}"
    )


blurred = cv2.GaussianBlur(
    image,
    (5, 5),
    0
)

edges = cv2.Canny(
    blurred,
    50,
    150,
    apertureSize=3
)

height, width = image.shape[:2]

lines = cv2.HoughLinesP(
    edges,
    1,
    np.pi / 180,
    threshold=100,
    minLineLength=max(
        50,
        width // 6
    ),
    maxLineGap=15
)


if lines is None:
    print("No lines detected.")
    raise SystemExit


print()
print("DETECTED LINES")
print("=" * 60)


angles = []


for index, line in enumerate(
    lines
):
    values = np.asarray(
        line
    ).reshape(-1)

    if values.size < 4:
        continue

    x1, y1, x2, y2 = (
        values[:4].astype(
            np.float32
        )
    )

    dx = x2 - x1
    dy = y2 - y1

    length = float(
        np.hypot(
            dx,
            dy
        )
    )

    if length == 0:
        continue

    angle = float(
        np.degrees(
            np.arctan2(
                dy,
                dx
            )
        )
    )

    while angle > 90:
        angle -= 180

    while angle <= -90:
        angle += 180

    angles.append(
        (
            angle,
            length
        )
    )


angles.sort(
    key=lambda item: item[1],
    reverse=True
)


for index, (
    angle,
    length
) in enumerate(
    angles[:30],
    start=1
):
    print(
        f"{index:2d}. "
        f"angle={angle:8.3f}°  "
        f"length={length:8.2f}"
    )


print()
print(
    "TOTAL LINES:",
    len(angles)
)


horizontal = [
    item
    for item in angles
    if abs(item[0]) <= 20
]


print(
    "LINES WITHIN ±20°:",
    len(horizontal)
)


if horizontal:
    weighted_mean = np.average(
        [
            item[0]
            for item in horizontal
        ],
        weights=[
            item[1]
            for item in horizontal
        ]
    )

    print(
        "WEIGHTED ANGLE:",
        round(
            float(
                weighted_mean
            ),
            3
        )
    )
