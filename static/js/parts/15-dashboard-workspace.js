"use strict";

let analysisSuiteImageId = null;

function ensureAnalysisMasterControl() {
    const previewSection = elements.documentPreviewSection;
    if (!previewSection) return null;
    let wrap = document.getElementById("analysisMasterControl");
    if (!wrap) {
        wrap = document.createElement("section");
        wrap.id = "analysisMasterControl";
        wrap.className = "analysis-master-control hidden";
        wrap.innerHTML = `
            <button id="analysisMasterToggle" class="analysis-master-toggle" type="button" aria-expanded="false">
                <span class="analysis-master-icon"><i class="bi bi-clipboard2-pulse-fill"></i></span>
                <span class="analysis-master-copy"><strong>عرض تحليلات الوثيقة</strong><small>الصورة على المنصة · نتائج الفحص · لوحة حالة الوثيقة</small></span>
                <i class="bi bi-chevron-down analysis-master-chevron" aria-hidden="true"></i>
            </button>`;
        previewSection.insertAdjacentElement("beforebegin", wrap);
    }
    return wrap;
}

function refreshAnalysisChartsAfterReveal() {
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            if (state.analysis?.metrics && typeof renderDashboardCharts === "function") {
                renderDashboardCharts(state.analysis.metrics);
            } else {
                if (typeof tonalChartInstance !== "undefined") tonalChartInstance?.resize?.();
                if (typeof qualityChartInstance !== "undefined") qualityChartInstance?.resize?.();
            }
        });
    });
}

function setAnalysisSuiteExpanded(expanded) {
    const wrap = ensureAnalysisMasterControl();
    const button = wrap?.querySelector("#analysisMasterToggle");
    if (!wrap || !button) return;
    document.body.classList.toggle("analysis-suite-collapsed", !expanded);
    button.setAttribute("aria-expanded", String(expanded));
    const title = button.querySelector("strong");
    const subtitle = button.querySelector("small");
    const chevron = button.querySelector(".analysis-master-chevron");
    if (title) title.textContent = expanded ? "إخفاء تحليلات الوثيقة" : "عرض تحليلات الوثيقة";
    if (subtitle) subtitle.textContent = expanded ? "إخفاء الصورة ونتائج الفحص ولوحة حالة الوثيقة" : "الصورة على المنصة · نتائج الفحص · لوحة حالة الوثيقة";
    if (chevron) chevron.className = expanded ? "bi bi-chevron-up analysis-master-chevron" : "bi bi-chevron-down analysis-master-chevron";
    if (expanded) refreshAnalysisChartsAfterReveal();
}

function syncAnalysisMasterControl() {
    const wrap = ensureAnalysisMasterControl();
    const previewSection = elements.documentPreviewSection;
    if (!wrap || !previewSection) return;
    const hasAnalysis = Boolean(state.analysis && state.imageId && !previewSection.classList.contains("hidden"));
    wrap.classList.toggle("hidden", !hasAnalysis);
    if (!hasAnalysis) {
        analysisSuiteImageId = null;
        document.body.classList.remove("analysis-suite-collapsed");
        return;
    }
    if (analysisSuiteImageId !== state.imageId) {
        analysisSuiteImageId = state.imageId;
        setAnalysisSuiteExpanded(false);
    }
}

function installDashboardWorkspace() {
    const dashboard = elements.examinationSection;
    const previewSection = elements.documentPreviewSection;
    if (!dashboard || !previewSection) return;
    if (dashboard.previousElementSibling !== previewSection) previewSection.insertAdjacentElement("afterend", dashboard);
    dashboard.classList.remove("dashboard-inline", "is-collapsed");
    dashboard.classList.add("dashboard-premium");

    let advanced = dashboard.querySelector(".dashboard-advanced");
    if (!advanced) {
        advanced = document.createElement("div");
        advanced.className = "dashboard-advanced";
        const analytics = dashboard.querySelector(".dashboard-analytics-pair");
        if (analytics) advanced.appendChild(analytics);
        dashboard.querySelector(".dashboard-layout")?.appendChild(advanced);
    }
    advanced.classList.remove("is-collapsed");
    dashboard.querySelector(".dashboard-reading-card")?.remove();
    const oldToggle = dashboard.querySelector(".dashboard-head .panel-toggle");
    if (oldToggle) oldToggle.hidden = true;

    const wrap = ensureAnalysisMasterControl();
    const masterToggle = wrap?.querySelector("#analysisMasterToggle");
    if (masterToggle && masterToggle.dataset.bound !== "true") {
        masterToggle.dataset.bound = "true";
        masterToggle.addEventListener("click", () => setAnalysisSuiteExpanded(document.body.classList.contains("analysis-suite-collapsed")));
    }

    document.body.classList.add("analysis-suite-collapsed");
    syncAnalysisMasterControl();
    new MutationObserver(syncAnalysisMasterControl).observe(previewSection, { attributes: true, attributeFilter: ["class"] });
    new MutationObserver(() => {
        if (!dashboard.classList.contains("hidden") && dashboard.classList.contains("is-collapsed")) dashboard.classList.remove("is-collapsed");
    }).observe(dashboard, { attributes: true, attributeFilter: ["class"] });
}

document.addEventListener("DOMContentLoaded", installDashboardWorkspace);
