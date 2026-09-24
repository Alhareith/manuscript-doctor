"""Repeatable route-level benchmark; no uploads/results in the real storage.
Run: PYTHONPATH=. python tools/benchmark_previews.py --output /tmp/before.json
"""
import argparse
import cProfile
import io
import json
import pstats
import statistics
import subprocess
import sys
import types
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import cv2
import app as module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--baseline', action='store_true', help='Measure HEAD app.py with unchanged processing algorithms')
    args = parser.parse_args()
    backend = module
    if args.baseline:
        # No checkout/reset, no writes to the working tree. This comparison is
        # valid only while tracked processing algorithms remain unchanged.
        subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', 'processing/'], check=True)
        backend = types.ModuleType('preview_baseline_app')
        backend.__file__ = module.__file__
        sys.modules[backend.__name__] = backend
        source_code = subprocess.check_output(['git', 'show', 'HEAD:app.py'])
        exec(compile(source_code, module.__file__, 'exec'), backend.__dict__)
    source = cv2.imread('static/assets/document-before.png')
    source = cv2.resize(source, (4200, 2799), interpolation=cv2.INTER_CUBIC)
    with tempfile.TemporaryDirectory() as root:
        root = Path(root)
        application = backend.create_app({
            'TESTING': True, 'UPLOAD_FOLDER': root / 'uploads',
            'RESULT_FOLDER': root / 'results', 'PREPARATION_PREVIEW_FOLDER': root / 'preparation',
        })
        image_id = 'a' * 32
        cv2.imwrite(str(root / 'uploads' / (image_id + '.jpg')), source)
        client = application.test_client()
        report = {'baseline': args.baseline, 'dimensions': [4200, 2799], 'opencv': cv2.__version__, 'routes': {}}
        for operation in ['clahe', 'sharpen', 'bilateral_denoise', 'preparation']:
            url = f'/api/images/{image_id}/' + ('preparation/preview' if operation == 'preparation' else 'preview')
            durations = []
            profiler = cProfile.Profile()
            with patch.object(backend, 'read_stored_image', wraps=backend.read_stored_image) as read, \
                 patch.object(cv2, 'imdecode', wraps=cv2.imdecode) as decode:
                for index in range(7):
                    t0 = time.perf_counter()
                    response = client.post(url, json={'operation_id': operation, 'parameters': {}}, headers={'X-Preview-Format': 'jpeg'})
                    durations.append(round((time.perf_counter() - t0) * 1000, 3))
                    assert response.status_code == 200, response.get_json()
                counts = {'read_stored_image': read.call_count, 'imdecode': decode.call_count}
            profiler.enable()
            client.post(url, json={'operation_id': operation, 'parameters': {}}, headers={'X-Preview-Format': 'jpeg'})
            profiler.disable()
            stream = io.StringIO()
            pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats('cumtime').print_stats(22)
            report['routes'][operation] = {
                'first_ms': durations[0], 'warm_median_ms': statistics.median(durations[1:]),
                'all_ms': durations, 'counts_7_requests': counts, 'profile': stream.getvalue(),
            }
        Path(args.output).write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps({k: {n:v for n,v in row.items() if n != 'profile'} for k,row in report['routes'].items()}, indent=2))

if __name__ == '__main__':
    main()
