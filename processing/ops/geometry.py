import cv2
import numpy as np

from .common import _validate_image

def rotate_right(image):
    _validate_image(image)
    return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)


def rotate_left(image):
    _validate_image(image)
    return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)


def flip_vertical(image):
    _validate_image(image)
    return cv2.flip(image, 0)


def flip_horizontal(image):
    _validate_image(image)
    return cv2.flip(image, 1)


def crop(image, x, y, width, height):
    _validate_image(image)

    values = (x, y, width, height)
    if not all(np.isfinite(float(value)) for value in values):
        raise ValueError("crop parameters must be finite numbers.")

    image_height, image_width = image.shape[:2]
    x = int(round(float(x)))
    y = int(round(float(y)))
    width = int(round(float(width)))
    height = int(round(float(height)))

    if x < 0 or y < 0 or width <= 0 or height <= 0:
        raise ValueError("crop rectangle must have positive dimensions and non-negative origin.")
    if x + width > image_width or y + height > image_height:
        raise ValueError("crop rectangle must stay inside the image bounds.")

    return image[y:y + height, x:x + width].copy()


def deskew(image, angle):
    _validate_image(image)

    angle = float(angle)

    if abs(angle) > 45:
        raise ValueError("angle must be between -45 and 45 degrees.")

    h, w = image.shape[:2]
    # مركز الصورة الأصلية
    center = (w / 2.0, h / 2.0)

    # حساب مصفوفة الدوران
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

    # حساب الأبعاد الجديدة لتستوعب الصورة كاملة بعد الدوران
    cos_val = np.abs(matrix[0, 0])
    sin_val = np.abs(matrix[0, 1])

    new_w = int((h * sin_val) + (w * cos_val))
    new_h = int((h * cos_val) + (w * sin_val))

    # تعديل الإزاحة لتكون نقطة الدوران في مركز الصورة الجديد تماماً
    matrix[0, 2] += (new_w / 2.0) - center[0]
    matrix[1, 2] += (new_h / 2.0) - center[1]

    # تحديد لون الخلفية للفراغات الناتجة
    if image.ndim == 2:
        border_value = 255
    elif image.shape[2] == 3:
        border_value = (255, 255, 255)
    else:
        border_value = (255, 255, 255, 0)

    # تطبيق التحويل
    return cv2.warpAffine(
        image,
        matrix,
        (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border_value,
    )

