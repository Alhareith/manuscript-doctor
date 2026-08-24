async function applyManualOperation(options = {}) {
    const live = Boolean(options.live);
    if (!state.imageId || !elements.manualOperation?.value) return;
    if (!live && state.isBusy) return;

    clearError();
    let parameters;
    try { parameters = collectManualParameters(); }
    catch (error) { if (!live) showError(error.message); return; }

    const operationId = elements.manualOperation.value;
    const preparationRoute = operationId === "document_prepare";
    const automaticRoute = { auto_crop: "auto-crop", auto_deskew: "auto-deskew" }[operationId];
    const requestId = ++manualPreviewSequence;

    if (live && !preparationRoute && !automaticRoute) {
        if (manualPreviewAbortController) manualPreviewAbortController.abort();
        const handledLocally = await renderLocalManualPreview(operationId, parameters, requestId);
        if (handledLocally) return;
    }
    const previewRoute = live && !automaticRoute && !preparationRoute;


    if (live) {
        if (manualPreviewAbortController) manualPreviewAbortController.abort();
        manualPreviewAbortController = new AbortController();
        setManualPreviewBusy(true);
    } else {
        setBusy(true, "جارٍ إنشاء المعاينة", `يتم تطبيق ${operationLabel(operationId)} ثم التحقق من أثرها على التفاصيل.`);
    }

    setWorkflow("treat");

    try {
        const signal = live ? manualPreviewAbortController.signal : undefined;
        const data = preparationRoute
            ? await apiRequest(
                `/api/images/${encodeURIComponent(state.imageId)}/preparation/preview`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({}),
                    signal
                }
            )
            : previewRoute
                ? await apiRequest(
                    `/api/images/${encodeURIComponent(state.imageId)}/preview`,
                    {
                        method: "POST",
                        headers: { "Content-Type": "application/json", "X-Preview-Format": "jpeg" },
                        body: JSON.stringify({
                            operation_id: operationId,
                            parameters,
                            source_result_id: state.manualWorkingResultId || null
                        }),
                        signal
                    }
                )
                : automaticRoute
                    ? await apiRequest(
                        `/api/images/${encodeURIComponent(state.imageId)}/${automaticRoute}`,
                        {
                            method: "POST",
                            signal
                        }
                    )
                    : await apiRequest(
                        `/api/images/${encodeURIComponent(state.imageId)}/operations`,
                        {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                                operation_id: operationId,
                                parameters,
                                source_result_id: state.manualWorkingResultId || null
                            }),
                            signal
                        }
                    );


        if (requestId !== manualPreviewSequence) return;

        if (preparationRoute) {
            renderPreparationPreview(data);
        } else {
            renderManualOperationResult(data, { live });
        }
    } catch (error) {
        if (error?.name === "AbortError") return;
        if (!live) showError(error.message);
        else if (elements.manualPreviewNote) elements.manualPreviewNote.textContent = `تعذر تحديث المعاينة: ${error.message}`;
    } finally {
        if (live) {
            if (requestId === manualPreviewSequence) setManualPreviewBusy(false);
        } else {
            setBusy(false);
        }
    }
}

function manualOriginalUrl() {
    return state.previewUrl || (state.imageId ? `/api/images/${encodeURIComponent(state.imageId)}?original=${Date.now()}` : "");
}

function syncManualChainSelection(options = {}) {
    const instant = Boolean(options.instant);
    const index = Number.isInteger(state.manualActiveIndex) ? state.manualActiveIndex : -1;
    const entry = index >= 0 ? state.manualChain[index] : null;
    state.manualPreviewCandidate = null;

    if (entry?.result?.id) {
        state.resultId = entry.result.id;
        state.currentResult = entry.result;
        state.currentOperation = entry.operation || null;
        state.manualWorkingResultId = entry.result.id;
        state.manualApprovedResult = { ...entry.result, operation: entry.operation || {} };
        const afterUrl = instant && entry.previewDataUrl
            ? entry.previewDataUrl
            : `/api/results/${encodeURIComponent(entry.result.id)}?chain=${Date.now()}`;
        const previousEntry = index > 0 ? state.manualChain[index - 1] : null;
        const beforeUrl = previousEntry?.result?.id
            ? (instant && previousEntry.previewDataUrl
                ? previousEntry.previewDataUrl
                : `/api/results/${encodeURIComponent(previousEntry.result.id)}?before=${Date.now()}`)
            : manualOriginalUrl();
        if (elements.manualOriginalPreview && beforeUrl) elements.manualOriginalPreview.src = beforeUrl;
        if (elements.manualLivePreview) elements.manualLivePreview.src = afterUrl;
        if (elements.manualPreviewNote) elements.manualPreviewNote.textContent = `${operationLabel(entry.operation?.id || "manual_operation")} · الخطوة النشطة في السلسلة.`;
        showSection("downloadSection");
    } else {
        state.resultId = null;
        state.currentResult = null;
        state.currentOperation = null;
        state.manualWorkingResultId = null;
        state.manualApprovedResult = null;
        const url = manualOriginalUrl();
        if (elements.manualOriginalPreview && url) elements.manualOriginalPreview.src = url;
        if (elements.manualLivePreview && url) elements.manualLivePreview.src = url;
        if (elements.manualPreviewNote) elements.manualPreviewNote.textContent = "تم الرجوع إلى الأصل — اختر عملية لمتابعة المعالجة.";
        hideSection("downloadSection");
    }

    updateViewerTabs(Boolean(state.resultId));
    updateManualApprovalUI();
    updateControls();
    renderHistory();
    syncCropGuide();
    renderManualChangeChart();
}

