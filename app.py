from pathlib import Path
from uuid import UUID, uuid4

import cv2
import numpy as np
import base64
import json

from flask import Flask, jsonify, render_template, request, send_file
from processing.analyzer import analyze_image
from processing.operations import apply_operation, get_operation
from processing.pipeline import run_smart_pipeline
from processing.preservation import verify_preservation
from processing.recommender import recommend_treatment
from processing.document_boundary import (
    detect_document_boundary,
    detect_preparation_boundary,
)
from processing.preparation_pipeline import prepare_document
from processing.preparation_verification import verify_preparation

BASE_DIR = Path(__file__).resolve().parent

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}

MAX_UPLOAD_SIZE = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 30_000_000


def success_response(data=None, message="Request completed successfully.", status=200):
    return (
        jsonify({"success": True, "message": message, "data": data, "error": None}),
        status,
    )


def error_response(code, message, status, details=None):
    return (
        jsonify(
            {
                "success": False,
                "message": message,
                "data": None,
                "error": {"code": code, "details": details},
            }
        ),
        status,
    )


def is_valid_resource_id(value):
    if not isinstance(value, str):
        return False

    try:
        return UUID(hex=value).hex == value.lower()

    except (ValueError, AttributeError):
        return False


def get_extension(filename):
    if not isinstance(filename, str):
        return ""

    clean_name = filename.replace("\\", "/").rsplit("/", 1)[-1]

    suffix = Path(clean_name).suffix.lower()

    return suffix.lstrip(".")


def display_filename(filename):
    return filename.replace("\\", "/").rsplit("/", 1)[-1]


def decode_image(raw_data):
    if not raw_data:
        return None

    buffer = np.frombuffer(raw_data, dtype=np.uint8)

    return cv2.imdecode(buffer, cv2.IMREAD_UNCHANGED)


def read_stored_image(path):
    try:
        raw_data = path.read_bytes()

    except OSError:
        return None

    return decode_image(raw_data)


def image_dimensions(image):
    height, width = image.shape[:2]

    channels = 1 if image.ndim == 2 else image.shape[2]

    return {"width": int(width), "height": int(height), "channels": int(channels)}

PREVIEW_MAX_WIDTH = 720
PREVIEW_MAX_HEIGHT = 960


def resize_for_preview(image, max_width=PREVIEW_MAX_WIDTH, max_height=PREVIEW_MAX_HEIGHT):
    """Return a proportional, bounded preview image without changing the source image."""
    if image is None or not isinstance(image, np.ndarray) or image.size == 0:
        raise ValueError("Invalid preview image.")

    height, width = image.shape[:2]
    scale = min(
        1.0,
        max_width / max(width, 1),
        max_height / max(height, 1),
    )

    if scale >= 1.0:
        return image.copy()

    new_size = (
        max(1, int(round(width * scale))),
        max(1, int(round(height * scale))),
    )
    return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)


def build_preview_payload(image, preferred_format="png"):
    """Encode a bounded in-memory preview without writing a result file."""
    preview = resize_for_preview(image)
    normalized_format = "jpeg" if str(preferred_format).lower() in {"jpg", "jpeg"} else "png"
    if normalized_format == "jpeg":
        success, encoded = cv2.imencode(".jpg", preview, [cv2.IMWRITE_JPEG_QUALITY, 82])
        mime = "image/jpeg"
    else:
        success, encoded = cv2.imencode(".png", preview)
        mime = "image/png"
    if not success:
        raise RuntimeError("Could not encode preview image.")

    data_url = f"data:{mime};base64," + base64.b64encode(encoded.tobytes()).decode("ascii")
    return {
        "data_url": data_url,
        "format": normalized_format,
        **image_dimensions(preview),
    }


def resolve_upload_file(folder, image_id):
    if not is_valid_resource_id(image_id):
        return None

    folder = Path(folder)

    for extension in ALLOWED_EXTENSIONS:
        candidate = folder / f"{image_id}.{extension}"

        if candidate.is_file():
            return candidate

    return None


def resolve_result_file(folder, result_id):
    if not is_valid_resource_id(result_id):
        return None

    candidate = Path(folder) / f"{result_id}.png"

    if candidate.is_file():
        return candidate

    return None

def preparation_manifest_path(folder, preparation_id):
    return Path(folder) / f"{preparation_id}.json"


