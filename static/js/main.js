const state = {
    selectedFile: null,
    originalPreviewUrl: null,
    imageId: null,
    resultId: null,
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
    errorMessage: document.getElementById("errorMessage")
};


const resultSectionIds = [
    "verificationSection",
    "decisionSection",
    "comparisonSection",
    "binarizationSection",
    "downloadSection"
];


const operationParameters = {
    clahe: [
        {
            name: "clip_limit",
            label: "Clip Limit",
            type: "number",
            value: 1.5,
            min: 0.1,
            step: 0.1
        },
        {
            name: "tile_grid_size",
            label: "Tile Grid Size",
            type: "number",
            value: 8,
            min: 2,
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
            step: 2
        }
    ],

    sharpen: [
        {
            name: "amount",
            label: "Amount",
            type: "number",
            value: 0.25,
            min: 0,
            max: 2,
            step: 0.05
        },
        {
            name: "kernel_size",
            label: "Kernel Size",
            type: "number",
            value: 3,
            min: 3,
            step: 2
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
            step: 2
        },
        {
            name: "c",
            label: "C",
            type: "number",
            value: 11,
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
            step: 2
        },
        {
            name: "sigma_color",
            label: "Sigma Color",
            type: "number",
            value: 25,
            min: 1
        },
        {
            name: "sigma_space",
            label: "Sigma Space",
            type: "number",
            value: 25,
            min: 1
        }
    ],
    non_local_means_denoise: [
        {
            name: "strength",
            label: "Strength",
            type: "number",
            value: 5,
            min: 1
        },
        {
            name: "template_window_size",
            label: "Template Window",
            type: "number",
            value: 7,
            min: 3,
            step: 2
        },
        {
            name: "search_window_size",
            label: "Search Window",
            type: "number",
            value: 21,
            min: 3,
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
    ]
};


function getElement(id) {
    return document.getElementById(id);
}


function showElement(element) {
    if (element) {
        element.classList.remove("hidden");
    }
}


function hideElement(element) {
    if (element) {
        element.classList.add("hidden");
    }
}


function showSection(id) {
    showElement(getElement(id));
}


function hideSection(id) {
    hideElement(getElement(id));
}


function scrollToSection(id) {
    const element = getElement(id);

    if (!element) {
        return;
    }

    element.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}


function clearError() {
    elements.errorMessage.textContent = "—";
    hideElement(elements.errorSection);
}


function showError(message) {
    elements.errorMessage.textContent =
        message || "حدث خطأ غير متوقع.";

    showElement(elements.errorSection);

    elements.errorSection.scrollIntoView({
        behavior: "smooth",
        block: "center"
    });
}


function formatFileSize(bytes) {
    if (bytes < 1024) {
        return `${bytes} B`;
    }

    const kilobytes = bytes / 1024;

    if (kilobytes < 1024) {
        return `${kilobytes.toFixed(1)} KB`;
    }

    return `${(kilobytes / 1024).toFixed(2)} MB`;
}


function formatNumber(value, digits = 4) {
    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "—";
    }

    return number.toFixed(digits);
}


function humanizeCode(value) {
    if (!value) {
        return "—";
    }

    return String(value)
        .replaceAll("_", " ")
        .replaceAll("-", " ");
}


function safeStatusClass(status) {
    if (!status) {
        return "neutral";
    }

    return String(status)
        .toLowerCase()
        .replaceAll("_", "-")
        .replace(/[^a-z0-9-]/g, "");
}


function isSupportedFile(file) {
    if (!file) {
        return false;
    }

    const allowedTypes = [
        "image/jpeg",
        "image/png"
    ];

    const allowedName =
        /\.(jpe?g|png)$/i.test(file.name);

    return (
        allowedTypes.includes(file.type)
        || allowedName
    );
}


function revokePreviewUrl() {
    if (!state.originalPreviewUrl) {
        return;
    }

    URL.revokeObjectURL(
        state.originalPreviewUrl
    );

    state.originalPreviewUrl = null;
}


