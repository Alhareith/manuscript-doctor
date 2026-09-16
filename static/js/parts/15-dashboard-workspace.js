"use strict";

function installDashboardWorkspace() {
    const dashboard = elements.examinationSection;
    const previewSection = elements.documentPreviewSection;
    if (!dashboard || !previewSection) return;

    // Keep the dashboard as a full-width section immediately after the image/status workspace.
    // Never re-parent it into the compact diagnosis deck.
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
        const reading = dashboard.querySelector(".dashboard-reading-card");
        if (analytics) advanced.appendChild(analytics);
        if (reading) advanced.appendChild(reading);
        dashboard.querySelector(".dashboard-layout")?.appendChild(advanced);
    }

    const toggle = dashboard.querySelector(".dashboard-head .panel-toggle");
    if (toggle && toggle.dataset.dashboardBound !== "true") {
        toggle.dataset.dashboardBound = "true";
        toggle.setAttribute("aria-expanded", "false");
        const label = toggle.querySelector("span");
        if (label) label.textContent = "التحليل المتقدم";
        toggle.addEventListener("click", () => {
            const collapsed = advanced.classList.toggle("is-collapsed");
            toggle.setAttribute("aria-expanded", String(!collapsed));
            if (label) label.textContent = collapsed ? "التحليل المتقدم" : "إخفاء التحليل المتقدم";
            const icon = toggle.querySelector("i");
            if (icon) icon.className = collapsed ? "bi bi-chevron-down" : "bi bi-chevron-up";
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
