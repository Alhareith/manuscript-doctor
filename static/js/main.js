
const state = {
    selectedFile: null,
    originalPreviewUrl: null,
    imageId: null,
    resultId: null
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

    manualOperation: document.getElementById("manualOperation"),
    manualParameters: document.getElementById("manualParameters"),
    applyManualButton: document.getElementById("applyManualButton"),

    runPipelineButton: document.getElementById("runPipelineButton"),

    downloadResultButton: document.getElementById("downloadResultButton"),
    startOverButton: document.getElementById("startOverButton"),

    errorSection: document.getElementById("errorSection"),
    errorMessage: document.getElementById("errorMessage")
};


const sections = [
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
    ]
};


function showElement(element) {
    element.classList.remove("hidden");
}


function hideElement(element) {
    element.classList.add("hidden");
}


function showSection(sectionId) {
    const section = document.getElementById(sectionId);

    if (section) {
        showElement(section);
    }
}


function hideSection(sectionId) {
    const section = document.getElementById(sectionId);

    if (section) {
        hideElement(section);
    }
}


function hideAllResultSections() {
    sections.forEach((sectionId) => {
        hideSection(sectionId);
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

    const megabytes = kilobytes / 1024;

    return `${megabytes.toFixed(2)} MB`;
}


function isSupportedFile(file) {
    const allowedTypes = [
        "image/jpeg",
        "image/png"
    ];

    return allowedTypes.includes(file.type);
}


function clearError() {
    hideElement(elements.errorSection);
    elements.errorMessage.textContent = "—";
}


function showError(message) {
    elements.errorMessage.textContent = message;
    showElement(elements.errorSection);

    elements.errorSection.scrollIntoView({
        behavior: "smooth",
        block: "center"
    });
}


function revokePreviewUrl() {
    if (state.originalPreviewUrl) {
        URL.revokeObjectURL(
            state.originalPreviewUrl
        );

        state.originalPreviewUrl = null;
    }
}


function resetRuntimeState() {
    state.imageId = null;
    state.resultId = null;

    elements.downloadResultButton.disabled = true;

    hideAllResultSections();

    clearError();
}


function clearSelectedFile() {
    revokePreviewUrl();

    state.selectedFile = null;

    elements.imageInput.value = "";

    elements.selectedFileName.textContent = "—";
    elements.selectedFileMeta.textContent = "—";

    hideElement(elements.selectedFile);

    elements.startExaminationButton.disabled = true;

    resetRuntimeState();
}


function selectFile(file) {
    clearError();

    if (!file) {
        return;
    }

    if (!isSupportedFile(file)) {
        showError(
            "نوع الملف غير مدعوم. اختر JPG أو PNG."
        );

        return;
    }

    revokePreviewUrl();

    state.selectedFile = file;

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

    showElement(elements.selectedFile);

    elements.startExaminationButton.disabled =
        false;
}


function handleDroppedFiles(files) {
    if (!files || files.length === 0) {
        return;
    }

    selectFile(files[0]);
}


function renderParameterFields(operationId) {
    elements.manualParameters.innerHTML = "";

    const definitions =
        operationParameters[operationId];

    if (!definitions) {
        elements.applyManualButton.disabled = true;
        return;
    }

    definitions.forEach((definition) => {
        const wrapper =
            document.createElement("div");

        wrapper.className =
            "parameter-field";

        const label =
            document.createElement("label");

        const input =
            document.createElement("input");

        const inputId =
            `param-${definition.name}`;

        label.htmlFor = inputId;
        label.textContent = definition.label;

        input.id = inputId;
        input.dataset.parameterName =
            definition.name;

        input.type = definition.type;
        input.value = definition.value;

        if (definition.min !== undefined) {
            input.min = definition.min;
        }

        if (definition.max !== undefined) {
            input.max = definition.max;
        }

        if (definition.step !== undefined) {
            input.step = definition.step;
        }

        wrapper.appendChild(label);
        wrapper.appendChild(input);

        elements.manualParameters.appendChild(
            wrapper
        );
    });

    elements.applyManualButton.disabled =
        !operationId;
}


function previewFrontendState() {
    if (!state.selectedFile) {
        return;
    }

    resetRuntimeState();

    showSection("documentPreviewSection");

    showError(
        "الواجهة جاهزة. ربط الفحص الحقيقي بالـBackend سيتم في المرحلة 14."
    );
}


elements.dropZone.addEventListener(
    "click",
    () => {
        elements.imageInput.click();
    }
);


elements.dropZone.addEventListener(
    "keydown",
    (event) => {
        if (
            event.key === "Enter"
            || event.key === " "
        ) {
            event.preventDefault();

            elements.imageInput.click();
        }
    }
);


elements.dropZone.addEventListener(
    "dragover",
    (event) => {
        event.preventDefault();

        elements.dropZone.classList.add(
            "dragging"
        );
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

        handleDroppedFiles(
            event.dataTransfer.files
        );
    }
);


elements.imageInput.addEventListener(
    "change",
    () => {
        selectFile(
            elements.imageInput.files[0]
        );
    }
);


elements.removeImageButton.addEventListener(
    "click",
    clearSelectedFile
);


elements.startExaminationButton.addEventListener(
    "click",
    previewFrontendState
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
    () => {
        showError(
            "Manual Processing سيتم ربطه بالـBackend في المرحلة 14."
        );
    }
);


elements.runPipelineButton.addEventListener(
    "click",
    () => {
        showError(
            "Smart Pipeline سيتم ربطه بالـBackend في المرحلة 14."
        );
    }
);


elements.downloadResultButton.addEventListener(
    "click",
    () => {
        showError(
            "لا توجد نتيجة Backend متاحة للتحميل بعد."
        );
    }
);


elements.startOverButton.addEventListener(
    "click",
    () => {
        clearSelectedFile();

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });
    }
);


window.addEventListener(
    "beforeunload",
    revokePreviewUrl
);


renderParameterFields("");