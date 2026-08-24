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
    manualChain: [],
    manualActiveIndex: -1,
    manualWorkingResultId: null,
    manualApprovedResult: null,
    manualPreviewCandidate: null,
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
    manualOriginalPreview: document.getElementById("manualOriginalPreview"),
    manualApprovalButton: document.getElementById("manualApprovalButton"),
    manualUndoButton: document.getElementById("manualUndoButton"),
    manualRedoButton: document.getElementById("manualRedoButton"),
    manualManualDownloadButton: document.getElementById("manualManualDownloadButton"),
    manualChainStatus: document.getElementById("manualChainStatus"),
    manualChainList: document.getElementById("manualChainList"),

    manualCropGuide: document.getElementById("manualCropGuide"),
    manualPreviewOverlay: document.getElementById("manualPreviewOverlay"),
    manualPreviewStatus: document.getElementById("manualPreviewStatus"),
    manualPreviewNote: document.getElementById("manualPreviewNote"),
    manualChangeChart: document.getElementById("manualChangeChart"),
    manualChangeChartStatus: document.getElementById("manualChangeChartStatus"),
    selectedOperationFriendly: document.getElementById("selectedOperationFriendly"),
    selectedOperationTechnical: document.getElementById("selectedOperationTechnical"),
    tonalDistributionChart: document.getElementById("tonalDistributionChart"),
    qualityMetricsChart: document.getElementById("qualityMetricsChart")
};

let manualPreviewTimer = null;
let manualPreviewSequence = 0;
let manualPreviewAbortController = null;
let tonalChartInstance = null;
let qualityChartInstance = null;
let cropDragState = null;
let activeDashboardMetric = null;
let dashboardMetricValues = {};

const dashboardMetricLabels = {
    brightness: "السطوع",
    contrast: "التباين",
    noise: "الضوضاء",
    sharpness: "الحدة",
    illumination: "تجانس الإضاءة",
    edges: "كثافة الحواف"
};

const dashboardMetricSourceKeys = {
    brightness: "brightness",
    contrast: "contrast",
    noise: "noise",
    sharpness: "sharpness",
    illumination: "illumination_variation",
    edges: "edge_density"
};

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
            label: "Sharpen Amount",
            type: "number",
            value: 0.5,
            min: 0,
            max: 2,
            step: 0.1
        },
        {
            name: "sigma",
            label: "Sharpen Sigma",
            type: "number",
            value: 1.0,
            min: 0.1,
            max: 5,
            step: 0.1
        }
    ],
    super_resolution: [
        {
            name: "scale",
            label: "Scale Factor",
            type: "number",
            value: 2,
            min: 2,
            max: 3,
            step: 1
        },
        {
            name: "amount",
            label: "Edge Recovery",
            type: "number",
            value: 0.35,
            min: 0,
            max: 1,
            step: 0.05
        },
        {
            name: "sigma",
            label: "Detail Sigma",
            type: "number",
            value: 1.0,
            min: 0.5,
            max: 3,
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
    document_prepare: [],
    rotate_right: [],
    rotate_left: [],
    flip_vertical: [],
    flip_horizontal: []
};

const operationNames = {
    clahe: ["تحسين التباين المحلي", "CLAHE"],
    histogram_equalization: ["موازنة المدرج", "Histogram Equalization"],
    median_denoise: ["إزالة الضوضاء النقطية", "Median Denoising"],
    sharpen: ["زيادة وضوح التفاصيل", "Sharpen"],
    super_resolution: ["تحسين دقة النص", "Super Resolution · Lanczos + Unsharp"],
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
    document_prepare: ["تصحيح الميل والاقتصاص التلقائي", "Deskew + Optional Perspective Crop"],
    rotate_right: ["تدوير لليمين", "Rotate Right · 90° Clockwise"],
    rotate_left: ["تدوير لليسار", "Rotate Left · 90° Counter-clockwise"],
    flip_vertical: ["قلب رأسي", "Flip Vertical · Top/Bottom"],
    flip_horizontal: ["قلب أفقي", "Flip Horizontal · Left/Right"],
    smart_pipeline: ["المعالجة الذكية", "Smart Pipeline"]

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

