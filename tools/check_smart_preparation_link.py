from io import BytesIO
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cv2
from app import create_app


def check(path: Path):
    app = create_app({'TESTING': True, 'UPLOAD_FOLDER': ROOT / 'storage' / 'check_uploads', 'RESULT_FOLDER': ROOT / 'storage' / 'check_results'})
    client = app.test_client()
    response = client.post('/api/images', data={'image': (BytesIO(path.read_bytes()), path.name)}, content_type='multipart/form-data')
    assert response.status_code == 201, response.get_json()
    image_id = response.get_json()['data']['image']['image_id']
    result = client.post(f'/api/images/{image_id}/pipeline')
    assert result.status_code == 201, result.get_json()
    data = result.get_json()['data']
    assert 'preparation' in data
    assert data['steps'][0]['operation_id'] == 'document_prepare'
    print(path.name, 'preparation_used=', data['preparation']['used'], 'status=', data['preparation']['verification'].get('status'), 'steps=', len(data['steps']))


check(ROOT / 'evaluation' / 'input' / 'b01.jpg')
check(ROOT / 'evaluation' / 'input' / '03_low_contrast.jpg')
print('smart_preparation_link=ok')
