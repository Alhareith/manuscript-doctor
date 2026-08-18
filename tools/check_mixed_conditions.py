from pathlib import Path
import cv2
from processing.analyzer import analyze_image
from processing.recommender import build_treatment_strategy

INPUT_DIR = Path("evaluation/input")

FILES = [
    "01_normal.jpg",
    "02_dark.jpg",
    "03_low_contrast.jpg",
    "04_noisy.jpg",
    "05_uneven_lighting.jpg",
    "06_fine_details.jpg",
    "07_bleed_through.jpg",
    "08_faded.jpg",
    "09_fragmented.jpg",
    "10_ink_spread.jpg",
    "11_skewed.jpg"
]

for filename in FILES:
    path = INPUT_DIR / filename
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)

    if image is None:
        print(f"\n{filename}: NOT FOUND")
        continue

    analysis = analyze_image(image)
    strategy = build_treatment_strategy(analysis)

    print(f"\n{'=' * 70}")
    print(filename)
    print(f"requires_treatment: {strategy['requires_treatment']}")
    print(f"conditions: {strategy['conditions']}")

    print("conflicts:")
    for conflict in strategy["conflicts"]:
        print(f"  - {conflict['code']}: {conflict['message']}")

    print("blocked:")
    for operation_id, reason in strategy["blocked_operations"].items():
        print(f"  - {operation_id}: {reason}")

    print("candidate plan:")
    for item in strategy["candidate_plan"]:
        print(f"  - priority={item['priority']} operation={item['operation_id']} mode={item['mode']} reanalysis={item['requires_reanalysis']}")