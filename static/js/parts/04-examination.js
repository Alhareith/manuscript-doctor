async function startExamination() {
    if (!state.selectedFile || state.isBusy) return;
    clearError();
    resetResultUI();
    resetManualChain();

    setBusy(true, "جارٍ فحص الوثيقة", "يتم رفع الصورة أولًا ثم تحليل نسخة مخففة لتقليل زمن الانتظار.");
    setWorkflow("diagnose");

    try {
        let uploadData = null;

        if (!state.imageId) {
            const body = new FormData();
            body.append("image", state.selectedFile);

            uploadData = await apiRequest("/api/images?defer_analysis=1", {
                method: "POST",
                body
            });

            if (!uploadData?.image?.image_id) {
                throw new Error("لم يُرجع الخادم معرفًا صالحًا للصورة.");
            }

            state.imageId = uploadData.image.image_id;
            state.imageData = uploadData.image;

            if (elements.processingMessage) {
                elements.processingMessage.textContent = "تم رفع الصورة. جارٍ تحليل الإضاءة والتباين والضوضاء والحدة...";
            }
        }

        const analysisData = await apiRequest(
            `/api/images/${encodeURIComponent(state.imageId)}/analysis`,
            { method: "POST" }
        );

        analysisData.image = {
            ...(uploadData?.image || state.imageData || {}),
            ...(analysisData.image || {}),
            image_id: state.imageId
        };

        renderUploadData(analysisData);
    } catch (error) {
        setWorkflow(state.imageId ? "diagnose" : "upload");
        showError(error.message);
    } finally {
        setBusy(false);
    }
}
