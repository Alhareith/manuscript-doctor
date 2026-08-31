function applyTheme(theme) {
    const normalized = theme === "dark" ? "dark" : "light";
    document.documentElement.dataset.theme = normalized;
    localStorage.setItem("document-doctor-theme", normalized);
    if (elements.themeToggleButton) {
        const dark = normalized === "dark";
        elements.themeToggleButton.setAttribute("aria-pressed", String(dark));
        elements.themeToggleButton.setAttribute("aria-label", dark ? "تفعيل الوضع الفاتح" : "تفعيل الوضع الليلي");
        const label = elements.themeToggleButton.querySelector(".theme-toggle-label");
        const icon = elements.themeToggleButton.querySelector(".theme-toggle-icon");
        if (label) label.textContent = dark ? "الوضع الفاتح" : "الوضع الليلي";
        if (icon) icon.className = dark ? "bi bi-sun theme-toggle-icon" : "bi bi-moon-stars theme-toggle-icon";
    }
    if (state.analysis?.metrics) renderDashboardCharts(state.analysis.metrics);
}

function initializeTheme() {
    const saved = localStorage.getItem("document-doctor-theme");
    if (saved === "dark" || saved === "light") {
        applyTheme(saved);
        return;
    }
    // The product default is the quiet metallic dark theme; the user can switch to light.
    applyTheme("dark");
}

function updateQuickAdjustmentReadout() {
    const brightness = Number(elements.quickBrightness?.value || 0);
    const contrast = Number(elements.quickContrast?.value || 100) / 100;
    if (elements.quickBrightnessValue) elements.quickBrightnessValue.textContent = brightness > 0 ? `+${brightness}` : String(brightness);
    if (elements.quickContrastValue) elements.quickContrastValue.textContent = contrast.toFixed(2);
    if (elements.quickAdjustmentStatus) {
        const changed = brightness !== 0 || Math.abs(contrast - 1) > 0.001;
        elements.quickAdjustmentStatus.textContent = changed
            ? `معاينة جاهزة للإعدادات الحالية: السطوع ${brightness > 0 ? "+" : ""}${brightness}، التباين ${contrast.toFixed(2)}.`
            : "حرّك السطوع أو التباين، ثم أنشئ معاينة عندما تريد.";
    }
}

function resetQuickAdjustments() {
    if (elements.quickBrightness) elements.quickBrightness.value = "0";
    if (elements.quickContrast) elements.quickContrast.value = "100";
    updateQuickAdjustmentReadout();
}

async function previewQuickAdjustments() {
    if (!state.imageId || state.isBusy) return;
    clearError();
    resetResultUI();
    const beta = Number(elements.quickBrightness?.value || 0);
    const alpha = Number(elements.quickContrast?.value || 100) / 100;
    setBusy(true, "جارٍ إنشاء المعاينة", "يتم تطبيق تعديل السطوع والتباين على الوثيقة ثم التحقق من النتيجة.");
    setWorkflow("treat");
    try {
        const data = await apiRequest(`/api/images/${encodeURIComponent(state.imageId)}/operations`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ operation_id: "intensity_adjust", parameters: { alpha, beta } })
        });
        renderManualOperationResult(data);
    } catch (error) {
        showError(error.message);
    } finally {
        setBusy(false);
    }
}

function syncOperationCardSelection(operationId) {
    document.querySelectorAll("[data-operation-card]").forEach((button) => {
        const selected = button.dataset.operationCard === operationId;
        button.classList.toggle("is-selected", selected);
        button.classList.toggle("is-active", selected);
        button.setAttribute("aria-pressed", String(selected));
    });
}

function selectOperationCard(operationId) {
    if (!operationId || !state.imageId || state.isBusy || !elements.manualOperation) return;

    /* Keep the existing compatibility mapping, but use the real manual deskew operation as-is. */
    const resolvedOperationId = operationId;
    state.manualPreviewCandidate = null;
    elements.manualOperation.value = resolvedOperationId;
    renderParameterFields(resolvedOperationId);
    syncOperationCardSelection(operationId);

    updateControls();

    if (resolvedOperationId === "crop") {
        const sourceUrl = state.manualWorkingResultId
            ? `/api/results/${encodeURIComponent(state.manualWorkingResultId)}?source=${Date.now()}`
            : manualOriginalUrl();
        if (sourceUrl && elements.manualLivePreview) elements.manualLivePreview.src = sourceUrl;
        if (elements.manualPreviewStatus) elements.manualPreviewStatus.innerHTML = '<i class="bi bi-crop"></i> حدد منطقة القص';
        if (elements.manualPreviewNote) elements.manualPreviewNote.textContent = "حرّك إطار القص على الصورة، ثم اضغط «اعتماد العملية» لتطبيقه.";
        requestAnimationFrame(syncCropGuide);
        updateManualApprovalUI();
        return;
    }

    if (elements.manualPreviewStatus) {
        elements.manualPreviewStatus.innerHTML = '<i class="bi bi-arrow-repeat"></i> جارٍ تطبيق العملية';
    }
    if (elements.manualPreviewNote) {
        elements.manualPreviewNote.textContent = `${operationLabel(resolvedOperationId)} — يتم إنشاء المعاينة الآن.`;
    }

    clearTimeout(manualPreviewTimer);
    applyManualOperation({ live: true });
}

function setOperationGroup(group) {
    document.querySelectorAll("[data-operation-group]").forEach((button) => button.classList.toggle("is-active", button.dataset.operationGroup === group));
    document.querySelectorAll("[data-operation-group-panel]").forEach((panel) => panel.classList.toggle("is-active", panel.dataset.operationGroupPanel === group));
}
