# → Phase C Section 15: Deskew End-to-End Validation
#
# لكل زاوية (0, ±1, ±2, ±3.5, ±5 درجات) وعلى كل مصدر:
#   1. تدوير الوثيقة بالزاوية.
#   2. قياس الزاوية عبر analyzer._estimate_skew.
#   3. التحقق من دقة الكشف (خطأ ≤ 0.75 درجة = عتبة التفعيل).
#   4. التحقق من أن deskew يبقى مؤجلًا (يدويًا) في Smart Pipeline.

import os
import sys

import cv2
import numpy as np

sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from processing.analyzer import (
    _estimate_skew,
    _to_gray,
    analyze_image,
)
from processing.pipeline import run_smart_pipeline


GENERATED = os.path.join(
    "evaluation",
    "operation_validation",
    "generated"
)

SOURCES = [
    "00_source_original",
    "source_01_clean_manuscript.png",
    "source_02_clean_document.png"
]

ANGLES = [0.0, 1.0, -1.0, 2.0, -2.0, 3.5, -3.5, 5.0, -5.0]

DETECTION_TOLERANCE = 0.75
ACTION_THRESHOLD = 0.75


def rotate(image, angle):
    h, w = image.shape[:2]

    center = (
        w / 2.0,
        h / 2.0
    )

    matrix = cv2.getRotationMatrix2D(
        center,
        angle,
        1.0
    )

    cos = abs(matrix[0, 0])
    sin = abs(matrix[0, 1])

    bound_w = int(
        h * sin + w * cos
    )

    bound_h = int(
        h * cos + w * sin
    )

    matrix[0, 2] += bound_w / 2.0 - center[0]
    matrix[1, 2] += bound_h / 2.0 - center[1]

    return cv2.warpAffine(
        image,
        matrix,
        (bound_w, bound_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )


def main():
    failures = []

    print(
        f"{'source':28s} "
        f"{'true':>6s} "
        f"{'detected':>9s} "
        f"{'err':>6s} "
        f"{'conf':>6s} "
        f"verdict"
    )

    for source in SOURCES:
        path = os.path.join(
            GENERATED,
            source,
            "01_normal.png"
        )

        base = cv2.imread(path)

        if base is None:
            failures.append(
                f"{source}: unreadable base"
            )

            continue

        for angle in ANGLES:
            rotated = rotate(
                base,
                angle
            )

            gray = _to_gray(rotated)

            skew = _estimate_skew(
                gray
            )

            detected = skew["angle"]
            confidence = skew["confidence"]

            error = abs(
                detected - angle
            )

            if angle == 0.0:
                ok = abs(
                    detected
                ) < ACTION_THRESHOLD

                verdict = (
                    "OK (no action)"
                    if ok
                    else "FAIL"
                )

            else:
                ok = (
                    error
                    <= DETECTION_TOLERANCE
                )

                verdict = (
                    "OK"
                    if ok
                    else "FAIL"
                )

            if not ok:
                failures.append(
                    f"{source} @ {angle}deg: "
                    f"detected {detected} "
                    f"(err {error:.2f})"
                )

            print(
                f"{source[:28]:28s} "
                f"{angle:6.1f} "
                f"{detected:9.2f} "
                f"{error:6.2f} "
                f"{confidence:6.2f} "
                f"{verdict}"
            )

    # التحقق من أن pipeline يؤجل deskew ولا ينفذه تلقائيًا

    print()

    skewed = rotate(
        cv2.imread(
            os.path.join(
                GENERATED,
                SOURCES[0],
                "01_normal.png"
            )
        ),
        3.5,
    )

    analysis = analyze_image(
        skewed
    )

    result = run_smart_pipeline(
        skewed,
        analysis
    )

    deskew_steps = [
        s
        for s in result["steps"]
        if s["operation_id"]
        == "deskew"
    ]

    auto_applied = any(
        s["execution_status"]
        == "accepted"
        for s in deskew_steps
    )

    if auto_applied:
        failures.append(
            "deskew was applied "
            "automatically (must be "
            "manual-only)"
        )

    print(
        "deskew in pipeline: "
        + (
            "deferred (manual-only) OK"
            if deskew_steps
            and not auto_applied
            else (
                "no deskew step"
                if not deskew_steps
                else "AUTO-APPLIED (FAIL)"
            )
        )
    )

    print()

    if failures:
        print("FAILURES:")

        for f in failures:
            print(f"  {f}")

        return 1

    print(
        "DESKEW E2E: ALL PASSED"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
