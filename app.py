from pathlib import Path
from uuid import UUID, uuid4

import cv2
import numpy as np
from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_file
)
from processing.analyzer import analyze_image
from processing.operations import apply_operation, get_operation
from processing.pipeline import run_smart_pipeline
from processing.preservation import verify_preservation
from processing.recommender import recommend_treatment


BASE_DIR = Path(__file__).resolve().parent

ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png"
}

MAX_UPLOAD_SIZE = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 30_000_000


def success_response(
    data=None,
    message="Request completed successfully.",
    status=200
):
    return jsonify({
        "success": True,
        "message": message,
        "data": data,
        "error": None
    }), status


def error_response(
    code,
    message,
    status,
    details=None
):
    return jsonify({
        "success": False,
        "message": message,
        "data": None,
        "error": {
            "code": code,
            "details": details
        }
    }), status


def is_valid_resource_id(value):
    if not isinstance(value, str):
        return False

    try:
        return (
            UUID(hex=value).hex
            == value.lower()
        )

    except (ValueError, AttributeError):
        return False


def get_extension(filename):
    if not isinstance(filename, str):
        return ""

    clean_name = (
        filename
        .replace("\\", "/")
        .rsplit("/", 1)[-1]
    )

    suffix = Path(
        clean_name
    ).suffix.lower()

    return suffix.lstrip(".")


def display_filename(filename):
    return (
        filename
        .replace("\\", "/")
        .rsplit("/", 1)[-1]
    )


def decode_image(raw_data):
    if not raw_data:
        return None

    buffer = np.frombuffer(
        raw_data,
        dtype=np.uint8
    )

    return cv2.imdecode(
        buffer,
        cv2.IMREAD_UNCHANGED
    )


def read_stored_image(path):
    try:
        raw_data = path.read_bytes()

    except OSError:
        return None

    return decode_image(
        raw_data
    )


def image_dimensions(image):
    height, width = image.shape[:2]

    channels = (
        1
        if image.ndim == 2
        else image.shape[2]
    )

    return {
        "width": int(width),
        "height": int(height),
        "channels": int(channels)
    }


def resolve_upload_file(
    folder,
    image_id
):
    if not is_valid_resource_id(
        image_id
    ):
        return None

    folder = Path(folder)

    for extension in (
        ALLOWED_EXTENSIONS
    ):
        candidate = (
            folder
            / f"{image_id}.{extension}"
        )

        if candidate.is_file():
            return candidate

    return None


def resolve_result_file(
    folder,
    result_id
):
    if not is_valid_resource_id(
        result_id
    ):
        return None

    candidate = (
        Path(folder)
        / f"{result_id}.png"
    )

    if candidate.is_file():
        return candidate

    return None


def save_png_result(
    image,
    folder
):
    if (
        image is None
        or not isinstance(
            image,
            np.ndarray
        )
        or image.size == 0
    ):
        raise ValueError(
            "Invalid result image."
        )

    if image.dtype != np.uint8:
        raise ValueError(
            "Result image must be 8-bit."
        )

    success, encoded = cv2.imencode(
        ".png",
        image
    )

    if not success:
        raise RuntimeError(
            "Could not encode result image."
        )

    result_id = uuid4().hex

    output_path = (
        Path(folder)
        / f"{result_id}.png"
    )

    output_path.write_bytes(
        encoded.tobytes()
    )

    return result_id, output_path


def build_result_metadata(
    result_id,
    image,
    source_image_id
):
    return {
        "id": result_id,
        "source_image_id": (
            source_image_id
        ),
        "format": "png",
        **image_dimensions(image)
    }


