from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import sys
import time
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402
from processing.ops.registry import OPERATIONS  # noqa: E402

QA_ROOT = ROOT / 'evaluation' / 'extended_qa'
INPUT_DIR = QA_ROOT / 'input'
REPORT_PATH = QA_ROOT / 'extended_report.json'
LOG_PATH = QA_ROOT / 'extended_runner.log'
REAL_INPUTS = [ROOT / 'evaluation' / 'input' / 'b01.jpg', ROOT / 'evaluation' / 'input' / 'b02.jpg']


def fresh_app():
    folders = {
        'UPLOAD_FOLDER': ROOT / 'storage' / 'extended_qa_uploads',
        'RESULT_FOLDER': ROOT / 'storage' / 'extended_qa_results',
        'PREPARATION_PREVIEW_FOLDER': ROOT / 'storage' / 'extended_qa_previews',
    }
    for folder in folders.values():
        if folder.exists():
            shutil.rmtree(folder)
    return create_app({'TESTING': True, **folders})


def json_payload(response):
    try:
        return response.get_json()
    except Exception:
        return {'status': response.status_code, 'body': response.data[:200].decode('utf-8', 'replace')}


def result_id(payload):
    data = payload.get('data', {}) if isinstance(payload, dict) else {}
    result = data.get('result', {}) if isinstance(data, dict) else {}
    return result.get('id') or result.get('result_id')


def record_failure(report, kind, image, detail):
    report['failures'].append({'kind': kind, 'image': image, 'detail': detail})


def upload(client, path):
    return client.post(
        '/api/images',
        data={'image': (io.BytesIO(path.read_bytes()), path.name)},
        content_type='multipart/form-data',
    )


def run_case(client, report, path, include_all_operations=True):
    name = path.name
    response = upload(client, path)
    if response.status_code != 201:
        record_failure(report, 'upload', name, json_payload(response))
        return None
    payload = json_payload(response)
    image_id = payload.get('data', {}).get('image', {}).get('image_id')
    if not image_id:
        record_failure(report, 'upload_missing_id', name, payload)
        return None
    report['counts']['uploads'] += 1
    if client.get(f'/api/images/{image_id}').status_code != 200:
        record_failure(report, 'image_get', name, image_id)

    operation_items = list(OPERATIONS.items()) if include_all_operations else list(OPERATIONS.items())[:6]
    for operation_id, spec in operation_items:
        parameters = dict(spec.get('default_parameters', {}))
        report['counts']['operation_cases'] += 1
        preview = client.post(f'/api/images/{image_id}/preview', json={'operation_id': operation_id, 'parameters': parameters})
        if preview.status_code != 200:
            record_failure(report, 'preview', name, {'operation': operation_id, 'status': preview.status_code, 'payload': json_payload(preview)})
        else:
            report['counts']['previews'] += 1
        executed = client.post(f'/api/images/{image_id}/operations', json={'operation_id': operation_id, 'parameters': parameters})
        if executed.status_code != 201:
            record_failure(report, 'execution', name, {'operation': operation_id, 'status': executed.status_code, 'payload': json_payload(executed)})
            continue
        report['counts']['executions'] += 1
        execution_payload = json_payload(executed)
        rid = result_id(execution_payload)
        if not rid:
            record_failure(report, 'missing_result_id', name, {'operation': operation_id, 'payload': execution_payload})
            continue
        fetched = client.get(f'/api/results/{rid}')
        downloaded = client.get(f'/api/results/{rid}/download')
        if fetched.status_code != 200 or downloaded.status_code != 200 or not downloaded.data:
            record_failure(report, 'result_or_download', name, {'operation': operation_id, 'result': fetched.status_code, 'download': downloaded.status_code, 'bytes': len(downloaded.data)})
        else:
            report['counts']['downloads'] += 1

    report['counts']['pipelines_attempted'] += 1
    pipeline = client.post(f'/api/images/{image_id}/pipeline')
    if pipeline.status_code != 201:
        record_failure(report, 'pipeline', name, {'status': pipeline.status_code, 'payload': json_payload(pipeline)})
    else:
        report['counts']['pipelines'] += 1

    if any(token in name for token in ('clear_boundary', 'perspective', 'b01', 'b02', 'skew')):
        report['counts']['preparation_attempted'] += 1
        preparation = client.post(f'/api/images/{image_id}/preparation/preview')
        if preparation.status_code == 200:
            report['counts']['preparation_previews'] += 1
            prep_payload = json_payload(preparation).get('data', {})
            preparation_id = prep_payload.get('preparation_id')
            if preparation_id:
                if client.get(f'/api/preparation/{preparation_id}').status_code != 200:
                    record_failure(report, 'preparation_get', name, preparation_id)
                approved = client.post(f'/api/images/{image_id}/preparation/{preparation_id}/approve')
                if approved.status_code == 201:
                    report['counts']['preparation_approvals'] += 1
                else:
                    record_failure(report, 'preparation_approve', name, {'status': approved.status_code, 'payload': json_payload(approved)})
        elif preparation.status_code != 422:
            record_failure(report, 'preparation_preview', name, {'status': preparation.status_code, 'payload': json_payload(preparation)})

    return image_id