def resolve_preparation_preview_file(folder, preparation_id):
    if not is_valid_resource_id(preparation_id):
        return None

    candidate = Path(folder) / f"{preparation_id}.png"
    return candidate if candidate.is_file() else None


def preparation_public_metadata(preparation):
    return {
        key: value
        for key, value in preparation.items()
        if key != "image"
    }


def save_preparation_preview(image, folder, preparation_metadata):
    preparation_id, output_path = save_png_result(image, folder)

    manifest = {
        "preparation_id": preparation_id,
        "status": "preview",
        "source_image_id": preparation_metadata["source_image_id"],
        "method_used": preparation_metadata.get("method_used"),
        "preparation": preparation_metadata["preparation"],
    }

    try:
        preparation_manifest_path(folder, preparation_id).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        output_path.unlink(missing_ok=True)
        raise

    return preparation_id, output_path


def read_preparation_manifest(folder, preparation_id):
    path = preparation_manifest_path(folder, preparation_id)

    if not path.is_file():
        return None

    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    return manifest if isinstance(manifest, dict) else None


def save_png_result(image, folder):
    if image is None or not isinstance(image, np.ndarray) or image.size == 0:
        raise ValueError("Invalid result image.")

    if image.dtype != np.uint8:
        raise ValueError("Result image must be 8-bit.")

    success, encoded = cv2.imencode(".png", image)

    if not success:
        raise RuntimeError("Could not encode result image.")

    result_id = uuid4().hex

    output_path = Path(folder) / f"{result_id}.png"

    output_path.write_bytes(encoded.tobytes())

    return result_id, output_path


def build_result_metadata(
    result_id,
    image,
    source_image_id,
    *,
    origin=None,
    status=None,
    parent_result_id=None,
    operation_id=None,
    method_used=None,
):

    return {
        "id": result_id,
        "source_image_id": (source_image_id),
        "format": "png",
        **image_dimensions(image),
        "origin": origin,
        "status": status,
        "parent_result_id": parent_result_id,
        "operation_id": operation_id,
        "method_used": method_used,
    }

def manual_manifest_path(folder, result_id):
    return Path(folder) / f"{result_id}.json"

def save_result_artifact(
    image,
    folder,
    *,
    source_image_id,
    origin,
    status,
    parent_result_id=None,
    operation_id=None,
    parameters=None,
    method_used=None,
    extra=None,
):
    result_id, output_path = save_png_result(image, folder)

    manifest = {
        "result_id": result_id,
        "source_image_id": source_image_id,
        "parent_result_id": parent_result_id,
        "origin": origin,
        "status": status,
        "operation_id": operation_id,
        "parameters": parameters or {},
        "method_used": method_used,
    }

    if isinstance(extra, dict):
        manifest.update(extra)

    try:
        manual_manifest_path(folder, result_id).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        output_path.unlink(missing_ok=True)
        raise

    return result_id, output_path


def save_manual_result(
    image,
    folder,
    source_image_id,
    parent_result_id=None,
    operation_id=None,
    parameters=None,
):
    return save_result_artifact(
        image,
        folder,
        source_image_id=source_image_id,
        origin="manual",
        status="approved",
        parent_result_id=parent_result_id,
        operation_id=operation_id,
        parameters=parameters,
    )

def read_manual_manifest(folder, result_id):
    manifest_path = manual_manifest_path(folder, result_id)
    if not manifest_path.is_file():
        return None

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    return manifest if isinstance(manifest, dict) else None


