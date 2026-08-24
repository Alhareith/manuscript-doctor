import io
import json
import os
import shutil
import sys
from pathlib import Path

import cv2

ROOT = Path('/home/ubuntu/image_project_split')
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402
from processing.ops.registry import OPERATIONS  # noqa: E402

QA_ROOT = ROOT / 'evaluation' / 'comprehensive_qa'
INPUT_DIR = QA_ROOT / 'input'
REAL_INPUTS = [ROOT / 'evaluation' / 'input' / 'b01.jpg', ROOT / 'evaluation' / 'input' / 'b02.jpg']
UPLOAD_DIR = ROOT / 'storage' / 'comprehensive_qa_uploads'
RESULT_DIR = ROOT / 'storage' / 'comprehensive_qa_results'
PREVIEW_DIR = ROOT / 'storage' / 'comprehensive_qa_previews'
REPORT_PATH = QA_ROOT / 'report.json'

for folder in (UPLOAD_DIR, RESULT_DIR, PREVIEW_DIR):
    if folder.exists():
        shutil.rmtree(folder)

app = create_app({
    'TESTING': True,
    'UPLOAD_FOLDER': UPLOAD_DIR,
    'RESULT_FOLDER': RESULT_DIR,
    'PREPARATION_PREVIEW_FOLDER': PREVIEW_DIR,
})
client = app.test_client()

images = sorted(INPUT_DIR.glob('*')) + [p for p in REAL_INPUTS if p.exists()]
images = [p for p in images if p.suffix.lower() in {'.png', '.jpg', '.jpeg'}]

report = {
    'images': [],
    'operations': list(OPERATIONS),
    'counts': {'images': len(images), 'operation_cases': 0, 'preview_ok': 0, 'execution_ok': 0, 'download_ok': 0, 'pipeline_ok': 0, 'preparation_preview_ok': 0, 'preparation_approved': 0},
    'failures': [],
}


def add_failure(kind, image, detail):
    report['failures'].append({'kind': kind, 'image': image, 'detail': detail})


def payload(response):
    try:
        return response.get_json()
    except Exception:
        return {'status': response.status_code, 'body_prefix': response.data[:200].decode('utf-8', 'replace')}


def result_id_from(data):
    result = data.get('data', {}).get('result', {}) if isinstance(data, dict) else {}
    return result.get('result_id') or result.get('id')

