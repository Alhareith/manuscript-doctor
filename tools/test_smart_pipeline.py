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


def image_bytes():
    image = np.full((260, 360, 3), 228, dtype=np.uint8)
    cv2.rectangle(image, (25, 25), (335, 235), (245, 245, 245), -1)
    cv2.putText(image, 'DOCUMENT TEST', (45, 95), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (45, 45, 45), 2, cv2.LINE_AA)
    cv2.line(image, (45, 130), (310, 130), (90, 90, 90), 2)
    cv2.rectangle(image, (55, 155), (145, 205), (180, 180, 180), 2)
    cv2.circle(image, (260, 175), 28, (70, 70, 70), 2)
    ok, encoded = cv2.imencode('.png', image)
    assert ok
    return encoded.tobytes()


app = create_app({
    'TESTING': True,
    'UPLOAD_FOLDER': ROOT / 'storage' / 'smart_test_uploads',
    'RESULT_FOLDER': ROOT / 'storage' / 'smart_test_results',
    'PREPARATION_PREVIEW_FOLDER': ROOT / 'storage' / 'smart_test_previews',
})
client = app.test_client()
upload = client.post('/api/images', data={'image': (io.BytesIO(image_bytes()), 'smart-test.png')}, content_type='multipart/form-data')
assert upload.status_code == 201, upload.get_json()
image_id = upload.get_json()['data']['image']['image_id']
response = client.post(f'/api/images/{image_id}/pipeline')
assert response.status_code == 201, response.get_json()
data = response.get_json()['data']
assert data['result']['id']
assert isinstance(data['steps'], list)
assert isinstance(data['binarization_candidates'], list)
result = client.get(f"/api/results/{data['result']['id']}")
assert result.status_code == 200 and result.data
print('smart pipeline: 201')
print('smart result retrieval: 200')
print(f"steps: {len(data['steps'])}, candidates: {len(data['binarization_candidates'])}")
