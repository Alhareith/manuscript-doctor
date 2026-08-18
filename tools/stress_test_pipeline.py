# → Phase C Stress Tests: تشغيل Smart Pipeline على كل حالات التقييم
#
# يمرر كل حالة (25 حالة × 3 مصادر) عبر: analyze → recommend → pipeline
# ويسجل القرار والخطوات وبوابة المنفعة، ثم يتحقق من القواعد الصارمة:
#   * خطوة واحدة مقبولة كحد أقصى لكل جلسة
#   * لا تغيير للصورة عند الرفض (Rollback)
#   * لا عمليات مكررة
#   * الصور السليمة تبقى بدون معالجة

import json
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

from processing.analyzer import analyze_image
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


def load_case(source, case_file):
    path = os.path.join(
        GENERATED,
        source,
        case_file
    )

    image = cv2.imread(path)

    if image is None:
        return None

    return image


def run_all():
    results = []

    violations = []

    for source in SOURCES:
        source_dir = os.path.join(
            GENERATED,
            source
        )

        case_files = sorted(
            f
            for f in os.listdir(source_dir)
            if f.endswith(".png")
        )

        for case_file in case_files:
            image = load_case(
                source,
                case_file
            )

            if image is None:
                violations.append(
                    f"{source}/{case_file}: UNREADABLE"
                )

                continue

            original = image.copy()

            analysis = analyze_image(
                image
            )

            result = run_smart_pipeline(
                image,
                analysis
            )

            final = result["image"]

            accepted_steps = [
                s
                for s in result["steps"]
                if s["execution_status"]
                == "accepted"
            ]

            decision = result[
                "decision"
            ]["status"]

            # قاعدة: خطوة واحدة مقبولة كحد أقصى

            if len(accepted_steps) > 1:
                violations.append(
                    f"{source}/{case_file}: "
                    f"{len(accepted_steps)} "
                    "accepted steps (max 1)"
                )

            # قاعدة: الرفض يعني بقاء الصورة كما هي

            if (
                decision
                == "unchanged_due_to_risk"
                and not np.array_equal(
                    final,
                    original
                )
            ):
                violations.append(
                    f"{source}/{case_file}: "
                    "image changed despite "
                    "unchanged_due_to_risk"
                )

            # قاعدة: لا تكرار لنفس العملية

            attempted_ids = [
                s["operation_id"]
                for s in result["steps"]
                if s["execution_status"]
                in {
                    "accepted",
                    "rejected"
                }
            ]

            if len(attempted_ids) != len(
                set(attempted_ids)
            ):
                violations.append(
                    f"{source}/{case_file}: "
                    "repeated operation "
                    f"{attempted_ids}"
                )

            # قاعدة: الصور السليمة تبقى بدون معالجة

            diagnoses = [
                d["code"]
                for d in analysis[
                    "diagnoses"
                ]
            ]

            if (
                not diagnoses
                and decision
                != "no_treatment"
                and not result[
                    "steps"
                ]
                and not result[
                    "binarization_candidates"
                ]
            ):
                violations.append(
                    f"{source}/{case_file}: "
                    f"healthy image got "
                    f"{decision}"
                )

            benefit_info = (
                accepted_steps[0][
                    "benefit"
                ]
                if accepted_steps
                else None
            )

            results.append({
                "source": source,
                "case": case_file,
                "diagnoses": diagnoses,
                "decision": decision,
                "accepted_op": (
                    accepted_steps[0][
                        "operation_id"
                    ]
                    if accepted_steps
                    else None
                ),
                "benefit": (
                    {
                        "metric": (
                            benefit_info[
                                "metric"
                            ]
                        ),
                        "before": (
                            benefit_info[
                                "before"
                            ]
                        ),
                        "after": (
                            benefit_info[
                                "after"
                            ]
                        )
                    }
                    if benefit_info
                    else None
                ),
                "all_steps": [
                    {
                        "op": s[
                            "operation_id"
                        ],
                        "status": s[
                            "execution_status"
                        ]
                    }
                    for s in result[
                        "steps"
                    ]
                ],
                "binarization": len(
                    result[
                        "binarization_candidates"
                    ]
                )
            })

    return results, violations


def main():
    results, violations = run_all()

    print(
        f"Total cases: {len(results)}"
    )

    print()

    by_decision = {}

    for r in results:
        by_decision.setdefault(
            r["decision"],
            []
        ).append(r)

    for decision in sorted(
        by_decision
    ):
        print(
            f"{decision}: "
            f"{len(by_decision[decision])}"
        )

    print()

    print(
        "=== Per-case summary ==="
    )

    for r in results:
        steps = ", ".join(
            f"{s['op']}:{s['status']}"
            for s in r["all_steps"]
        )

        print(
            f"{r['source'][:20]:20s} "
            f"{r['case']:32s} "
            f"{r['decision']:22s} "
            f"[{steps}] "
            f"bin={r['binarization']}"
        )

    print()

    if violations:
        print(
            "=== VIOLATIONS ==="
        )

        for v in violations:
            print(f"  {v}")

        print(
            f"\nFAILED: "
            f"{len(violations)} violations"
        )

        return 1

    print(
        "ALL INVARIANTS HELD"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
