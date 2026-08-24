from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path('/home/ubuntu/image_project_split')
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
from app import create_app  # noqa: E402


def rotated_line_image():
    image = np.full((600, 800, 3), 255, dtype=np.uint8)
    for y in range(180, 480, 55):
        cv2.line(image, (120, y), (680, y), (0, 0, 0), 4)
    matrix = cv2.getRotationMatrix2D((400.0, 300.0), 6.0, 1.0)
    return cv2.warpAffine(
        image, matrix, (800, 600), flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255)
    )


ok, encoded = cv2.imencode('.png', rotated_line_image())
assert ok
app = create_app({
    'TESTING': True,
    'UPLOAD_FOLDER': ROOT / 'storage' / 'deskew_test_uploads',
    'RESULT_FOLDER': ROOT / 'storage' / 'deskew_test_results',
    'PREPARATION_PREVIEW_FOLDER': ROOT / 'storage' / 'deskew_test_previews',
})
client = app.test_client()
upload = client.post('/api/images', data={'image': (io.BytesIO(encoded.tobytes()), 'deskew-only.png')}, content_type='multipart/form-data')
assert upload.status_code == 201, upload.get_json()
image_id = upload.get_json()['data']['image']['image_id']
preview = client.post(f'/api/images/{image_id}/preparation/preview')
assert preview.status_code == 200, preview.get_json()
data = preview.get_json()['data']
prep = data['preparation']
assert data['status'] == 'review_required'
assert data['method_used'] == 'deskew-only'
assert prep['boundary']['detected'] is False
assert prep['perspective'] is None
assert prep['deskew']['applied'] is True
assert prep['deskew']['crop_applied'] is False
print('deskew metadata:', prep['deskew'])
assert 'no reliable boundary' in (prep['deskew'].get('crop_reason') or '') or 'no reliable document boundary' in (prep['deskew'].get('crop_reason') or '')
preparation_id = data['preparation_id']
approve = client.post(f'/api/images/{image_id}/preparation/{preparation_id}/approve')
assert approve.status_code == 201, approve.get_json()
result = approve.get_json()['data']['result']
assert result['id']
print('deskew-only preview: 200')
print('deskew-only status: review_required')
print('deskew-only crop: false')
print('deskew-only approval: 201')
