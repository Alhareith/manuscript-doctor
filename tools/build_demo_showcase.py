from __future__ import annotations

import io
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

import cv2
from app import create_app

SRC = ROOT / 'evaluation' / 'input'
OUT = ROOT / 'evaluation' / 'demo_showcase'
OUT.mkdir(parents=True, exist_ok=True)

CASES = [
    {
        'key': '01_handwritten_parchment',
        'source': '01_handwritten_legal_parchment.jpg',
        'title': 'مخطوطة قانونية مكتوبة بخط اليد',
        'reason': 'صورة عالية الدقة ذات خلفية قديمة ونص كثيف؛ مناسبة لإظهار CLAHE وFaded Text وIllumination Normalization.',
        'operations': [('clahe', {}), ('faded_text_enhance', {}), ('illumination_normalize', {})],
    },
    {
        'key': '02_open_handwritten_book',
        'source': '02_handwritten_book_pages.jpg',
        'title': 'صفحتان متقابلتان من دفتر قديم',
        'reason': 'تُظهر صفحتين وحدوداً واضحة وتفاوتاً في الإضاءة؛ مناسبة لإظهار التشخيص والمعالجة المحافظة.',
        'operations': [('illumination_normalize', {}), ('clahe', {}), ('adaptive_threshold', {})],
    },
    {
        'key': '03_aged_newspaper',
        'source': '05_printed_newspaper_aged_page1.jpg',
        'title': 'صفحة جريدة قديمة متدهورة',
        'reason': 'تحتوي نصاً مطبوعاً وخلفية صفراء وضوضاء عمرية؛ مناسبة لفصل النص وتقليل الخلفية.',
        'operations': [('background_suppress', {}), ('bilateral_denoise', {}), ('otsu_threshold', {})],
    },
    {
        'key': '04_arabic_newspaper',
        'source': '08_arabic_printed_newspaper_page1.jpg',
        'title': 'صفحة جريدة عربية متعددة الأعمدة',
        'reason': 'تُظهر دعماً بصرياً للوثائق العربية وتعدد الأعمدة؛ مناسبة للمقارنة بين CLAHE وAdaptive Threshold.',
        'operations': [('clahe', {}), ('adaptive_threshold', {}), ('morphological_closing', {})],
    },
    {
        'key': '05_clear_boundary',
        'source': 'boundary_test_011.jpg',
        'title': 'وثيقة رسمية بحدود واضحة',
        'reason': 'أفضل حالة لعرض Preparation وRegion/Guided والاقتصاص المنظوري مع الحفاظ على الأصل.',
        'operations': [('deskew', {'angle': 0.0}), ('illumination_normalize', {}), ('adaptive_threshold', {})],
    },
    {
        'key': '06_skewed_document',
        'source': '11_skewed.jpg',
        'title': 'وثيقة مائلة لاختبار Deskew',
        'reason': 'حالة قصيرة وواضحة بصرياً لإظهار تصحيح الميل مع إبقاء الإطار عند غياب حدود موثوقة.',
        'operations': [('deskew', {'angle': -15.0}), ('clahe', {}), ('otsu_threshold', {})],
    },
]

app = create_app({
    'TESTING': True,
    'UPLOAD_FOLDER': ROOT / 'storage' / 'showcase_uploads',
    'RESULT_FOLDER': ROOT / 'storage' / 'showcase_results',
    'PREPARATION_PREVIEW_FOLDER': ROOT / 'storage' / 'showcase_previews',
})
client = app.test_client()

for folder in (ROOT / 'storage' / 'showcase_uploads', ROOT / 'storage' / 'showcase_results', ROOT / 'storage' / 'showcase_previews'):
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True, exist_ok=True)

manifest = []
for case in CASES:
    src = SRC / case['source']
    upload = client.post('/api/images', data={'image': (io.BytesIO(src.read_bytes()), src.name)}, content_type='multipart/form-data')
    if upload.status_code != 201:
        raise RuntimeError(f'upload failed for {src.name}: {upload.status_code} {upload.get_json()}')
    image_id = upload.get_json()['data']['image']['image_id']
    upload_data = upload.get_json()['data']
    analysis = upload_data['analysis']
    image_metadata = upload_data.get('image', {})
    case_dir = OUT / case['key']
    if case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True)
    shutil.copy2(src, case_dir / f'original{src.suffix.lower()}')
    outputs = []
    for operation_id, params in case['operations']:
        response = client.post(f'/api/images/{image_id}/operations', json={'operation_id': operation_id, 'parameters': params})
        if response.status_code != 201:
            raise RuntimeError(f'operation failed {case["key"]}/{operation_id}: {response.status_code} {response.get_json()}')
        payload = response.get_json()['data']
        result = payload.get('result', {})
        result_id = result.get('id') or result.get('result_id')
        download = client.get(f'/api/results/{result_id}/download')
        if download.status_code != 200:
            raise RuntimeError(f'download failed {result_id}: {download.status_code}')
        ext = '.png'
        output_path = case_dir / f'{operation_id}{ext}'
        output_path.write_bytes(download.data)
        outputs.append({'operation_id': operation_id, 'parameters': params, 'file': str(output_path.relative_to(OUT)), 'result_id': result_id})
    prep = None
    if case['key'] == '05_clear_boundary':
        preparation = client.post(f'/api/images/{image_id}/preparation/preview')
        prep = {'status': preparation.status_code}
        if preparation.status_code == 200:
            prep_data = preparation.get_json().get('data', {})
            prep['preparation_id'] = prep_data.get('preparation_id')
            prep['decision'] = prep_data.get('decision')
            prep['metadata'] = prep_data.get('metadata')
    manifest.append({
        'key': case['key'], 'source': case['source'], 'title': case['title'], 'reason': case['reason'],
        'dimensions': image_metadata, 'diagnoses': analysis.get('diagnoses', []), 'outputs': outputs, 'preparation': prep,
    })

(OUT / 'showcase_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'created showcase for {len(manifest)} images at {OUT}')
