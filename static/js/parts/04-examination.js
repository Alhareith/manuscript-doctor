let examinationTaskRunning = false;
let examinationTicket = 0;

function runInstantExaminationWorker(file, ticket) {
    return new Promise((resolve, reject) => {
        if (typeof Worker === "undefined") {
            reject(new Error("Web Worker غير مدعوم في هذا المتصفح."));
            return;
        }

        const worker = new Worker("/static/js/workers/instant-examination-worker.js?v=20260919-page-tools-r1");
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

async function uploadOriginalForExamination(file) {
    if (!file) throw new Error("لم يتم تحديد صورة للرفع.");
    if (file.size > MAX_CLIENT_UPLOAD_BYTES) {
        throw new Error("الحد الأقصى لحجم الصورة هو 5 MB.");
    }

    const body = new FormData();
    /*
     * Geometric preparation must always operate on the exact selected image.
     * Do not resize/re-encode the server copy: doing so changes edge evidence,
     * document boundaries and the coordinate system used by crop/perspective.
     */
    body.append("image", file, file.name || "document.jpg");

    return apiRequest("/api/images?defer_analysis=1", {
        method: "POST",
        body
    });
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
        "يتم تحليل نسخة صغيرة محليًا، بينما تُرفع الصورة الأصلية نفسها للمعالجة الهندسية."
    );

    /*
     * Start the exact original upload in parallel with the local Worker.
     * The examination UI is not blocked by the network, while all later
     * geometry operations receive the same pixels selected by the user.
     */
    const uploadPromise = uploadOriginalForExamination(file)
        .then((data) => ({ ok: true, data }))
        .catch((error) => ({ ok: false, error }));

    try {
        let instantData = null;

        try {
            instantData = await runInstantExaminationWorker(file, ticket);
        } catch (localError) {
            const uploadResult = await uploadPromise;
            if (!uploadResult.ok) throw uploadResult.error;
            if (ticket !== examinationTicket) return;

            if (elements.processingMessage) {
                elements.processingMessage.textContent = "تعذر الفحص المحلي؛ يتم استخدام الفحص الاحتياطي على الخادم.";
            }

            await backendExaminationFallback(uploadResult.data);
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

        /* The diagnostic result is complete now; original upload may still finish. */
        setBusy(false);

        if (elements.dashboardInterpretation) {
            elements.dashboardInterpretation.textContent += " · جارٍ رفع الأصل للمعالجة دون إعادة تحجيم أو ضغط.";
        }

        const uploadResult = await uploadPromise;
        if (ticket !== examinationTicket) return;

        if (!uploadResult.ok) {
            const uploadError = uploadResult.error;
            const code = uploadError?.code ? ` [${uploadError.code}]` : "";
            const status = uploadError?.status ? ` HTTP ${uploadError.status}` : "";
            const message = uploadError?.message || "تعذر رفع الصورة الأصلية للخادم.";
            showError(`اكتمل الفحص، لكن تعذر رفع الأصل للمعالجة: ${message}${code}${status}`);
            return;
        }

        if (!uploadResult.data?.image?.image_id) {
            showError("اكتمل الفحص، لكن الخادم لم يُرجع معرفًا صالحًا للصورة الأصلية.");
            return;
        }

        attachUploadedImage(uploadResult.data.image);

        if (elements.dashboardInterpretation) {
            const kb = Math.max(1, Math.round(file.size / 1024));
            elements.dashboardInterpretation.textContent += ` · الأصل جاهز للمعالجة (${kb} KB).`;
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