for path in images:
    image_name = path.name
    with path.open('rb') as handle:
        upload = client.post('/api/images', data={'image': (io.BytesIO(handle.read()), image_name)}, content_type='multipart/form-data')
    if upload.status_code != 201:
        add_failure('upload', image_name, payload(upload))
        continue
    image_id = payload(upload)['data']['image']['image_id']
    image_entry = {'name': image_name, 'image_id': image_id, 'operations': {}, 'pipeline': None, 'preparation': None}

    info = client.get(f'/api/images/{image_id}')
    if info.status_code != 200:
        add_failure('image_get', image_name, payload(info))

    for operation_id, spec in OPERATIONS.items():
        report['counts']['operation_cases'] += 1
        params = dict(spec.get('default_parameters', {}))
        case = {'preview': None, 'execution': None, 'download': None}
        preview = client.post(f'/api/images/{image_id}/preview', json={'operation_id': operation_id, 'parameters': params})
        case['preview'] = preview.status_code
        if preview.status_code == 200:
            report['counts']['preview_ok'] += 1
        else:
            add_failure('operation_preview', image_name, {'operation': operation_id, 'response': payload(preview)})

        executed = client.post(f'/api/images/{image_id}/operations', json={'operation_id': operation_id, 'parameters': params})
        case['execution'] = executed.status_code
        if executed.status_code != 201:
            add_failure('operation_execution', image_name, {'operation': operation_id, 'response': payload(executed)})
            image_entry['operations'][operation_id] = case
            continue
        report['counts']['execution_ok'] += 1
        result_id = result_id_from(payload(executed))
        case['result_id'] = result_id
        if not result_id:
            add_failure('missing_result_id', image_name, {'operation': operation_id, 'response': payload(executed)})
        else:
            fetched = client.get(f'/api/results/{result_id}')
            downloaded = client.get(f'/api/results/{result_id}/download')
            case['download'] = {'get': fetched.status_code, 'download': downloaded.status_code, 'bytes': len(downloaded.data)}
            if fetched.status_code == 200 and downloaded.status_code == 200 and downloaded.data:
                report['counts']['download_ok'] += 1
            else:
                add_failure('result_or_download', image_name, {'operation': operation_id, 'result': fetched.status_code, 'download': downloaded.status_code, 'bytes': len(downloaded.data)})
        image_entry['operations'][operation_id] = case

    pipeline = client.post(f'/api/images/{image_id}/pipeline')
    image_entry['pipeline'] = {'status': pipeline.status_code}
    if pipeline.status_code == 201:
        report['counts']['pipeline_ok'] += 1
        pipeline_data = payload(pipeline)
        image_entry['pipeline']['decision'] = pipeline_data.get('data', {}).get('decision')
        image_entry['pipeline']['steps'] = len(pipeline_data.get('data', {}).get('steps', []))
        pipeline_result_id = result_id_from(pipeline_data)
        if pipeline_result_id and client.get(f'/api/results/{pipeline_result_id}').status_code != 200:
            add_failure('pipeline_result_get', image_name, {'result_id': pipeline_result_id})
    else:
        add_failure('pipeline', image_name, payload(pipeline))

    preparation = client.post(f'/api/images/{image_id}/preparation/preview')
    image_entry['preparation'] = {'preview_status': preparation.status_code}
    if preparation.status_code == 200:
        report['counts']['preparation_preview_ok'] += 1
        preparation_data = payload(preparation).get('data', {})
        preparation_id = preparation_data.get('preparation_id')
        image_entry['preparation'].update({'status': preparation_data.get('status'), 'method_used': preparation_data.get('method_used')})
        if preparation_id:
            preview_get = client.get(f'/api/preparation/{preparation_id}')
            image_entry['preparation']['preview_get'] = preview_get.status_code
            if preview_get.status_code != 200:
                add_failure('preparation_preview_get', image_name, payload(preview_get))
            approved = client.post(f'/api/images/{image_id}/preparation/{preparation_id}/approve')
            image_entry['preparation']['approve_status'] = approved.status_code
            if approved.status_code == 201:
                report['counts']['preparation_approved'] += 1
            else:
                add_failure('preparation_approve', image_name, payload(approved))
    elif preparation.status_code == 422:
        # Rejection is a valid safety outcome; record it rather than treating it as a server defect.
        image_entry['preparation']['rejected_safely'] = True
    else:
        add_failure('preparation_preview', image_name, payload(preparation))

    report['images'].append(image_entry)

# Chaining regression across every operation on a clean synthetic input.
chain_path = INPUT_DIR / '01_normal_grayscale.png'
with chain_path.open('rb') as handle:
    upload = client.post('/api/images', data={'image': (io.BytesIO(handle.read()), 'chain.png')}, content_type='multipart/form-data')
chain_ok = upload.status_code == 201
chain_result = None
if chain_ok:
    chain_image_id = payload(upload)['data']['image']['image_id']
    for operation_id, spec in OPERATIONS.items():
        response = client.post(f'/api/images/{chain_image_id}/operations', json={'operation_id': operation_id, 'parameters': dict(spec.get('default_parameters', {})), 'source_result_id': chain_result} if chain_result else {'operation_id': operation_id, 'parameters': dict(spec.get('default_parameters', {}))})
        if response.status_code != 201:
            chain_ok = False
            add_failure('full_chain', chain_path.name, {'operation': operation_id, 'response': payload(response)})
            break
        chain_result = result_id_from(payload(response))
        if not chain_result:
            chain_ok = False
            add_failure('full_chain_missing_result', chain_path.name, {'operation': operation_id})
            break
report['chain_all_operations_ok'] = chain_ok

invalid = client.post('/api/images/does-not-exist/operations', json={'operation_id': 'not_real', 'parameters': {}})
report['invalid_guard'] = invalid.status_code in {400, 404}
if not report['invalid_guard']:
    add_failure('invalid_guard', '-', payload(invalid))

REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'counts': report['counts'], 'chain_all_operations_ok': report['chain_all_operations_ok'], 'invalid_guard': report['invalid_guard'], 'failure_count': len(report['failures']), 'report': str(REPORT_PATH)}, ensure_ascii=False, indent=2))
if report['failures']:
    raise SystemExit(1)