function updateControls() {
    elements.startExaminationButton.disabled =
        state.isBusy
        || !state.selectedFile;

    elements.removeImageButton.disabled =
        state.isBusy;

    elements.runPipelineButton.disabled =
        state.isBusy
        || !state.imageId;

    elements.manualOperation.disabled =
        state.isBusy
        || !state.imageId;

    elements.applyManualButton.disabled =
        state.isBusy
        || !state.imageId
        || !elements.manualOperation.value;

    elements.downloadResultButton.disabled =
        state.isBusy
        || !state.resultId;
}


function setBusy(
    busy,
    title = "جاري التنفيذ",
    message = "يرجى الانتظار..."
) {
    state.isBusy = busy;

    if (busy) {
        elements.processingTitle.textContent =
            title;

        elements.processingMessage.textContent =
            message;

        showSection(
            "processingStateSection"
        );

        scrollToSection(
            "processingStateSection"
        );
    } else {
        hideSection(
            "processingStateSection"
        );
    }

    updateControls();
}


function resetMetrics() {
    elements.brightnessMetric.textContent = "—";
    elements.contrastMetric.textContent = "—";
    elements.sharpnessMetric.textContent = "—";
    elements.noiseMetric.textContent = "—";
    elements.illuminationMetric.textContent = "—";
    elements.edgeDensityMetric.textContent = "—";
}


function resetPreservationMetrics() {
    elements.edgeRetentionMetric.textContent = "—";
    elements.componentRetentionMetric.textContent = "—";
    elements.structureSimilarityMetric.textContent = "—";
    elements.edgeInflationMetric.textContent = "—";

    elements.preservationWarnings.innerHTML = "";
}


function clearTreatmentResult() {
    state.resultId = null;

    resultSectionIds.forEach(
        hideSection
    );

    resetPreservationMetrics();

    elements.resultPreview.removeAttribute(
        "src"
    );

    elements.binarizationList.innerHTML = "";

    elements.decisionCard.className =
        "decision-card neutral";

    elements.decisionStatus.textContent =
        "—";

    elements.decisionMessage.textContent =
        "—";

    updateControls();
}


function resetAnalysisUI() {
    resetMetrics();

    elements.diagnosisList.innerHTML = `
        <div class="empty-state">
            <span>—</span>
            لم يتم إجراء الفحص بعد.
        </div>
    `;

    elements.recommendationList.innerHTML = `
        <div class="empty-state">
            <span>—</span>
            لا توجد توصيات حتى الآن.
        </div>
    `;

    elements.automaticExclusionList.innerHTML =
        "";

    hideElement(
        elements.automaticExclusions
    );

    const badgeValue =
        elements.preservationLevelBadge
            .querySelector("strong");

    if (badgeValue) {
        badgeValue.textContent = "—";
    }

    elements.preservationLevelBadge.className =
        "preservation-badge neutral";

    elements.preservationMessage.textContent =
        "—";

    elements.preservationIndicators.innerHTML =
        "";
}


function resetRuntimeState() {
    state.imageId = null;
    state.resultId = null;

    [
        "documentPreviewSection",
        "examinationSection",
        "diagnosisSection",
        "preservationProfileSection",
        "treatmentPlanSection",
        "treatmentSection",
        "processingStateSection",
        "verificationSection",
        "decisionSection",
        "comparisonSection",
        "binarizationSection",
        "downloadSection"
    ].forEach(
        hideSection
    );

    resetAnalysisUI();
    clearTreatmentResult();
    clearError();

    updateControls();
}


function clearSelectedFile() {
    if (state.isBusy) {
        return;
    }

    revokePreviewUrl();

    state.selectedFile = null;
    state.imageId = null;
    state.resultId = null;

    elements.imageInput.value = "";

    elements.selectedFileName.textContent =
        "—";

    elements.selectedFileMeta.textContent =
        "—";

    elements.originalPreview.removeAttribute(
        "src"
    );

    elements.comparisonOriginal.removeAttribute(
        "src"
    );

    elements.resultPreview.removeAttribute(
        "src"
    );

    hideElement(
        elements.selectedFile
    );

    resetRuntimeState();
}


