/* ==========================================================================
   12-clinic-enhancements.js — تحسينات "الاستوديو العيادي"
   إضافات عرض فقط: منزلق المقارنة قبل/بعد، سطر حالة الملف الطبي،
   وانكماش مقدمة الرفع بعد اختيار الوثيقة. لا يغيّر أي منطق قائم.
   ========================================================================== */

function setCompareSplit(percent) {
    const wrap = document.querySelector("[data-compare-wrap]");
    if (!wrap) return;
    const value = clamp(Number(percent) || 50, 0, 100);
    wrap.style.setProperty("--split", `${value}%`);
}

function resetCompareSplit() {
    const range = document.querySelector("[data-compare-range]");
    if (range) range.value = "50";
    setCompareSplit(50);
}

function bindCompareSlider() {
    const stage = document.querySelector("[data-compare-stage]");
    const range = document.querySelector("[data-compare-range]");
    if (!stage || !range || range.dataset.clinicBound === "true") return;
    range.dataset.clinicBound = "true";
    range.addEventListener("input", () => setCompareSplit(range.value));
    resetCompareSplit();
    [elements.resultPreview, elements.comparisonOriginal].forEach((image) => {
        image?.addEventListener("load", resetCompareSplit);
    });
}

function syncClinicComparison() {
    if (!elements.resultPreview || !elements.comparisonOriginal) return;
    const download = document.getElementById("downloadSection");
    const hasResult = Boolean(state.resultId) && download && !download.classList.contains("hidden");
    if (!hasResult) return;
    const resultSrc = `/api/results/${encodeURIComponent(state.resultId)}?compare=${Date.now()}`;
    const currentAfter = elements.resultPreview.getAttribute("src") || "";
    if (!currentAfter.includes(String(state.resultId))) elements.resultPreview.src = resultSrc;
    const originalSrc = manualOriginalUrl();
    if (originalSrc && elements.comparisonOriginal.getAttribute("src") !== originalSrc) {
        elements.comparisonOriginal.src = originalSrc;
    }
}

function observeClinicComparison() {
    const download = document.getElementById("downloadSection");
    const chainStatus = elements.manualChainStatus;
    if (download && download.dataset.clinicObserved !== "true") {
        download.dataset.clinicObserved = "true";
        new MutationObserver(syncClinicComparison).observe(download, { attributes: true, attributeFilter: ["class"] });
    }
    if (chainStatus && chainStatus.dataset.clinicObserved !== "true") {
        chainStatus.dataset.clinicObserved = "true";
        new MutationObserver(syncClinicComparison).observe(chainStatus, { childList: true, characterData: true, subtree: true });
    }
}

const CLINIC_WORKFLOW_STATUS = {
    upload: "بانتظار الوثيقة — ارفع صورة للبدء",
    prepare: "الوثيقة على المنصة — راجعها وجهّزها",
    diagnose: "جارٍ فحص الوثيقة وتشخيص حالتها",
    treat: "مرحلة المعالجة — طبّق وراقب الأثر",
    verify: "جارٍ التحقق من المحافظة على التفاصيل",
    output: "النتيجة جاهزة للتنزيل"
};

const CLINIC_WORKFLOW_LABELS = { upload: "رفع", prepare: "تهيئة", diagnose: "تشخيص", treat: "معالجة", verify: "تحقق", output: "إخراج" };

function updateClinicWorkflowStatus() {
    const statusText = document.getElementById("workflowStatus");
    if (!statusText) return;
    const items = [...document.querySelectorAll("[data-workflow-step]")];
    let currentIndex = 0;
    items.forEach((item, index) => { if (item.classList.contains("is-current")) currentIndex = index; });
    const stepKey = items[currentIndex]?.dataset.workflowStep || "upload";
    const next = (text) => { statusText.textContent = text; };
    if (state.isBusy) {
        next(elements.processingTitle?.textContent?.trim() || CLINIC_WORKFLOW_STATUS[stepKey]);
        return;
    }
    const hasResult = Boolean(state.resultId);
    if (stepKey === "output" || (stepKey === "verify" && hasResult)) { next(CLINIC_WORKFLOW_STATUS.output); return; }
    next(CLINIC_WORKFLOW_STATUS[stepKey] || `المرحلة الحالية: ${CLINIC_WORKFLOW_LABELS[stepKey] || "—"}`);
}

function observeClinicWorkflow() {
    const items = document.querySelectorAll("[data-workflow-step]");
    if (!items.length) return;
    const observer = new MutationObserver(() => updateClinicWorkflowStatus());
    items.forEach((item) => observer.observe(item, { attributes: true, attributeFilter: ["class"] }));
    updateClinicWorkflowStatus();
}

function syncBodyDocumentState() {
    const selected = elements.selectedFile;
    const hasDocument = Boolean(selected && !selected.classList.contains("hidden"));
    document.body.classList.toggle("has-document", hasDocument);
}

function observeSelectedFile() {
    const selected = elements.selectedFile;
    if (!selected) return;
    const observer = new MutationObserver(syncBodyDocumentState);
    observer.observe(selected, { attributes: true, attributeFilter: ["class"] });
    syncBodyDocumentState();
}

function applyClinicSeverityTone() {
    document.querySelectorAll("#diagnosisList .item-heading > span, #preservationWarnings .item-heading > span").forEach((chip) => {
        const text = chip.textContent || "";
        chip.classList.toggle("is-high", text.includes("مرتفعة"));
        chip.classList.toggle("is-medium", text.includes("متوسطة"));
        chip.classList.toggle("is-low", text.includes("منخفضة"));
    });
}

document.addEventListener("DOMContentLoaded", () => {
    bindCompareSlider();
    observeClinicComparison();
    observeClinicWorkflow();
    observeSelectedFile();
    [elements.diagnosisList, elements.preservationWarnings].forEach((list) => {
        if (!list) return;
        const observer = new MutationObserver(applyClinicSeverityTone);
        observer.observe(list, { childList: true, subtree: true });
    });
    const processing = elements.processingSection;
    if (processing) {
        const observer = new MutationObserver(updateClinicWorkflowStatus);
        observer.observe(processing, { attributes: true, attributeFilter: ["class"] });
    }
});
