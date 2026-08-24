import numpy as np

from processing.analyzer import analyze_image
from processing.pipeline import run_smart_pipeline
from processing.preparation_pipeline import prepare_document
from processing.preparation_verification import verify_preparation


def _validate_image(image):
    if image is None or not isinstance(image, np.ndarray):
        raise ValueError("Image must be a valid NumPy array.")

    if image.size == 0:
        raise ValueError("Image cannot be empty.")


def run_smart_document_pipeline(image):
    _validate_image(image)

    original = image.copy()

    preparation = prepare_document(image)
    preparation_verification = verify_preparation(preparation)

    result = {
        "image": original.copy(),
        "prepared_image": None,
        "preparation": preparation,
        "preparation_verification": preparation_verification,
        "prepared_analysis": None,
        "treatment": None,
        "decision": {
            "status": "stopped",
            "stage": "preparation",
            "message": "",
        },
    }

    if not preparation["prepared"]:
        result["decision"] = {
            "status": "stopped",
            "stage": "preparation",
            "message": "تم إيقاف المسار لأن إعداد الوثيقة لم ينجح بصورة موثوقة.",
        }

        return result

    if preparation_verification["status"] != "accept":
        result["prepared_image"] = preparation["image"].copy()

        result["decision"] = {
            "status": "review_required",
            "stage": "preparation_verification",
            "message": "تم إعداد الوثيقة، لكن Preparation Verification لم تسمح بالانتقال التلقائي إلى المعالجة.",
        }

        return result

    prepared_image = preparation["image"]
    prepared_analysis = analyze_image(prepared_image)

    result["prepared_image"] = prepared_image.copy()
    result["prepared_analysis"] = prepared_analysis

    treatment = run_smart_pipeline(prepared_image, prepared_analysis)

    result["treatment"] = treatment
    result["image"] = treatment["image"]

    treatment_decision = treatment.get("decision", {})

    result["decision"] = {
        "status": treatment_decision.get("status", "review_required"),
        "stage": "treatment",
        "message": treatment_decision.get(
            "message",
            "اكتملت مرحلة الإعداد ثم المعالجة، لكن القرار النهائي يحتاج مراجعة."
        ),
    }

    if not np.array_equal(image, original):
        raise RuntimeError("Smart document pipeline modified the original input image.")

    return result