function undoManualStep() {
    if (state.isBusy || state.manualActiveIndex < 0) return;
    state.manualActiveIndex -= 1;
    syncManualChainSelection({ instant: true });
}

function redoManualStep() {
    if (state.isBusy || state.manualActiveIndex >= state.manualChain.length - 1) return;
    state.manualActiveIndex += 1;
    syncManualChainSelection({ instant: true });
}

function prepareManualChainBranch() {
    const activeIndex = Number.isInteger(state.manualActiveIndex) ? state.manualActiveIndex : -1;
    if (activeIndex < state.manualChain.length - 1) state.manualChain = state.manualChain.slice(0, activeIndex + 1);
}

async function approveManualOperation() {
    const candidate = state.manualPreviewCandidate;
    const operationId = candidate?.operation?.id || elements.manualOperation?.value || "";

    if (!state.imageId || !operationId || !candidate || state.isBusy) return;

    clearError();
    let parameters = candidate.operation?.parameters;

    if (!parameters || typeof parameters !== "object") {
        try {
            parameters = collectManualParameters();
        } catch (error) {
            showError(error.message);
            return;
        }
    }

    if (operationId === "crop" && candidate.data?.draft) {
        try {
            const localPreview = await createLocalManualPreview("crop", parameters);
            if (localPreview?.data_url) candidate.data = { preview: localPreview, local: true };
        } catch (error) {
            console.debug("Crop optimistic preview fallback:", error);
        }
    }
    if (candidate.data?.preview?.data_url) setOptimisticManualApprovalPreview(candidate);

    setBusy(true, "جارٍ اعتماد العملية", `يتم اعتماد ${operationLabel(operationId)} وإضافتها إلى سلسلة المعالجة.`);
    setWorkflow("treat");


    if (operationId === "document_prepare" && candidate.preparationId) {
        try {
            const data = await apiRequest(
                `/api/images/${encodeURIComponent(state.imageId)}/preparation/${encodeURIComponent(candidate.preparationId)}/approve`,
                { method: "POST" }
            );

            if (!data?.result?.id) {
                throw new Error("لم يُرجع Backend نتيجة Preparation معتمدة.");
            }

            prepareManualChainBranch();
            state.resultId = data.result.id;
            state.currentResult = data.result;
            state.manualWorkingResultId = data.result.id;
            state.manualApprovedResult = {
                ...data.result,
                operation: {
                    id: "document_prepare",
                    parameters: {}
                }
            };
            state.manualChain.push({
                result: data.result,
                operation: {
                    id: "document_prepare",
                    parameters: {}
                },
                source_result_id: state.manualActiveIndex >= 0 ? state.manualChain[state.manualActiveIndex]?.result?.id || null : null,
                previewDataUrl: candidate?.data?.preview?.data_url || null
            });
            state.manualActiveIndex = state.manualChain.length - 1;
            state.manualPreviewCandidate = null;
            setBusy(false);

            const approvedUrl = `/api/results/${encodeURIComponent(data.result.id)}?approved=${Date.now()}`;
            if (elements.manualOriginalPreview) elements.manualOriginalPreview.src = approvedUrl;
            if (elements.manualLivePreview) elements.manualLivePreview.src = approvedUrl;
            if (elements.manualPreviewNote) elements.manualPreviewNote.textContent = "Preparation · النتيجة المعتمدة أصبحت الصورة الحالية";

            updateManualApprovalUI();
            updateTechnicalDetails();
            syncManualChainSelection();
        } catch (error) {
            showError(error.message);
        } finally {
            setBusy(false);
            updateManualApprovalUI();
        }

        return;
    }

    try {
        const data = await apiRequest(
            `/api/images/${encodeURIComponent(state.imageId)}/operations`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    operation_id: operationId,
                    parameters,
                    source_result_id: state.manualWorkingResultId || null
                })
            }
        );

        if (!data?.result?.id) {
            throw new Error("لم يُرجع Backend نتيجة صالحة للاعتماد.");
        }

        prepareManualChainBranch();
        state.resultId = data.result.id;
        state.currentResult = data.result;
        state.manualWorkingResultId = data.result.id;
        state.manualApprovedResult = {
            ...data.result,
            operation: data.operation || { id: operationId, parameters }
        };
        state.manualChain.push({
            result: data.result,
            operation: data.operation || { id: operationId, parameters },
            source_result_id: data.source_result_id || null,
            previewDataUrl: candidate?.data?.preview?.data_url || candidate?.data?.result?.data_url || null
        });
        state.manualActiveIndex = state.manualChain.length - 1;
        state.manualPreviewCandidate = null;
        setBusy(false);

        setManualPreviewResult(
            data.result,
            operationId,
            data.preservation?.assessment?.status || data.verification?.status
        );
        const approvedUrl = `/api/results/${encodeURIComponent(data.result.id)}?approved=${Date.now()}`;

        if (elements.manualOriginalPreview) {
            elements.manualOriginalPreview.src = approvedUrl;
        }

        if (elements.manualLivePreview) {
            elements.manualLivePreview.src = approvedUrl;
        }

        if (elements.manualPreviewNote) {
            elements.manualPreviewNote.textContent = `${operationLabel(operationId)} · تم الاعتماد، وهذه هي الصورة الحالية للسلسلة.`;
        }


        updateManualApprovalUI();
        updateTechnicalDetails();
        syncManualChainSelection();
    } catch (error) {
        showError(error.message);
    } finally {
        setBusy(false);
        updateManualApprovalUI();
    }
}