def run_negative_cases(client, report):
    report['counts']['negative_cases'] += 1
    unsupported = INPUT_DIR / 'unsupported.webp'
    if unsupported.exists():
        unsupported_response = upload(client, unsupported)
        if unsupported_response.status_code not in {400, 415, 422}:
            record_failure(report, 'unsupported_upload_guard', unsupported.name, json_payload(unsupported_response))

    for name, data in [('corrupt.jpg', b'not-an-image'), ('empty.png', b''), ('missing-extension', b'fake')]:
        report['counts']['negative_cases'] += 1
        response = client.post('/api/images', data={'image': (io.BytesIO(data), name)}, content_type='multipart/form-data')
        if response.status_code not in {400, 415, 422}:
            record_failure(report, 'invalid_upload_guard', name, {'status': response.status_code, 'payload': json_payload(response)})

    report['counts']['negative_cases'] += 1
    invalid = client.post('/api/images/not-a-valid-id/operations', json={'operation_id': 'not_real', 'parameters': {}})
    if invalid.status_code not in {400, 404}:
        record_failure(report, 'invalid_image_guard', '-', json_payload(invalid))


def run_full_chain(client, report, path):
    response = upload(client, path)
    if response.status_code != 201:
        record_failure(report, 'chain_upload', path.name, json_payload(response))
        return
    image_id = json_payload(response)['data']['image']['image_id']
    parent = None
    for operation_id, spec in OPERATIONS.items():
        body = {'operation_id': operation_id, 'parameters': dict(spec.get('default_parameters', {}))}
        if parent:
            body['source_result_id'] = parent
        response = client.post(f'/api/images/{image_id}/operations', json=body)
        if response.status_code != 201:
            record_failure(report, 'full_chain', path.name, {'operation': operation_id, 'status': response.status_code, 'payload': json_payload(response)})
            return
        parent = result_id(json_payload(response))
        if not parent:
            record_failure(report, 'full_chain_missing_result', path.name, operation_id)
            return
        report['counts']['chain_steps'] += 1
    report['counts']['full_chains'] += 1


def build_report(cycle, started):
    return {
        'started_at': started,
        'last_cycle': cycle,
        'operations': list(OPERATIONS),
        'counts': {
            'cycles': cycle,
            'uploads': 0,
            'operation_cases': 0,
            'previews': 0,
            'executions': 0,
            'downloads': 0,
            'pipelines_attempted': 0,
            'pipelines': 0,
            'preparation_attempted': 0,
            'preparation_previews': 0,
            'preparation_approvals': 0,
            'negative_cases': 0,
            'chain_steps': 0,
            'full_chains': 0,
        },
        'failures': [],
    }


def run_cycle(cycle, started):
    client = fresh_app().test_client()
    report = build_report(cycle, started)
    generated = sorted(p for p in INPUT_DIR.iterdir() if p.suffix.lower() in {'.png', '.jpg', '.jpeg'})
    real = [p for p in REAL_INPUTS if p.exists()]
    all_paths = generated + real
    # Full operation matrix on the first 18 inputs, including all size bands and feature classes.
    full_paths = all_paths[:18]
    for path in full_paths:
        run_case(client, report, path, include_all_operations=True)
    # Broader image coverage with a representative subset of operations.
    for path in all_paths[18:]:
        run_case(client, report, path, include_all_operations=False)
    run_negative_cases(client, report)
    run_full_chain(client, report, INPUT_DIR / 'valid_04_640x480_gray.png')
    report['counts']['total_assertions'] = (
        report['counts']['previews'] + report['counts']['executions'] + report['counts']['downloads']
        + report['counts']['pipelines'] + report['counts']['preparation_approvals'] + report['counts']['chain_steps']
    )
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration', type=int, default=7200)
    parser.add_argument('--cycles', type=int, default=0)
    parser.add_argument('--sleep', type=int, default=2)
    args = parser.parse_args()
    started_epoch = time.time()
    started = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(started_epoch))
    cycle = 0
    while True:
        cycle += 1
        report = run_cycle(cycle, started)
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        line = json.dumps({'cycle': cycle, 'assertions': report['counts']['total_assertions'], 'failures': len(report['failures'])}, ensure_ascii=False)
        LOG_PATH.open('a', encoding='utf-8').write(line + '\n')
        print(line, flush=True)
        if report['failures']:
            # Keep running to reveal whether the failure is deterministic across cycles.
            LOG_PATH.open('a', encoding='utf-8').write('FAILURES_PRESENT\n')
        if args.cycles and cycle >= args.cycles:
            break
        if time.time() - started_epoch >= args.duration:
            break
        time.sleep(args.sleep)


if __name__ == '__main__':
    main()