function selectFile(file) {
    clearError();

    if (!file) {
        return;
    }

    if (!isSupportedFile(file)) {
        showError(
            "نوع الملف غير مدعوم. اختر JPG أو JPEG أو PNG."
        );

        return;
    }

    revokePreviewUrl();

    state.selectedFile = file;
    state.imageId = null;
    state.resultId = null;

    state.originalPreviewUrl =
        URL.createObjectURL(file);

    elements.selectedFileName.textContent =
        file.name;

    elements.selectedFileMeta.textContent =
        formatFileSize(file.size);

    elements.originalPreview.src =
        state.originalPreviewUrl;

    elements.comparisonOriginal.src =
        state.originalPreviewUrl;

    showElement(
        elements.selectedFile
    );

    resetAnalysisUI();
    clearTreatmentResult();

    [
        "documentPreviewSection",
        "examinationSection",
        "diagnosisSection",
        "preservationProfileSection",
        "treatmentPlanSection",
        "treatmentSection"
    ].forEach(
        hideSection
    );

    updateControls();
}


async function apiRequest(
    url,
    options = {}
) {
    let response;

    try {
        response = await fetch(
            url,
            options
        );
    } catch {
        throw new Error(
            "تعذر الاتصال بالخادم. تأكد أن التطبيق يعمل ثم أعد المحاولة."
        );
    }

    const contentType =
        response.headers.get(
            "content-type"
        ) || "";

    let payload = null;

    if (
        contentType.includes(
            "application/json"
        )
    ) {
        try {
            payload =
                await response.json();
        } catch {
            payload = null;
        }
    }

    if (!response.ok) {
        throw new Error(
            payload?.message
            || `فشل الطلب برمز HTTP ${response.status}.`
        );
    }

    if (
        !payload
        || payload.success !== true
    ) {
        throw new Error(
            payload?.message
            || "أعاد الخادم استجابة غير متوقعة."
        );
    }

    return payload.data;
}


function getMetric(
    metrics,
    names
) {
    for (const name of names) {
        if (
            metrics
            && metrics[name] !== undefined
            && metrics[name] !== null
        ) {
            return metrics[name];
        }
    }

    return null;
}


function renderMetrics(analysis) {
    const metrics = analysis?.metrics;

    if (!metrics) {
        throw new Error(
            "Backend لم يرجع analysis.metrics."
        );
    }

    elements.brightnessMetric.textContent =
        formatNumber(
            metrics.brightness?.value,
            3
        );

    elements.contrastMetric.textContent =
        formatNumber(
            metrics.contrast?.value,
            3
        );

    elements.sharpnessMetric.textContent =
        formatNumber(
            metrics.sharpness?.value,
            3
        );

    elements.noiseMetric.textContent =
        formatNumber(
            metrics.noise?.value,
            3
        );

    elements.illuminationMetric.textContent =
        formatNumber(
            metrics.illumination_variation?.value,
            4
        );

    elements.edgeDensityMetric.textContent =
        formatNumber(
            metrics.edge_density?.value,
            4
        );
}


function renderDiagnoses(diagnoses) {
    elements.diagnosisList.innerHTML = "";

    if (
        !Array.isArray(diagnoses)
        || diagnoses.length === 0
    ) {
        const empty =
            document.createElement("div");

        empty.className =
            "empty-state";

        empty.textContent =
            "لم يحدد محرك التشخيص مشكلة واضحة تحتاج معالجة.";

        elements.diagnosisList.appendChild(
            empty
        );

        return;
    }

    diagnoses.forEach(
        (diagnosis) => {
            const article =
                document.createElement(
                    "article"
                );

            article.className =
                "diagnosis-item";

            const heading =
                document.createElement(
                    "div"
                );

            heading.className =
                "item-heading";

            const title =
                document.createElement(
                    "strong"
                );

            title.textContent =
                diagnosis.label
                || diagnosis.name
                || humanizeCode(
                    diagnosis.code
                );

            const severity =
                document.createElement(
                    "span"
                );

            severity.textContent =
                diagnosis.severity
                || "detected";

            heading.append(
                title,
                severity
            );

            article.appendChild(
                heading
            );

            const description =
                diagnosis.message
                || diagnosis.description
                || diagnosis.reason;

            if (description) {
                const paragraph =
                    document.createElement(
                        "p"
                    );

                paragraph.textContent =
                    description;

                article.appendChild(
                    paragraph
                );
            }

            elements.diagnosisList.appendChild(
                article
            );
        }
    );
}


