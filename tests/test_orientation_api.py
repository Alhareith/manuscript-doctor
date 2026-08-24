from io import BytesIO

import cv2
import numpy as np

from app import create_app


def make_image():
    image = np.full((120, 180, 3), 220, dtype=np.uint8)
    cv2.rectangle(image, (20, 20), (160, 100), (30, 30, 30), 3)
    cv2.putText(image, 'DOC', (45, 75), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (20, 20, 20), 2, cv2.LINE_AA)
    return image


def upload(client):
    ok, encoded = cv2.imencode('.png', make_image())
    assert ok
    response = client.post(
        '/api/images',
        data={'image': (BytesIO(encoded.tobytes()), 'orientation.png')},
        content_type='multipart/form-data',
    )
    assert response.status_code == 201
    return response.get_json()['data']['image']['image_id']


def test_orientation_operations_work_through_api(tmp_path):
    app = create_app({'TESTING': True, 'UPLOAD_FOLDER': tmp_path / 'uploads', 'RESULT_FOLDER': tmp_path / 'results'})
    client = app.test_client()
    image_id = upload(client)

    for operation_id in ('rotate_right', 'rotate_left', 'flip_vertical', 'flip_horizontal'):
        response = client.post(f'/api/images/{image_id}/operations', json={'operation_id': operation_id, 'parameters': {}})
        assert response.status_code == 201, response.get_json()
        payload = response.get_json()['data']
        assert payload['operation']['id'] == operation_id
        assert payload['result']['source_image_id'] == image_id
        downloaded = client.get(f"/api/results/{payload['result']['id']}/download")
        assert downloaded.status_code == 200


def test_manual_operation_can_continue_after_smart_result(tmp_path):
    app = create_app({'TESTING': True, 'UPLOAD_FOLDER': tmp_path / 'uploads', 'RESULT_FOLDER': tmp_path / 'results'})
    client = app.test_client()
    image_id = upload(client)

    pipeline = client.post(f'/api/images/{image_id}/pipeline')
    assert pipeline.status_code == 201, pipeline.get_json()
    smart_result_id = pipeline.get_json()['data']['result']['id']

    response = client.post(
        f'/api/images/{image_id}/operations',
        json={'operation_id': 'rotate_right', 'parameters': {}, 'source_result_id': smart_result_id},
    )
    assert response.status_code == 201, response.get_json()
    assert response.get_json()['data']['source_result_id'] == smart_result_id
