"""Regression contracts for preview isolation and bounded caching (no timing thresholds)."""
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock

import cv2
import numpy as np
import pytest

import app as module
from processing.preview_cache import PreviewCache


@pytest.fixture
def preview_app(tmp_path):
    return module.create_app({
        'TESTING': True, 'UPLOAD_FOLDER': tmp_path / 'uploads',
        'RESULT_FOLDER': tmp_path / 'results',
        'PREPARATION_PREVIEW_FOLDER': tmp_path / 'preparation',
    })


def seed(application, key='a' * 32, shape=(1600, 1200, 3)):
    image = np.full(shape, 210, np.uint8)
    image[100:300, 100:300] = 40
    path = Path(application.config['UPLOAD_FOLDER']) / (key + '.png')
    assert cv2.imwrite(str(path), image)
    return key, path


def test_preview_decodes_once_and_never_analyzes_verifies_or_saves(preview_app, monkeypatch):
    image_id, _ = seed(preview_app)
    decode = Mock(wraps=module.read_stored_image)
    monkeypatch.setattr(module, 'read_stored_image', decode)
    def forbidden(*args, **kwargs):
        pytest.fail('Full result work executed during a live preview')
    for name in ['analyze_image', 'verify_preservation', 'save_result_artifact']:
        monkeypatch.setattr(module, name, forbidden)
    real_apply = module.apply_operation
    sizes = []
    def record(operation, image, parameters):
        sizes.append(image.shape)
        return real_apply(operation, image, parameters)
    monkeypatch.setattr(module, 'apply_operation', record)
    client = preview_app.test_client()
    for gamma in [0.8, 1.0, 1.4, 0.8]:
        response = client.post(f'/api/images/{image_id}/preview',
                               json={'operation_id': 'gamma_correct', 'parameters': {'gamma': gamma}},
                               headers={'X-Preview-Format': 'jpeg'})
        assert response.status_code == 200
        assert response.json['data']['preview']['format'] == 'jpeg'
    assert decode.call_count == 1
    assert all(h <= 960 and w <= 720 for h, w, _ in sizes)
    assert not list(Path(preview_app.config['RESULT_FOLDER']).iterdir())


def test_cache_invalidates_on_file_replacement(preview_app, monkeypatch):
    image_id, path = seed(preview_app)
    read = Mock(wraps=module.read_stored_image)
    monkeypatch.setattr(module, 'read_stored_image', read)
    client = preview_app.test_client()
    args = {'operation_id': 'gamma_correct', 'parameters': {'gamma': 1}}
    first = client.post(f'/api/images/{image_id}/preview', json=args).json
    replacement = path.with_suffix('.new.png')
    cv2.imwrite(str(replacement), np.full((100, 80, 3), 80, np.uint8))
    replacement.replace(path)
    second = client.post(f'/api/images/{image_id}/preview', json=args).json
    assert read.call_count == 2
    assert first['data']['preview']['width'] != second['data']['preview']['width']


def test_preview_uses_only_approved_source_and_checks_document(preview_app, monkeypatch):
    image_id, original = seed(preview_app)
    folder = preview_app.config['RESULT_FOLDER']
    result_id, result_path = module.save_result_artifact(
        np.full((1500, 1000, 3), 150, np.uint8), folder,
        source_image_id=image_id, origin='manual', status='approved', parent_result_id=None,
    )
    read = Mock(wraps=module.read_stored_image)
    monkeypatch.setattr(module, 'read_stored_image', read)
    client = preview_app.test_client()
    data = {'operation_id': 'clahe', 'parameters': {}, 'source_result_id': result_id}
    assert client.post(f'/api/images/{image_id}/preview', json=data).status_code == 200
    assert [call.args[0] for call in read.call_args_list] == [result_path]
    other, _ = seed(preview_app, 'b' * 32)
    response = client.post(f'/api/images/{other}/preview', json=data)
    assert response.status_code == 400
    assert response.json['error']['code'] == 'SOURCE_RESULT_MISMATCH'


def test_crop_preview_maps_full_coordinates_without_full_size_operation(preview_app, monkeypatch):
    image_id, _ = seed(preview_app)
    apply = Mock(wraps=module.apply_operation)
    monkeypatch.setattr(module, 'apply_operation', apply)
    response = preview_app.test_client().post(f'/api/images/{image_id}/preview', json={
        'operation_id': 'crop', 'parameters': {'x': 100, 'y': 200, 'width': 600, 'height': 800}})
    assert response.status_code == 200
    assert apply.call_args.args[1].shape[:2] == (960, 720)
    assert response.json['data']['preview']['width'] == 360
    assert response.json['data']['preview']['height'] == 480