function preservationLevelLabel(level) {
    const labels = {
        low: "LOW",
        moderate: "MODERATE",
        high: "HIGH"
    };

    return (
        labels[level]
        || humanizeCode(level).toUpperCase()
    );
}


function extractProfileIndicators(profile) {
    if (!profile) {
        return [];
    }

    const candidates = [
        profile.indicators,
        profile.reasons,
        profile.signals,
        profile.warnings
    ];

    for (const candidate of candidates) {
        if (Array.isArray(candidate)) {
            return candidate;
        }
    }

    return [];
}


function renderPreservationProfile(profile) {
    const safeProfile =
        profile || {};

    const level =
        String(
            safeProfile.level
            || "moderate"
        ).toLowerCase();

    elements.preservationLevelBadge.className =
        `preservation-badge ${safeStatusClass(level)}`;

    const value =
        elements.preservationLevelBadge
            .querySelector("strong");

    if (value) {
        value.textContent =
            preservationLevelLabel(
                level
            );
    }

    elements.preservationMessage.textContent =
        safeProfile.message
        || (
            `المستوى الوارد من محرك التحليل: `
            + preservationLevelLabel(level)
        );

    elements.preservationIndicators.innerHTML =
        "";

    const indicators =
        extractProfileIndicators(
            safeProfile
        );

    indicators.forEach(
        (indicator) => {
            const item =
                document.createElement("li");

            if (
                typeof indicator
                === "string"
            ) {
                item.textContent =
                    indicator;
            } else {
                item.textContent =
                    indicator.message
                    || indicator.reason
                    || indicator.code
                    || "مؤشر Preservation";
            }

            elements.preservationIndicators
                .appendChild(item);
        }
    );
}


function createRecommendationMeta(
    recommendation
) {
    const meta =
        document.createElement("div");

    meta.className =
        "recommendation-meta";

    const values = [
        recommendation.mode,
        recommendation.risk
    ].filter(Boolean);

    values.forEach(
        (value) => {
            const badge =
                document.createElement(
                    "span"
                );

            badge.textContent =
                humanizeCode(value);

            meta.appendChild(
                badge
            );
        }
    );

    return meta;
}


function renderRecommendations(
    recommendations,
    summary
) {
    elements.recommendationList.innerHTML =
        "";

    if (
        !Array.isArray(recommendations)
        || recommendations.length === 0
    ) {
        const empty =
            document.createElement("div");

        empty.className =
            "empty-state";

        empty.textContent =
            summary?.message
            || "لا توجد معالجة تلقائية موصى بها حاليًا.";

        elements.recommendationList
            .appendChild(empty);

        return;
    }

    recommendations.forEach(
        (recommendation) => {
            const article =
                document.createElement(
                    "article"
                );

            article.className =
                "recommendation-item";

            const heading =
                document.createElement(
                    "div"
                );

            heading.className =
                "item-heading";

            const title =
                document.createElement(
                    "strong"
                );

            title.textContent =
                humanizeCode(
                    recommendation.operation_id
                );

            const priority =
                document.createElement(
                    "span"
                );

            priority.textContent =
                recommendation.priority !== undefined
                    ? `Priority ${recommendation.priority}`
                    : (
                        recommendation.mode
                        || "recommended"
                    );

            heading.append(
                title,
                priority
            );

            article.appendChild(
                heading
            );

            if (recommendation.reason) {
                const reason =
                    document.createElement(
                        "p"
                    );

                reason.textContent =
                    recommendation.reason;

                article.appendChild(
                    reason
                );
            }

            article.appendChild(
                createRecommendationMeta(
                    recommendation
                )
            );

            const parameters =
                recommendation.parameters;

            if (
                parameters
                && Object.keys(
                    parameters
                ).length > 0
            ) {
                const parameterLine =
                    document.createElement(
                        "small"
                    );

                parameterLine.className =
                    "recommendation-parameters";

                parameterLine.textContent =
                    Object.entries(parameters)
                        .map(
                            ([key, value]) =>
                                `${key}: ${value}`
                        )
                        .join(" · ");

                article.appendChild(
                    parameterLine
                );
            }

            elements.recommendationList
                .appendChild(article);
        }
    );
}


