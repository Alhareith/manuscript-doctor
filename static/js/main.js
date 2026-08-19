"use strict";

const state = {
    selectedFile: null,
    previewUrl: null,
    imageId: null,
    resultId: null,
    imageData: null,
    analysis: null,
    diagnoses: [],
    preservationProfile: null,
    recommendations: [],
    exclusions: [],
    currentResult: null,
    currentOperation: null,
    lastPipeline: null,
    lastDecisionStatus: null,
    uiMode: "standard",
    activeEditorTab: "advanced",
    isBusy: false
};

const elements = {
    dropZone: document.getElementById("dropZone"),
    imageInput: document.getElementById("imageInput"),
    selectedFile: document.getElementById("selectedFile"),
    selectedFileName: document.getElementById("selectedFileName"),
    selectedFileMeta: document.getElementById("selectedFileMeta"),
    removeImageButton: document.getElementById("removeImageButton"),
    startExaminationButton: document.getElementById("startExaminationButton"),
    originalPreview: document.getElementById("originalPreview"),
    comparisonOriginal: document.getElementById("comparisonOriginal"),
    resultPreview: document.getElementById("resultPreview"),
    brightnessMetric: document.getElementById("brightnessMetric"),
    contrastMetric: document.getElementById("contrastMetric"),
    sharpnessMetric: document.getElementById("sharpnessMetric"),
    noiseMetric: document.getElementById("noiseMetric"),
    illuminationMetric: document.getElementById("illuminationMetric"),
    edgeDensityMetric: document.getElementById("edgeDensityMetric"),
    diagnosisList: document.getElementById("diagnosisList"),
    preservationLevelBadge: document.getElementById("preservationLevelBadge"),
    preservationMessage: document.getElementById("preservationMessage"),
    preservationIndicators: document.getElementById("preservationIndicators"),
    recommendationList: document.getElementById("recommendationList"),
    automaticExclusions: document.getElementById("automaticExclusions"),
    automaticExclusionList: document.getElementById("automaticExclusionList"),
    manualOperation: document.getElementById("manualOperation"),
    manualParameters: document.getElementById("manualParameters"),
    applyManualButton: document.getElementById("applyManualButton"),
    runPipelineButton: document.getElementById("runPipelineButton"),
    smartPipelineHint: document.getElementById("smartPipelineHint"),
    processingTitle: document.getElementById("processingTitle"),
    processingMessage: document.getElementById("processingMessage"),
    edgeRetentionMetric: document.getElementById("edgeRetentionMetric"),
    componentRetentionMetric: document.getElementById("componentRetentionMetric"),
    structureSimilarityMetric: document.getElementById("structureSimilarityMetric"),
    edgeInflationMetric: document.getElementById("edgeInflationMetric"),
    preservationWarnings: document.getElementById("preservationWarnings"),
    decisionCard: document.getElementById("decisionCard"),
    decisionStatus: document.getElementById("decisionStatus"),
    decisionMessage: document.getElementById("decisionMessage"),
    binarizationList: document.getElementById("binarizationList"),
    downloadResultButton: document.getElementById("downloadResultButton"),
    startOverButton: document.getElementById("startOverButton"),
    errorSection: document.getElementById("errorSection"),
    errorMessage: document.getElementById("errorMessage"),
    processingSection: document.getElementById("processingStateSection"),
    documentPreviewSection: document.getElementById("documentPreviewSection"),
    examinationSection: document.getElementById("examinationSection"),
    treatmentSection: document.getElementById("treatmentSection"),
    technicalDetails: document.querySelector("[data-technical-details]"),
    technicalDetailsBody: document.querySelector(".technical-details-body"),
    dashboardInterpretation: document.querySelector("[data-dashboard-interpretation]"),
    treatmentHistory: document.querySelector("[data-treatment-history]"),
    historyTimeline: document.querySelector(".history-timeline"),
    previewDecision: document.querySelector("[data-preview-decision]"),
    stopExplanation: document.querySelector("[data-stop-explanation] p"),
    documentStatusTitle: document.querySelector(".document-status-block strong"),
    documentStatusMessage: document.querySelector(".document-status-block p"),
    editorStateText: document.querySelector(".editor-state span:last-child"),
    themeToggleButton: document.getElementById("themeToggleButton"),
    quickBrightness: document.getElementById("quickBrightness"),
    quickBrightnessValue: document.getElementById("quickBrightnessValue"),
    quickContrast: document.getElementById("quickContrast"),
    quickContrastValue: document.getElementById("quickContrastValue"),
    quickResetButton: document.getElementById("quickResetButton"),
    quickPreviewButton: document.getElementById("quickPreviewButton"),
    quickAdjustmentStatus: document.getElementById("quickAdjustmentStatus"),
    manualLivePreview: document.getElementById("manualLivePreview"),
    manualCropGuide: document.getElementById("manualCropGuide"),
    manualPreviewOverlay: document.getElementById("manualPreviewOverlay"),
    manualPreviewStatus: document.getElementById("manualPreviewStatus"),
    manualPreviewNote: document.getElementById("manualPreviewNote"),
    selectedOperationFriendly: document.getElementById("selectedOperationFriendly"),
    selectedOperationTechnical: document.getElementById("selectedOperationTechnical"),
    tonalDistributionChart: document.getElementById("tonalDistributionChart"),
    qualityMetricsChart: document.getElementById("qualityMetricsChart")
};

let manualPreviewTimer = null;
let manualPreviewSequence = 0;
let tonalChartInstance = null;
let qualityChartInstance = null;
let cropDragState = null;

