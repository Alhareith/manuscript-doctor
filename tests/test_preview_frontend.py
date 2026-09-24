"""Exercise JS failure races with Node; no browser/network timing assumptions."""
from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.mark.parametrize('stale', [True, False])
def test_failed_preview_cannot_replace_newer_operation_message(stale):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is required for the frontend race contract')
    file = Path(__file__).resolve().parents[1] / 'static/js/parts/07-manual-execution.js'
    script = r'''
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
let failRequest, started;
const start = new Promise(resolve => { started = resolve; });
const note = {textContent: 'original'};
const context = {
    state: {imageId:'sample',isBusy:false},
    elements: {manualOperation:{value:'clahe'},manualPreviewNote:note},
    manualPreviewSequence:0,manualPreviewAbortController:null,
    clearError(){}, collectManualParameters(){return {};},
    renderLocalManualPreview:async()=>false,
    setManualPreviewBusy(){},setWorkflow(){},setBusy(){},
    AbortController,
    apiRequest(){started();return new Promise((resolve,reject)=>{failRequest=reject;});}
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'),context);
(async()=>{
    const pending=context.executeManualOperation({live:true});
    await start;
    const stale=process.argv[2]==='true';
    if(stale){context.manualPreviewSequence++;note.textContent='new crop instructions';}
    failRequest(new Error('old request failed'));
    await pending;
    if(stale)assert.equal(note.textContent,'new crop instructions');
    else assert.match(note.textContent,/old request failed/);
})().catch(e=>{console.error(e);process.exitCode=1});
'''
    result = subprocess.run([node, '-e', script, str(file), str(stale).lower()],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