def create_app(test_config=None):
    app = Flask(__name__)

    app.config.from_mapping(
        MAX_CONTENT_LENGTH=(MAX_UPLOAD_SIZE),
        MAX_IMAGE_PIXELS=(MAX_IMAGE_PIXELS),
        UPLOAD_FOLDER=(BASE_DIR / "storage" / "uploads"),
        RESULT_FOLDER=(BASE_DIR / "storage" / "results"),
        PREPARATION_PREVIEW_FOLDER=( BASE_DIR / "storage" / "preparation_previews" ),
    )

    if test_config:
        app.config.update(test_config)

    upload_folder = Path(app.config["UPLOAD_FOLDER"])

    result_folder = Path(app.config["RESULT_FOLDER"])

    upload_folder.mkdir(parents=True, exist_ok=True)

    result_folder.mkdir(parents=True, exist_ok=True)
    preparation_preview_folder = Path(
    app.config["PREPARATION_PREVIEW_FOLDER"]
    )
    preparation_preview_folder.mkdir(
        parents=True,
        exist_ok=True
    )


    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/api/images")
    def upload_image():
        uploaded_file = request.files.get("image")

        if uploaded_file is None:
            return error_response("NO_FILE", "لم يتم إرسال ملف صورة.", 400)

        filename = uploaded_file.filename or ""

        if not filename.strip():
            return error_response("EMPTY_FILENAME", "اسم الملف فارغ.", 400)

        extension = get_extension(filename)

        if extension not in ALLOWED_EXTENSIONS:
            return error_response("UNSUPPORTED_FILE_TYPE", "نوع الملف غير مدعوم.", 400)

        raw_data = uploaded_file.read()

        if not raw_data:
            return error_response(
                "UNREADABLE_IMAGE", "ملف الصورة فارغ أو غير قابل للقراءة.", 400
            )

        image = decode_image(raw_data)

        if image is None:
            return error_response(
                "UNREADABLE_IMAGE", "تعذر قراءة الملف كصورة صالحة.", 400
            )

        if image.dtype != np.uint8:
            return error_response(
                "UNSUPPORTED_IMAGE_DEPTH",
                ("عمق الصورة غير مدعوم. " "استخدم صورة JPG أو PNG " "بعمق 8-bit."),
                400,
            )

        height, width = image.shape[:2]

        pixel_count = int(height) * int(width)

        if pixel_count > app.config["MAX_IMAGE_PIXELS"]:
            return error_response(
                "IMAGE_DIMENSIONS_TOO_LARGE", "أبعاد الصورة أكبر من الحد المسموح.", 400
            )

        try:
            analysis = analyze_image(image)

            recommendation_result = recommend_treatment(analysis)

        except Exception:
            return error_response(
                "PROCESSING_FAILED", ("تعذر تحليل الصورة " "وإنشاء التوصيات."), 500
            )

        image_id = uuid4().hex

        output_path = upload_folder / f"{image_id}.{extension}"

        try:
            output_path.write_bytes(raw_data)

        except OSError:
            return error_response("INTERNAL_ERROR", "تعذر حفظ الصورة.", 500)

        return success_response(
            data={
                "image": {
                    "image_id": image_id,
                    "original_name": (display_filename(filename)),
                    "format": extension,
                    **image_dimensions(image),
                },
                "analysis": {
                    "dimensions": (analysis["dimensions"]),
                    "metrics": (analysis["metrics"]),
                },
                "diagnoses": (analysis["diagnoses"]),
                "preservation_profile": (analysis["preservation_profile"]),
                "recommendations": (recommendation_result["recommendations"]),
                "excluded_from_automatic": (
                    recommendation_result["excluded_from_automatic"]
                ),
                "recommendation_summary": (recommendation_result["summary"]),
            },
            message=("تم رفع الصورة وتحليلها بنجاح."),
            status=201,
        )

    @app.get("/api/images/<image_id>")
    def get_image(image_id):
        if not is_valid_resource_id(image_id):
            return error_response("INVALID_IMAGE_ID", "معرف الصورة غير صالح.", 400)

        path = resolve_upload_file(upload_folder, image_id)

        if path is None:
            return error_response("IMAGE_NOT_FOUND", "الصورة غير موجودة.", 404)

        return send_file(path)

    @app.post("/api/images/<image_id>/operations")
    def apply_manual_operation(image_id):
        if not is_valid_resource_id(image_id):
            return error_response("INVALID_IMAGE_ID", "معرف الصورة غير صالح.", 400)

        path = resolve_upload_file(upload_folder, image_id)

        if path is None:
            return error_response("IMAGE_NOT_FOUND", "الصورة غير موجودة.", 404)

        payload = request.get_json(silent=True)

        if not isinstance(payload, dict):
            return error_response(
                "INVALID_REQUEST_BODY", ("يجب إرسال JSON صالح " "لطلب العملية."), 400
            )

        operation_id = payload.get("operation_id")

        parameters = payload.get("parameters", {})

        source_result_id = payload.get("source_result_id")

        if source_result_id is not None:
            if not isinstance(source_result_id, str) or not is_valid_resource_id(source_result_id):
                return error_response(
                    "INVALID_SOURCE_RESULT_ID",
                    "معرف النتيجة المصدرية غير صالح.",
                    400,
                )

        if not isinstance(operation_id, str):
            return error_response("INVALID_OPERATION", "معرف العملية غير صالح.", 400)

        if not isinstance(parameters, dict):
            return error_response(
                "INVALID_OPERATION_PARAMETERS",
                "Parameters يجب أن تكون JSON object.",
                400,
            )

        try:
            get_operation(operation_id)

        except ValueError:
            return error_response(
                "INVALID_OPERATION", "العملية المطلوبة غير معروفة.", 400
            )

        original = read_stored_image(path)

        if original is None:
            return error_response("UNREADABLE_IMAGE", "تعذر قراءة الصورة المخزنة.", 500)

        working_image = original

        if source_result_id:
            source_result_path = resolve_result_file(result_folder, source_result_id)
            source_manifest = read_manual_manifest(result_folder, source_result_id)

            if source_result_path is None or source_manifest is None:
                return error_response(
                    "SOURCE_RESULT_NOT_FOUND",
                    "النتيجة المعتمدة المصدرية غير موجودة أو غير صالحة للسلسلة اليدوية.",
                    404,
                )

            if source_manifest.get("source_image_id") != image_id:
                return error_response(
                    "SOURCE_RESULT_MISMATCH",
                    "لا يمكن استخدام نتيجة مرتبطة بوثيقة أخرى.",
                    400,
                )

            working_image = read_stored_image(source_result_path)
            if working_image is None:
                return error_response(
                    "UNREADABLE_SOURCE_RESULT",
                    "تعذر قراءة النتيجة المعتمدة المصدرية.",
                    500,
                )

        try:
            processed = apply_operation(operation_id, working_image, parameters)


        except (ValueError, TypeError) as error:
            return error_response(
                "INVALID_OPERATION_PARAMETERS",
                "Parameters العملية غير صالحة.",
                400,
                details=str(error),
            )

        except cv2.error:
            return error_response("PROCESSING_FAILED", "فشلت عملية معالجة الصورة.", 500)

        preservation = None

        verification = {
            "status": "available",
            "message": ("تم تنفيذ Preservation " "Verification."),
        }

        try:
            preservation = verify_preservation(original, processed)

        except Exception:
            verification = {
                "status": "unavailable",
                "message": (
                    "تم إنشاء النتيجة، لكن " "تعذر تنفيذ Preservation " "Verification."
                ),
            }

        try:
            result_id, _ = save_manual_result(
                processed,
                result_folder,
                source_image_id=image_id,
                parent_result_id=source_result_id,
                operation_id=operation_id,
                parameters=parameters,
            )


        except (ValueError, RuntimeError, OSError):
            return error_response("PROCESSING_FAILED", "تعذر حفظ نتيجة المعالجة.", 500)

        return success_response(
            data={
                "result": (build_result_metadata(result_id, processed, image_id, origin="manual", status="approved", parent_result_id=source_result_id, operation_id=operation_id, method_used="manual")),
                "operation": {"id": operation_id, "parameters": parameters},
                "source_result_id": source_result_id,
                "preservation": (preservation),
                "verification": (verification),
            },
            message=("تم تنفيذ العملية وإنشاء النتيجة."),
            status=201,
        )

    @app.post("/api/images/<image_id>/preview")
    def preview_manual_operation(image_id):
        if not is_valid_resource_id(image_id):
            return error_response("INVALID_IMAGE_ID", "معرف الصورة غير صالح.", 400)

        path = resolve_upload_file(upload_folder, image_id)
        if path is None:
            return error_response("IMAGE_NOT_FOUND", "الصورة غير موجودة.", 404)

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return error_response(
                "INVALID_REQUEST_BODY",
                "يجب إرسال JSON صالح لطلب المعاينة.",
                400,
            )

        operation_id = payload.get("operation_id")
        parameters = payload.get("parameters", {})

        if not isinstance(operation_id, str):
            return error_response("INVALID_OPERATION", "معرف العملية غير صالح.", 400)
        if not isinstance(parameters, dict):
            return error_response(
                "INVALID_OPERATION_PARAMETERS",
                "Parameters يجب أن تكون JSON object.",
                400,
            )

        try:
            get_operation(operation_id)
        except ValueError:
            return error_response(
                "INVALID_OPERATION",
                "العملية المطلوبة غير متاحة للمعاينة.",
                400,
            )

        source_result_id = payload.get("source_result_id")

        if source_result_id is not None:
            if not isinstance(source_result_id, str) or not is_valid_resource_id(source_result_id):
                return error_response(
                   "INVALID_SOURCE_RESULT_ID",
                    "معرف النتيجة المصدرية غير صالح.",
                    400,
                )

        original = read_stored_image(path)
        if original is None:
            return error_response("UNREADABLE_IMAGE", "تعذر قراءة الصورة المخزنة.", 500)

        working_image = original

        if source_result_id:
            source_result_path = resolve_result_file(result_folder, source_result_id)
            source_manifest = read_manual_manifest(result_folder, source_result_id)

            if source_result_path is None or source_manifest is None:
                return error_response(
                    "SOURCE_RESULT_NOT_FOUND",
                    "النتيجة المعتمدة المصدرية غير موجودة أو غير صالحة.",
                    404,
                )

            source_kind = source_manifest.get("kind")
            source_origin = source_manifest.get("origin")
            source_status = source_manifest.get("status")
            
            is_approved_manual_source = source_kind == "manual_approved"
            is_approved_unified_source = (
                source_origin in {"manual", "preparation"}
                and source_status == "approved"
            )
            is_approved_smart_source = (
                source_origin == "smart"
                and source_status in {
                    "accepted",
                    "accepted_with_caution",
                    "review_required",
                    "no_treatment",
                    "unchanged_due_to_risk",
                }
            )

            if not (is_approved_manual_source or is_approved_unified_source or is_approved_smart_source):
                return error_response(
                    "INVALID_SOURCE_RESULT_KIND",
                    "النتيجة المصدرية يجب أن تكون نتيجة Manual أو Smart أو Preparation صالحة.",
                    400,
                )



            working_image = read_stored_image(source_result_path)
            if working_image is None:
                return error_response(
                    "UNREADABLE_SOURCE_RESULT",
                    "تعذر قراءة النتيجة اليدوية المعتمدة.",
                    500,
                )

        try:
            if operation_id == "crop":
                processed = apply_operation(operation_id, working_image, parameters)
                processed = resize_for_preview(processed)
            else:
                preview_source = resize_for_preview(working_image)
                processed = apply_operation(operation_id, preview_source, parameters)

            preferred_preview_format = request.headers.get("X-Preview-Format", "png")
            preview = build_preview_payload(processed, preferred_preview_format)
        except (ValueError, TypeError) as error:
            return error_response(
                "INVALID_OPERATION_PARAMETERS",
                "Parameters العملية غير صالحة.",
                400,
                details=str(error),
            )
        except cv2.error:
            return error_response("PROCESSING_FAILED", "فشلت عملية إنشاء المعاينة.", 500)
        except (RuntimeError, OSError):
            return error_response("PROCESSING_FAILED", "تعذر إنشاء المعاينة.", 500)

        return success_response(
            data={
                "preview": preview,
                "source_result_id": source_result_id,
                "operation": {"id": operation_id, "parameters": parameters},
                "verification": {
                    "status": "skipped_for_preview",
                    "message": "تم تخطي Preservation Verification لأن هذه معاينة غير نهائية.",
                },
            },
            message="تم تحديث المعاينة.",
            status=200,
        )
    @app.post("/api/images/<image_id>/pipeline")
    def run_pipeline(image_id):
        if not is_valid_resource_id(image_id):
            return error_response("INVALID_IMAGE_ID", "معرف الصورة غير صالح.", 400)

        path = resolve_upload_file(upload_folder, image_id)

        if path is None:
            return error_response("IMAGE_NOT_FOUND", "الصورة غير موجودة.", 404)

        original = read_stored_image(path)

        if original is None:
            return error_response("UNREADABLE_IMAGE", "تعذر قراءة الصورة المخزنة.", 500)

        try:
            preparation = prepare_document(original)
            preparation_verification = verify_preparation(preparation)
            preparation_used = bool(
                preparation.get("prepared")
                and preparation_verification.get("status") == "accept"
            )
            treatment_input = preparation["image"] if preparation_used else original
            analysis = analyze_image(treatment_input)
            pipeline_result = run_smart_pipeline(treatment_input, analysis)

        except Exception:
            return error_response("PROCESSING_FAILED", "فشل تنفيذ Smart Pipeline.", 500)

        preparation_summary = {
            "used": preparation_used,
            "prepared": bool(preparation.get("prepared")),
            "verification": preparation_verification,
            "reason": preparation.get("reason", ""),
            "method_used": preparation.get("boundary", {}).get("method_used") or ("deskew-only" if preparation.get("deskew", {}).get("applied") else None),
            "boundary_detected": bool(preparation.get("boundary", {}).get("detected")),
            "deskew": preparation.get("deskew"),
            "steps": preparation.get("steps", []),
        }
        preparation_step = {
            "operation_id": "document_prepare",
            "parameters": {},
            "reason": (
                "تم إدراج تجهيز الوثيقة تلقائياً قبل المعالجة الذكية بعد نجاح التحقق المحافظ."
                if preparation_used
                else "لم تُدرج Preparation تلقائياً لأن التحقق المحافظ لم يسمح باستخدامها؛ بقيت الصورة الأصلية."
            ),
            "mode": "preparation",
            "execution_status": "accepted" if preparation_used else "deferred",
            "decision": {
                "accepted": preparation_used,
                "status": "accepted" if preparation_used else "review_required",
                "message": (
                    "تم اعتماد تجهيز الوثيقة تلقائياً قبل Smart Pipeline."
                    if preparation_used
                    else "يمكن مراجعة تجهيز الوثيقة يدوياً من قسم تجهيز الوثيقة."
                ),
            },
        }
        pipeline_result["steps"] = [preparation_step, *pipeline_result.get("steps", [])]
        final_image = pipeline_result["image"]

        try:
            pipeline_decision = pipeline_result.get("decision", {})
            pipeline_status = pipeline_decision.get("status", "review_required")

            result_id, _ = save_result_artifact(
                final_image,
                result_folder,
                source_image_id=image_id,
                origin="smart",
                status=pipeline_status,
                parent_result_id=None,
                extra={"decision": pipeline_decision},
            )


        except (ValueError, RuntimeError, OSError):
            return error_response(
                "PROCESSING_FAILED", "تعذر حفظ نتيجة Smart Pipeline.", 500
            )

        binarization_results = []

        for candidate in pipeline_result["binarization_candidates"]:
            candidate_image = candidate["image"]

            try:
                candidate_decision = candidate.get("decision", {})

                candidate_id, _ = save_result_artifact(
                    candidate_image,
                    result_folder,
                    source_image_id=image_id,
                    origin="smart_candidate",
                    status=candidate_decision.get("status", "review_required"),
                    parent_result_id=result_id,
                    operation_id=candidate.get("operation_id"),
                    parameters=candidate.get("parameters", {}),
                )


            except (ValueError, RuntimeError, OSError):
                return error_response(
                    "PROCESSING_FAILED",
                    ("تعذر حفظ أحد " "Binarization Candidates."),
                    500,
                )

            binarization_results.append(
                {
                    "result": (
                        build_result_metadata(candidate_id, candidate_image, image_id, origin="smart_candidate", status=candidate_decision.get("status", "review_required"), parent_result_id=result_id, operation_id=candidate.get("operation_id"))
                    ),
                    "operation_id": (candidate["operation_id"]),
                    "parameters": (candidate["parameters"]),
                    "reason": (candidate["reason"]),
                    "risk": (candidate["risk"]),
                    "preservation": (candidate["preservation"]),
                    "decision": (candidate["decision"]),
                }
            )

        return success_response(
            data={
                "result": (build_result_metadata(result_id, final_image, image_id, origin="smart", status=pipeline_status, parent_result_id=None)),
                "decision": (pipeline_result["decision"]),
                "steps": (pipeline_result["steps"]),
                "preservation": (pipeline_result["preservation"]),
                "recommendation": (pipeline_result["recommendation"]),
                "binarization_candidates": (binarization_results),
                                "policy": (pipeline_result["policy"]),
                "preparation": preparation_summary,

            },
            message=("تم تنفيذ Smart Pipeline."),
            status=201,
        )

    @app.get("/api/results/<result_id>")
    def get_result(result_id):
        if not is_valid_resource_id(result_id):
            return error_response("INVALID_RESULT_ID", "معرف النتيجة غير صالح.", 400)

        path = resolve_result_file(result_folder, result_id)

        if path is None:
            return error_response("RESULT_NOT_FOUND", "النتيجة غير موجودة.", 404)

        return send_file(path, mimetype="image/png")

    @app.get("/api/results/<result_id>/download")
    def download_result(result_id):
        if not is_valid_resource_id(result_id):
            return error_response("INVALID_RESULT_ID", "معرف النتيجة غير صالح.", 400)

        path = resolve_result_file(result_folder, result_id)

        if path is None:
            return error_response("RESULT_NOT_FOUND", "النتيجة غير موجودة.", 404)

        return send_file(
            path,
            mimetype="image/png",
            as_attachment=True,
            download_name=(f"{result_id}.png"),
        )

    @app.get("/api/images/<image_id>/boundary")
    def detect_image_boundary(image_id):
        if not is_valid_resource_id(image_id):
            return error_response("INVALID_IMAGE_ID", "معرف الصورة غير صالح.", 400)

        path = resolve_upload_file(upload_folder, image_id)

        if path is None:
            return error_response("IMAGE_NOT_FOUND", "الصورة غير موجودة.", 404)

        image = read_stored_image(path)

        if image is None:
            return error_response("UNREADABLE_IMAGE", "تعذر قراءة الصورة المخزنة.", 500)

        try:
            boundary = detect_document_boundary(image)

        except ValueError as error:
            return error_response(
                "BOUNDARY_INPUT_INVALID",
                "تعذر تحليل حدود الوثيقة.",
                400,
                details=str(error),
            )

        except Exception:
            return error_response(
                "BOUNDARY_DETECTION_FAILED", "حدث خطأ أثناء اكتشاف حدود الوثيقة.", 500
            )

        return success_response(
            data={"image_id": image_id, "boundary": boundary},
            message=("تم تحليل حدود الوثيقة بنجاح."),
        )

    @app.post("/api/images/<image_id>/preparation/preview")
    def preview_preparation(image_id):
        if not is_valid_resource_id(image_id):
            return error_response("INVALID_IMAGE_ID", "معرف الصورة غير صالح.", 400)

        upload_path = resolve_upload_file(upload_folder, image_id)
        if upload_path is None:
            return error_response("IMAGE_NOT_FOUND", "الصورة غير موجودة.", 404)

        image = read_stored_image(upload_path)
        if image is None:
            return error_response("UNREADABLE_IMAGE", "تعذر قراءة الصورة المخزنة.", 500)

        try:
            preparation = prepare_document(
                image,
                boundary_detector=detect_preparation_boundary,
            )
        except (ValueError, RuntimeError) as error:
            return error_response(
                "PREPARATION_FAILED",
                "تعذر تنفيذ Preparation.",
                422,
                details=str(error),
            )
        except Exception:
            return error_response(
                "PREPARATION_FAILED",
                "حدث خطأ أثناء تنفيذ Preparation.",
                500,
            )

        preparation_metadata = preparation_public_metadata(preparation)
        boundary = preparation_metadata.get("boundary", {})
        deskew_metadata = preparation_metadata.get("deskew", {})
        preparation_status = boundary.get("status", "reject")
        if not boundary.get("detected") and deskew_metadata.get("applied"):
            preparation_status = "review_required"

        if not preparation.get("prepared"):
            return error_response(
                "PREPARATION_REJECTED",
                "لم ينتج Preparation مرشحًا صالحًا للمراجعة.",
                422,
                details={
                    "preparation": preparation_metadata,
                    "image_id": image_id,
                },
            )

        preparation_metadata["source_image_id"] = image_id
        preparation_metadata["method_used"] = boundary.get("method_used") or (
            "deskew-only" if deskew_metadata.get("applied") else None
        )

        try:
            preparation_id, _ = save_preparation_preview(
                preparation["image"],
                preparation_preview_folder,
                {
                    "source_image_id": image_id,
                    "method_used": preparation_metadata.get("method_used"),
                    "preparation": preparation_metadata,
                },
            )
        except (ValueError, RuntimeError, OSError):
            return error_response(
                "PREPARATION_PREVIEW_SAVE_FAILED",
                "تعذر حفظ معاينة Preparation.",
                500,
            )

        return success_response(
            data={
                "preparation_id": preparation_id,
                "image_id": image_id,
                "status": preparation_status,
                "method_used": preparation_metadata.get("method_used"),
                "preparation": preparation_metadata,
                "preview": {
                    "id": preparation_id,
                    "url": f"/api/preparation/{preparation_id}",
                    **image_dimensions(preparation["image"]),
                },
            },
            message="تم إنشاء معاينة Preparation.",
            status=200,
        )

    @app.get("/api/preparation/<preparation_id>")
    def get_preparation_preview(preparation_id):
        path = resolve_preparation_preview_file(
            preparation_preview_folder,
            preparation_id,
        )

        if path is None:
            return error_response(
                "PREPARATION_NOT_FOUND",
                "معاينة Preparation غير موجودة.",
                404,
            )

        return send_file(path, mimetype="image/png")

    @app.post("/api/images/<image_id>/preparation/<preparation_id>/approve")
    def approve_preparation(image_id, preparation_id):
        if not is_valid_resource_id(image_id):
            return error_response("INVALID_IMAGE_ID", "معرف الصورة غير صالح.", 400)

        manifest = read_preparation_manifest(
            preparation_preview_folder,
            preparation_id,
        )

        if manifest is None:
            return error_response(
                "PREPARATION_NOT_FOUND",
                "معاينة Preparation غير موجودة.",
                404,
            )

        if manifest.get("source_image_id") != image_id:
            return error_response(
                "PREPARATION_SOURCE_MISMATCH",
                "المعاينة لا تخص هذه الصورة.",
                400,
            )

        if manifest.get("status") != "preview":
            return error_response(
                "PREPARATION_NOT_APPROVABLE",
                "هذه المعاينة لم تعد قابلة للاعتماد.",
                409,
            )

        preview_path = resolve_preparation_preview_file(
            preparation_preview_folder,
            preparation_id,
        )
        prepared_image = read_stored_image(preview_path)

        if prepared_image is None:
            return error_response(
                "UNREADABLE_PREPARATION",
                "تعذر قراءة معاينة Preparation.",
                500,
            )

        try:
            result_id, _ = save_result_artifact(
                prepared_image,
                result_folder,
                source_image_id=image_id,
                origin="preparation",
                status="approved",
                parent_result_id=None,
                method_used=manifest.get("method_used"),
                extra={
                    "preparation_id": preparation_id,
                    "preparation": manifest.get("preparation", {}),
                },
            )
        except (ValueError, RuntimeError, OSError):
            return error_response(
                "PREPARATION_RESULT_SAVE_FAILED",
                "تعذر حفظ نتيجة Preparation.",
                500,
            )

        manifest["status"] = "approved"
        manifest["approved_result_id"] = result_id

        preparation_manifest_path(
            preparation_preview_folder,
            preparation_id,
        ).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return success_response(
            data={
                "preparation_id": preparation_id,
                "result": build_result_metadata(
                    result_id,
                    prepared_image,
                    image_id,
                    origin="preparation",
                    status="approved",
                    parent_result_id=None,
                    method_used=manifest.get("method_used"),
                ),
                "preparation": manifest.get("preparation", {}),
            },
            message="تم اعتماد نتيجة Preparation.",
            status=201,
        )

    @app.post("/api/images/<image_id>/preparation/<preparation_id>/reject")
    def reject_preparation(image_id, preparation_id):
        if not is_valid_resource_id(image_id):
            return error_response("INVALID_IMAGE_ID", "معرف الصورة غير صالح.", 400)

        manifest = read_preparation_manifest(
            preparation_preview_folder,
            preparation_id,
        )

        if manifest is None:
            return error_response(
                "PREPARATION_NOT_FOUND",
                "معاينة Preparation غير موجودة.",
                404,
            )

        if manifest.get("source_image_id") != image_id:
            return error_response(
                "PREPARATION_SOURCE_MISMATCH",
                "المعاينة لا تخص هذه الصورة.",
                400,
            )

        manifest["status"] = "rejected"
        preparation_manifest_path(
            preparation_preview_folder,
            preparation_id,
        ).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        preview_path = resolve_preparation_preview_file(
            preparation_preview_folder,
            preparation_id,
        )
        if preview_path is not None:
            preview_path.unlink(missing_ok=True)

        return success_response(
            data={
                "preparation_id": preparation_id,
                "image_id": image_id,
                "status": "rejected",
            },
            message="تم رفض معاينة Preparation دون تغيير الصورة الأصلية.",
            status=200,
        )


    @app.errorhandler(413)
    def request_too_large(error):
        return error_response("FILE_TOO_LARGE", "حجم الملف أكبر من الحد المسموح.", 413)

    @app.errorhandler(404)
    def route_not_found(error):
        return error_response("NOT_FOUND", "المسار المطلوب غير موجود.", 404)

    @app.errorhandler(500)
    def internal_error(error):
        return error_response("INTERNAL_ERROR", "حدث خطأ داخلي غير متوقع.", 500)

    return app
