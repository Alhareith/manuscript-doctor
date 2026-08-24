function show(element) { if (element) element.classList.remove("hidden"); }
function hide(element) { if (element) element.classList.add("hidden"); }
function byId(id) { return document.getElementById(id); }
function showSection(id) { show(byId(id)); }
function hideSection(id) { hide(byId(id)); }
function formatNumber(value, digits = 3) { const n = Number(value); return Number.isFinite(n) ? n.toFixed(digits).replace(/\.?0+$/, "") : "—"; }
function clamp(value, min, max) { return Math.min(max, Math.max(min, value)); }
function operationLabel(id) { return operationNames[id]?.[0] || humanizeCode(id); }
function technicalOperationLabel(id) { return operationNames[id]?.[1] || humanizeCode(id); }
function humanizeCode(value) { return String(value || "—").replaceAll("_", " "); }
function statusLabel(value) { return statusLabels[value] || humanizeCode(value); }
function severityLabel(value) { return severityLabels[value] || humanizeCode(value); }
function safeStatusClass(value) {
    const normalized = String(value || "neutral").toLowerCase();
    if (["acceptable", "accepted", "low"].includes(normalized)) return "safe";
    if (["caution", "accepted_with_caution", "moderate", "medium", "review_required"].includes(normalized)) return "caution";
    if (normalized.includes("reject") || normalized.includes("risk") || normalized === "high") return "danger";
    return "neutral";
}

function setWorkflow(step) {
    const currentIndex = workflowOrder.indexOf(step);
    document.querySelectorAll("[data-workflow-step]").forEach((item) => {
        const index = workflowOrder.indexOf(item.dataset.workflowStep);
        item.classList.toggle("is-current", index === currentIndex);
        item.classList.toggle("is-complete", currentIndex > index);
    });
}

function setMode(mode) {
    state.uiMode = mode === "advanced" ? "advanced" : "standard";
    document.documentElement.dataset.uiMode = state.uiMode;
    document.querySelectorAll("[data-ui-mode]").forEach((button) => {
        const active = button.dataset.uiMode === state.uiMode;
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-pressed", String(active));
    });
    document.querySelectorAll("[data-standard-mode-panel]").forEach((panel) => panel.classList.toggle("hidden", state.uiMode !== "standard"));
    document.querySelectorAll("[data-advanced-mode-panel]").forEach((panel) => panel.classList.toggle("hidden", state.uiMode !== "advanced"));
}

function setEditorTab(tab) {
    state.activeEditorTab = tab;
    document.querySelectorAll("[data-editor-tab]").forEach((button) => {
        const active = button.dataset.editorTab === tab;
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-selected", String(active));
    });
    document.querySelectorAll("[data-editor-panel]").forEach((panel) => panel.classList.toggle("is-active", panel.dataset.editorPanel === tab));
}

function setBusy(busy, title = "جارٍ التنفيذ", message = "يرجى الانتظار...") {
    state.isBusy = busy;
    if (elements.processingTitle) elements.processingTitle.textContent = title;
    if (elements.processingMessage) elements.processingMessage.textContent = message;
    elements.processingSection?.setAttribute("aria-busy", String(busy));
    busy ? show(elements.processingSection) : hide(elements.processingSection);
    updateControls();
}

function updateControls() {
    const hasFile = Boolean(state.selectedFile);
    const hasImage = Boolean(state.imageId);
    if (elements.startExaminationButton) elements.startExaminationButton.disabled = !hasFile || state.isBusy;
    if (elements.removeImageButton) elements.removeImageButton.disabled = state.isBusy;
    if (elements.runPipelineButton) elements.runPipelineButton.disabled = !hasImage || state.isBusy;
    if (elements.smartPipelineHint) {
        elements.smartPipelineHint.classList.toggle("is-ready", hasImage && !state.isBusy);
        elements.smartPipelineHint.innerHTML = hasImage && !state.isBusy
            ? '<i class="bi bi-check-circle-fill"></i> جاهزة الآن: اختر المسار الذكي للحصول على نتيجة محافظة.'
            : state.isBusy
                ? '<i class="bi bi-arrow-repeat"></i> يتم تجهيز المعالجة الذكية…'
                : '<i class="bi bi-hourglass-split"></i> ارفع الوثيقة ثم أكمل الفحص لتفعيل المسار.';
    }
    if (elements.manualOperation) elements.manualOperation.disabled = !hasImage || state.isBusy;
    document.querySelectorAll("[data-operation-card]").forEach((button) => { button.disabled = !hasImage || state.isBusy; });
    
    [elements.quickBrightness, elements.quickContrast, elements.quickResetButton, elements.quickPreviewButton].forEach((control) => { if (control) control.disabled = !hasImage || state.isBusy; });
    if (elements.downloadResultButton) {
        const blockedResult = state.lastDecisionStatus === "high_risk" || String(state.lastDecisionStatus || "").startsWith("rejected_high_risk");
        elements.downloadResultButton.disabled = !state.resultId || state.isBusy || blockedResult;
    }
    document.querySelectorAll("[data-open-technical-details]").forEach((button) => button.disabled = !state.analysis);
}

function clearError() { hide(elements.errorSection); if (elements.errorMessage) elements.errorMessage.textContent = "—"; }
function showError(message) { if (elements.errorMessage) elements.errorMessage.textContent = message || "حدث خطأ غير متوقع."; show(elements.errorSection); elements.errorSection?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }

