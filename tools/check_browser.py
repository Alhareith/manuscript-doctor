"""Browser acceptance test against a running app (pip install playwright).
python tools/check_browser.py --url http://127.0.0.1:5002 --output /tmp/browser-review
"""
import argparse
import asyncio
import json
import tempfile
from pathlib import Path

import cv2
import numpy as np
from playwright.async_api import async_playwright

SIZES = [1440, 1024, 768, 430, 390]
LAYOUT = '''() => {
 const box = e => e.getBoundingClientRect();
 const cards = [...document.querySelectorAll('.manual-preview-card')];
 const stage = box(document.querySelector('.manual-preview-stage'));
 const approval = box(document.querySelector('.manual-approval-bar'));
 const result = {width:innerWidth, errors:[], imageHeights:[], diagnosisWidths:[]};
 const fail = message => result.errors.push(message);
 for (const [i,card] of cards.entries()) {
   const img=card.querySelector('img'), wrap=card.querySelector('.manual-preview-image-wrap');
   const r=box(img), w=box(wrap), c=box(card);
   if (!img.complete || !img.naturalHeight) fail(`image ${i} not loaded`);
   if (Math.abs(r.width/r.height-img.naturalWidth/img.naturalHeight)>.015) fail(`image ${i} stretched`);
   if(r.bottom>w.bottom+1 || r.top<w.top-1 || r.left<w.left-1 || r.right>w.right+1) fail(`image ${i} clipped`);
   if(c.bottom>stage.bottom+1) fail(`card ${i} escapes stage`);
   if(c.bottom>approval.top+1) fail(`card ${i} overlaps approval`);
   result.imageHeights.push(r.height);
 }
 const a=box(cards[0]), b=box(cards[1]);
 if(innerWidth<=430 && b.top<a.bottom) fail('mobile before/after not stacked');
 const pane=box(document.querySelector('.manual-preview-pane')), controls=box(document.querySelector('.manual-controls-pane'));
 if(pane.left<controls.right-1 && pane.right>controls.left+1 && pane.top<controls.bottom-1 && pane.bottom>controls.top+1) fail('tools overlap preview');
 for(const e of document.querySelectorAll('.diagnosis-item .item-heading strong,.recommendation-item .item-heading strong')) {
   if(!e.getClientRects().length) continue;
   result.diagnosisWidths.push(box(e).width);
   if(box(e).width<100) fail('narrow finding title');
 }
 for(const e of document.querySelectorAll('.manual-preview-pane,.manual-controls-pane,.manual-approval-actions .button,.finding-inline-details,.section-head,.manual-editor-head')) {
   if(!e.getClientRects().length)continue;
   const r=box(e);if(r.left < -1 || r.right > innerWidth+1)fail('outside viewport: '+e.className);
 }
 // Inspect overflow without relying on body overflow-x:clip to conceal it.
 const viewport=document.documentElement.clientWidth;
 const rootOverflow=document.documentElement.scrollWidth>viewport+1;
 if(rootOverflow)fail('horizontal document overflow');
 return result;
}'''


