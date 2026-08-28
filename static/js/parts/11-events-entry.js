function bindEvents() {
    elements.themeToggleButton?.addEventListener("click", () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"));
    elements.quickBrightness?.addEventListener("input", updateQuickAdjustmentReadout);
    elements.quickContrast?.addEventListener("input", updateQuickAdjustmentReadout);
    elements.quickResetButton?.addEventListener("click", resetQuickAdjustments);
    elements.quickPreviewButton?.addEventListener("click", previewQuickAdjustments);
    document.querySelectorAll("[data-operation-card]").forEach((button) => button.addEventListener("click", () => selectOperationCard(button.dataset.operationCard)));
    document.querySelectorAll("[data-operation-group]").forEach((button) => button.addEventListener("click", () => setOperationGroup(button.dataset.operationGroup)));
    bindDashboardMetricCards();
    elements.dropZone?.addEventListener("click", () => { if (!state.isBusy) elements.imageInput?.click(); });
    elements.dropZone?.addEventListener("keydown", (event) => { if ((event.key === "Enter" || event.key === " ") && !state.isBusy) { event.preventDefault(); elements.imageInput?.click(); } });
    ["dragenter", "dragover"].forEach((name) => elements.dropZone?.addEventListener(name, (event) => { event.preventDefault(); elements.dropZone.classList.add("is-dragging"); }));
    ["dragleave", "drop"].forEach((name) => elements.dropZone?.addEventListener(name, (event) => { event.preventDefault(); elements.dropZone.classList.remove("is-dragging"); }));
    elements.dropZone?.addEventListener("drop", (event) => selectFile(event.dataTransfer?.files?.[0]));
    elements.imageInput?.addEventListener("change", (event) => selectFile(event.target.files?.[0]));
    elements.removeImageButton?.addEventListener("click", resetAll);
    elements.startExaminationButton?.addEventListener("click", startExamination);
    elements.manualOperation?.addEventListener("change", () => {
        renderParameterFields(elements.manualOperation.value);
        document.querySelectorAll("[data-operation-card]").forEach((button) => {
            const selected = button.dataset.operationCard === elements.manualOperation.value;
            button.classList.toggle("is-selected", selected);
            button.classList.toggle("is-active", selected);
        });
        updateControls();
        clearTimeout(manualPreviewTimer);
        if (elements.manualOperation.value === "crop") {
            if (elements.manualPreviewNote) elements.manualPreviewNote.textContent = "حرّك إطار القص على الصورة، ثم اضغط «اعتماد العملية» لتطبيقه.";
            syncCropGuide();
            return;
        }
        applyManualOperation({ live: true });
    });
    elements.manualCropGuide?.addEventListener("pointerdown", beginCropDrag);
    elements.manualCropGuide?.addEventListener("pointermove", moveCropDrag);
    elements.manualCropGuide?.addEventListener("pointerup", endCropDrag);
        elements.manualCropGuide?.addEventListener("pointercancel", endCropDrag);
    elements.manualLivePreview?.addEventListener("load", () => { syncCropGuide(); renderManualChangeChart(); });
    elements.manualOriginalPreview?.addEventListener("load", () => renderManualChangeChart());

    elements.manualUndoButton?.addEventListener("click", undoManualStep);
    elements.manualRedoButton?.addEventListener("click", redoManualStep);
    

    elements.runPipelineButton?.addEventListener("click", runSmartPipeline);
    elements.downloadResultButton?.addEventListener("click", downloadCurrentResult);
    elements.startOverButton?.addEventListener("click", resetAll);
    elements.manualApprovalButton?.addEventListener("click", approveManualOperation);
    elements.manualManualDownloadButton?.addEventListener("click", downloadApprovedManualResult);

    document.querySelectorAll("[data-ui-mode]").forEach((button) => button.addEventListener("click", () => setMode(button.dataset.uiMode)));
    document.querySelectorAll("[data-editor-tab]").forEach((button) => button.addEventListener("click", () => setEditorTab(button.dataset.editorTab)));
    document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => switchViewer(button.dataset.view)));
        document.querySelectorAll("[data-open-technical-details]").forEach((button) => button.addEventListener("click", openTechnicalDetails));
    document.querySelectorAll("[data-panel-toggle]").forEach((button) => button.addEventListener("click", () => toggleAnalysisPanel(button)));
    elements.technicalDetails?.querySelector("header button")?.addEventListener("click", closeTechnicalDetails);

    document.querySelector(".details-summary")?.addEventListener("click", (event) => toggleExclusions(event.currentTarget));
}

function initialize() {
    initializeTheme();
    bindEvents();
    setMode("standard");
    setEditorTab("quick");
    setOperationGroup("page");
    if (elements.manualOperation) elements.manualOperation.value = "document_prepare";
    syncOperationCardSelection("document_prepare");
    resetDashboard();
    renderParameterFields(elements.manualOperation?.value || "");
    renderHistory();
    updateControls();
    bindFooterNavigation();
    bindWorkflowNavigation();
    setWorkflow("upload");
    if (elements.automaticExclusionList) elements.automaticExclusionList.classList.add("hidden");
}

document.addEventListener("DOMContentLoaded", initialize);