function renderAutomaticExclusions(
    exclusions
) {
    elements.automaticExclusionList
        .innerHTML = "";

    if (
        !Array.isArray(exclusions)
        || exclusions.length === 0
    ) {
        hideElement(
            elements.automaticExclusions
        );

        return;
    }

    exclusions.forEach(
        (exclusion) => {
            const article =
                document.createElement(
                    "article"
                );

            article.className =
                "exclusion-item";

            const heading =
                document.createElement(
                    "div"
                );

            heading.className =
                "item-heading";

            const title =
                document.createElement(
                    "strong"
                );

            title.textContent =
                humanizeCode(
                    exclusion.operation_id
                );

            const risk =
                document.createElement(
                    "span"
                );

            risk.textContent =
                exclusion.risk
                || "manual";

            heading.append(
                title,
                risk
            );

            article.appendChild(
                heading
            );

            if (exclusion.reason) {
                const paragraph =
                    document.createElement(
                        "p"
                    );

                paragraph.textContent =
                    exclusion.reason;

                article.appendChild(
                    paragraph
                );
            }

            elements.automaticExclusionList
                .appendChild(article);
        }
    );

    showElement(
        elements.automaticExclusions
    );
}


function renderUploadResult(data) {
    if (!data) {
        throw new Error(
            "لم تصل بيانات من Backend."
        );
    }
    const imageId =
        data?.image?.id
        ?? data?.image?.image_id
        ?? data?.image?.uuid
        ?? data?.image_id
        ?? data?.id;

    console.log(
        "IMAGE OBJECT:",
        data?.image
    );

    console.log(
        "RESOLVED IMAGE ID:",
        imageId
    );

    if (!imageId) {
        throw new Error(
            "لم يتم العثور على معرف الصورة في استجابة Backend."
        );
    }

    state.imageId = imageId;

    renderMetrics(
        data.analysis
    );

    if (
        typeof renderDiagnoses
        === "function"
    ) {
        renderDiagnoses(
            data.diagnoses || []
        );
    }

    if (
        typeof renderPreservationProfile
        === "function"
    ) {
        renderPreservationProfile(
            data.preservation_profile
        );
    }

    if (
        typeof renderRecommendations
        === "function"
    ) {
        renderRecommendations(
            data.recommendations || [],
            data.recommendation_summary
        );
    }

    if (
        typeof renderAutomaticExclusions
        === "function"
    ) {
        renderAutomaticExclusions(
            data.excluded_from_automatic || []
        );
    }

    [
        "documentPreviewSection",
        "examinationSection",
        "diagnosisSection",
        "preservationProfileSection",
        "treatmentPlanSection",
        "treatmentSection"
    ].forEach(
        (sectionId) => {
            const section =
                document.getElementById(
                    sectionId
                );

            if (section) {
                section.classList.remove(
                    "hidden"
                );
            }
        }
    );

    elements.runPipelineButton.disabled =
        false;

    updateControls();
}


async function startExamination() {
    if (!state.selectedFile) {
        showError(
            "اختر صورة أولاً."
        );

        return;
    }

    clearError();

    const formData =
        new FormData();

    formData.append(
        "image",
        state.selectedFile
    );

    setBusy(
        true,
        "جاري فحص الوثيقة",
        "يتم تحليل الصورة وإنشاء التشخيص."
    );

    try {
        const response =
            await fetch(
                "/api/images",
                {
                    method: "POST",
                    body: formData
                }
            );

        const payload =
            await response.json();

        console.log(
            "UPLOAD RESPONSE:",
            payload
        );

        if (!response.ok) {
            throw new Error(
                payload.message
                || "فشل فحص الصورة."
            );
        }

        if (
            payload.success !== true
        ) {
            throw new Error(
                payload.message
                || "Backend رفض الطلب."
            );
        }

        renderUploadResult(
            payload.data
        );

    } catch (error) {
        console.error(
            "EXAMINATION ERROR:",
            error
        );

        showError(
            error.message
        );

    } finally {
        setBusy(false);
    }
}


