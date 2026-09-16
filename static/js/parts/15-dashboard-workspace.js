"use strict";

function installDashboardWorkspace() {
    const dashboard = elements.examinationSection;
    const previewSection = elements.documentPreviewSection;
    if (!dashboard || !previewSection) return;

    // Keep the dashboard as a full-width section immediately after the image/status workspace.
    if (dashboard.previousElementSibling !== previewSection) {
        previewSection.insertAdjacentElement("afterend", dashboard);
    }

    dashboard.classList.remove("dashboard-inline", "is-collapsed");
    dashboard.classList.add("dashboard-premium");

    let advanced = dashboard.querySelector(".dashboard-advanced");
    if (!advanced) {
        advanced = document.createElement("div");
        advanced.className = "dashboard-advanced is-collapsed";
        const analytics = dashboard.querySelector(".dashboard-analytics-pair");
        if (analytics) advanced.appendChild(analytics);
        dashboard.querySelector(".dashboard-layout")?.appendChild(advanced);
    }

    // The former explanatory card duplicated information and added visual noise.
    dashboard.querySelector(".dashboard-reading-card")?.remove();

    const toggle = dashboard.querySelector(".dashboard-head .panel-toggle");
    if (toggle && toggle.dataset.dashboardBound !== "true") {
        toggle.dataset.dashboardBound = "true";
        toggle.classList.add("dashboard-advanced-toggle");
        toggle.setAttribute("aria-expanded", "false");
        const label = toggle.querySelector("span");
        const icon = toggle.querySelector("i");
        if (label) label.textContent = "عرض الرسوم المتقدمة";

        toggle.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            const collapsed = advanced.classList.toggle("is-collapsed");
            toggle.setAttribute("aria-expanded", String(!collapsed));
            if (label) label.textContent = collapsed ? "عرض الرسوم المتقدمة" : "إخفاء الرسوم المتقدمة";
            if (icon) icon.className = collapsed ? "bi bi-chevron-down" : "bi bi-chevron-up";

            if (!collapsed) {
                requestAnimationFrame(() => {
                    tonalChartInstance?.resize?.();
                    qualityChartInstance?.resize?.();
                });
            }
        });
    }

    // Defensive guard: legacy refinements must never collapse the main dashboard again.
    new MutationObserver(() => {
        if (!dashboard.classList.contains("hidden") && dashboard.classList.contains("is-collapsed")) {
            dashboard.classList.remove("is-collapsed");
        }
    }).observe(dashboard, { attributes: true, attributeFilter: ["class"] });
}

document.addEventListener("DOMContentLoaded", installDashboardWorkspace);