def test_approval_still_processes_full_resolution(preview_app, monkeypatch):
    image_id, _ = seed(preview_app)
    apply = Mock(wraps=module.apply_operation)
    monkeypatch.setattr(module, 'apply_operation', apply)
    response = preview_app.test_client().post(f'/api/images/{image_id}/operations', json={
        'operation_id': 'gamma_correct', 'parameters': {'gamma': 1}})
    assert response.status_code == 201
    assert apply.call_args.args[1].shape[:2] == (1600, 1200)
    assert response.json['data']['result']['width'] == 1200


def test_preparation_computation_cached_but_review_tokens_independent(preview_app, monkeypatch):
    image_id, _ = seed(preview_app)
    seen_shapes = []
    def prepare(image, **kwargs):
        seen_shapes.append(image.shape)
        return {'prepared': True, 'image': image.copy(),
                'boundary': {'detected': True, 'status': 'accept_automatic', 'method_used': 'guided'},
                'deskew': {'applied': False}, 'steps': []}
    monkeypatch.setattr(module, 'prepare_document', prepare)
    client = preview_app.test_client()
    previews = [client.post(f'/api/images/{image_id}/preparation/preview') for _ in range(2)]
    assert all(p.status_code == 200 for p in previews)
    ids = [p.json['data']['preparation_id'] for p in previews]
    assert ids[0] != ids[1]
    assert len(seen_shapes) == 1
    assert max(seen_shapes[0][:2]) <= 1400
    assert client.post(f'/api/images/{image_id}/preparation/{ids[0]}/approve').status_code == 201
    assert seen_shapes[-1][:2] == (1600, 1200)
    assert client.post(f'/api/images/{image_id}/preparation/{ids[0]}/approve').status_code == 409
    assert client.post(f'/api/images/{image_id}/preparation/{ids[1]}/reject').status_code == 200


def test_cache_is_bounded_and_single_flight():
    cache = PreviewCache(max_bytes=20, max_entries=2)
    calls = []
    def create():
        calls.append(1)
        time.sleep(.02)
        return bytes(12)
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda _: cache.get_or_create('a', create, len), range(5)))
    assert len(calls) == 1
    assert len(results) == 5
    cache.get_or_create('b', create, len)
    assert cache.bytes <= 20
    cache.get_or_create('a', create, len)
    assert len(calls) == 3  # a was evicted by b


def test_cache_failure_does_not_poison_entry():
    cache = PreviewCache()
    with pytest.raises(ValueError):
        cache.get_or_create('broken', lambda: (_ for _ in ()).throw(ValueError()), len)
    assert cache.get_or_create('broken', lambda: b'ok', len) == b'ok'


def test_stylesheet_imports_are_real_and_no_escaped_line_separators():
    import re
    base = Path(__file__).resolve().parents[1] / 'static/css'
    text = (base / 'style.css').read_text()
    assert '\\n' not in text
    paths = re.findall(r'@import url\("([^"]+)"\)', text)
    assert paths[-1] == 'clinic/21-crop-editor.css'
    for path in paths:
        sheet = base / path
        assert sheet.is_file()
        assert '\\n' not in sheet.read_text(), str(sheet)


@pytest.mark.parametrize('operation,parameters', [
    ('clahe', {}),
    ('gamma_correct', {'gamma': 1.4}),
    ('intensity_adjust', {'alpha': 1.2, 'beta': -15}),
    ('morphological_opening', {}),
])
def test_cached_preview_matches_existing_operation_pixels(preview_app, operation, parameters):
    import base64
    image_id, path = seed(preview_app)
    expected = module.apply_operation(operation, module.resize_for_preview(module.read_stored_image(path)), parameters)
    expected = module.resize_for_preview(expected)
    response = preview_app.test_client().post(f'/api/images/{image_id}/preview', json={
        'operation_id': operation, 'parameters': parameters})
    assert response.status_code == 200
    encoded = response.json['data']['preview']['data_url'].split(',', 1)[1]
    actual = cv2.imdecode(np.frombuffer(base64.b64decode(encoded), np.uint8), cv2.IMREAD_UNCHANGED)
    assert np.array_equal(expected, actual)
