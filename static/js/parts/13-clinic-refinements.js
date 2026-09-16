/* UI-only refinements: collapse all post-exam detail by default and enlarge the real crop workspace. */

function ensureAnalysisOverviewStructure() {
    const deck = document.querySelector(".after-exam-deck");
    const summary = deck?.querySelector(".analysis-summary-card");
    if (!deck || !summary) return null;

    let details = deck.querySelector(".analysis-details-stack");
    if (!details) {
        details = document.createElement("div");
        details.className = "analysis-details-stack";
        [...deck.querySelectorAll(":scope > .analysis-compact-panel")].forEach((panel) => details.appendChild(panel));
        deck.appendChild(details);
    }

    let button = summary.querySelector("[data-analysis-overview-toggle]");
    if (!button) {
        button = document.createElement("button");
        button.type = "button";
        button.className = "analysis-overview-toggle";
        button.dataset.analysisOverviewToggle = "";
        button.setAttribute("aria-expanded", "false");
        button.innerHTML = '<span>عرض تفاصيل الفحص</span><i class="bi bi-chevron-down"></i>';
        summary.appendChild(button);
    }

    return { deck, button };
}

function syncAnalysisOverviewState(collapsed = true) {
    const structure = ensureAnalysisOverviewStructure();
    if (!structure) return;
    const { deck, button } = structure;
    deck.classList.toggle("is-collapsed", collapsed);
    button.setAttribute("aria-expanded", String(!collapsed));
    const label = button.querySelector("span");
    if (label) label.textContent = collapsed ? "عرض تفاصيل الفحص" : "إخفاء تفاصيل الفحص";
    const icon = button.querySelector("i");
    if (icon) icon.className = collapsed ? "bi bi-chevron-down" : "bi bi-chevron-up";
}

function toggleAnalysisOverview() {
    const deck = document.querySelector(".after-exam-deck");
    if (!deck) return;
    syncAnalysisOverviewState(!deck.classList.contains("is-collapsed"));
}

function syncClinicCropFocus() {
    const editor = document.getElementById("manualEditor");
    if (!editor || !elements.manualOperation) return;
    const cropActive = elements.manualOperation.value === "crop";
    editor.classList.toggle("clinic-crop-focus", cropActive);
    if (cropActive) {
        requestAnimationFrame(() => {
            syncCropGuide();
            requestAnimationFrame(syncCropGuide);
        });
    }
}

function bindClinicRefinements() {
    const structure = ensureAnalysisOverviewStructure();
    const overviewToggle = structure?.button;
    if (overviewToggle && overviewToggle.dataset.bound !== "true") {
        overviewToggle.dataset.bound = "true";
        overviewToggle.addEventListener("click", toggleAnalysisOverview);
    }

    syncAnalysisOverviewState(true);
    elements.examinationSection?.classList.add("is-collapsed");

    elements.manualOperation?.addEventListener("change", () => requestAnimationFrame(syncClinicCropFocus));
    document.addEventListener("click", (event) => {
        if (event.target.closest("[data-operation-card]")) {
            requestAnimationFrame(syncClinicCropFocus);
        }
    });

    const selectedFile = elements.selectedFile;
    if (selectedFile) {
        new MutationObserver(() => {
            if (selectedFile.classList.contains("hidden")) {
                document.getElementById("manualEditor")?.classList.remove("clinic-crop-focus");
                syncAnalysisOverviewState(true);
                elements.examinationSection?.classList.add("is-collapsed");
            }
        }).observe(selectedFile, { attributes: true, attributeFilter: ["class"] });
    }

    const diagnosisList = elements.diagnosisList;
    if (diagnosisList) {
        new MutationObserver(() => {
            if (state.analysis) {
                syncAnalysisOverviewState(true);
                elements.examinationSection?.classList.add("is-collapsed");
            }
        }).observe(diagnosisList, { childList: true, subtree: true });
    }

    window.addEventListener("resize", () => {
        if (document.getElementById("manualEditor")?.classList.contains("clinic-crop-focus")) {
            requestAnimationFrame(syncCropGuide);
        }
    });

    syncClinicCropFocus();
}

document.addEventListener("DOMContentLoaded", bindClinicRefinements);
