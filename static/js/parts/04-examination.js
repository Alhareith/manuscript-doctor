async function startExamination() {
    if (!state.selectedFile || state.isBusy) return;
    clearError();
    resetResultUI();
    resetManualChain();

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

