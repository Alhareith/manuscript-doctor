from pathlib import Path
from uuid import UUID, uuid4

import cv2
import numpy as np
from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "storage" / "uploads"
RESULT_FOLDER = BASE_DIR / "storage" / "results"

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}

MAX_UPLOAD_SIZE = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 30_000_000


def success_response(message, data=None, status=200):
    return jsonify({
        "success": True,
        "message": message,
        "data": data,
        "error": None
    }), status


def error_response(code, message, status=400, details=None):
    return jsonify({
        "success": False,
        "message": message,
        "data": None,
        "error": {
            "code": code,
            "details": details
        }
    }), status


def is_valid_id(value):
    try:
        return UUID(hex=value).hex == value.lower()
    except (ValueError, AttributeError):
        return False


def get_extension(filename):
    return Path(filename).suffix.lower().lstrip(".")


def resolve_file(folder, resource_id):
    if not is_valid_id(resource_id):
        return None

    for path in folder.glob(f"{resource_id}.*"):
        if path.is_file() and get_extension(path.name) in ALLOWED_EXTENSIONS:
            return path

    return None


def decode_image(raw_data):
    if not raw_data:
        return None

    buffer = np.frombuffer(raw_data, dtype=np.uint8)

    if buffer.size == 0:
        return None

    return cv2.imdecode(buffer, cv2.IMREAD_UNCHANGED)


def create_app(test_config=None):
    app = Flask(__name__)

    app.config.update(
        MAX_CONTENT_LENGTH=MAX_UPLOAD_SIZE,
        MAX_IMAGE_PIXELS=MAX_IMAGE_PIXELS,
        UPLOAD_FOLDER=UPLOAD_FOLDER,
        RESULT_FOLDER=RESULT_FOLDER
    )

    if test_config:
        app.config.update(test_config)

    upload_folder = Path(app.config["UPLOAD_FOLDER"])
    result_folder = Path(app.config["RESULT_FOLDER"])

    upload_folder.mkdir(parents=True, exist_ok=True)
    result_folder.mkdir(parents=True, exist_ok=True)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/api/images")
    def upload_image():
        if "image" not in request.files:
            return error_response(
                "NO_FILE",
                "لم يتم إرسال صورة.",
                400
            )

        file = request.files["image"]

        filename = (file.filename or "").strip()

        if not filename:
            return error_response(
                "EMPTY_FILENAME",
                "لم يتم اختيار ملف.",
                400
            )

        extension = get_extension(filename)

        if extension not in ALLOWED_EXTENSIONS:
            return error_response(
                "UNSUPPORTED_FILE_TYPE",
                "نوع الملف غير مدعوم. استخدم JPG أو JPEG أو PNG.",
                400
            )

        raw_data = file.read()

        image = decode_image(raw_data)

        if image is None:
            return error_response(
                "UNREADABLE_IMAGE",
                "تعذر قراءة الملف كصورة صالحة.",
                400
            )

        if image.dtype != np.uint8:
            return error_response(
                "UNSUPPORTED_IMAGE_DEPTH",
                "عمق الصورة غير مدعوم. استخدم صورة JPG أو PNG بعمق 8-bit.",
                400
            )
        height, width = image.shape[:2]

        total_pixels = width * height

        if total_pixels > app.config["MAX_IMAGE_PIXELS"]:
            return error_response(
                "IMAGE_DIMENSIONS_TOO_LARGE",
                "أبعاد الصورة أكبر من الحد المسموح.",
                400
            )

        channels = 1 if image.ndim == 2 else image.shape[2]

        image_id = uuid4().hex

        stored_filename = f"{image_id}.{extension}"
        destination = upload_folder / stored_filename

        destination.write_bytes(raw_data)

        original_name = filename.replace("\\", "/").split("/")[-1]

        data = {
            "image": {
                "image_id": image_id,
                "original_name": original_name,
                "width": width,
                "height": height,
                "channels": channels,
                "url": f"/api/images/{image_id}"
            },

            "analysis": None,
            "diagnoses": [],
            "preservation_profile": None,
            "recommendations": []
        }

        return success_response(
            "تم رفع الصورة والتحقق منها بنجاح.",
            data,
            201
        )

    @app.get("/api/images/<image_id>")
    def get_image(image_id):
        image_path = resolve_file(upload_folder, image_id)

        if image_path is None:
            return error_response(
                "IMAGE_NOT_FOUND",
                "الصورة المطلوبة غير موجودة.",
                404
            )

        return send_file(image_path)

    @app.post("/api/images/<image_id>/operations")
    def apply_operation(image_id):
        image_path = resolve_file(upload_folder, image_id)

        if image_path is None:
            return error_response(
                "IMAGE_NOT_FOUND",
                "الصورة المطلوبة غير موجودة.",
                404
            )

        return error_response(
            "FEATURE_NOT_READY",
            "عمليات معالجة الصور ستتم إضافتها في مرحلة المعالجة.",
            501
        )

    @app.post("/api/images/<image_id>/pipeline")
    def run_pipeline(image_id):
        image_path = resolve_file(upload_folder, image_id)

        if image_path is None:
            return error_response(
                "IMAGE_NOT_FOUND",
                "الصورة المطلوبة غير موجودة.",
                404
            )

        return error_response(
            "FEATURE_NOT_READY",
            "المعالجة التلقائية ستتم إضافتها في مرحلة Smart Pipeline.",
            501
        )

    @app.get("/api/results/<result_id>")
    def get_result(result_id):
        result_path = resolve_file(result_folder, result_id)

        if result_path is None:
            return error_response(
                "RESULT_NOT_FOUND",
                "النتيجة المطلوبة غير موجودة.",
                404
            )

        return send_file(result_path)

    @app.get("/api/results/<result_id>/download")
    def download_result(result_id):
        result_path = resolve_file(result_folder, result_id)

        if result_path is None:
            return error_response(
                "RESULT_NOT_FOUND",
                "النتيجة المطلوبة غير موجودة.",
                404
            )

        return send_file(
            result_path,
            as_attachment=True,
            download_name=f"manuscript-result-{result_id}{result_path.suffix}"
        )

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_file(error):
        return error_response(
            "FILE_TOO_LARGE",
            "حجم الملف يتجاوز الحد المسموح.",
            413
        )

    return app


app = create_app()
