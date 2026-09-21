function setManualPreviewBusy(busy) {
    elements.manualPreviewOverlay?.classList.toggle("hidden", !busy);
    if (elements.manualPreviewStatus) {
        elements.manualPreviewStatus.innerHTML = busy
            ? '<i class="bi bi-arrow-repeat"></i> جارٍ تحديث المعاينة'
            : '<i class="bi bi-eye-fill"></i> المعاينة المباشرة جاهزة';
    }
}

function scheduleManualPreview(delay = 120) {
    if (!state.imageId || !elements.manualOperation?.value || state.isBusy) return;
    clearTimeout(manualPreviewTimer);
    if (elements.manualPreviewNote) elements.manualPreviewNote.textContent = "تغيّرت الإعدادات — يتم تحديث المعاينة تلقائيًا.";
    manualPreviewTimer = setTimeout(() => applyManualOperation({ live: true }), delay);
}

function setManualPreviewResult(result, operationId, decisionStatus = null) {
    if (!result?.id || !elements.manualLivePreview) return;
    elements.manualLivePreview.src = `/api/results/${encodeURIComponent(result.id)}?preview=${Date.now()}`;
    if (elements.manualPreviewNote) {
        const decisionText = decisionStatus ? ` · ${statusLabel(decisionStatus)}` : "";
        elements.manualPreviewNote.textContent = `${operationLabel(operationId)}${decisionText}`;
    }
    updateManualApprovalUI();

}

