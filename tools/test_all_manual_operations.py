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
from processing.ops.registry import OPERATIONS  # noqa: E402


def sample_bytes() -> bytes:
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
    'UPLOAD_FOLDER': ROOT / 'storage' / 'manual_test_uploads',
    'RESULT_FOLDER': ROOT / 'storage' / 'manual_test_results',
    'PREPARATION_PREVIEW_FOLDER': ROOT / 'storage' / 'manual_test_previews',
})
client = app.test_client()

upload = client.post('/api/images', data={'image': (io.BytesIO(sample_bytes()), 'manual-test.png')}, content_type='multipart/form-data')
assert upload.status_code == 201, upload.get_json()
image_id = upload.get_json()['data']['image']['image_id']

preview_failures = []
execution_failures = []
results = []
for operation_id, spec in OPERATIONS.items():
    params = dict(spec.get('default_parameters', {}))
    preview = client.post(f'/api/images/{image_id}/preview', json={'operation_id': operation_id, 'parameters': params})
    if preview.status_code != 200:
        preview_failures.append((operation_id, preview.status_code, preview.get_json()))
    executed = client.post(f'/api/images/{image_id}/operations', json={'operation_id': operation_id, 'parameters': params})
    if executed.status_code != 201:
        execution_failures.append((operation_id, executed.status_code, executed.get_json()))
        continue
    data = executed.get_json()['data']
    result_id = data['result'].get('result_id') or data['result'].get('id')
    if not result_id:
        execution_failures.append((operation_id, 'missing_result_id', executed.get_json()))
        continue
    fetched = client.get(f'/api/results/{result_id}')
    downloaded = client.get(f'/api/results/{result_id}/download')
    if fetched.status_code != 200 or downloaded.status_code != 200 or not downloaded.data:
        execution_failures.append((operation_id, 'result_or_download', fetched.status_code, downloaded.status_code))
    results.append((operation_id, result_id))

assert not preview_failures, preview_failures
assert not execution_failures, execution_failures
assert len(results) == len(OPERATIONS)

# Regression: preview after an approved manual result must accept the source result.
approved_source = results[0][1]
followup_preview = client.post(
    f'/api/images/{image_id}/preview',
    json={
        'operation_id': 'gamma_correct',
        'parameters': dict(OPERATIONS['gamma_correct'].get('default_parameters', {})),
        'source_result_id': approved_source,
    },
)
assert followup_preview.status_code == 200, followup_preview.get_json()

# Verify linked manual chaining for three representative operations.
parent = results[0][1]
for operation_id in ['gamma_correct', 'median_denoise', 'deskew']:
    params = dict(OPERATIONS[operation_id].get('default_parameters', {}))
    chained = client.post(f'/api/images/{image_id}/operations', json={'operation_id': operation_id, 'parameters': params, 'source_result_id': parent})
    assert chained.status_code == 201, (operation_id, chained.get_json())
    chained_result = chained.get_json()['data']['result']
    parent = chained_result.get('result_id') or chained_result.get('id')
    assert parent, (operation_id, chained.get_json())

invalid = client.post(f'/api/images/{image_id}/operations', json={'operation_id': 'not_real', 'parameters': {}})
assert invalid.status_code == 400

print(f'uploaded image: ok ({image_id})')
print(f'operations tested: {len(results)}/{len(OPERATIONS)}')
print('preview for all operations: ok')
print('execution, result retrieval, and download for all operations: ok')
print('manual chaining: ok')
print('invalid operation guard: ok')