const operationParameters = {
    clahe: [
        {
            name: "clip_limit",
            label: "Clip Limit",
            type: "number",
            value: 1.5,
            min: 0.1,
            max: 5,
            step: 0.1
        },
        {
            name: "tile_grid_size",
            label: "Tile Grid Size",
            type: "number",
            value: 8,
            min: 2,
            max: 32,
            step: 1
        }
    ],

    histogram_equalization: [],

    median_denoise: [
        {
            name: "kernel_size",
            label: "Kernel Size",
            type: "number",
            value: 3,
            min: 3,
            max: 15,
            step: 2
        }
    ],

    sharpen: [
        {
            name: "amount",
            label: "Amount",
            type: "number",
            value: 0.5,
            min: 0,
            max: 2,
            step: 0.05
        },
        {
            name: "sigma",
            label: "Sigma",
            type: "number",
            value: 1.0,
            min: 0.1,
            max: 5,
            step: 0.1
        }
    ],

    global_threshold: [
        {
            name: "threshold",
            label: "Threshold",
            type: "number",
            value: 127,
            min: 0,
            max: 255,
            step: 1
        }
    ],

    otsu_threshold: [],

    adaptive_threshold: [
        {
            name: "block_size",
            label: "Block Size",
            type: "number",
            value: 35,
            min: 3,
            max: 101,
            step: 2
        },
        {
            name: "c",
            label: "C",
            type: "number",
            value: 11,
            min: -30,
            max: 30,
            step: 1
        }
    ],

    morphological_opening: [
        {
            name: "kernel_size",
            label: "Kernel Size",
            type: "number",
            value: 3,
            min: 3,
            step: 2
        }
    ],

    morphological_closing: [
        {
            name: "kernel_size",
            label: "Kernel Size",
            type: "number",
            value: 3,
            min: 3,
            step: 2
        }
    ],
    bilateral_denoise: [
        {
            name: "diameter",
            label: "Diameter",
            type: "number",
            value: 5,
            min: 1,
            max: 15,
            step: 2
        },
        {
            name: "sigma_color",
            label: "Sigma Color",
            type: "number",
            value: 25,
            min: 1,
            max: 150,
            step: 1
        },
        {
            name: "sigma_space",
            label: "Sigma Space",
            type: "number",
            value: 25,
            min: 1,
            max: 150,
            step: 1
        }
    ],
    non_local_means_denoise: [
        {
            name: "strength",
            label: "Strength",
            type: "number",
            value: 5,
            min: 1,
            max: 30,
            step: 1
        },
        {
            name: "template_window_size",
            label: "Template Window",
            type: "number",
            value: 7,
            min: 3,
            max: 15,
            step: 2
        },
        {
            name: "search_window_size",
            label: "Search Window",
            type: "number",
            value: 21,
            min: 3,
            max: 41,
            step: 2
        }
    ],
    illumination_normalize: [
        {
            name: "kernel_size",
            label: "Background Scale",
            type: "number",
            value: 51,
            min: 15,
            max: 151,
            step: 2
        },
        {
            name: "strength",
            label: "Correction Strength",
            type: "number",
            value: 0.65,
            min: 0.1,
            max: 1,
            step: 0.05
        }
    ],
    gamma_correct: [
        {
            name: "gamma",
            label: "Gamma",
            type: "number",
            value: 1.0,
            min: 0.1,
            max: 3,
            step: 0.05
        }
    ],
    intensity_adjust: [
        {
            name: "alpha",
            label: "Contrast Scale",
            type: "number",
            value: 1.0,
            min: 0.1,
            max: 3,
            step: 0.05
        },
        {
            name: "beta",
            label: "Brightness Offset",
            type: "number",
            value: 0,
            min: -100,
            max: 100,
            step: 1
        }
    ],
    faded_text_enhance: [
        {
            name: "clip_limit",
            label: "Local Contrast",
            type: "number",
            value: 1.4,
            min: 0.1,
            max: 5,
            step: 0.1
        },
        {
            name: "gamma",
            label: "Gamma",
            type: "number",
            value: 0.95,
            min: 0.1,
            max: 3,
            step: 0.05
        }
    ],
    background_suppress: [
        {
            name: "kernel_size",
            label: "Background Scale",
            type: "number",
            value: 31,
            min: 15,
            max: 151,
            step: 2
        },
        {
            name: "strength",
            label: "Suppression Strength",
            type: "number",
            value: 0.45,
            min: 0.1,
            max: 1,
            step: 0.05
        }
    ],
    weak_structure_suppress: [
        {
            name: "kernel_size",
            label: "Background Scale",
            type: "number",
            value: 31,
            min: 15,
            max: 151,
            step: 2
        },
        {
            name: "threshold",
            label: "Weak Structure Threshold",
            type: "number",
            value: 12,
            min: 1,
            max: 50,
            step: 1
        },
        {
            name: "strength",
            label: "Suppression Strength",
            type: "number",
            value: 0.35,
            min: 0.1,
            max: 1,
            step: 0.05
        }
    ],
    morphological_top_hat: [
        {
            name: "kernel_size",
            label: "Kernel Size",
            type: "number",
            value: 3,
            min: 3,
            max: 15,
            step: 2
        }
    ],
    morphological_black_hat: [
        {
            name: "kernel_size",
            label: "Kernel Size",
            type: "number",
            value: 5,
            min: 3,
            max: 15,
            step: 2
        }
    ],
    deskew: [
        {
            name: "angle",
            label: "Angle",
            type: "number",
            value: 0,
            min: -45,
            max: 45,
            step: 0.1
        }
    ],
    crop: [
        { name: "x", label: "بداية القص أفقياً", type: "number", value: 0, min: 0, max: 10000, step: 1 },
        { name: "y", label: "بداية القص عمودياً", type: "number", value: 0, min: 0, max: 10000, step: 1 },
        { name: "width", label: "عرض منطقة القص", type: "number", value: 1000, min: 1, max: 10000, step: 1 },
        { name: "height", label: "ارتفاع منطقة القص", type: "number", value: 1000, min: 1, max: 10000, step: 1 }
    ],
    auto_deskew: [],
    auto_crop: []

};

const operationNames = {
    clahe: ["تحسين التباين المحلي", "CLAHE"],
    histogram_equalization: ["موازنة المدرج", "Histogram Equalization"],
    median_denoise: ["إزالة الضوضاء النقطية", "Median Denoising"],
    sharpen: ["زيادة وضوح التفاصيل", "Sharpen"],
    global_threshold: ["فصل بعتبة ثابتة", "Global Threshold"],
    otsu_threshold: ["فصل تلقائي للنص", "Otsu Threshold"],
    adaptive_threshold: ["فصل تكيفي للنص", "Adaptive Threshold"],
    morphological_opening: ["تنظيف بنيوي", "Morphological Opening"],
    morphological_closing: ["إغلاق فجوات بنيوية", "Morphological Closing"],
    bilateral_denoise: ["إزالة ضوضاء محافظة على الحواف", "Bilateral Denoising"],
    non_local_means_denoise: ["إزالة ضوضاء متقدمة", "Non-Local Means Denoising"],
    illumination_normalize: ["توحيد الإضاءة", "Illumination Normalization"],
    gamma_correct: ["تصحيح السطوع التدريجي", "Gamma Correction"],
    intensity_adjust: ["ضبط الشدة", "Intensity Adjustment"],
    faded_text_enhance: ["تحسين النص الباهت", "Faded Text Enhancement"],
    background_suppress: ["تقليل أثر الخلفية", "Background Suppression"],
    weak_structure_suppress: ["تقليل البنى الضعيفة", "Weak Structure Suppression"],
    morphological_top_hat: ["إبراز البنى الفاتحة", "Morphological Top-Hat"],
    morphological_black_hat: ["إبراز البنى الداكنة", "Morphological Black-Hat"],
    deskew: ["تصحيح الميل", "Deskew"],
    crop: ["اقتصاص الوثيقة", "Document Crop"],
    auto_deskew: ["تصحيح الميل تلقائياً", "Auto Deskew"],
    auto_crop: ["تصحيح المنظور تلقائياً", "Automatic Perspective Rectification"]
};

const statusLabels = {
    acceptable: "آمنة",
    caution: "تحتاج مراجعتك",
    high_risk: "خطورة مرتفعة",
    accepted: "مقبولة",
    accepted_with_caution: "مقبولة مع تنبيه",
    rejected_high_risk: "مرفوضة لحماية الأصل",
    rejected_sensitive_document: "مرفوضة لحساسية التفاصيل",
    rejected_no_benefit: "لا تحقق فائدة كافية",
    rejected_dimension_change: "مرفوضة بسبب تغير الأبعاد",
    verification_failed: "تعذر التحقق",
    execution_failed: "فشل التنفيذ",
    review_required: "تحتاج مراجعة",
    no_treatment: "لا تحتاج معالجة تلقائية",
    unchanged_due_to_risk: "لم تتغير بسبب المخاطرة"
};

