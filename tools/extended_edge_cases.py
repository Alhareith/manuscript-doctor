from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402

app = create_app({
    'TESTING': True,
    'UPLOAD_FOLDER': ROOT / 'storage' / 'edge_qa_uploads',
    'RESULT_FOLDER': ROOT / 'storage' / 'edge_qa_results',
    'PREPARATION_PREVIEW_FOLDER': ROOT / 'storage' / 'edge_qa_previews',
})
client = app.test_client()


def image_bytes(width=320, height=240):
    image = np.full((height, width, 3), 240, dtype=np.uint8)
    cv2.putText(image, 'EDGE QA', (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (20, 20, 20), 2, cv2.LINE_AA)
    ok, encoded = cv2.imencode('.png', image)
    assert ok
    return encoded.tobytes()


def upload(name='edge.png', data=None):
    payload = image_bytes() if data is None else data
    return client.post('/api/images', data={'image': (io.BytesIO(payload), name)}, content_type='multipart/form-data')


def expect(label, response, statuses):
    if response.status_code not in statuses:
        raise AssertionError(f'{label}: got {response.status_code}, expected {statuses}, payload={response.get_json()}')
    print(f'{label}: {response.status_code}')


expect('missing upload', client.post('/api/images', data={}, content_type='multipart/form-data'), {400})
expect('unsupported extension', upload('edge.webp', image_bytes()), {400})
expect('corrupt bytes', upload('corrupt.png', b'not-an-image'), {400})
expect('empty bytes', upload('empty.png', b''), {400})
expect('invalid image id get', client.get('/api/images/not-a-valid-id'), {400})
expect('missing image get', client.get('/api/images/' + 'a' * 32), {404})
expect('invalid result id get', client.get('/api/results/not-a-valid-id'), {400})
expect('missing result get', client.get('/api/results/' + 'b' * 32), {404})
expect('invalid operation image id', client.post('/api/images/not-a-valid-id/operations', json={'operation_id': 'clahe', 'parameters': {}}), {400})

first = upload('first.png')
second = upload('second.png')
expect('first upload', first, {201})
expect('second upload', second, {201})
first_id = first.get_json()['data']['image']['image_id']
second_id = second.get_json()['data']['image']['image_id']

expect('unknown operation', client.post(f'/api/images/{first_id}/operations', json={'operation_id': 'no_such_operation', 'parameters': {}}), {400})
expect('parameters not object', client.post(f'/api/images/{first_id}/operations', json={'operation_id': 'clahe', 'parameters': []}), {400})
expect('preview unknown operation', client.post(f'/api/images/{first_id}/preview', json={'operation_id': 'no_such_operation', 'parameters': {}}), {400})
expect('pipeline missing image', client.post('/api/images/' + 'c' * 32 + '/pipeline'), {404})

first_result_response = client.post(f'/api/images/{first_id}/operations', json={'operation_id': 'clahe', 'parameters': {}})
expect('first valid result', first_result_response, {201})
first_result_id = first_result_response.get_json()['data']['result']['id']
expect('cross-image source rejection', client.post(f'/api/images/{second_id}/operations', json={'operation_id': 'sharpen', 'parameters': {}, 'source_result_id': first_result_id}), {400})
expect('invalid source result', client.post(f'/api/images/{first_id}/operations', json={'operation_id': 'sharpen', 'parameters': {}, 'source_result_id': 'd' * 32}), {404})
expect('result download', client.get(f'/api/results/{first_result_id}/download'), {200})

# A compressed image above the pixel budget should be rejected before processing.
large = np.zeros((5001, 6001), dtype=np.uint8)
ok, encoded = cv2.imencode('.png', large)
assert ok
expect('pixel limit', upload('too-many-pixels.png', encoded.tobytes()), {400, 413})

print('edge_cases: all passed')