function renderParameterFields(
    operationId
) {
    elements.manualParameters.innerHTML =
        "";

    const definitions =
        operationParameters[
            operationId
        ];

    if (!definitions) {
        updateControls();
        return;
    }

    definitions.forEach(
        (definition) => {
            const wrapper =
                document.createElement(
                    "div"
                );

            wrapper.className =
                "parameter-field";

            const label =
                document.createElement(
                    "label"
                );

            const input =
                document.createElement(
                    "input"
                );

            const id =
                `param-${definition.name}`;

            label.htmlFor = id;
            label.textContent =
                definition.label;

            input.id = id;
            input.type =
                definition.type;

            input.value =
                definition.value;

            input.dataset.parameterName =
                definition.name;

            if (
                definition.min
                !== undefined
            ) {
                input.min =
                    definition.min;
            }

            if (
                definition.max
                !== undefined
            ) {
                input.max =
                    definition.max;
            }

            if (
                definition.step
                !== undefined
            ) {
                input.step =
                    definition.step;
            }

            wrapper.append(
                label,
                input
            );

            elements.manualParameters
                .appendChild(wrapper);
        }
    );

    updateControls();
}


function collectManualParameters() {
    const parameters = {};

    const inputs =
        elements.manualParameters
            .querySelectorAll(
                "[data-parameter-name]"
            );

    inputs.forEach(
        (input) => {
            const value =
                Number(input.value);

            if (!Number.isFinite(value)) {
                throw new Error(
                    `قيمة ${input.dataset.parameterName} غير صالحة.`
                );
            }

            parameters[
                input.dataset.parameterName
            ] = value;
        }
    );

    return parameters;
}


function preservationMetric(
    metrics,
    key
) {
    return formatNumber(
        metrics?.[key],
        4
    );
}


function renderPreservation(
    preservation
) {
    resetPreservationMetrics();

    if (!preservation) {
        hideSection(
            "verificationSection"
        );

        return;
    }

    const metrics =
        preservation.metrics || {};

    elements.edgeRetentionMetric.textContent =
        preservationMetric(
            metrics,
            "edge_retention"
        );

    elements.componentRetentionMetric.textContent =
        preservationMetric(
            metrics,
            "component_retention"
        );

    elements.structureSimilarityMetric.textContent =
        preservationMetric(
            metrics,
            "structure_similarity"
        );

    elements.edgeInflationMetric.textContent =
        preservationMetric(
            metrics,
            "edge_inflation"
        );

    elements.preservationWarnings.innerHTML =
        "";

    const warnings =
        Array.isArray(
            preservation.warnings
        )
            ? preservation.warnings
            : [];

    if (warnings.length === 0) {
        const item =
            document.createElement(
                "article"
            );

        item.className =
            "warning-item";

        const paragraph =
            document.createElement(
                "p"
            );

        paragraph.textContent =
            "لم يرجع محرك Preservation تحذيرات إضافية.";

        item.appendChild(
            paragraph
        );

        elements.preservationWarnings
            .appendChild(item);
    } else {
        warnings.forEach(
            (warning) => {
                const item =
                    document.createElement(
                        "article"
                    );

                item.className =
                    "warning-item";

                const heading =
                    document.createElement(
                        "div"
                    );

                heading.className =
                    "item-heading";

                const title =
                    document.createElement(
                        "strong"
                    );

                const severity =
                    document.createElement(
                        "span"
                    );

                if (
                    typeof warning
                    === "string"
                ) {
                    title.textContent =
                        "Preservation Warning";

                    severity.textContent =
                        "warning";
                } else {
                    title.textContent =
                        warning.code
                        ? humanizeCode(
                            warning.code
                        )
                        : "Preservation Warning";

                    severity.textContent =
                        warning.severity
                        || "warning";
                }

                heading.append(
                    title,
                    severity
                );

                item.appendChild(
                    heading
                );

                const message =
                    typeof warning
                    === "string"
                        ? warning
                        : (
                            warning.message
                            || warning.reason
                            || warning.description
                        );

                if (message) {
                    const paragraph =
                        document.createElement(
                            "p"
                        );

                    paragraph.textContent =
                        message;

                    item.appendChild(
                        paragraph
                    );
                }

                elements.preservationWarnings
                    .appendChild(item);
            }
        );
    }

    showSection(
        "verificationSection"
    );
}


