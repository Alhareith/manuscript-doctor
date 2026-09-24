"""Browser validation for the one-screen Premium Command Studio.

Runs against a live Flask instance and writes:
- command-studio-1536x1024.png
- report.json
"""
import argparse
import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright


LAYOUT_CHECK = r"""() => {
  const q = (s) => document.querySelector(s);
  const rect = (s) => {
    const el = q(s);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return {left:r.left, top:r.top, right:r.right, bottom:r.bottom, width:r.width, height:r.height};
  };
  const inside = (r) => r && r.left >= -1 && r.top >= -1 && r.right <= innerWidth + 1 && r.bottom <= innerHeight + 1;
  const overlap = (a,b) => a && b && a.left < b.right-1 && a.right > b.left+1 && a.top < b.bottom-1 && a.bottom > b.top+1;

  const panels = {
    header: rect('.app-header'),
    upload: rect('#uploadSection'),
    preview: rect('.manual-preview-pane'),
    controls: rect('.manual-controls-pane'),
    crop: rect('#commandCropPanel'),
    actions: rect('#commandActionBar'),
    results: rect('#commandResultsDock'),
    info: rect('#commandInfoPanel')
  };
  const errors = [];
  if (!document.body.classList.contains('command-studio-active')) errors.push('command studio class missing');
  if (document.documentElement.scrollHeight > innerHeight + 2) errors.push('document has vertical page scroll');
  if (document.documentElement.scrollWidth > innerWidth + 2) errors.push('document has horizontal page scroll');
  for (const [name, value] of Object.entries(panels)) {
    if (!value) errors.push('missing panel: ' + name);
    else if (!inside(value)) errors.push('panel outside viewport: ' + name);
  }
  const expectedNonOverlap = [
    ['upload','preview'],['preview','controls'],['crop','actions'],['actions','controls'],
    ['crop','results'],['results','info']
  ];
  for (const [a,b] of expectedNonOverlap) {
    if (overlap(panels[a], panels[b])) errors.push('unexpected overlap: ' + a + '/' + b);
  }
  const ids = [...document.querySelectorAll('[data-operation-card]')].map(e => e.dataset.operationCard).filter(Boolean);
  const styleInfo = (s) => {
    const e=q(s); if(!e) return null; const x=getComputedStyle(e);
    return {
      margin:x.margin, padding:x.padding, transform:x.transform,
      position:x.position, top:x.top, display:x.display,
      height:x.height, minHeight:x.minHeight, boxSizing:x.boxSizing,
      alignContent:x.alignContent, justifyContent:x.justifyContent
    };
  };
  return {
    viewport: {width:innerWidth,height:innerHeight},
    computed: {
      html: styleInfo('html'),
      body: styleInfo('body'),
      shell: styleInfo('.app-shell'),
      header: styleInfo('.app-header'),
      workspace: styleInfo('#workspace')
    },
    scroll: {width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight},
    panels,
    operationCount: new Set(ids).size,
    errors
  };
}"""


async def ready(page):
    await page.wait_for_function("!state.isBusy && !manualRequestInFlight", timeout=180000)


async def main(args):
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width": 1536, "height": 1024}, reduced_motion="reduce")
        browser_errors = []
        failed_assets = []
        page.on("pageerror", lambda e: browser_errors.append(str(e)))
        page.on("console", lambda m: browser_errors.append(m.text) if m.type == "error" else None)
        page.on("response", lambda r: failed_assets.append([r.url, r.status]) if r.status >= 400 and "/static/" in r.url else None)

        await page.goto(args.url, wait_until="networkidle")
        initial = await page.evaluate(LAYOUT_CHECK)
        assert not initial["errors"], initial
        assert initial["operationCount"] >= 36, initial["operationCount"]

        # All eight real categories remain reachable through the three visual toolsets.
        expected = {
            "basic": {"page", "lighting", "contrast", "noise"},
            "advanced": {"detail", "threshold"},
            "restoration": {"structure", "background"},
        }
        visible_groups = {}
        for toolset, groups in expected.items():
            await page.locator(f'[data-command-toolset="{toolset}"]').click()
            visible = await page.locator('.category-tab:not([hidden])').evaluate_all(
                "els => els.map(e => e.dataset.operationGroup)"
            )
            visible_groups[toolset] = visible
            assert set(visible) == groups, (toolset, visible)

        # Upload a real repository fixture; existing auto-examination must still work.
        fixture = Path("static/assets/document-before.png").resolve()
        await page.locator("#imageInput").set_input_files(str(fixture))
        await page.wait_for_function("state.imageId && !state.isBusy", timeout=180000)
        await page.wait_for_function(
            "document.querySelector('#manualOriginalPreview')?.naturalWidth > 0 && "
            "document.querySelector('#manualLivePreview')?.naturalWidth > 0",
            timeout=180000,
        )

        # Real manual operation -> preview -> approval.
        await page.locator('[data-ref-operation-select]').select_option('clahe')
        await ready(page)
        assert await page.evaluate("state.manualPreviewCandidate?.operation?.id") == "clahe"
        assert await page.locator("#manualApprovalButton").is_enabled()
        await page.locator("#manualApprovalButton").click()
        await ready(page)
        assert await page.evaluate("Boolean(state.resultId)")

        # Reference toolbar modes are functional, not decorative.
        pair = page.locator(".manual-preview-pair")
        await page.locator('[data-ref-view="zoom"]').click()
        assert "ref-zoom" in (await pair.get_attribute("class") or "")
        await page.locator('[data-ref-view="overlay"]').click()
        assert "ref-overlay" in (await pair.get_attribute("class") or "")
        await page.locator('[data-ref-view="side"]').click()
        assert await pair.get_attribute("data-command-preview-mode") == "side"

        # Crop shortcut must route to the existing crop tool, preserving the real editor.
        await page.locator('[data-ref-crop="crop"]').click()
        await page.wait_for_function("document.querySelector('#manualOperation').value === 'crop'", timeout=10000)
        assert await page.evaluate("state.manualPreviewCandidate?.operation?.id") in [None, "crop"]

        # Result details remain accessible without turning the page into a long document.
        await page.locator("#commandInfoPanel [data-command-results]").click()
        assert await page.locator("body").evaluate("e => e.classList.contains('command-results-open')")
        await page.locator("#commandResultOverlay .command-result-overlay-head button").click()

        final_layout = await page.evaluate(LAYOUT_CHECK)
        assert not final_layout["errors"], final_layout
        assert final_layout["scroll"]["height"] <= 1026, final_layout["scroll"]

        screenshot = output / "command-studio-1536x1024.png"
        await page.screenshot(path=str(screenshot), full_page=False)

        report = {
            "initial": initial,
            "final": final_layout,
            "visible_groups": visible_groups,
            "browser_errors": browser_errors,
            "failed_assets": failed_assets,
            "checks": [
                "single-screen 1536x1024",
                "no page scroll",
                "panels inside viewport",
                "36+ operations retained",
                "all 8 categories reachable",
                "upload and automatic examination",
                "CLAHE preview and approval",
                "reference zoom/overlay/side preview modes",
                "crop shortcut uses existing crop editor",
                "result detail overlay",
            ],
        }
        (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        assert not browser_errors, browser_errors
        assert not failed_assets, failed_assets
        print(json.dumps(report, ensure_ascii=False, indent=2))
        await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5002")
    parser.add_argument("--output", default="command-studio-artifact")
    asyncio.run(main(parser.parse_args()))
