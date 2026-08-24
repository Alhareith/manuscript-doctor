function renderBinarizationCandidates(candidates) {
    elements.binarizationList.innerHTML = "";
    if (!Array.isArray(candidates) || candidates.length === 0) { hideSection("binarizationSection"); return; }
    candidates.forEach((candidate) => {
        const item = document.createElement("article");
        item.className = "binarization-item";
        const title = operationLabel(candidate.operation_id);
        const decision = statusLabel(candidate.decision?.status || "review_required");
        item.innerHTML = `<div class="item-heading"><div><strong></strong><small></small></div><span></span></div>`;
        item.querySelector("strong").textContent = title;
        item.querySelector("small").textContent = technicalOperationLabel(candidate.operation_id);
        item.querySelector(".item-heading > span").textContent = decision;
        if (candidate.result?.id) {
            const image = document.createElement("img");
            image.className = "binarization-preview";
            image.alt = `نتيجة ${title}`;
            image.src = `/api/results/${encodeURIComponent(candidate.result.id)}`;
            item.appendChild(image);
        }
        if (candidate.reason) { const p = document.createElement("p"); p.textContent = candidate.reason; item.appendChild(p); }
        if (candidate.decision?.message) { const small = document.createElement("small"); small.className = "binarization-decision"; small.textContent = candidate.decision.message; item.appendChild(small); }
        elements.binarizationList.appendChild(item);
    });
    showSection("binarizationSection");
}

function pipelineStopExplanation(data) {
    const steps = Array.isArray(data?.steps) ? data.steps : [];
    const decision = data?.decision || {};
    const last = steps.at(-1);
    if (decision.message) return decision.message;
    if (last?.note) return last.note;
    if (last?.decision?.message) return last.decision.message;
    if (last?.benefit?.message) return last.benefit.message;
    return "توقف المسار وفق سياسة المعالجة المحافظة بعد تقييم الخطوة الحالية.";
}

function setStopExplanation(message) { if (elements.stopExplanation) elements.stopExplanation.textContent = message || "—"; }

function renderPipelineResult(data) {
    state.lastPipeline = data;
    showPrimaryResult(data.result, "pipeline");
    renderDecision(data.decision);
    data.preservation ? renderPreservation(data.preservation) : hideSection("verificationSection");
    renderBinarizationCandidates(data.binarization_candidates);
    setStopExplanation(pipelineStopExplanation(data));
    renderHistory();
    updateTechnicalDetails();
    byId("manualEditor")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function runSmartPipeline() {
    if (!state.imageId || state.isBusy) return;
    clearError();
    resetResultUI();
    resetManualChain();
    setBusy(true, "جارٍ تنفيذ المعالجة الذكية", "يتم اختيار المرشح المؤهل، تطبيقه، إعادة التقييم، ثم التحقق من المحافظة على التفاصيل قبل قبول النتيجة.");
    setWorkflow("treat");
    try {
        const data = await apiRequest(`/api/images/${encodeURIComponent(state.imageId)}/pipeline`, { method: "POST" });
        renderPipelineResult(data);
    } catch (error) { showError(error.message); }
    finally { setBusy(false); }
}

