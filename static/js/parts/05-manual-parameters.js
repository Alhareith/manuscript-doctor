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
        note.textContent = operationId === "document_prepare"
            ? "سيحاول النظام اكتشاف الحدود أولًا ويطبق Perspective Crop عند الحاجة. إذا لم تكن الحدود موثوقة فسيطبق Deskew على الإطار الكامل دون اقتصاص ثم يعرض النتيجة للمراجعة."
            : "هذه العملية محسومة الإعدادات في الـBackend الحالي؛ اختيارها ينشئ معاينة مباشرة دون قيمة رقمية مصطنعة.";
        if (operationId === "super_resolution") {
            note.textContent = "تكبير محافظ عبر Lanczos + Unsharp Masking. قد يحسن قابلية قراءة النص، لكنه لا يستعيد تفاصيل فُقدت تماماً بسبب الضبابية أو انخفاض الدقة.";
        }

        elements.manualParameters.appendChild(note);
        syncCropGuide();
        return;
    }
    if (operationId === "super_resolution") {
        const note = document.createElement("p");
        note.className = "parameter-note";
        note.textContent = "تكبير محافظ عبر Lanczos + Unsharp Masking. قد يحسن قابلية قراءة النص، لكنه لا يستعيد تفاصيل فُقدت تماماً بسبب الضبابية أو انخفاض الدقة.";
        elements.manualParameters.appendChild(note);
    }
    fields.forEach((field) => {
        const [min, defaultMax] = parameterBounds(field);
        const dimensions = operationId === "crop" ? cropDimensions() : { width: 0, height: 0 };
        const max = operationId === "crop"
            ? (field.name === "x" || field.name === "width" ? Math.max(1, dimensions.width || defaultMax) : Math.max(1, dimensions.height || defaultMax))
            : defaultMax;
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
        input.id = id;
        input.name = field.name;
        input.type = "range";
        input.min = min;
        input.max = max;
        input.step = field.step ?? 1;
        input.value = field.value;
        output.textContent = input.value;
        meta.className = "parameter-slider-meta";
        meta.innerHTML = `<span>${min}</span><span>${max}</span>`;
        input.addEventListener("input", () => {
            output.textContent = input.value;
            if (operationId === "crop") {
                syncCropGuide();
                markCropDraft();
                return;
            }
            if (typeof LOCAL_PREVIEW_OPERATIONS !== "undefined" && LOCAL_PREVIEW_OPERATIONS.has(operationId)) {
                clearTimeout(manualPreviewTimer);
                applyManualOperation({ live: true });
                return;
            }
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
    const source = elements.manualLivePreview?.naturalWidth && elements.manualLivePreview?.naturalHeight
        ? elements.manualLivePreview
        : elements.manualOriginalPreview;
    const width = Number(source?.naturalWidth || state.imageData?.width || 0);
    const height = Number(source?.naturalHeight || state.imageData?.height || 0);
    return { width, height };
}

function cropInputValue(name, fallback = 0) {
    const value = Number(byId(`parameter-${name}`)?.value);
    return Number.isFinite(value) ? value : fallback;
}

function markCropDraft() {
    if (elements.manualOperation?.value !== "crop" || !state.imageId || state.isBusy) return;
    let parameters;
    try {
        parameters = collectManualParameters();
    } catch {
        return;
    }
    state.manualPreviewCandidate = {
        result: null,
        operation: { id: "crop", parameters },
        data: { draft: true }
    };
    if (elements.manualPreviewNote) {
        elements.manualPreviewNote.textContent = "إطار القص جاهز — اضغط «اعتماد العملية» لتطبيق القص وحفظه في السلسلة.";
    }
    updateManualApprovalUI();
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
    const marginX = Math.max(1, Math.round(dimensions.width * 0.05));
    const marginY = Math.max(1, Math.round(dimensions.height * 0.05));
    setCropInputValue("x", marginX);
    setCropInputValue("y", marginY);
    setCropInputValue("width", Math.max(1, dimensions.width - (marginX * 2)));
    setCropInputValue("height", Math.max(1, dimensions.height - (marginY * 2)));
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
    const preview = elements.manualLivePreview;
    const wrap = guide.parentElement;
    const imageRect = getCropRenderRect(preview, dimensions);
    const wrapRect = wrap?.getBoundingClientRect();
    const canUseRenderedImage = imageRect?.width > 0 && imageRect?.height > 0 && wrapRect?.width > 0 && wrapRect?.height > 0;
    const leftBase = canUseRenderedImage ? ((imageRect.left - wrapRect.left) / wrapRect.width) * 100 : 0;
    const topBase = canUseRenderedImage ? ((imageRect.top - wrapRect.top) / wrapRect.height) * 100 : 0;
    const widthBase = canUseRenderedImage ? (imageRect.width / wrapRect.width) * 100 : 100;
    const heightBase = canUseRenderedImage ? (imageRect.height / wrapRect.height) * 100 : 100;
    guide.style.left = `${leftBase + (crop.x / dimensions.width) * widthBase}%`;
    guide.style.top = `${topBase + (crop.y / dimensions.height) * heightBase}%`;
    guide.style.width = `${(crop.width / dimensions.width) * widthBase}%`;
    guide.style.height = `${(crop.height / dimensions.height) * heightBase}%`;
    guide.setAttribute("aria-valuetext", `${Math.round(crop.width)}×${Math.round(crop.height)} عند (${Math.round(crop.x)}, ${Math.round(crop.y)})`);
    guide.classList.remove("hidden");
}

function getCropRenderRect(preview, dimensions) {
    const box = preview?.getBoundingClientRect();
    if (!box?.width || !box?.height || !dimensions?.width || !dimensions?.height) return box;
    const sourceRatio = dimensions.width / dimensions.height;
    const boxRatio = box.width / box.height;
    if (sourceRatio > boxRatio) {
        const height = box.width / sourceRatio;
        return { left: box.left, top: box.top + (box.height - height) / 2, width: box.width, height };
    }
    const width = box.height * sourceRatio;
    return { left: box.left + (box.width - width) / 2, top: box.top, width, height: box.height };
}

function beginCropDrag(event) {
    if (elements.manualOperation?.value !== "crop" || state.isBusy) return;
    const preview = elements.manualLivePreview;
    const guide = elements.manualCropGuide;
    const dimensions = cropDimensions();
    if (!preview || !guide || !dimensions.width || !dimensions.height) return;
    const rect = getCropRenderRect(preview, dimensions);
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
    markCropDraft();
    event.preventDefault();
}

function endCropDrag(event) {
    if (!cropDragState || event.pointerId !== cropDragState.pointerId) return;
    elements.manualCropGuide?.releasePointerCapture?.(event.pointerId);
    cropDragState = null;
}


