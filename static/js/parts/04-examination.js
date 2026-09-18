let examinationTaskRunning = false;
let examinationTicket = 0;

const PROCESSING_UPLOAD_MAX_DIMENSION = 2000;
const PROCESSING_UPLOAD_TARGET_BYTES = 1500 * 1024;

function runInstantExaminationWorker(file, ticket) {
    return new Promise((resolve, reject) => {
        if (typeof Worker === "undefined") {
            reject(new Error("Web Worker غير مدعوم في هذا المتصفح."));
            return;
        }

        const worker = new Worker("/static/js/workers/instant-examination-worker.js?v=20260918-r3");
        const timeout = window.setTimeout(() => {
            worker.terminate();
            reject(new Error("تجاوز الفحص المحلي الزمن المسموح."));
        }, 3500);

        worker.onmessage = (event) => {
            const payload = event.data || {};
            if (payload.ticket !== ticket) return;
            window.clearTimeout(timeout);
            worker.terminate();

            if (!payload.ok || !payload.data) {
                reject(new Error(payload.error || "تعذر تنفيذ الفحص المحلي."));
                return;
            }

            resolve(payload.data);
        };

        worker.onerror = () => {
            window.clearTimeout(timeout);
            worker.terminate();
            reject(new Error("تعذر تشغيل محرك الفحص المحلي."));
        };

        worker.postMessage({ file, ticket });
    });
}

function processingUploadSize(dimensions, maxDimension = PROCESSING_UPLOAD_MAX_DIMENSION) {
    const width = Number(dimensions?.width || 0);
    const height = Number(dimensions?.height || 0);

    if (!width || !height) return null;

    const scale = Math.min(1, maxDimension / Math.max(width, height));
    return {
        width: Math.max(1, Math.round(width * scale)),
        height: Math.max(1, Math.round(height * scale))
    };
}

async function jpegBlobFromBitmap(bitmap, width, height, quality) {
    if (typeof OffscreenCanvas !== "undefined") {
        const canvas = new OffscreenCanvas(width, height);
        const context = canvas.getContext("2d", { alpha: false });
        context.drawImage(bitmap, 0, 0, width, height);
        return canvas.convertToBlob({ type: "image/jpeg", quality });
    }

    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d", { alpha: false });
    context.drawImage(bitmap, 0, 0, width, height);

    return new Promise((resolve, reject) => {
        canvas.toBlob(
            (blob) => blob ? resolve(blob) : reject(new Error("تعذر تجهيز نسخة المعالجة.")),
            "image/jpeg",
            quality
        );
    });
}

async function createProcessingUpload(file, dimensions, profile = 0) {
    if (typeof createImageBitmap === "undefined") {
        return {
            blob: file,
            filename: file.name || "document.jpg",
            optimized: false,
            source_bytes: file.size,
            upload_bytes: file.size
        };
    }

    const presets = [
        { maxDimension: 2000, quality: 0.90 },
        { maxDimension: 1650, quality: 0.84 },
        { maxDimension: 1350, quality: 0.78 }
    ];
    const preset = presets[Math.min(profile, presets.length - 1)];
    const target = processingUploadSize(dimensions, preset.maxDimension);

    let bitmap = null;
    try {
        if (target) {
            bitmap = await createImageBitmap(file, {
                resizeWidth: target.width,
                resizeHeight: target.height,
                resizeQuality: "high"
            });
        } else {
            bitmap = await createImageBitmap(file);
        }

        const width = bitmap.width;
        const height = bitmap.height;
        let blob = await jpegBlobFromBitmap(bitmap, width, height, preset.quality);

        if (blob.size > PROCESSING_UPLOAD_TARGET_BYTES && profile < presets.length - 1) {
            bitmap.close?.();
            return createProcessingUpload(file, dimensions, profile + 1);
        }

        return {
            blob,
            filename: "document-processing.jpg",
            optimized: true,
            source_bytes: file.size,
            upload_bytes: blob.size,
            width,
            height
        };
    } finally {
        bitmap?.close?.();
    }
}

async function postProcessingUpload(upload) {
    const body = new FormData();
    body.append("image", upload.blob, upload.filename);

    return apiRequest("/api/images?defer_analysis=1", {
        method: "POST",
        body
    });
}