function setManualPreviewData(preview, operationId) {
    if (!preview?.data_url || !elements.manualLivePreview) return;

    elements.manualLivePreview.src = preview.data_url;
    if (elements.manualPreviewNote) {
        elements.manualPreviewNote.textContent = `${operationLabel(operationId)} · معاينة لحظية`;
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

    if (source === "pipeline") {
        state.manualWorkingResultId = result.id;
        state.manualApprovedResult = {
            ...result,
            operation: { id: "smart_pipeline", parameters: {} }
        };
        state.manualChain = [{
            result,
            operation: { id: "smart_pipeline", parameters: {} },
            source_result_id: null
        }];
        state.manualActiveIndex = 0;
        state.manualPreviewCandidate = null;
        if (elements.manualOriginalPreview) elements.manualOriginalPreview.src = manualOriginalUrl() || `${url}?base=${Date.now()}`;
        if (elements.manualLivePreview) elements.manualLivePreview.src = `${url}?base=${Date.now()}`;
        if (elements.manualPreviewNote) elements.manualPreviewNote.textContent = "المعالجة الذكية هي الصورة الحالية — يمكنك متابعة تجهيز الوثيقة يدويًا.";
        updateManualApprovalUI();
    }

    showSection("downloadSection");
    updateViewerTabs(true);
    if (elements.editorStateText) elements.editorStateText.textContent = source === "pipeline"
        ? "نتيجة المعالجة الذكية أصبحت الصورة الحالية للتجهيز اليدوي"
        : "نتيجة المعالجة اليدوية جاهزة للمراجعة";
    setWorkflow("treat");
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
    const operationId = data.operation?.id || elements.manualOperation?.value || "";
    const decisionStatus = data.preservation?.assessment?.status || data.verification?.status || "review_required";

    /* Live preview only updates the image beside the controls. It is not a final result. */
    if (options.live) {
        state.manualPreviewCandidate = {
            result: data.result || data.preview || null,
            operation: data.operation || {
                id: operationId,
                parameters: collectManualParameters()
            },
            data
        };
        if (data.preview?.data_url) {
            setManualPreviewData(data.preview, operationId);
        } else {
            setManualPreviewResult(data.result, operationId, decisionStatus);
        }

        updateManualApprovalUI();
        updateControls();
        syncCropGuide();
        return;
    }

    state.currentOperation = data.operation || null;
    showPrimaryResult(data.result, "manual");

    if (data.preservation) {
        renderPreservation(data.preservation);
        renderDecision(data.preservation.assessment || { status: "review_required", message: "تم إنشاء النتيجة، وتحتاج إلى مراجعتك قبل الاعتماد النهائي." });
    } else {
        hideSection("verificationSection");
        renderDecision({ status: "review_required", message: data.verification?.message || "تم إنشاء النتيجة لكن التحقق من المحافظة غير متاح." });
    }

        setManualPreviewResult(data.result, operationId, decisionStatus);
    setStopExplanation(state.manualWorkingResultId
        ? "هذه النتيجة جزء من سلسلة تجهيز الوثيقة الحالية، ويمكن متابعة عمليات يدوية أخرى فوقها."
        : "هذه نتيجة لعملية يدوية واحدة ويمكن مراجعتها قبل اعتمادها.");

    renderHistory();
    updateTechnicalDetails();
    document.querySelector(".manual-editor")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function renderPreparationPreview(data) {
    const preparationId = data?.preparation_id;
    const preview = data?.preview;

    if (!preparationId || !preview?.url) {
        throw new Error("لم يُرجع Backend معاينة Preparation صالحة.");
    }

    state.manualPreviewCandidate = {
        preparationId,
        result: { id: preparationId },
        operation: {
            id: "document_prepare",
            parameters: {}
        },
        data
    };

    state.currentOperation = {
        id: "document_prepare",
        parameters: {}
    };

    if (elements.manualLivePreview) {
        elements.manualLivePreview.src = `${preview.url}?preview=${Date.now()}`;
    }

    if (elements.manualPreviewNote) {
        const method = data.method_used === "region" ? "Region" : "Guided";
        const status = data.status || "review_required";
        elements.manualPreviewNote.textContent = `Preparation · ${method} · ${statusLabel(status)}`;
    }

    updateManualApprovalUI();
    updateTechnicalDetails();
}



function manualImageHistogram(image) {
    if (!image?.complete || !image.naturalWidth || !image.naturalHeight) return null;
    const sample = document.createElement("canvas");
    sample.width = 160;
    sample.height = 90;
    const context = sample.getContext("2d", { willReadFrequently: true });
    context.drawImage(image, 0, 0, sample.width, sample.height);
    const pixels = context.getImageData(0, 0, sample.width, sample.height).data;
    const histogram = Array(16).fill(0);
    for (let i = 0; i < pixels.length; i += 4) {
        const gray = (pixels[i] * 0.299) + (pixels[i + 1] * 0.587) + (pixels[i + 2] * 0.114);
        histogram[Math.min(15, Math.floor(gray / 16))] += 1;
    }
    const peak = Math.max(...histogram, 1);
    return histogram.map((value) => value / peak);
}

function renderManualChangeChart() {
    const canvas = elements.manualChangeChart;
    if (!canvas) return;
    const before = manualImageHistogram(elements.manualOriginalPreview);
    const after = manualImageHistogram(elements.manualLivePreview);
    if (!before || !after) {
        if (elements.manualChangeChartStatus) elements.manualChangeChartStatus.textContent = "بانتظار المعاينة";
        return;
    }
    const box = canvas.getBoundingClientRect();
    const ratio = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
    const width = Math.max(220, Math.floor(box.width || 320));
    const height = Math.max(86, Math.floor(box.height || 104));
    canvas.width = width * ratio;
    canvas.height = height * ratio;
    const context = canvas.getContext("2d");
    context.scale(ratio, ratio);
    context.clearRect(0, 0, width, height);
    const styles = getComputedStyle(document.documentElement);
    const grid = styles.getPropertyValue("--border").trim() || "#dce7df";
    const beforeColor = "rgba(189, 116, 13, .30)";
    const afterColor = "rgba(11, 122, 98, .62)";
    const left = 8;
    const right = width - 8;
    const top = 8;
    const bottom = height - 14;
    context.strokeStyle = grid;
    context.lineWidth = 1;
    [0.25, 0.5, 0.75].forEach((level) => {
        const y = bottom - ((bottom - top) * level);
        context.beginPath();
        context.moveTo(left, y);
        context.lineTo(right, y);
        context.stroke();
    });
    const gap = 2;
    const barWidth = ((right - left) / 16) - gap;
    before.forEach((value, index) => {
        const x = left + index * (barWidth + gap);
        const beforeHeight = value * (bottom - top);
        const afterHeight = after[index] * (bottom - top);
        context.fillStyle = beforeColor;
        context.fillRect(x, bottom - beforeHeight, Math.max(2, barWidth), beforeHeight);
        context.fillStyle = afterColor;
        context.fillRect(x + barWidth * .23, bottom - afterHeight, Math.max(2, barWidth * .54), afterHeight);
    });
    context.strokeStyle = grid;
    context.beginPath();
    context.moveTo(left, bottom + .5);
    context.lineTo(right, bottom + .5);
    context.stroke();
    if (elements.manualChangeChartStatus) elements.manualChangeChartStatus.textContent = "تحديث لحظي قبل / بعد";
}

/* ---------- Instant local preview layer ---------- */
const LOCAL_PREVIEW_OPERATIONS = new Set([
    "rotate_right",
    "rotate_left",
    "flip_vertical",
    "flip_horizontal",
    "intensity_adjust",
    "gamma_correct"
]);

function currentManualSourceUrl() {
    const displayed = elements.manualLivePreview?.currentSrc || elements.manualLivePreview?.src;
    if (displayed) return displayed;
    const activeEntry = state.manualActiveIndex >= 0 ? state.manualChain[state.manualActiveIndex] : null;
    if (activeEntry?.previewDataUrl) return activeEntry.previewDataUrl;
    if (activeEntry?.result?.id) return `/api/results/${encodeURIComponent(activeEntry.result.id)}?source=${Date.now()}`;
    return manualOriginalUrl();
}

function loadCanvasImage(sourceUrl) {
    return new Promise((resolve, reject) => {
        if (!sourceUrl) { reject(new Error("لم يُحدد مصدر المعاينة.")); return; }
        const image = new Image();
        image.onload = () => resolve(image);
        image.onerror = () => reject(new Error("تعذر تحميل مصدر المعاينة المحلية."));
        image.src = sourceUrl;
    });
}

async function createLocalManualPreview(operationId, parameters = {}) {
    if (!LOCAL_PREVIEW_OPERATIONS.has(operationId) && operationId !== "crop") return null;
    const image = await loadCanvasImage(currentManualSourceUrl());
    const sourceWidth = image.naturalWidth || image.width;
    const sourceHeight = image.naturalHeight || image.height;
    if (!sourceWidth || !sourceHeight) return null;

    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d", { willReadFrequently: true });
    if (!context) return null;

    if (operationId === "crop") {
        const x = clamp(Math.round(Number(parameters.x) || 0), 0, sourceWidth - 1);
        const y = clamp(Math.round(Number(parameters.y) || 0), 0, sourceHeight - 1);
        const width = clamp(Math.round(Number(parameters.width) || sourceWidth), 1, sourceWidth - x);
        const height = clamp(Math.round(Number(parameters.height) || sourceHeight), 1, sourceHeight - y);
        canvas.width = width;
        canvas.height = height;
        context.drawImage(image, x, y, width, height, 0, 0, width, height);
    } else if (operationId === "rotate_right" || operationId === "rotate_left") {
        canvas.width = sourceHeight;
        canvas.height = sourceWidth;
        context.translate(canvas.width / 2, canvas.height / 2);
        context.rotate(operationId === "rotate_right" ? Math.PI / 2 : -Math.PI / 2);
        context.drawImage(image, -sourceWidth / 2, -sourceHeight / 2);
    } else if (operationId === "flip_vertical" || operationId === "flip_horizontal") {
        canvas.width = sourceWidth;
        canvas.height = sourceHeight;
        context.translate(operationId === "flip_horizontal" ? sourceWidth : 0, operationId === "flip_vertical" ? sourceHeight : 0);
        context.scale(operationId === "flip_horizontal" ? -1 : 1, operationId === "flip_vertical" ? -1 : 1);
        context.drawImage(image, 0, 0);
    } else {
        canvas.width = sourceWidth;
        canvas.height = sourceHeight;
        context.drawImage(image, 0, 0);
        const pixels = context.getImageData(0, 0, canvas.width, canvas.height);
        const data = pixels.data;
        const alpha = Number(parameters.alpha ?? 1);
        const beta = Number(parameters.beta ?? 0);
        const gamma = Number(parameters.gamma ?? 1);
        for (let index = 0; index < data.length; index += 4) {
            for (let channel = 0; channel < 3; channel += 1) {
                const normalized = Math.max(0, Math.min(255, data[index + channel]));
                const adjusted = operationId === "gamma_correct"
                    ? 255 * Math.pow(normalized / 255, gamma)
                    : (normalized * alpha) + beta;
                data[index + channel] = Math.max(0, Math.min(255, Math.round(adjusted)));
            }
        }
        context.putImageData(pixels, 0, 0);
    }

    return {
        data_url: canvas.toDataURL("image/jpeg", 0.86),
        width: canvas.width,
        height: canvas.height
    };
}

async function renderLocalManualPreview(operationId, parameters = {}, requestId = manualPreviewSequence) {
    if (!LOCAL_PREVIEW_OPERATIONS.has(operationId)) return false;
    try {
        const preview = await createLocalManualPreview(operationId, parameters);
        if (requestId !== manualPreviewSequence) return true;
        if (!preview?.data_url) return false;
        state.manualPreviewCandidate = {
            result: null,
            operation: { id: operationId, parameters },
            data: { preview, local: true }
        };
        setManualPreviewData(preview, operationId);
        if (elements.manualPreviewStatus) elements.manualPreviewStatus.innerHTML = '<i class="bi bi-lightning-charge-fill"></i> معاينة محلية فورية';
        if (elements.manualPreviewNote) elements.manualPreviewNote.textContent = `${operationLabel(operationId)} · معاينة محلية فورية، والاعتماد يحفظ النتيجة بدقة.`;
        updateManualApprovalUI();
        updateControls();
        renderManualChangeChart();
        return true;
    } catch (error) {
        console.debug("Local preview fallback:", error);
        return false;
    }
}

function setOptimisticManualApprovalPreview(candidate) {
    const dataUrl = candidate?.data?.preview?.data_url;
    if (!dataUrl) return;
    const activeEntry = state.manualActiveIndex >= 0 ? state.manualChain[state.manualActiveIndex] : null;
    const displayedBefore = elements.manualLivePreview?.currentSrc || elements.manualLivePreview?.src;
    const beforeUrl = displayedBefore
        || activeEntry?.previewDataUrl
        || (activeEntry?.result?.id ? `/api/results/${encodeURIComponent(activeEntry.result.id)}?before=${Date.now()}` : manualOriginalUrl());
    if (elements.manualOriginalPreview && beforeUrl) elements.manualOriginalPreview.src = beforeUrl;
    if (elements.manualLivePreview) elements.manualLivePreview.src = dataUrl;
    if (elements.manualPreviewNote) elements.manualPreviewNote.textContent = `${operationLabel(candidate.operation?.id || "manual_operation")} · تم تطبيق المعاينة فورياً، جارٍ حفظها.`;
    renderManualChangeChart();
}
