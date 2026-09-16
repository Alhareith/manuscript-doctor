"use strict";

function installDashboardWorkspace() {
    const deck = document.querySelector(".after-exam-deck");
    const dashboard = elements.examinationSection;
    if (!deck || !dashboard) return;

    const detailsStack = deck.querySelector(".analysis-details-stack");
    if (dashboard.parentElement !== deck) {
        deck.insertBefore(dashboard, detailsStack || null);
    }

    dashboard.classList.add("dashboard-inline");
    dashboard.classList.remove("is-collapsed");

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
        if (label) label.textContent = "التفاصيل المتقدمة";
        toggle.addEventListener("click", () => {
            const collapsed = advanced.classList.toggle("is-collapsed");
            toggle.setAttribute("aria-expanded", String(!collapsed));
            if (label) label.textContent = collapsed ? "التفاصيل المتقدمة" : "إخفاء التفاصيل";
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