async def main(args):
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as root:
        tall = np.full((2600, 600, 3), 240, np.uint8)
        for y in range(90, 2500, 70):
            cv2.putText(tall, 'Document detail 123', (30, y), cv2.FONT_HERSHEY_SIMPLEX, .85, (20, 30, 20), 2)
        tall[:8] = (0, 0, 255)
        tall[-8:] = (255, 0, 0)
        path = Path(root) / 'tall.png'
        cv2.imwrite(str(path), tall)
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=['--no-sandbox'])
            page = await browser.new_page(viewport={'width':1440,'height':900}, reduced_motion='reduce')
            errors, failed_assets, posts = [], [], []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('console', lambda m: errors.append(m.text) if m.type=='error' else None)
            page.on('response', lambda r: failed_assets.append([r.url,r.status]) if r.status>=400 and ('/static/' in r.url) else None)
            page.on('request', lambda r: posts.append(r.url) if r.method=='POST' else None)
            await page.goto(args.url, wait_until='networkidle')
            async def upload(file):
                await page.locator('#imageInput').set_input_files(str(file))
                await page.wait_for_function('state.imageId && !state.isBusy', timeout=180000)
                await page.wait_for_function('document.querySelector("#manualLivePreview").complete && document.querySelector("#manualLivePreview").naturalWidth>0')
            async def ready():
                await page.wait_for_function('!manualRequestInFlight && !state.isBusy',timeout=180000)
            await upload(Path('static/assets/document-before.png'))
            assert await page.locator('.manual-change-chart').is_hidden()
            imported = await page.evaluate('''()=> [...document.styleSheets].filter(s=>s.href?.endsWith('/style.css')).flatMap(s=>[...s.cssRules].filter(r=>r.styleSheet).map(r=>({href:r.styleSheet.href,rules:r.styleSheet.cssRules.length})))''')
            assert imported[-2]['href'].endswith('/clinic/21-crop-editor.css')\n            assert imported[-1]['href'].endswith('/clinic/22-command-studio.css')
            assert all(x['rules']>0 for x in imported)
            layout = []
            for width in SIZES:
                await page.set_viewport_size({'width':width,'height':900})
                await page.wait_for_timeout(150)
                measurement = await page.evaluate(LAYOUT)
                assert not measurement['errors'], measurement
                layout.append(measurement)
                await page.locator('.after-exam-deck').screenshot(path=str(output/f'findings-{width}.png'))
            await page.set_viewport_size({'width':1440,'height':900})
            await page.locator('[data-operation-group="contrast"]').click()
            await page.locator('[data-operation-card="clahe"]').click()
            await ready()
            posts.clear()
            await page.evaluate("window.histogramReads=0; const originalHistogram=manualImageHistogram; manualImageHistogram=(...args)=>{window.histogramReads++;return originalHistogram(...args)}; undefined")
            await page.evaluate('''async()=>{const e=document.querySelector('#parameter-clip_limit');for(let i=0;i<20;i++){e.value=1+i/10;e.dispatchEvent(new Event('input',{bubbles:true}));await new Promise(r=>setTimeout(r,20))}}''')
            await page.wait_for_timeout(200)
            await ready()
            slider_posts=posts.copy()
            assert await page.evaluate('window.histogramReads')==0, 'closed chart did work during slider burst'
            assert len(slider_posts)==1 and slider_posts[0].endswith('/preview'), slider_posts
            assert await page.locator('.manual-change-chart').is_visible()
            assert not await page.locator('.manual-change-chart').evaluate('(e)=>e.open')
            await page.locator('.manual-change-chart > summary').click()
            await page.wait_for_function("document.querySelector('#manualChangeChartStatus').textContent === 'تحديث لحظي قبل / بعد'", timeout=5000)
            # Older, slow response must not enable approval for a newly selected operation.
            async def delay(route):
                await asyncio.sleep(.35)
                await route.continue_()
            await page.route('**/preview', delay)
            await page.locator('[data-operation-card="clahe"]').click()
            await page.locator('[data-operation-group="page"]').click()
            await page.locator('[data-operation-card="crop"]').click()
            await ready()
            assert await page.evaluate('state.manualPreviewCandidate?.operation?.id') in [None,'crop']
            await page.unroute('**/preview', delay)
            # Preparation produces review-only data, approval creates full result.
            await page.locator('[data-operation-card="document_prepare"]').click()
            await ready()
            assert await page.evaluate('Boolean(state.manualPreviewCandidate?.preparationId)')
            await page.locator('#manualApprovalButton').click()
            await ready()
            first_id=await page.evaluate('state.resultId')
            assert first_id
            await page.locator('[data-operation-group="lighting"]').click()
            await page.locator('[data-operation-card="gamma_correct"]').click()
            await ready()
            first=await page.evaluate('state.manualPreviewCandidate.data.preview.data_url')
            await page.locator('[data-operation-card="gamma_correct"]').click()
            await ready()
            second=await page.evaluate('state.manualPreviewCandidate.data.preview.data_url')
            assert first==second, 'same parameters compounded a prior draft'
            await page.locator('#manualApprovalButton').click()
            await ready()
            second_id=await page.evaluate('state.resultId')
            assert second_id!=first_id
            await page.locator('#manualUndoButton').click()
            assert await page.evaluate('state.resultId')==first_id
            await page.locator('#manualRedoButton').click()
            assert await page.evaluate('state.resultId')==second_id
            async with page.expect_download() as download_info:
                await page.locator('#manualManualDownloadButton').click()
            download=await download_info.value
            await download.save_as(str(output/'download.png'))
            assert cv2.imread(str(output/'download.png')) is not None
            await page.locator('#runPipelineButton').click()
            await ready()
            assert await page.evaluate('Boolean(state.lastPipeline?.result?.id)')
            assert await page.locator('#downloadResultButton').is_enabled()
            # Test long images, both colors/themes and all required viewport widths.
            await page.locator('#startOverButton').click()
            await upload(path)
            tall_layout=[]
            for width in SIZES:
                await page.set_viewport_size({'width':width,'height':900})
                await page.wait_for_timeout(100)
                m=await page.evaluate(LAYOUT);assert not m['errors'],m;tall_layout.append(m)
                await page.locator('#manualEditor').screenshot(path=str(output/f'tall-{width}.png'))
                await page.locator('#themeToggleButton').click()
                m=await page.evaluate(LAYOUT);assert not m['errors'],m
            # Local geometry previews: zero POST, bounded, stable source (not draft).
            await page.set_viewport_size({'width':1440,'height':900})
            posts.clear()
            await page.locator('[data-operation-card="flip_horizontal"]').click();await ready()
            await page.wait_for_function('state.manualPreviewCandidate?.data?.local')
            local_first=await page.evaluate('state.manualPreviewCandidate.data.preview')
            await page.locator('[data-operation-card="flip_horizontal"]').click();await ready()
            local_second=await page.evaluate('state.manualPreviewCandidate.data.preview')
            assert local_first==local_second
            assert max(local_first['width'],local_first['height'])<=960
            assert not posts,posts
            await page.locator('[data-operation-card="crop"]').click()
            await page.wait_for_timeout(150)
            crop_posts=len(posts)
            await page.locator('#parameter-width').fill('300')
            await page.locator('#parameter-width').dispatch_event('input')
            assert len(posts)==crop_posts
            assert await page.evaluate('state.manualPreviewCandidate?.operation?.id')=='crop'
            await page.locator('#manualApprovalButton').click();await ready()
            assert await page.evaluate('state.currentResult.width')==300
            for width in [430,390]:
                await page.set_viewport_size({'width':width,'height':900})
                m=await page.evaluate(LAYOUT);assert not m['errors'],m
            # Even the legacy quick-preview entry point is draft-only.
            approved_id = await page.evaluate('state.resultId')
            posts.clear()
            await page.evaluate('previewQuickAdjustments()')
            await ready()
            assert await page.evaluate('state.resultId') == approved_id
            assert await page.evaluate('state.manualPreviewCandidate?.operation?.id') == 'intensity_adjust'
            assert len(posts) == 1 and posts[0].endswith('/preview'), posts
            # Comparison slider repaired: real input changes the split, no JS errors.
            await page.locator('[data-view="compare"]').first.click()
            await page.locator('[data-compare-range]').evaluate("e=>{e.value=30;e.dispatchEvent(new Event('input',{bubbles:true}))}")
            assert await page.locator('[data-compare-wrap]').evaluate("e=>e.style.getPropertyValue('--split')")=='30%'
            assert not errors,errors
            assert not failed_assets,failed_assets
            report={'layout':layout,'tall_layout':tall_layout,'slider_posts':slider_posts,'errors':errors,'failed_assets':failed_assets,'stylesheets':imported,'checks':['prep approval','smart pipeline','closed chart zero work','two steps','undo redo','download','stable gamma','local flip','crop coordinates','slider race','comparison slider','legacy quick preview draft-only','both themes']}
            (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
            print(json.dumps(report,ensure_ascii=False,indent=2))
            await browser.close()

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:5002')
    parser.add_argument('--output',default='/tmp/manuscript-browser-review')
    asyncio.run(main(parser.parse_args()))