function renderDecision(
    decision
) {
    const safeDecision =
        decision || {
            status: "review_required",
            message: "تحتاج النتيجة إلى مراجعة."
        };

    const status =
        safeDecision.status
        || "review_required";

    elements.decisionCard.className =
        `decision-card ${safeStatusClass(status)}`;

    elements.decisionStatus.textContent =
        humanizeCode(status).toUpperCase();

    elements.decisionMessage.textContent =
        safeDecision.message
        || "—";

    showSection(
        "decisionSection"
    );
}


function showPrimaryResult(
    result
) {
    if (!result?.id) {
        return;
    }

    state.resultId =
        result.id;

    elements.resultPreview.src =
        `/api/results/${encodeURIComponent(result.id)}`;

    showSection(
        "comparisonSection"
    );

    showSection(
        "downloadSection"
    );

    updateControls();
}


function renderManualOperationResult(
    data
) {
    showPrimaryResult(
        data.result
    );

    if (data.preservation) {
        renderPreservation(
            data.preservation
        );

        renderDecision(
            data.preservation.assessment
            || {
                status: "review_required",
                message: (
                    "تم إنشاء النتيجة، لكن لا يوجد "
                    + "Assessment نهائي في بيانات Preservation."
                )
            }
        );
    } else {
        hideSection(
            "verificationSection"
        );

        renderDecision({
            status: "review_required",
            message:
                data.verification?.message
                || (
                    "تم إنشاء النتيجة، لكن Preservation Verification غير متاح."
                )
        });
    }

    scrollToSection(
        "decisionSection"
    );
}


async function applyManualOperation() {
    if (
        !state.imageId
        || !elements.manualOperation.value
        || state.isBusy
    ) {
        return;
    }

    clearError();
    clearTreatmentResult();

    let parameters;

    try {
        parameters =
            collectManualParameters();
    } catch (error) {
        showError(
            error.message
        );

        return;
    }

    const operationId =
        elements.manualOperation.value;

    setBusy(
        true,
        "جاري تنفيذ المعالجة اليدوية",
        `يتم تطبيق ${humanizeCode(operationId)} ثم فحص أثر النتيجة.`
    );

    try {
        const data =
            await apiRequest(
                `/api/images/${encodeURIComponent(state.imageId)}/operations`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify({
                        operation_id:
                            operationId,

                        parameters:
                            parameters
                    })
                }
            );

        renderManualOperationResult(
            data
        );
    } catch (error) {
        showError(
            error.message
        );
    } finally {
        setBusy(false);
    }
}


function renderBinarizationCandidates(
    candidates
) {
    elements.binarizationList.innerHTML =
        "";

    if (
        !Array.isArray(candidates)
        || candidates.length === 0
    ) {
        hideSection(
            "binarizationSection"
        );

        return;
    }

    candidates.forEach(
        (candidate) => {
            const article =
                document.createElement(
                    "article"
                );

            article.className =
                "binarization-item";

            const heading =
                document.createElement(
                    "div"
                );

            heading.className =
                "item-heading";

            const title =
                document.createElement(
                    "strong"
                );

            title.textContent =
                humanizeCode(
                    candidate.operation_id
                );

            const status =
                document.createElement(
                    "span"
                );

            status.textContent =
                humanizeCode(
                    candidate.decision?.status
                    || "review_required"
                );

            heading.append(
                title,
                status
            );

            article.appendChild(
                heading
            );

            if (candidate.result?.id) {
                const image =
                    document.createElement(
                        "img"
                    );

                image.className =
                    "binarization-preview";

                image.alt =
                    `نتيجة ${humanizeCode(candidate.operation_id)}`;

                image.src =
                    `/api/results/${encodeURIComponent(candidate.result.id)}`;

                article.appendChild(
                    image
                );
            }

            if (candidate.reason) {
                const reason =
                    document.createElement(
                        "p"
                    );

                reason.textContent =
                    candidate.reason;

                article.appendChild(
                    reason
                );
            }

            if (
                candidate.decision?.message
            ) {
                const decisionMessage =
                    document.createElement(
                        "small"
                    );

                decisionMessage.className =
                    "binarization-decision";

                decisionMessage.textContent =
                    candidate.decision.message;

                article.appendChild(
                    decisionMessage
                );
            }

            elements.binarizationList
                .appendChild(article);
        }
    );

    showSection(
        "binarizationSection"
    );
}


