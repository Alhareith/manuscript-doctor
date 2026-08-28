function renderHistory() {
    if (!elements.historyTimeline) return;
    const activeIndex = Number.isInteger(state.manualActiveIndex) ? state.manualActiveIndex : -1;
    elements.historyTimeline.innerHTML = "";

    const original = document.createElement("li");
    original.className = activeIndex < 0 ? "is-current" : "is-complete";
    original.innerHTML = '<span>الأصل</span><small>الصورة المرفوعة</small>';
    elements.historyTimeline.appendChild(original);

    state.manualChain.forEach((entry, index) => {
        const operationId = entry.operation?.id || "manual_operation";
        const item = document.createElement("li");
        item.className = index === activeIndex ? "is-current" : index < activeIndex ? "is-complete" : "is-future";
        item.innerHTML = '<span></span><small></small>';
        item.querySelector("span").textContent = operationLabel(operationId);
        item.querySelector("small").textContent = index === activeIndex
            ? `الخطوة ${index + 1} · نشطة`
            : index < activeIndex
                ? `الخطوة ${index + 1} · سابقة`
                : `الخطوة ${index + 1} · قابلة للإعادة`;
        elements.historyTimeline.appendChild(item);
    });

    if (!state.manualChain.length && state.lastPipeline?.steps?.length) {
        state.lastPipeline.steps.forEach((step) => {
            const item = document.createElement("li");
            const decision = step.decision?.status || step.status || step.execution_status;
            item.className = decision?.startsWith("accepted") ? "is-complete" : "";
            item.innerHTML = '<span></span><small></small>';
            item.querySelector("span").textContent = operationLabel(step.operation_id || step.operation?.id || "pipeline_step");
            item.querySelector("small").textContent = statusLabel(decision || "review_required");
            elements.historyTimeline.appendChild(item);
        });
    }
    elements.treatmentHistory.classList.toggle("hidden", !state.imageId);
}

function technicalSnapshot() {
    return {
        image: state.imageData,
        analysis: state.analysis,
        diagnoses: state.diagnoses,
        preservation_profile: state.preservationProfile,
        recommendations: state.recommendations,
        excluded_from_automatic: state.exclusions,
        current_operation: state.currentOperation,
        pipeline: state.lastPipeline
    };
}

function updateTechnicalDetails() {
    if (!elements.technicalDetailsBody) return;
    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(technicalSnapshot(), null, 2);
    elements.technicalDetailsBody.replaceChildren(pre);
}

function setAnalysisPanelsCollapsed(collapsed = true) {
    document.querySelectorAll("#diagnosisSection, #preservationProfileSection, #treatmentPlanSection").forEach((panel) => {
        panel.classList.toggle("is-collapsed", collapsed);
        const button = panel.querySelector("[data-panel-toggle]");
        if (button) {
            button.setAttribute("aria-expanded", String(!collapsed));
            const label = button.querySelector("span");
            if (label) label.textContent = collapsed ? "عرض" : "إخفاء";
        }
    });
}

function toggleAnalysisPanel(button) {
    const panel = button.closest(".analysis-compact-panel");
    if (!panel) return;
    const collapsed = panel.classList.toggle("is-collapsed");
    button.setAttribute("aria-expanded", String(!collapsed));
    const label = button.querySelector("span");
    if (label) label.textContent = collapsed ? "عرض" : "إخفاء";
}

function openTechnicalDetails() { updateTechnicalDetails(); show(elements.technicalDetails); elements.technicalDetails?.scrollIntoView({ behavior: "smooth", block: "start" }); }
function closeTechnicalDetails() { hide(elements.technicalDetails); }

function downloadCurrentResult() {
    if (!state.resultId) return;
    window.location.href = `/api/results/${encodeURIComponent(state.resultId)}/download`;
}
function downloadApprovedManualResult() {
    const resultId = state.manualApprovedResult?.id;
    if (!resultId) return;

    window.location.href = `/api/results/${encodeURIComponent(resultId)}/download`;
}


function switchViewer(view) {
    if (view === "original") {
        elements.originalPreview.style.display = "block";
        hideSection("comparisonSection");
    } else if (["current", "preview", "compare"].includes(view) && state.resultId) {
        showSection("comparisonSection");
        byId("comparisonSection")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
    document.querySelectorAll("[data-view]").forEach((button) => button.classList.toggle("is-active", button.dataset.view === view));
}

function toggleExclusions(button) {
    const expanded = button.getAttribute("aria-expanded") === "true";
    button.setAttribute("aria-expanded", String(!expanded));
    elements.automaticExclusionList.classList.toggle("hidden", expanded);
}

function bindFooterNavigation() {
    const links = [...document.querySelectorAll("[data-footer-nav]")];
    const footer = document.querySelector(".app-footer-fixed");
    if (!links.length || !footer) return;
    links.forEach((link) => link.addEventListener("click", (event) => {
        const target = document.querySelector(link.getAttribute("href"));
        if (!target) return;
        event.preventDefault();
        const offset = footer.getBoundingClientRect().height + 20;
        const top = Math.max(0, target.getBoundingClientRect().top + window.scrollY - offset);
        window.scrollTo({ top, behavior: "smooth" });
        links.forEach((item) => item.classList.toggle("is-active", item === link));
    }));
}

function bindWorkflowNavigation() {
    const links = [...document.querySelectorAll("[data-workflow-nav]")];
    const header = document.querySelector(".app-header");
    const workflow = document.querySelector(".workflow-bar");
    if (!links.length || !header || !workflow) return;
    links.forEach((link) => link.addEventListener("click", (event) => {
        const target = document.querySelector(link.getAttribute("href"));
        if (!target || target.classList.contains("hidden")) return;
        event.preventDefault();
        const offset = header.getBoundingClientRect().height + workflow.getBoundingClientRect().height + 18;
        const top = Math.max(0, target.getBoundingClientRect().top + window.scrollY - offset);
        window.scrollTo({ top, behavior: "smooth" });
    }));
}


