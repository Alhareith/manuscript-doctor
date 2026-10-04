from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_preview_source_state_exists_and_current_src_is_not_authoritative():
    state_js = _read("static/js/parts/00-state-constants.js")
    preview_js = _read("static/js/parts/06-manual-preview.js")

    assert "manualPreviewSource" in state_js
    assert "manualApprovedSource" in state_js
    assert "function currentManualSourceUrl()" in preview_js
    assert "state.manualPreviewSource?.url" in preview_js

    current_source_block = preview_js.split(
        "function currentManualSourceUrl()", 1
    )[1].split("function loadCanvasImage", 1)[0]

    assert "currentSrc ||" not in current_source_block
    assert "manualOriginalUrl()" in current_source_block


def test_preparation_preview_is_persisted_in_preview_source_state():
    preview_js = _read("static/js/parts/06-manual-preview.js")

    preparation_block = preview_js.split(
        "function renderPreparationPreview", 1
    )[1].split("function manualImageHistogram", 1)[0]

    assert "setManualPreviewSource" in preparation_block
    assert "preview.url" in preparation_block


def test_preview_load_sequence_guards_stale_load_events():
    state_js = _read("static/js/parts/00-state-constants.js")
    preview_js = _read("static/js/parts/06-manual-preview.js")

    assert "manualPreviewLoadSequence" in state_js
    assert "loadId = ++manualPreviewLoadSequence" in preview_js
    assert "active.loadId !== loadId" in preview_js
    assert "requestId !== manualPreviewSequence" in preview_js


def test_crop_tool_uses_authoritative_preview_source():
    tools_js = _read("static/js/parts/10-theme-quick-tools.js")

    assert tools_js.count("currentManualSourceUrl()") >= 2
    assert "manualLivePreview?.currentSrc" not in tools_js