def create_app(test_config=None):
    app = Flask(__name__)

    app.config.from_mapping(
        MAX_CONTENT_LENGTH=(
            MAX_UPLOAD_SIZE
        ),
        MAX_IMAGE_PIXELS=(
            MAX_IMAGE_PIXELS
        ),
        UPLOAD_FOLDER=(
            BASE_DIR
            / "storage"
            / "uploads"
        ),
        RESULT_FOLDER=(
            BASE_DIR
            / "storage"
            / "results"
        )
    )

    if test_config:
        app.config.update(
            test_config
        )

    upload_folder = Path(
        app.config[
            "UPLOAD_FOLDER"
        ]
    )

    result_folder = Path(
        app.config[
            "RESULT_FOLDER"
        ]
    )

    upload_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    result_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    @app.get("/")
    def index():
        return render_template(
            "index.html"
        )

    @app.post("/api/images")
    def upload_image():
        uploaded_file = (
            request.files.get(
                "image"
            )
        )

        if uploaded_file is None:
            return error_response(
                "NO_FILE",
                "لم يتم إرسال ملف صورة.",
                400
            )

        filename = (
            uploaded_file.filename
            or ""
        )

        if not filename.strip():
            return error_response(
                "EMPTY_FILENAME",
                "اسم الملف فارغ.",
                400
            )

        extension = get_extension(
            filename
        )

        if (
            extension
            not in ALLOWED_EXTENSIONS
        ):
            return error_response(
                "UNSUPPORTED_FILE_TYPE",
                "نوع الملف غير مدعوم.",
                400
            )

        raw_data = (
            uploaded_file.read()
        )

        if not raw_data:
            return error_response(
                "UNREADABLE_IMAGE",
                "ملف الصورة فارغ أو غير قابل للقراءة.",
                400
            )

        image = decode_image(
            raw_data
        )

        if image is None:
            return error_response(
                "UNREADABLE_IMAGE",
                "تعذر قراءة الملف كصورة صالحة.",
                400
            )

        if image.dtype != np.uint8:
            return error_response(
                "UNSUPPORTED_IMAGE_DEPTH",
                (
                    "عمق الصورة غير مدعوم. "
                    "استخدم صورة JPG أو PNG "
                    "بعمق 8-bit."
                ),
                400
            )

        height, width = (
            image.shape[:2]
        )

        pixel_count = (
            int(height)
            * int(width)
        )

        if (
            pixel_count
            > app.config[
                "MAX_IMAGE_PIXELS"
            ]
        ):
            return error_response(
                "IMAGE_DIMENSIONS_TOO_LARGE",
                "أبعاد الصورة أكبر من الحد المسموح.",
                400
            )

        try:
            analysis = analyze_image(
                image
            )

            recommendation_result = (
                recommend_treatment(
                    analysis
                )
            )

        except Exception:
            return error_response(
                "PROCESSING_FAILED",
                (
                    "تعذر تحليل الصورة "
                    "وإنشاء التوصيات."
                ),
                500
            )

        image_id = uuid4().hex

        output_path = (
            upload_folder
            / f"{image_id}.{extension}"
        )

        try:
            output_path.write_bytes(
                raw_data
            )

        except OSError:
            return error_response(
                "INTERNAL_ERROR",
                "تعذر حفظ الصورة.",
                500
            )

        return success_response(
            data={
                "image": {
                    "image_id": image_id,
                    "original_name": (
                        display_filename(
                            filename
                        )
                    ),
                    "format": extension,
                    **image_dimensions(
                        image
                    )
                },
                "analysis": {
                    "dimensions": (
                        analysis[
                            "dimensions"
                        ]
                    ),
                    "metrics": (
                        analysis[
                            "metrics"
                        ]
                    )
                },
                "diagnoses": (
                    analysis[
                        "diagnoses"
                    ]
                ),
                "preservation_profile": (
                    analysis[
                        "preservation_profile"
                    ]
                ),
                "recommendations": (
                    recommendation_result[
                        "recommendations"
                    ]
                ),
                "excluded_from_automatic": (
                    recommendation_result[
                        "excluded_from_automatic"
                    ]
                ),
                "recommendation_summary": (
                    recommendation_result[
                        "summary"
                    ]
                )
            },
            message=(
                "تم رفع الصورة وتحليلها بنجاح."
            ),
            status=201
        )

    @app.get(
        "/api/images/<image_id>"
    )
    def get_image(image_id):
        if not is_valid_resource_id(
            image_id
        ):
            return error_response(
                "INVALID_IMAGE_ID",
                "معرف الصورة غير صالح.",
                400
            )

        path = resolve_upload_file(
            upload_folder,
            image_id
        )

        if path is None:
            return error_response(
                "IMAGE_NOT_FOUND",
                "الصورة غير موجودة.",
                404
            )

        return send_file(
            path
        )

    @app.post(
        "/api/images/<image_id>/operations"
    )
    def apply_manual_operation(
        image_id
    ):
        if not is_valid_resource_id(
            image_id
        ):
            return error_response(
                "INVALID_IMAGE_ID",
                "معرف الصورة غير صالح.",
                400
            )

        path = resolve_upload_file(
            upload_folder,
            image_id
        )

        if path is None:
            return error_response(
                "IMAGE_NOT_FOUND",
                "الصورة غير موجودة.",
                404
            )

        payload = request.get_json(
            silent=True
        )

        if not isinstance(
            payload,
            dict
        ):
            return error_response(
                "INVALID_REQUEST_BODY",
                (
                    "يجب إرسال JSON صالح "
                    "لطلب العملية."
                ),
                400
            )

        operation_id = payload.get(
            "operation_id"
        )

        parameters = payload.get(
            "parameters",
            {}
        )

        if not isinstance(
            operation_id,
            str
        ):
            return error_response(
                "INVALID_OPERATION",
                "معرف العملية غير صالح.",
                400
            )

        if not isinstance(
            parameters,
            dict
        ):
            return error_response(
                "INVALID_OPERATION_PARAMETERS",
                "Parameters يجب أن تكون JSON object.",
                400
            )

        try:
            get_operation(
                operation_id
            )

        except ValueError:
            return error_response(
                "INVALID_OPERATION",
                "العملية المطلوبة غير معروفة.",
                400
            )

        original = read_stored_image(
            path
        )

        if original is None:
            return error_response(
                "UNREADABLE_IMAGE",
                "تعذر قراءة الصورة المخزنة.",
                500
            )

        try:
            processed = apply_operation(
                operation_id,
                original,
                parameters
            )

        except (
            ValueError,
            TypeError
        ) as error:
            return error_response(
                "INVALID_OPERATION_PARAMETERS",
                "Parameters العملية غير صالحة.",
                400,
                details=str(error)
            )

        except cv2.error:
            return error_response(
                "PROCESSING_FAILED",
                "فشلت عملية معالجة الصورة.",
                500
            )

        preservation = None

        verification = {
            "status": "available",
            "message": (
                "تم تنفيذ Preservation "
                "Verification."
            )
        }

        try:
            preservation = (
                verify_preservation(
                    original,
                    processed
                )
            )

        except Exception:
            verification = {
                "status": "unavailable",
                "message": (
                    "تم إنشاء النتيجة، لكن "
                    "تعذر تنفيذ Preservation "
                    "Verification."
                )
            }

        try:
            result_id, _ = (
                save_png_result(
                    processed,
                    result_folder
                )
            )

        except (
            ValueError,
            RuntimeError,
            OSError
        ):
            return error_response(
                "PROCESSING_FAILED",
                "تعذر حفظ نتيجة المعالجة.",
                500
            )

        return success_response(
            data={
                "result": (
                    build_result_metadata(
                        result_id,
                        processed,
                        image_id
                    )
                ),
                "operation": {
                    "id": operation_id,
                    "parameters": parameters
                },
                "preservation": (
                    preservation
                ),
                "verification": (
                    verification
                )
            },
            message=(
                "تم تنفيذ العملية وإنشاء النتيجة."
            ),
            status=201
        )

    @app.post(
        "/api/images/<image_id>/pipeline"
    )
    def run_pipeline(image_id):
        if not is_valid_resource_id(
            image_id
        ):
            return error_response(
                "INVALID_IMAGE_ID",
                "معرف الصورة غير صالح.",
                400
            )

        path = resolve_upload_file(
            upload_folder,
            image_id
        )

        if path is None:
            return error_response(
                "IMAGE_NOT_FOUND",
                "الصورة غير موجودة.",
                404
            )

        original = read_stored_image(
            path
        )

        if original is None:
            return error_response(
                "UNREADABLE_IMAGE",
                "تعذر قراءة الصورة المخزنة.",
                500
            )

        try:
            analysis = analyze_image(
                original
            )

            pipeline_result = (
                run_smart_pipeline(
                    original,
                    analysis
                )
            )

        except Exception:
            return error_response(
                "PROCESSING_FAILED",
                "فشل تنفيذ Smart Pipeline.",
                500
            )

        final_image = (
            pipeline_result[
                "image"
            ]
        )

        try:
            result_id, _ = (
                save_png_result(
                    final_image,
                    result_folder
                )
            )

        except (
            ValueError,
            RuntimeError,
            OSError
        ):
            return error_response(
                "PROCESSING_FAILED",
                "تعذر حفظ نتيجة Smart Pipeline.",
                500
            )

        binarization_results = []

        for candidate in (
            pipeline_result[
                "binarization_candidates"
            ]
        ):
            candidate_image = (
                candidate[
                    "image"
                ]
            )

            try:
                candidate_id, _ = (
                    save_png_result(
                        candidate_image,
                        result_folder
                    )
                )

            except (
                ValueError,
                RuntimeError,
                OSError
            ):
                return error_response(
                    "PROCESSING_FAILED",
                    (
                        "تعذر حفظ أحد "
                        "Binarization Candidates."
                    ),
                    500
                )

            binarization_results.append({
                "result": (
                    build_result_metadata(
                        candidate_id,
                        candidate_image,
                        image_id
                    )
                ),
                "operation_id": (
                    candidate[
                        "operation_id"
                    ]
                ),
                "parameters": (
                    candidate[
                        "parameters"
                    ]
                ),
                "reason": (
                    candidate[
                        "reason"
                    ]
                ),
                "risk": (
                    candidate[
                        "risk"
                    ]
                ),
                "preservation": (
                    candidate[
                        "preservation"
                    ]
                ),
                "decision": (
                    candidate[
                        "decision"
                    ]
                )
            })

        return success_response(
            data={
                "result": (
                    build_result_metadata(
                        result_id,
                        final_image,
                        image_id
                    )
                ),
                "decision": (
                    pipeline_result[
                        "decision"
                    ]
                ),
                "steps": (
                    pipeline_result[
                        "steps"
                    ]
                ),
                "preservation": (
                    pipeline_result[
                        "preservation"
                    ]
                ),
                "recommendation": (
                    pipeline_result[
                        "recommendation"
                    ]
                ),
                "binarization_candidates": (
                    binarization_results
                ),
                "policy": (
                    pipeline_result[
                        "policy"
                    ]
                )
            },
            message=(
                "تم تنفيذ Smart Pipeline."
            ),
            status=201
        )

    @app.get(
        "/api/results/<result_id>"
    )
    def get_result(result_id):
        if not is_valid_resource_id(
            result_id
        ):
            return error_response(
                "INVALID_RESULT_ID",
                "معرف النتيجة غير صالح.",
                400
            )

        path = resolve_result_file(
            result_folder,
            result_id
        )

        if path is None:
            return error_response(
                "RESULT_NOT_FOUND",
                "النتيجة غير موجودة.",
                404
            )

        return send_file(
            path,
            mimetype="image/png"
        )

    @app.get(
        "/api/results/<result_id>/download"
    )
    def download_result(result_id):
        if not is_valid_resource_id(
            result_id
        ):
            return error_response(
                "INVALID_RESULT_ID",
                "معرف النتيجة غير صالح.",
                400
            )

        path = resolve_result_file(
            result_folder,
            result_id
        )

        if path is None:
            return error_response(
                "RESULT_NOT_FOUND",
                "النتيجة غير موجودة.",
                404
            )

        return send_file(
            path,
            mimetype="image/png",
            as_attachment=True,
            download_name=(
                f"{result_id}.png"
            )
        )

    @app.errorhandler(413)
    def request_too_large(error):
        return error_response(
            "FILE_TOO_LARGE",
            "حجم الملف أكبر من الحد المسموح.",
            413
        )

    @app.errorhandler(404)
    def route_not_found(error):
        return error_response(
            "NOT_FOUND",
            "المسار المطلوب غير موجود.",
            404
        )

    @app.errorhandler(500)
    def internal_error(error):
        return error_response(
            "INTERNAL_ERROR",
            "حدث خطأ داخلي غير متوقع.",
            500
        )

    return app
