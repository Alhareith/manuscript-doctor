import argparse
import os
import sys
from pathlib import Path

import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.smart_document_pipeline import run_smart_document_pipeline


def main():
    parser = argparse.ArgumentParser(description="Run the Smart Document Pipeline on multiple real images.")
    parser.add_argument("images", nargs="+", help="Paths to input document images.")
    args = parser.parse_args()

    for image_name in args.images:
        path = Path(image_name)

        print()
        print("=" * 70)
        print("image       :", path.name)

        if not path.is_file():
            print("result      : skipped")
            print("reason      : file not found")
            continue

        image = cv2.imread(str(path), cv2.IMREAD_COLOR)

        if image is None:
            print("result      : skipped")
            print("reason      : OpenCV could not decode image")
            continue

        try:
            result = run_smart_document_pipeline(image)
        except Exception as error:
            print("result      : ERROR")
            print("error       :", type(error).__name__, str(error))
            continue

        preparation = result["preparation"]
        verification = result["preparation_verification"]

        print("prepared    :", preparation["prepared"])
        print("prep_verify :", verification["status"])
        print("reanalyzed  :", result["prepared_analysis"] is not None)
        print("treatment   :", result["treatment"] is not None)
        print("stage       :", result["decision"]["stage"])
        print("status      :", result["decision"]["status"])
        print("message     :", result["decision"]["message"])

        if preparation["boundary"]:
            print("boundary    :", preparation["boundary"]["detected"])
            print("boundary_cf :", preparation["boundary"]["confidence"])

        if preparation["skew"]:
            print("skew        :", preparation["skew"]["angle"])
            print("skew_cf     :", preparation["skew"]["confidence"])

    print()


if __name__ == "__main__":
    main()

    