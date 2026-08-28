function isSupportedFile(file) {
    if (!file) return false;
    const name = String(file.name || "").toLowerCase();
    return ["image/jpeg", "image/png"].includes(file.type) || /\.(jpe?g|png)$/.test(name);
}

function formatFileSize(bytes) {
    const value = Number(bytes);
    if (!Number.isFinite(value)) return "—";
    if (value < 1024) return `${value} B`;
    if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`;
    return `${(value / 1024 ** 2).toFixed(1)} MB`;
}

function revokePreviewUrl() {
    if (state.previewUrl) URL.revokeObjectURL(state.previewUrl);
    state.previewUrl = null;
}

function resetResultUI() {
    state.resultId = null;
    state.currentResult = null;
    state.currentOperation = null;
    state.lastPipeline = null;
    state.lastDecisionStatus = null;
    ["verificationSection", "decisionSection", "comparisonSection", "binarizationSection", "downloadSection"].forEach(hideSection);
    hide(elements.previewDecision);
    if (elements.resultPreview) elements.resultPreview.removeAttribute("src");
    if (elements.preservationWarnings) elements.preservationWarnings.innerHTML = "";
    if (elements.binarizationList) elements.binarizationList.innerHTML = "";
    [elements.edgeRetentionMetric, elements.componentRetentionMetric, elements.structureSimilarityMetric, elements.edgeInflationMetric].forEach((el) => { if (el) el.textContent = "—"; });
    renderHistory();
    updateViewerTabs();
    updateControls();
}

function updateManualApprovalUI() {
    const count = state.manualChain.length;
    const hasCandidate = Boolean(state.manualPreviewCandidate);
    const hasApproved = Boolean(state.manualApprovedResult?.id);

    if (elements.manualChainStatus) {
        elements.manualChainStatus.textContent = hasApproved
            ? `تم اعتماد ${count} ${count === 1 ? "عملية" : "عمليات"}`
            : "لا توجد عملية معتمدة";
    }

    if (elements.manualChainList) {
                elements.manualChainList.textContent = hasApproved
            ? `الصورة الحالية: ${operationLabel(state.manualApprovedResult.operation?.id || "manual_operation")} — يمكنك إضافة خطوة يدوية أخرى.`

            : hasCandidate
                ? "توجد معاينة غير معتمدة — راجعها قبل الاعتماد."
                : "المعاينة الحالية غير محفوظة بعد.";
    }

    const activeIndex = Number.isInteger(state.manualActiveIndex) ? state.manualActiveIndex : -1;
    const canUndo = activeIndex >= 0 && !state.isBusy;
    const canRedo = activeIndex >= -1 && activeIndex < state.manualChain.length - 1 && !state.isBusy;
    if (elements.manualUndoButton) elements.manualUndoButton.disabled = !canUndo;
    if (elements.manualRedoButton) elements.manualRedoButton.disabled = !canRedo;
    if (elements.manualApprovalButton) {
        elements.manualApprovalButton.disabled = !hasCandidate || state.isBusy;
    }

    if (elements.manualManualDownloadButton) {
        elements.manualManualDownloadButton.disabled = !hasApproved || state.isBusy;
    }
}

function resetManualChain() {
    state.manualChain = [];
    state.manualActiveIndex = -1;
    state.manualWorkingResultId = null;
    state.manualApprovedResult = null;
    state.manualPreviewCandidate = null;
    updateManualApprovalUI();
}


function resetAll() {
    clearTimeout(manualPreviewTimer);
    manualPreviewSequence += 1;
    manualPreviewAbortController?.abort();
    manualPreviewAbortController = null;
    revokePreviewUrl();
    state.selectedFile = null;
    state.imageId = null;
    state.imageData = null;
    state.analysis = null;
    state.diagnoses = [];
    state.preservationProfile = null;
    state.recommendations = [];
    state.exclusions = [];
    resetResultUI();
    resetManualChain();

    if (elements.imageInput) elements.imageInput.value = "";
    hide(elements.selectedFile);
    hide(elements.documentPreviewSection);
    hide(elements.examinationSection);
    hide(elements.treatmentSection);
    hide(elements.technicalDetails);
    show(byId("uploadSection"));
    if (elements.originalPreview) elements.originalPreview.removeAttribute("src");
    if (elements.comparisonOriginal) elements.comparisonOriginal.removeAttribute("src");
    if (elements.manualLivePreview) elements.manualLivePreview.removeAttribute("src");
    if (elements.manualOriginalPreview) elements.manualOriginalPreview.removeAttribute("src");
    resetDashboard();
    clearError();
    setWorkflow("upload");
    updateControls();
}

function selectFile(file) {
    clearError();
    if (!isSupportedFile(file)) { showError("نوع الملف غير مدعوم. استخدم JPG أو PNG."); return; }
    revokePreviewUrl();
    state.selectedFile = file;
    state.previewUrl = URL.createObjectURL(file);
        state.imageId = null;
    state.imageData = null;
    state.analysis = null;
    state.diagnoses = [];
    state.preservationProfile = null;
    state.recommendations = [];
    state.exclusions = [];
    resetManualChain();
    resetResultUI();
    hide(elements.examinationSection);
    hide(elements.treatmentSection);
    hide(elements.technicalDetails);
    resetDashboard();

    if (elements.selectedFileName) elements.selectedFileName.textContent = file.name || "صورة وثيقة";
    if (elements.selectedFileMeta) elements.selectedFileMeta.textContent = formatFileSize(file.size);
    if (elements.originalPreview) elements.originalPreview.src = state.previewUrl;
    if (elements.comparisonOriginal) elements.comparisonOriginal.src = state.previewUrl;
    if (elements.manualLivePreview) elements.manualLivePreview.src = state.previewUrl;
    if (elements.manualOriginalPreview) elements.manualOriginalPreview.src = state.previewUrl;
    if (elements.manualOperation) {
        elements.manualOperation.value = "document_prepare";
        syncOperationCardSelection("document_prepare");
        renderParameterFields("document_prepare");
    }
    if (elements.manualPreviewNote) elements.manualPreviewNote.textContent = "الصورة الأصلية — تجهيز الوثيقة محدد افتراضياً؛ اختره أو جرّب عملية أخرى.";
    show(elements.selectedFile);
    show(elements.documentPreviewSection);
    setWorkflow("upload");
    updateControls();

    // Start the examination as soon as a valid image is selected.
    // The visible button remains available as a manual retry/fallback.
    startExamination();
}

async function apiRequest(url, options = {}) {
    let response;
    try { response = await fetch(url, options); }
    catch { throw new Error("تعذر الاتصال بالخادم. تحقق من تشغيل التطبيق ثم أعد المحاولة."); }
    const contentType = response.headers.get("content-type") || "";
    let payload = null;
    if (contentType.includes("application/json")) {
        try { payload = await response.json(); } catch { payload = null; }
    }
    if (!response.ok || payload?.success === false) {
        throw new Error(payload?.message || payload?.error?.message || `فشل الطلب (${response.status}).`);
    }
    return payload?.data ?? payload;
}