const severityLabels = { high: "مرتفعة", medium: "متوسطة", low: "منخفضة" };
const workflowOrder = ["upload", "prepare", "diagnose", "treat", "verify", "output"];

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
    if (elements.applyManualButton) elements.applyManualButton.disabled = !hasImage || !elements.manualOperation?.value || state.isBusy;
    [elements.quickBrightness, elements.quickContrast, elements.quickResetButton, elements.quickPreviewButton].forEach((control) => { if (control) control.disabled = !hasImage || state.isBusy; });
    if (elements.downloadResultButton) {
        const blockedResult = state.lastDecisionStatus === "high_risk" || String(state.lastDecisionStatus || "").startsWith("rejected_high_risk");
        elements.downloadResultButton.disabled = !state.resultId || state.isBusy || blockedResult;
    }
    document.querySelectorAll("[data-open-technical-details]").forEach((button) => button.disabled = !state.analysis);
}

function clearError() { hide(elements.errorSection); if (elements.errorMessage) elements.errorMessage.textContent = "—"; }
function showError(message) { if (elements.errorMessage) elements.errorMessage.textContent = message || "حدث خطأ غير متوقع."; show(elements.errorSection); elements.errorSection?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }

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

function resetAll() {
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
    resetResultUI();
    if (elements.selectedFileName) elements.selectedFileName.textContent = file.name || "صورة وثيقة";
    if (elements.selectedFileMeta) elements.selectedFileMeta.textContent = formatFileSize(file.size);
    if (elements.originalPreview) elements.originalPreview.src = state.previewUrl;
    if (elements.comparisonOriginal) elements.comparisonOriginal.src = state.previewUrl;
    if (elements.manualLivePreview) elements.manualLivePreview.src = state.previewUrl;
    if (elements.manualPreviewNote) elements.manualPreviewNote.textContent = "الصورة الأصلية — اختر عملية لبدء المعاينة.";
    show(elements.selectedFile);
    show(elements.documentPreviewSection);
    setWorkflow("upload");
    updateControls();
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

function metricValue(metrics, key) { return Number(metrics?.[key]?.value); }

function humanMetric(key, value) {
    if (!Number.isFinite(value)) return "غير متاح";
    if (key === "brightness") {
        if (value < 55) return "منخفض جدًا";
        if (value < 85) return "منخفض";
        if (value > 220) return "مرتفع جدًا";
        if (value > 200) return "مرتفع";
        return "مناسب";
    }
    if (key === "contrast") return value < 20 ? "منخفض جدًا" : value < 35 ? "منخفض" : "مقبول";
    if (key === "noise") return value > 20 ? "مرتفعة" : value > 12 ? "متوسطة" : "منخفضة";
    if (key === "sharpness") return value < 25 ? "منخفضة جدًا" : value < 60 ? "منخفضة" : "مقبولة";
    if (key === "illumination") return value > 0.18 ? "غير متجانسة بوضوح" : value > 0.10 ? "غير متجانسة" : "متجانسة نسبيًا";
    if (key === "edges") return value >= 0.12 ? "كثيفة" : "طبيعية";
    return "مقروء";
}

function metricPosition(key, value) {
    if (!Number.isFinite(value)) return 0;
    const max = { brightness: 255, contrast: 100, noise: 30, sharpness: 150, illumination: 0.30, edges: 0.20 }[key] || 1;
    return clamp((value / max) * 100, 3, 97);
}

function updateMetricCard(key, value, digits = 3) {
    const rawId = { brightness: "brightnessMetric", contrast: "contrastMetric", noise: "noiseMetric", sharpness: "sharpnessMetric", illumination: "illuminationMetric", edges: "edgeDensityMetric" }[key];
    const raw = byId(rawId);
    if (raw) raw.textContent = formatNumber(value, digits);
    const human = document.querySelector(`[data-human-metric="${key}"]`);
    if (human) human.textContent = humanMetric(key, value);
    const card = document.querySelector(`[data-metric="${key}"]`);
    const scale = card?.querySelector(".health-scale span");
    if (scale) scale.style.width = `${metricPosition(key, value)}%`;
    const meter = card?.querySelector(".metric-ring");
    if (meter) meter.style.setProperty("--meter", `${metricPosition(key, value)}%`);
}

function updateQualityScales(metrics) {
    const keys = ["brightness", "contrast", "noise", "sharpness"];
    document.querySelectorAll(".quality-scale-row").forEach((row, index) => {
        const key = keys[index];
        const backendKey = key;
        const value = metricValue(metrics, backendKey);
        const marker = row.querySelector(".quality-track i");
        if (marker) marker.style.insetInlineStart = `${metricPosition(key, value)}%`;
    });
}

function cssVariable(name, fallback) {
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || fallback;
}

function chartFontFamily() {
    return getComputedStyle(document.body).fontFamily || 'IBM Plex Sans Arabic, sans-serif';
}

function destroyDashboardCharts() {
    if (tonalChartInstance) {
        tonalChartInstance.destroy();
        tonalChartInstance = null;
    }
    if (qualityChartInstance) {
        qualityChartInstance.destroy();
        qualityChartInstance = null;
    }
}

function chartMetricPercent(key, value) {
    if (!Number.isFinite(value)) return 0;
    const max = { brightness: 255, contrast: 100, noise: 30, sharpness: 150, illumination: 0.30, edges: 0.20 }[key] || 1;
    return clamp((value / max) * 100, 0, 100);
}

function renderTonalDistributionChart(metrics) {
    if (!elements.tonalDistributionChart || typeof Chart === "undefined") return;
    if (tonalChartInstance) tonalChartInstance.destroy();

    const darkRatio = clamp(metricValue(metrics, "dark_clipped_ratio") || 0, 0, 1);
    const brightRatio = clamp(metricValue(metrics, "bright_clipped_ratio") || 0, 0, 1);
    const middleRatio = clamp(1 - darkRatio - brightRatio, 0, 1);
    const values = [darkRatio * 100, middleRatio * 100, brightRatio * 100];

    const text = cssVariable("--text", "#4b342b");
    const muted = cssVariable("--text-muted", "#846f65");
    const border = cssVariable("--border", "#e7ddd6");
    const primary = cssVariable("--primary", "#0b7a62");
    const accent = cssVariable("--accent", "#bd740d");
    const context = elements.tonalDistributionChart.getContext("2d");
    const tonalGradient = context.createLinearGradient(0, 0, 0, 260);
    tonalGradient.addColorStop(0, "rgba(11, 122, 98, .42)");
    tonalGradient.addColorStop(.58, "rgba(85, 156, 127, .16)");
    tonalGradient.addColorStop(1, "rgba(189, 116, 13, .03)");

    tonalChartInstance = new Chart(elements.tonalDistributionChart, {
        type: "line",
        data: {
            labels: ["الظلال الشديدة", "النطاق الوسطي", "الإضاءات الشديدة"],
            datasets: [{
                label: "النسبة من الصورة",
                data: values,
                backgroundColor: tonalGradient,
                borderColor: primary,
                borderWidth: 3,
                pointBackgroundColor: [primary, "#75ad90", accent],
                pointBorderColor: "#fffefa",
                pointBorderWidth: 3,
                pointRadius: 6,
                pointHoverRadius: 8,
                fill: true,
                tension: .42
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 450 },
            layout: { padding: { top: 8, right: 4, left: 4, bottom: 0 } },
            plugins: {
                legend: { display: false },
                tooltip: {
                    rtl: true,
                    textDirection: "rtl",
                    titleFont: { family: chartFontFamily() },
                    bodyFont: { family: chartFontFamily() },
                    callbacks: { label: (context) => `${context.raw.toFixed(2)}%` }
                }
            },
            scales: {
                x: {
                    grid: { color: border, borderDash: [3, 4] },
                    border: { display: false },
                    ticks: { color: muted, font: { family: chartFontFamily(), size: 11, weight: "600" } }
                },
                y: {
                    beginAtZero: true,
                    max: 100,
                    border: { display: false },
                    grid: { color: border, borderDash: [3, 4] },
                    ticks: {
                        color: muted,
                        font: { family: chartFontFamily(), size: 10 },
                        stepSize: 10,
                        callback: (value) => `${value}%`
                    }
                }
            }
        }
    });
}

function renderQualityMetricsChart(metrics) {
    if (!elements.qualityMetricsChart || typeof Chart === "undefined") return;
    if (qualityChartInstance) qualityChartInstance.destroy();

    const rows = [
        ["السطوع", "brightness", metricValue(metrics, "brightness")],
        ["التباين", "contrast", metricValue(metrics, "contrast")],
        ["الضوضاء", "noise", metricValue(metrics, "noise")],
        ["الحدة", "sharpness", metricValue(metrics, "sharpness")],
        ["تفاوت الإضاءة", "illumination", metricValue(metrics, "illumination_variation")],
        ["كثافة الحواف", "edges", metricValue(metrics, "edge_density")]
    ];
    const values = rows.map(([, key, value]) => chartMetricPercent(key, value));

    const muted = cssVariable("--text-muted", "#846f65");
    const border = cssVariable("--border", "#e7ddd6");
    const primary = cssVariable("--primary", "#0b7a62");
    const context = elements.qualityMetricsChart.getContext("2d");
    const qualityGradient = context.createLinearGradient(0, 0, 260, 0);
    qualityGradient.addColorStop(0, "rgba(11, 122, 98, .35)");
    qualityGradient.addColorStop(.7, primary);
    qualityGradient.addColorStop(1, "#bd740d");

    qualityChartInstance = new Chart(elements.qualityMetricsChart, {
        type: "bar",
        data: {
            labels: rows.map(([label]) => label),
            datasets: [{
                label: "قراءة مقننة",
                data: values,
                backgroundColor: qualityGradient,
                borderRadius: 8,
                borderSkipped: false,
                barThickness: 13
            }]
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 450 },
            plugins: {
                legend: { display: false },
                tooltip: {
                    rtl: true,
                    textDirection: "rtl",
                    titleFont: { family: chartFontFamily() },
                    bodyFont: { family: chartFontFamily() },
                    callbacks: {
                        label: (context) => {
                            const source = rows[context.dataIndex]?.[2];
                            return `القراءة الأصلية: ${formatNumber(source, 4)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    max: 100,
                    border: { display: false },
                    grid: { color: border },
                    ticks: { display: false }
                },
                y: {
                    border: { display: false },
                    grid: { display: false },
                    ticks: { color: muted, font: { family: chartFontFamily(), size: 11, weight: "600" } }
                }
            }
        }
    });
}

function renderDashboardCharts(metrics) {
    renderTonalDistributionChart(metrics);
    renderQualityMetricsChart(metrics);
}

function renderDashboard(analysis, diagnoses = []) {
    const metrics = analysis?.metrics || {};
    updateMetricCard("brightness", metricValue(metrics, "brightness"));
    updateMetricCard("contrast", metricValue(metrics, "contrast"));
    updateMetricCard("noise", metricValue(metrics, "noise"));
    updateMetricCard("sharpness", metricValue(metrics, "sharpness"));
    updateMetricCard("illumination", metricValue(metrics, "illumination_variation"), 4);
    updateMetricCard("edges", metricValue(metrics, "edge_density"), 4);
    updateQualityScales(metrics);
    renderDashboardCharts(metrics);
    const problems = diagnoses.slice(0, 3).map((item) => item.label || humanizeCode(item.code));
    if (elements.dashboardInterpretation) elements.dashboardInterpretation.textContent = problems.length ? `أبرز ما كشفه الفحص: ${problems.join("، ")}. تُختار المعالجة بناءً على الأولوية ثم يُتحقق من أثرها قبل قبولها.` : "لا تظهر القياسات الحالية مشكلة واضحة تستدعي معالجة تلقائية. يمكن مراجعة التفاصيل أو استخدام الأدوات المتقدمة عند الحاجة.";
    show(elements.examinationSection);
}

function resetDashboard() {
    destroyDashboardCharts();
    ["brightness", "contrast", "noise", "sharpness", "illumination", "edges"].forEach((key) => {
        const raw = byId({ brightness: "brightnessMetric", contrast: "contrastMetric", noise: "noiseMetric", sharpness: "sharpnessMetric", illumination: "illuminationMetric", edges: "edgeDensityMetric" }[key]);
        if (raw) raw.textContent = "—";
        const human = document.querySelector(`[data-human-metric="${key}"]`);
        if (human) human.textContent = "بانتظار الفحص";
        const scale = document.querySelector(`[data-metric="${key}"] .health-scale span`);
        if (scale) scale.style.width = "0%";
        const meter = document.querySelector(`[data-metric="${key}"] .metric-ring`);
        if (meter) meter.style.setProperty("--meter", "0%");
    });
    if (elements.dashboardInterpretation) elements.dashboardInterpretation.textContent = "سيظهر هنا تفسير مختصر مبني على نتائج التشخيص الفعلية دون ادعاء تحسن غير مثبت.";
}

function renderDiagnoses(diagnoses) {
    elements.diagnosisList.innerHTML = "";
    if (!Array.isArray(diagnoses) || diagnoses.length === 0) {
        elements.diagnosisList.innerHTML = '<div class="empty-state"><span>✓</span>لم يحدد محرك التشخيص مشكلة واضحة تحتاج معالجة.</div>';
        return;
    }
    diagnoses.forEach((diagnosis) => {
        const item = document.createElement("article");
        item.className = "diagnosis-item";
        item.innerHTML = `<div class="item-heading"><strong></strong><span></span></div><p></p>`;
        item.querySelector("strong").textContent = diagnosis.label || humanizeCode(diagnosis.code);
        item.querySelector("span").textContent = severityLabel(diagnosis.severity || "detected");
        item.querySelector("p").textContent = diagnosis.message || diagnosis.description || diagnosis.reason || "";
        elements.diagnosisList.appendChild(item);
    });
}

function renderPreservationProfile(profile) {
    const safe = profile || {};
    const level = String(safe.level || "moderate").toLowerCase();
    elements.preservationLevelBadge.className = `preservation-badge ${safeStatusClass(level)}`;
    const strong = elements.preservationLevelBadge.querySelector("strong");
    if (strong) strong.textContent = level === "high" ? "عالية" : level === "moderate" ? "متوسطة" : "منخفضة";
    elements.preservationMessage.textContent = safe.message || "لا تتوفر تفاصيل كافية عن حساسية الوثيقة.";
    elements.preservationIndicators.innerHTML = "";
    const indicators = Array.isArray(safe.indicators) ? safe.indicators : [];
    indicators.forEach((indicator) => {
        const line = document.createElement("div");
        line.className = "preservation-indicator";
        line.textContent = typeof indicator === "string" ? indicator : indicator.message || humanizeCode(indicator.code);
        elements.preservationIndicators.appendChild(line);
    });
}

function renderRecommendations(recommendations, summary) {
    elements.recommendationList.innerHTML = "";
    if (!Array.isArray(recommendations) || recommendations.length === 0) {
        const message = summary?.message || "لا توجد معالجة تلقائية موصى بها حاليًا.";
        elements.recommendationList.innerHTML = `<div class="empty-state"><span>✓</span>${message}</div>`;
        return;
    }
    recommendations.forEach((rec) => {
        const item = document.createElement("article");
        item.className = "recommendation-item";
        const title = operationLabel(rec.operation_id);
        const technical = rec.operation_id ? technicalOperationLabel(rec.operation_id) : "Manual review";
        item.innerHTML = `<div class="item-heading"><div><strong></strong><small></small></div><span></span></div><p></p>`;
        item.querySelector("strong").textContent = title;
        item.querySelector("small").textContent = technical;
        item.querySelector(".item-heading > span").textContent = rec.mode === "manual_review" ? "مراجعة يدوية" : (rec.risk ? `مخاطرة ${severityLabel(rec.risk)}` : "مرشح");
        item.querySelector("p").textContent = rec.reason || "مرشح وفق نتائج التشخيص الحالية.";
        elements.recommendationList.appendChild(item);
    });
}

function renderExclusions(exclusions) {
    elements.automaticExclusionList.innerHTML = "";
    if (!Array.isArray(exclusions) || exclusions.length === 0) { hide(elements.automaticExclusions); return; }
    exclusions.forEach((item) => {
        const row = document.createElement("div");
        row.className = "exclusion-item";
        row.innerHTML = `<strong></strong><small></small><p></p>`;
        row.querySelector("strong").textContent = operationLabel(item.operation_id);
        row.querySelector("small").textContent = technicalOperationLabel(item.operation_id);
        row.querySelector("p").textContent = item.reason || "مستبعد من التنفيذ التلقائي في الحالة الحالية.";
        elements.automaticExclusionList.appendChild(row);
    });
    show(elements.automaticExclusions);
}

function updateDocumentStatus(diagnoses, recommendations) {
    const high = diagnoses.filter((item) => item.severity === "high").length;
    const medium = diagnoses.filter((item) => item.severity === "medium").length;
    let title = "لا تظهر مشكلة واضحة";
    let message = "يمكن مراجعة الوثيقة أو استخدام الأدوات المتقدمة عند الحاجة.";
    if (high) { title = "تحتاج إلى معالجة واضحة"; message = "كشف الفحص مشكلة مرتفعة الشدة. راجع التوصية قبل تنفيذ أي معالجة."; }
    else if (medium) { title = "تحتاج إلى تحسين متوسط"; message = "كشف الفحص مشكلة أو أكثر بدرجة متوسطة ويمكن معالجتها بشكل محافظ."; }
    else if (recommendations.length) { title = "يوجد اقتراح معالجة"; message = "توجد معالجة مرشحة وفق القياسات الحالية."; }
    if (elements.documentStatusTitle) elements.documentStatusTitle.textContent = title;
    if (elements.documentStatusMessage) elements.documentStatusMessage.textContent = message;
}

function renderUploadData(data) {
    state.imageId = data.image?.image_id || null;
    state.imageData = data.image || null;
    state.analysis = data.analysis || null;
    state.diagnoses = Array.isArray(data.diagnoses) ? data.diagnoses : [];
    state.preservationProfile = data.preservation_profile || null;
    state.recommendations = Array.isArray(data.recommendations) ? data.recommendations : [];
    state.exclusions = Array.isArray(data.excluded_from_automatic) ? data.excluded_from_automatic : [];
    const originalUrl = `/api/images/${encodeURIComponent(state.imageId)}`;
    elements.originalPreview.src = originalUrl;
    elements.comparisonOriginal.src = originalUrl;
    if (elements.manualLivePreview) elements.manualLivePreview.src = originalUrl;
    if (elements.manualPreviewNote) elements.manualPreviewNote.textContent = "الصورة الأصلية — اختر عملية من المحرر.";
    if (state.imageData && elements.selectedFileMeta) elements.selectedFileMeta.textContent = `${state.imageData.width}×${state.imageData.height} · ${String(state.imageData.format || "").toUpperCase()}`;
    renderDashboard(state.analysis, state.diagnoses);
    renderDiagnoses(state.diagnoses);
    renderPreservationProfile(state.preservationProfile);
    renderRecommendations(state.recommendations, data.recommendation_summary);
    renderExclusions(state.exclusions);
    updateDocumentStatus(state.diagnoses, state.recommendations);
    showSection("diagnosisSection");
    showSection("preservationProfileSection");
    showSection("treatmentPlanSection");
    show(elements.treatmentSection);
    show(elements.treatmentHistory);
    setWorkflow("treat");
    updateTechnicalDetails();
    updateControls();
    elements.documentPreviewSection?.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function startExamination() {
    if (!state.selectedFile || state.isBusy) return;
    clearError();
    resetResultUI();
    const body = new FormData();
    body.append("image", state.selectedFile);
    setBusy(true, "جارٍ فحص الوثيقة", "يتم تحليل الإضاءة والتباين والضوضاء والحدة وحساسية التفاصيل وإنشاء التوصيات.");
    setWorkflow("diagnose");
    try {
        const data = await apiRequest("/api/images", { method: "POST", body });
        renderUploadData(data);
    } catch (error) {
        setWorkflow("upload");
        showError(error.message);
    } finally { setBusy(false); }
}

function parameterBounds(field) {
    const fallback = {
        clip_limit: [0.1, 5], tile_grid_size: [2, 32], kernel_size: [3, 151], amount: [0, 2], sigma: [0.1, 5],
        threshold: [0, 255], block_size: [3, 101], c: [-30, 30], diameter: [1, 15], sigma_color: [1, 150], sigma_space: [1, 150],
        strength: [0.1, 30], template_window_size: [3, 15], search_window_size: [3, 41], gamma: [0.1, 3], alpha: [0.1, 3], beta: [-100, 100], angle: [-45, 45]
    }[field.name] || [0, Math.max(100, Number(field.value) * 2 || 100)];
    return [field.min ?? fallback[0], field.max ?? fallback[1]];
}

function renderParameterFields(operationId) {
    if (!elements.manualParameters) return;
    elements.manualParameters.innerHTML = "";
    const fields = operationParameters[operationId] || [];
    if (elements.selectedOperationFriendly) elements.selectedOperationFriendly.textContent = operationId ? operationLabel(operationId) : "اختر عملية من الأعلى";
    if (elements.selectedOperationTechnical) elements.selectedOperationTechnical.textContent = operationId ? technicalOperationLabel(operationId) : "ستظهر إعداداتها هنا.";
    if (!operationId) return;
    if (!fields.length) {
        const note = document.createElement("p");
        note.className = "parameter-note";
        note.textContent = ["auto_crop", "auto_deskew"].includes(operationId)
            ? "سيحلل النظام الوثيقة تلقائياً ثم ينشئ نتيجة قابلة للمراجعة: تصحيح أركان الوثيقة للمنظور أو تقدير زاوية الميل بحسب العملية المختارة."
            : "هذه العملية محسومة الإعدادات في الـBackend الحالي؛ اختيارها ينشئ معاينة مباشرة دون قيمة رقمية مصطنعة.";
        elements.manualParameters.appendChild(note);
        syncCropGuide();
        return;
    }
    fields.forEach((field) => {
        const [min, max] = parameterBounds(field);
        const wrapper = document.createElement("div");
        wrapper.className = "parameter-slider";
        const head = document.createElement("div");
        head.className = "parameter-slider-head";
        const label = document.createElement("label");
        const output = document.createElement("output");
        const input = document.createElement("input");
        const meta = document.createElement("div");
        const id = `parameter-${field.name}`;
        label.htmlFor = id;
        label.textContent = field.label;
        output.htmlFor = id;
        output.textContent = field.value;
        input.id = id;
        input.name = field.name;
        input.type = "range";
        input.value = field.value;
        input.min = min;
        input.max = max;
        input.step = field.step ?? 1;
        meta.className = "parameter-slider-meta";
        meta.innerHTML = `<span>${min}</span><span>${max}</span>`;
        input.addEventListener("input", () => {
            output.textContent = input.value;
            scheduleManualPreview();
        });
        head.append(label, output);
        wrapper.append(head, input, meta);
        elements.manualParameters.appendChild(wrapper);
    });
    if (operationId === "crop") initializeCropParameters();
    syncCropGuide();
}
function collectManualParameters() {
    const fields = operationParameters[elements.manualOperation.value] || [];
    const parameters = {};
    fields.forEach((field) => {
        const input = byId(`parameter-${field.name}`);
        if (!input) return;
        const value = Number(input.value);
        if (!Number.isFinite(value)) throw new Error(`القيمة المدخلة لـ ${field.label} غير صالحة.`);
        parameters[field.name] = value;
    });
    return parameters;
}

function cropDimensions() {
    const width = Number(state.imageData?.width || elements.manualLivePreview?.naturalWidth || 0);
    const height = Number(state.imageData?.height || elements.manualLivePreview?.naturalHeight || 0);
    return { width, height };
}

function cropInputValue(name, fallback = 0) {
    const value = Number(byId(`parameter-${name}`)?.value);
    return Number.isFinite(value) ? value : fallback;
}

function setCropInputValue(name, value) {
    const input = byId(`parameter-${name}`);
    if (!input) return;
    const min = Number(input.min || 0);
    const max = Number(input.max || 10000);
    input.value = String(clamp(Math.round(value), min, max));
    const output = document.querySelector(`output[for="parameter-${name}"]`);
    if (output) output.textContent = input.value;
}

function currentCropRect() {
    const dimensions = cropDimensions();
    return {
        x: cropInputValue("x"),
        y: cropInputValue("y"),
        width: cropInputValue("width", dimensions.width),
        height: cropInputValue("height", dimensions.height)
    };
}

function initializeCropParameters() {
    const dimensions = cropDimensions();
    if (!dimensions.width || !dimensions.height) return;
    setCropInputValue("x", 0);
    setCropInputValue("y", 0);
    setCropInputValue("width", dimensions.width);
    setCropInputValue("height", dimensions.height);
}

function syncCropGuide() {
    const guide = elements.manualCropGuide;
    const isCrop = elements.manualOperation?.value === "crop";
    const dimensions = cropDimensions();
    if (!guide || !isCrop || !dimensions.width || !dimensions.height) {
        guide?.classList.add("hidden");
        return;
    }
    const crop = currentCropRect();
    guide.style.left = `${clamp((crop.x / dimensions.width) * 100, 0, 100)}%`;
    guide.style.top = `${clamp((crop.y / dimensions.height) * 100, 0, 100)}%`;
    guide.style.width = `${clamp((crop.width / dimensions.width) * 100, 1, 100)}%`;
    guide.style.height = `${clamp((crop.height / dimensions.height) * 100, 1, 100)}%`;
    guide.classList.remove("hidden");
}

function beginCropDrag(event) {
    if (elements.manualOperation?.value !== "crop" || state.isBusy) return;
    const preview = elements.manualLivePreview;
    const guide = elements.manualCropGuide;
    const dimensions = cropDimensions();
    if (!preview || !guide || !dimensions.width || !dimensions.height) return;
    const rect = preview.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const handle = event.target.closest("[data-crop-handle]")?.dataset.cropHandle || "move";
    cropDragState = { pointerId: event.pointerId, handle, rect, dimensions, crop: currentCropRect(), startX: event.clientX, startY: event.clientY };
    guide.setPointerCapture?.(event.pointerId);
    event.preventDefault();
}

function moveCropDrag(event) {
    const drag = cropDragState;
    if (!drag || event.pointerId !== drag.pointerId) return;
    const dx = ((event.clientX - drag.startX) / drag.rect.width) * drag.dimensions.width;
    const dy = ((event.clientY - drag.startY) / drag.rect.height) * drag.dimensions.height;
    const minSize = Math.min(24, drag.dimensions.width, drag.dimensions.height);
    let { x, y, width, height } = drag.crop;
    const handle = drag.handle;
    if (handle === "move") { x += dx; y += dy; }
    if (handle.includes("w")) { x += dx; width -= dx; }
    if (handle.includes("e")) width += dx;
    if (handle.includes("n")) { y += dy; height -= dy; }
    if (handle.includes("s")) height += dy;
    width = Math.max(minSize, width); height = Math.max(minSize, height);
    x = clamp(x, 0, Math.max(0, drag.dimensions.width - width));
    y = clamp(y, 0, Math.max(0, drag.dimensions.height - height));
    width = Math.min(width, drag.dimensions.width - x); height = Math.min(height, drag.dimensions.height - y);
    setCropInputValue("x", x); setCropInputValue("y", y); setCropInputValue("width", width); setCropInputValue("height", height);
    syncCropGuide();
    scheduleManualPreview(120);
    event.preventDefault();
}

function endCropDrag(event) {
    if (!cropDragState || event.pointerId !== cropDragState.pointerId) return;
    elements.manualCropGuide?.releasePointerCapture?.(event.pointerId);
    cropDragState = null;
}


function setManualPreviewBusy(busy) {
    elements.manualPreviewOverlay?.classList.toggle("hidden", !busy);
    if (elements.manualPreviewStatus) {
        elements.manualPreviewStatus.innerHTML = busy
            ? '<i class="bi bi-arrow-repeat"></i> جارٍ تحديث المعاينة'
            : '<i class="bi bi-eye-fill"></i> المعاينة المباشرة جاهزة';
    }
}

function scheduleManualPreview(delay = 650) {
    if (!state.imageId || !elements.manualOperation?.value || state.isBusy) return;
    clearTimeout(manualPreviewTimer);
    if (elements.manualPreviewNote) elements.manualPreviewNote.textContent = "تغيّرت الإعدادات — ستتحدث المعاينة تلقائيًا.";
    manualPreviewTimer = setTimeout(() => applyManualOperation({ live: true }), delay);
}

function setManualPreviewResult(result, operationId, decisionStatus = null) {
    if (!result?.id || !elements.manualLivePreview) return;
    elements.manualLivePreview.src = `/api/results/${encodeURIComponent(result.id)}?preview=${Date.now()}`;
    if (elements.manualPreviewNote) {
        const decisionText = decisionStatus ? ` · ${statusLabel(decisionStatus)}` : "";
        elements.manualPreviewNote.textContent = `${operationLabel(operationId)}${decisionText}`;
    }
}

function preservationMetric(preservation, names) {
    for (const name of names) {
        const value = preservation?.metrics?.[name] ?? preservation?.[name];
        if (value !== undefined && value !== null) return value;
    }
    return null;
}

function renderPreservation(preservation) {
    if (!preservation) { hideSection("verificationSection"); return; }
    elements.edgeRetentionMetric.textContent = formatNumber(preservationMetric(preservation, ["edge_retention"]), 4);
    elements.componentRetentionMetric.textContent = formatNumber(preservationMetric(preservation, ["component_retention"]), 4);
    elements.structureSimilarityMetric.textContent = formatNumber(preservationMetric(preservation, ["structure_similarity"]), 4);
    elements.edgeInflationMetric.textContent = formatNumber(preservationMetric(preservation, ["edge_inflation"]), 4);
    elements.preservationWarnings.innerHTML = "";
    const warnings = Array.isArray(preservation.warnings) ? preservation.warnings : [];
    if (!warnings.length) elements.preservationWarnings.innerHTML = '<div class="empty-state"><span>✓</span>لم تسجل طبقة التحقق تحذيرًا بنيويًا إضافيًا.</div>';
    warnings.forEach((warning) => {
        const item = document.createElement("article");
        item.className = "warning-item";
        item.innerHTML = `<div class="item-heading"><strong></strong><span></span></div><p></p>`;
        item.querySelector("strong").textContent = typeof warning === "string" ? "تنبيه محافظة" : humanizeCode(warning.code || "تنبيه محافظة");
        item.querySelector("span").textContent = severityLabel(typeof warning === "string" ? "medium" : warning.severity || "medium");
        item.querySelector("p").textContent = typeof warning === "string" ? warning : warning.message || warning.reason || warning.description || "";
        elements.preservationWarnings.appendChild(item);
    });
    showSection("verificationSection");
}

function renderDecision(decision) {
    const safe = decision || { status: "review_required", message: "تحتاج النتيجة إلى مراجعة." };
    const status = safe.status || "review_required";
    state.lastDecisionStatus = status;
    elements.decisionCard.className = `decision-card ${safeStatusClass(status)}`;
    elements.decisionStatus.textContent = statusLabel(status);
    elements.decisionMessage.textContent = safe.message || "—";
    showSection("decisionSection");
    setWorkflow("verify");
    updateControls();
}

function showPrimaryResult(result, source = "result") {
    if (!result?.id) return;
    state.resultId = result.id;
    state.currentResult = result;
    const url = `/api/results/${encodeURIComponent(result.id)}`;
    elements.resultPreview.src = url;
    showSection("comparisonSection");
    showSection("downloadSection");
    updateViewerTabs(true);
    if (elements.editorStateText) elements.editorStateText.textContent = source === "pipeline" ? "نتيجة المعالجة الذكية جاهزة للمراجعة" : "نتيجة المعالجة اليدوية جاهزة للمراجعة";
    setWorkflow(source === "pipeline" ? "verify" : "treat");
    updateControls();
}

function updateViewerTabs(hasResult = Boolean(state.resultId)) {
    const tabs = [...document.querySelectorAll("[data-view]")];
    tabs.forEach((button) => {
        if (button.dataset.view === "original") button.disabled = false;
        else button.disabled = !hasResult;
    });
}

function renderManualOperationResult(data, options = {}) {
    state.currentOperation = data.operation || null;
    const operationId = data.operation?.id || elements.manualOperation?.value || "";
    if (options.live) {
        state.resultId = data.result?.id || null;
        state.currentResult = data.result || null;
        if (elements.resultPreview && data.result?.id) elements.resultPreview.src = `/api/results/${encodeURIComponent(data.result.id)}`;
        updateControls();
    } else {
        showPrimaryResult(data.result, "manual");
    }
    if (data.preservation) {
        renderPreservation(data.preservation);
        renderDecision(data.preservation.assessment || { status: "review_required", message: "تم إنشاء المعاينة، وتحتاج إلى مراجعتك قبل الاعتماد النهائي." });
    } else {
        hideSection("verificationSection");
        renderDecision({ status: "review_required", message: data.verification?.message || "تم إنشاء المعاينة لكن التحقق من المحافظة غير متاح." });
    }
    const decisionStatus = data.preservation?.assessment?.status || data.verification?.status || "review_required";
    setManualPreviewResult(data.result, operationId, decisionStatus);
    setStopExplanation("هذه معاينة لعملية يدوية واحدة على الصورة الأصلية وفق الـAPI الحالية. الاعتماد التراكمي سيُفعّل فقط بعد إضافة Working Image بشكل صريح.");
    renderHistory();
    updateTechnicalDetails();
    if (!options.live) document.querySelector(".manual-editor")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
}
async function applyManualOperation(options = {}) {
    if (!state.imageId || !elements.manualOperation?.value || state.isBusy) return;
    const live = Boolean(options.live);
    clearError();
    let parameters;
    try { parameters = collectManualParameters(); }
    catch (error) { if (!live) showError(error.message); return; }
    const operationId = elements.manualOperation.value;
    const automaticRoute = { auto_crop: "auto-crop", auto_deskew: "auto-deskew" }[operationId];
    const requestId = ++manualPreviewSequence;
    if (live) setManualPreviewBusy(true);
    else setBusy(true, "جارٍ إنشاء المعاينة", `يتم تطبيق ${operationLabel(operationId)} ثم التحقق من أثرها على التفاصيل.`);
    setWorkflow("treat");
    try {
        const data = automaticRoute
            ? await apiRequest(`/api/images/${encodeURIComponent(state.imageId)}/${automaticRoute}`, { method: "POST" })
            : await apiRequest(`/api/images/${encodeURIComponent(state.imageId)}/operations`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ operation_id: operationId, parameters })
            });
        if (requestId !== manualPreviewSequence) return;
        renderManualOperationResult(data, { live });
    } catch (error) {
        if (!live) showError(error.message);
        else if (elements.manualPreviewNote) elements.manualPreviewNote.textContent = `تعذر تحديث المعاينة: ${error.message}`;
    } finally {
        if (live) {
            if (requestId === manualPreviewSequence) setManualPreviewBusy(false);
        } else setBusy(false);
    }
}
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
    byId("decisionSection")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function runSmartPipeline() {
    if (!state.imageId || state.isBusy) return;
    clearError();
    resetResultUI();
    setBusy(true, "جارٍ تنفيذ المعالجة الذكية", "يتم اختيار المرشح المؤهل، تطبيقه، إعادة التقييم، ثم التحقق من المحافظة على التفاصيل قبل قبول النتيجة.");
    setWorkflow("treat");
    try {
        const data = await apiRequest(`/api/images/${encodeURIComponent(state.imageId)}/pipeline`, { method: "POST" });
        renderPipelineResult(data);
    } catch (error) { showError(error.message); }
    finally { setBusy(false); }
}

function renderHistory() {
    if (!elements.historyTimeline) return;
    elements.historyTimeline.innerHTML = '<li class="is-current"><span>الأصل</span><small>Original</small></li>';
    if (state.currentOperation?.id && state.resultId) {
        const item = document.createElement("li");
        item.className = "is-current";
        item.innerHTML = `<span></span><small>نتيجة للمراجعة</small>`;
        item.querySelector("span").textContent = operationLabel(state.currentOperation.id);
        elements.historyTimeline.appendChild(item);
    }
    if (state.lastPipeline?.steps?.length) {
        state.lastPipeline.steps.forEach((step) => {
            const item = document.createElement("li");
            const decision = step.decision?.status || step.status || step.execution_status;
            item.className = decision?.startsWith("accepted") ? "is-current" : "";
            item.innerHTML = `<span></span><small></small>`;
            item.querySelector("span").textContent = operationLabel(step.operation_id || step.operation?.id || "pipeline_step");
            item.querySelector("small").textContent = statusLabel(decision || "review_required");
            elements.historyTimeline.appendChild(item);
        });
    }
    elements.treatmentHistory.classList.toggle("hidden", !state.imageId);
}

function technicalSnapshot() {
    return {
        image: state.imageData,
        analysis: state.analysis,
        diagnoses: state.diagnoses,
        preservation_profile: state.preservationProfile,
        recommendations: state.recommendations,
        excluded_from_automatic: state.exclusions,
        current_operation: state.currentOperation,
        pipeline: state.lastPipeline
    };
}

function updateTechnicalDetails() {
    if (!elements.technicalDetailsBody) return;
    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(technicalSnapshot(), null, 2);
    elements.technicalDetailsBody.replaceChildren(pre);
}

function openTechnicalDetails() { updateTechnicalDetails(); show(elements.technicalDetails); elements.technicalDetails?.scrollIntoView({ behavior: "smooth", block: "start" }); }
function closeTechnicalDetails() { hide(elements.technicalDetails); }

function downloadCurrentResult() {
    if (!state.resultId) return;
    window.location.href = `/api/results/${encodeURIComponent(state.resultId)}/download`;
}

function switchViewer(view) {
    if (view === "original") {
        elements.originalPreview.style.display = "block";
        hideSection("comparisonSection");
    } else if (["current", "preview", "compare"].includes(view) && state.resultId) {
        showSection("comparisonSection");
        byId("comparisonSection")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
    document.querySelectorAll("[data-view]").forEach((button) => button.classList.toggle("is-active", button.dataset.view === view));
}

function toggleExclusions(button) {
    const expanded = button.getAttribute("aria-expanded") === "true";
    button.setAttribute("aria-expanded", String(!expanded));
    elements.automaticExclusionList.classList.toggle("hidden", expanded);
}

function bindFooterNavigation() {
    const links = [...document.querySelectorAll("[data-footer-nav]")];
    const footer = document.querySelector(".app-footer-fixed");
    if (!links.length || !footer) return;
    links.forEach((link) => link.addEventListener("click", (event) => {
        const target = document.querySelector(link.getAttribute("href"));
        if (!target) return;
        event.preventDefault();
        const offset = footer.getBoundingClientRect().height + 20;
        const top = Math.max(0, target.getBoundingClientRect().top + window.scrollY - offset);
        window.scrollTo({ top, behavior: "smooth" });
        links.forEach((item) => item.classList.toggle("is-active", item === link));
    }));
}

function bindWorkflowNavigation() {
    const links = [...document.querySelectorAll("[data-workflow-nav]")];
    const header = document.querySelector(".app-header");
    const workflow = document.querySelector(".workflow-bar");
    if (!links.length || !header || !workflow) return;
    links.forEach((link) => link.addEventListener("click", (event) => {
        const target = document.querySelector(link.getAttribute("href"));
        if (!target || target.classList.contains("hidden")) return;
        event.preventDefault();
        const offset = header.getBoundingClientRect().height + workflow.getBoundingClientRect().height + 18;
        const top = Math.max(0, target.getBoundingClientRect().top + window.scrollY - offset);
        window.scrollTo({ top, behavior: "smooth" });
    }));
}


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
    const prefersDark = window.matchMedia?.("(prefers-color-scheme: dark)")?.matches;
    applyTheme(prefersDark ? "dark" : "light");
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

function selectOperationCard(operationId) {
    if (!operationId || !state.imageId || state.isBusy || !elements.manualOperation) return;
    const resolvedOperationId = operationId === "perspective_crop" ? "auto_crop" : operationId === "deskew" ? "auto_deskew" : operationId;
    elements.manualOperation.value = resolvedOperationId;
    renderParameterFields(resolvedOperationId);
    document.querySelectorAll("[data-operation-card]").forEach((button) => button.classList.toggle("is-selected", button.dataset.operationCard === operationId));
    updateControls();
    if (elements.manualPreviewNote) elements.manualPreviewNote.textContent = `${operationId === "perspective_crop" ? "سيكتشف النظام أركان الوثيقة ويصحح المنظور فعلياً" : operationLabel(resolvedOperationId)} — جارٍ تجهيز المعاينة.`;
    scheduleManualPreview(220);
}

function setOperationGroup(group) {
    document.querySelectorAll("[data-operation-group]").forEach((button) => button.classList.toggle("is-active", button.dataset.operationGroup === group));
    document.querySelectorAll("[data-operation-group-panel]").forEach((panel) => panel.classList.toggle("is-active", panel.dataset.operationGroupPanel === group));
}
function bindEvents() {
    elements.themeToggleButton?.addEventListener("click", () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"));
    elements.quickBrightness?.addEventListener("input", updateQuickAdjustmentReadout);
    elements.quickContrast?.addEventListener("input", updateQuickAdjustmentReadout);
    elements.quickResetButton?.addEventListener("click", resetQuickAdjustments);
    elements.quickPreviewButton?.addEventListener("click", previewQuickAdjustments);
    document.querySelectorAll("[data-operation-card]").forEach((button) => button.addEventListener("click", () => selectOperationCard(button.dataset.operationCard)));
    document.querySelectorAll("[data-operation-group]").forEach((button) => button.addEventListener("click", () => setOperationGroup(button.dataset.operationGroup)));

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
        document.querySelectorAll("[data-operation-card]").forEach((button) => button.classList.toggle("is-selected", button.dataset.operationCard === elements.manualOperation.value));
        updateControls();
        scheduleManualPreview(220);
    });
    elements.manualCropGuide?.addEventListener("pointerdown", beginCropDrag);
    elements.manualCropGuide?.addEventListener("pointermove", moveCropDrag);
    elements.manualCropGuide?.addEventListener("pointerup", endCropDrag);
    elements.manualCropGuide?.addEventListener("pointercancel", endCropDrag);
    elements.applyManualButton?.addEventListener("click", () => applyManualOperation({ live: false }));
    elements.runPipelineButton?.addEventListener("click", runSmartPipeline);
    elements.downloadResultButton?.addEventListener("click", downloadCurrentResult);
    elements.startOverButton?.addEventListener("click", resetAll);
    document.querySelectorAll("[data-ui-mode]").forEach((button) => button.addEventListener("click", () => setMode(button.dataset.uiMode)));
    document.querySelectorAll("[data-editor-tab]").forEach((button) => button.addEventListener("click", () => setEditorTab(button.dataset.editorTab)));
    document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => switchViewer(button.dataset.view)));
    document.querySelectorAll("[data-open-technical-details]").forEach((button) => button.addEventListener("click", openTechnicalDetails));
    elements.technicalDetails?.querySelector("header button")?.addEventListener("click", closeTechnicalDetails);
    document.querySelector(".details-summary")?.addEventListener("click", (event) => toggleExclusions(event.currentTarget));
}

function initialize() {
    initializeTheme();
    bindEvents();
    setMode("standard");
    setEditorTab("quick");
    setOperationGroup("lighting");
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