async function uploadOriginalForExamination(file, dimensions) {
    let lastError = null;

    for (let profile = 0; profile < 3; profile += 1) {
        try {
            const prepared = await createProcessingUpload(file, dimensions, profile);
            const data = await postProcessingUpload(prepared);
            return {
                ...data,
                processing_upload: {
                    optimized: prepared.optimized,
                    source_bytes: prepared.source_bytes,
                    upload_bytes: prepared.upload_bytes,
                    width: prepared.width || data?.image?.width || null,
                    height: prepared.height || data?.image?.height || null
                }
            };
        } catch (error) {
            lastError = error;
        }
    }

    throw lastError || new Error("تعذر رفع نسخة المعالجة.");
}

async function backendExaminationFallback(uploadData) {
    const imageId = uploadData?.image?.image_id || state.imageId;
    if (!imageId) throw new Error("تعذر رفع الصورة قبل الفحص الاحتياطي.");

    attachUploadedImage({
        ...(uploadData?.image || {}),
        image_id: imageId
    });

    const data = await apiRequest(
        `/api/images/${encodeURIComponent(imageId)}/analysis`,
        { method: "POST" }
    );

    data.image = {
        ...(uploadData?.image || state.imageData || {}),
        ...(data.image || {}),
        image_id: imageId
    };

    renderUploadData(data);
}

async function startExamination() {
    const file = state.selectedFile;
    if (!file || examinationTaskRunning) return;

    if (file.size > MAX_CLIENT_UPLOAD_BYTES) {
        showError("الحد الأقصى لحجم الصورة هو 5 MB.");
        return;
    }

    examinationTaskRunning = true;
    const ticket = ++examinationTicket;

    clearError();
    resetResultUI();
    resetManualChain();
    setWorkflow("diagnose");
    setBusy(
        true,
        "فحص فوري للوثيقة",
        "يتم تحليل نسخة صغيرة محليًا داخل المتصفح."
    );

    try {
        let instantData = null;

        try {
            instantData = await runInstantExaminationWorker(file, ticket);
        } catch (localError) {
            const prepared = await createProcessingUpload(file, null, 2);
            const uploadData = await postProcessingUpload(prepared);
            if (ticket !== examinationTicket) return;

            if (elements.processingMessage) {
                elements.processingMessage.textContent = "تعذر الفحص المحلي؛ يتم استخدام الفحص الاحتياطي على الخادم.";
            }

            await backendExaminationFallback(uploadData);
            return;
        }

        if (ticket !== examinationTicket) return;

        const dimensions = instantData.analysis?.dimensions || {};
        state.imageData = {
            ...(state.imageData || {}),
            width: dimensions.width || null,
            height: dimensions.height || null,
            format: String(file.name || "").split(".").pop()?.toLowerCase() || "",
            original_name: file.name || "document"
        };

        renderInstantExamination(instantData);

        /* The diagnostic result is ready now; uploading the processing copy
           continues separately so a slow network never blocks the examination. */
        setBusy(false);

        if (elements.dashboardInterpretation) {
            elements.dashboardInterpretation.textContent += " · جارٍ تجهيز نسخة المعالجة في الخلفية.";
        }

        let uploadData;
        try {
            uploadData = await uploadOriginalForExamination(file, dimensions);
        } catch (uploadError) {
            if (ticket === examinationTicket) {
                const code = uploadError?.code ? ` [${uploadError.code}]` : "";
                const status = uploadError?.status ? ` HTTP ${uploadError.status}` : "";
                const message = uploadError?.message || "تعذر تجهيز نسخة المعالجة للخادم.";
                showError(`اكتمل الفحص، لكن تعذر تجهيز نسخة المعالجة للخادم: ${message}${code}${status}`);
            }
            return;
        }

        if (ticket !== examinationTicket) return;

        if (!uploadData?.image?.image_id) {
            showError("اكتمل الفحص، لكن الخادم لم يُرجع معرفًا صالحًا لنسخة المعالجة.");
            return;
        }

        attachUploadedImage(uploadData.image);

        if (elements.dashboardInterpretation && uploadData.processing_upload) {
            const kb = Math.max(1, Math.round(uploadData.processing_upload.upload_bytes / 1024));
            elements.dashboardInterpretation.textContent += ` · نسخة المعالجة جاهزة (${kb} KB).`;
        }
    } catch (error) {
        if (ticket === examinationTicket) {
            setWorkflow(state.imageId ? "diagnose" : "upload");
            showError(error.message || "فشل إكمال الفحص.");
        }
    } finally {
        if (ticket === examinationTicket) {
            examinationTaskRunning = false;
            setBusy(false);
        }
    }
}