function renderPipelineResult(data) {
    showPrimaryResult(
        data.result
    );

    renderDecision(
        data.decision
    );

    if (data.preservation) {
        renderPreservation(
            data.preservation
        );
    } else {
        hideSection(
            "verificationSection"
        );
    }

    renderBinarizationCandidates(
        data.binarization_candidates
    );

    scrollToSection(
        "decisionSection"
    );
}


async function runSmartPipeline() {
    if (
        !state.imageId
        || state.isBusy
    ) {
        return;
    }

    clearError();
    clearTreatmentResult();

    setBusy(
        true,
        "جاري تنفيذ Smart Pipeline",
        "يتم تنفيذ العمليات المؤهلة والتحقق من أثر كل نتيجة قبل اعتمادها."
    );

    try {
        const data =
            await apiRequest(
                `/api/images/${encodeURIComponent(state.imageId)}/pipeline`,
                {
                    method: "POST"
                }
            );

        renderPipelineResult(
            data
        );
    } catch (error) {
        showError(
            error.message
        );
    } finally {
        setBusy(false);
    }
}


function downloadCurrentResult() {
    if (!state.resultId) {
        return;
    }

    window.location.href =
        `/api/results/${encodeURIComponent(state.resultId)}/download`;
}


function startOver() {
    if (state.isBusy) {
        return;
    }

    clearSelectedFile();

    elements.manualOperation.value = "";

    renderParameterFields("");

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
}


elements.dropZone.addEventListener(
    "click",
    () => {
        if (!state.isBusy) {
            elements.imageInput.click();
        }
    }
);


elements.dropZone.addEventListener(
    "keydown",
    (event) => {
        if (
            state.isBusy
            || (
                event.key !== "Enter"
                && event.key !== " "
            )
        ) {
            return;
        }

        event.preventDefault();

        elements.imageInput.click();
    }
);


elements.dropZone.addEventListener(
    "dragover",
    (event) => {
        event.preventDefault();

        if (!state.isBusy) {
            elements.dropZone.classList.add(
                "dragging"
            );
        }
    }
);


elements.dropZone.addEventListener(
    "dragleave",
    () => {
        elements.dropZone.classList.remove(
            "dragging"
        );
    }
);


elements.dropZone.addEventListener(
    "drop",
    (event) => {
        event.preventDefault();

        elements.dropZone.classList.remove(
            "dragging"
        );

        if (state.isBusy) {
            return;
        }

        const files =
            event.dataTransfer.files;

        if (
            files
            && files.length > 0
        ) {
            selectFile(
                files[0]
            );
        }
    }
);


elements.imageInput.addEventListener(
    "change",
    () => {
        const file =
            elements.imageInput.files[0];

        if (file) {
            selectFile(file);
        }
    }
);


elements.removeImageButton.addEventListener(
    "click",
    clearSelectedFile
);


elements.startExaminationButton.addEventListener(
    "click",
    startExamination
);


elements.manualOperation.addEventListener(
    "change",
    () => {
        renderParameterFields(
            elements.manualOperation.value
        );
    }
);


elements.applyManualButton.addEventListener(
    "click",
    applyManualOperation
);


elements.runPipelineButton.addEventListener(
    "click",
    runSmartPipeline
);


elements.downloadResultButton.addEventListener(
    "click",
    downloadCurrentResult
);


elements.startOverButton.addEventListener(
    "click",
    startOver
);


window.addEventListener(
    "beforeunload",
    revokePreviewUrl
);


resetAnalysisUI();
resetPreservationMetrics();
renderParameterFields("");
updateControls();