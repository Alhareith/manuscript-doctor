"use strict";

const premiumMetricMeta = {
    brightness: { label: "السطوع", icon: "bi-sun-fill", color: "#f0b94a" },
    contrast: { label: "التباين", icon: "bi-circle-half", color: "#67c7ff" },
    noise: { label: "الضوضاء", icon: "bi-grid-3x3-gap-fill", color: "#f17878" },
    sharpness: { label: "الحدة", icon: "bi-crosshair", color: "#70d6a8" },
    illumination: { label: "تجانس الإضاءة", icon: "bi-lightbulb-fill", color: "#b9a0ff" },
    edges: { label: "كثافة الحواف", icon: "bi-bezier2", color: "#66d2d5" }
};

function dashboardTone(key, text) {
    const value = String(text || "");
    if (!value || value.includes("بانتظار") || value.includes("غير متاح")) return "neutral";
    if (key === "noise") {
        if (value.includes("منخفض")) return "good";
        if (value.includes("متوسطة")) return "warning";
        return "danger";
    }
    if (key === "illumination") {
        if (value.includes("متجانسة نسبيًا")) return "good";
        if (value.includes("غير متجانسة بوضوح")) return "danger";
        return "warning";
    }
    if (key === "edges") return value.includes("طبيعية") ? "good" : "info";
    if (value.includes("مناسب") || value.includes("مقبول")) return "good";
    if (value.includes("منخفض جدًا") || value.includes("مرتفع جدًا")) return "danger";
    if (value.includes("منخفض") || value.includes("مرتفع")) return "warning";
    return "info";
}

function ensureAnalysisSnapshot() {
    const deck = document.querySelector(".after-exam-deck");
    const summary = deck?.querySelector(".analysis-summary-card");
    if (!deck || !summary) return null;

    let snapshot = deck.querySelector(".analysis-quick-findings");
    if (!snapshot) {
        snapshot = document.createElement("section");
        snapshot.className = "analysis-quick-findings";
        snapshot.setAttribute("aria-label", "ملخص اكتشافات الفحص");
        snapshot.innerHTML = `
            <article data-finding="issues"><span><i class="bi bi-activity"></i></span><div class="finding-copy"><small>ما اكتشفه الفحص</small><strong>بانتظار التحليل</strong><p>ستظهر الملاحظات هنا.</p></div></article>
            <article data-finding="preservation"><span><i class="bi bi-shield-check"></i></span><div class="finding-copy"><small>حساسية التفاصيل</small><strong>—</strong><p>تقدير مستوى المحافظة على البنية.</p></div></article>
            <article data-finding="recommendation"><span><i class="bi bi-stars"></i></span><div class="finding-copy"><small>الخطوة المقترحة</small><strong>—</strong><p>ستظهر أول معالجة مرشحة بعد الفحص.</p></div></article>`;
        const details = deck.querySelector(".analysis-details-stack");
        deck.insertBefore(snapshot, details || null);
    }
    return snapshot;
}

function moveFindingDetailsInline() {
    const snapshot = ensureAnalysisSnapshot();
    if (!snapshot) return;

    const mappings = [
        ["issues", [elements.diagnosisList]],
        ["preservation", [elements.preservationMessage, elements.preservationIndicators]],
        ["recommendation", [elements.recommendationList, elements.automaticExclusions]]
    ];

    mappings.forEach(([name, nodes]) => {
        const card = snapshot.querySelector(`[data-finding="${name}"]`);
        if (!card) return;
        let details = card.querySelector(".finding-inline-details");
        if (!details) {
            details = document.createElement("div");
            details.className = "finding-inline-details";
            card.appendChild(details);
        }
        nodes.filter(Boolean).forEach((node) => {
            if (node.parentElement !== details) details.appendChild(node);
        });
    });

    const deck = document.querySelector(".after-exam-deck");
    deck?.querySelector(".analysis-overview-toggle")?.remove();
    deck?.querySelector(".analysis-details-stack")?.classList.add("finding-panels-retired");
}

function updateAnalysisSnapshot() {
    const snapshot = ensureAnalysisSnapshot();
    if (!snapshot) return;

    const issues = snapshot.querySelector('[data-finding="issues"]');
    const preservation = snapshot.querySelector('[data-finding="preservation"]');
    const recommendation = snapshot.querySelector('[data-finding="recommendation"]');

    const diagnoses = Array.isArray(state.diagnoses) ? state.diagnoses : [];
    const high = diagnoses.filter((item) => String(item.severity).toLowerCase() === "high").length;
    const medium = diagnoses.filter((item) => String(item.severity).toLowerCase() === "medium").length;
    const issueLabels = diagnoses.map((item) => item.label || humanizeCode(item.code)).filter(Boolean);
    if (issues) {
        const strong = issues.querySelector(".finding-copy > strong");
        const p = issues.querySelector(".finding-copy > p");
        if (strong) strong.textContent = diagnoses.length ? `${diagnoses.length} ملاحظة مكتشفة` : "لا توجد مشكلة واضحة";
        if (p) p.textContent = issueLabels.length ? issueLabels.join(" · ") : "القياسات الحالية لا تشير إلى مشكلة واضحة تستدعي تدخلاً تلقائيًا.";
        issues.dataset.tone = high ? "danger" : medium ? "warning" : "good";
    }

    const profile = state.preservationProfile || {};
    const level = String(profile.level || "").toLowerCase();
    if (preservation) {
        const strong = preservation.querySelector(".finding-copy > strong");
        const p = preservation.querySelector(".finding-copy > p");
        if (strong) strong.textContent = level === "high" ? "حساسية عالية" : level === "moderate" ? "حساسية متوسطة" : level ? "حساسية منخفضة" : "قيد التقييم";
        if (p) p.textContent = profile.message || "يتم تقدير حساسية التفاصيل الأصلية قبل اعتماد المعالجة.";
        preservation.dataset.tone = level === "high" ? "danger" : level === "moderate" ? "warning" : level ? "good" : "neutral";
    }

    const firstRec = Array.isArray(state.recommendations) ? state.recommendations[0] : null;
    if (recommendation) {
        const strong = recommendation.querySelector(".finding-copy > strong");
        const p = recommendation.querySelector(".finding-copy > p");
        if (firstRec) {
            if (strong) strong.textContent = operationLabel(firstRec.operation_id);
            if (p) p.textContent = firstRec.reason || "معالجة مرشحة بناءً على القياسات الحالية.";
            recommendation.dataset.tone = firstRec.risk === "high" ? "danger" : firstRec.risk === "medium" ? "warning" : "info";
        } else {
            if (strong) strong.textContent = "لا معالجة تلقائية ضرورية";
            if (p) p.textContent = "يمكن المتابعة بالمراجعة اليدوية أو الأدوات المتقدمة عند الحاجة.";
            recommendation.dataset.tone = "good";
        }
    }
}

function ensureDashboardOverview() {
    const dashboard = elements.examinationSection;
    const head = dashboard?.querySelector(".dashboard-head");
    if (!dashboard || !head) return null;
    let strip = dashboard.querySelector(".dashboard-overview-strip");
    if (!strip) {
        strip = document.createElement("div");
        strip.className = "dashboard-overview-strip";
        strip.innerHTML = `
            <div class="dashboard-overview-main"><span class="overview-pulse"><i class="bi bi-activity"></i></span><div><small>ملخص المؤشرات</small><strong data-dashboard-health>بانتظار نتائج الفحص</strong></div></div>
            <div class="dashboard-overview-meta"><span><i class="bi bi-grid-3x3-gap"></i><b data-dashboard-count>6</b> مؤشرات</span><span><i class="bi bi-shield-check"></i> تحليل محافظ</span></div>`;
        head.insertAdjacentElement("afterend", strip);
    }
    return strip;
}

function updatePremiumDashboard() {
    const dashboard = elements.examinationSection;
    if (!dashboard) return;
    const overview = ensureDashboardOverview();
    let danger = 0;
    let warning = 0;
    let populated = 0;

    Object.keys(premiumMetricMeta).forEach((key, index) => {
        const meta = premiumMetricMeta[key];
        const card = dashboard.querySelector(`.metric-card[data-metric="${key}"]`);
        if (!card) return;
        const human = card.querySelector("[data-human-metric]")?.textContent?.trim() || "";
        const raw = card.querySelector("em")?.textContent?.trim() || "—";
        const sourceKey = typeof dashboardMetricSourceKeys !== "undefined" ? dashboardMetricSourceKeys[key] : key;
        const rawValue = typeof metricValue === "function" ? metricValue(dashboardMetricValues, sourceKey) : Number.NaN;
        const progress = typeof metricPosition === "function" ? metricPosition(key, rawValue) : 0;
        const tone = dashboardTone(key, human);

        card.dataset.tone = tone;
        card.style.setProperty("--metric-order", index);
        card.style.setProperty("--metric-accent", meta.color);
        card.style.setProperty("--metric-progress", `${Math.max(0, Math.min(100, progress)) * 3.6}deg`);
        card.classList.toggle("is-populated", Boolean(human && !human.includes("بانتظار")));
        card.setAttribute("aria-label", `${meta.label}: ${human || "غير متاح"}، القراءة ${raw}`);
        if (tone === "danger") danger += 1;
        if (tone === "warning") warning += 1;
        if (tone !== "neutral") populated += 1;
    });

    if (overview) {
        const health = overview.querySelector("[data-dashboard-health]");
        const count = overview.querySelector("[data-dashboard-count]");
        if (count) count.textContent = String(populated || 6);
        if (health) {
            health.textContent = !populated ? "بانتظار نتائج الفحص" : danger ? "توجد مؤشرات تحتاج انتباهًا واضحًا" : warning ? "الوثيقة تحتاج تحسينًا محافظًا" : "المؤشرات الأساسية مستقرة";
            overview.dataset.tone = danger ? "danger" : warning ? "warning" : populated ? "good" : "neutral";
        }
    }
}

let premiumDashboardFrame = 0;
function schedulePremiumDashboardUpdate() {
    cancelAnimationFrame(premiumDashboardFrame);
    premiumDashboardFrame = requestAnimationFrame(() => {
        moveFindingDetailsInline();
        updateAnalysisSnapshot();
        updatePremiumDashboard();
    });
}

document.addEventListener("DOMContentLoaded", () => {
    ensureAnalysisSnapshot();
    moveFindingDetailsInline();
    ensureDashboardOverview();
    schedulePremiumDashboardUpdate();

    [elements.examinationSection, elements.diagnosisList, elements.recommendationList, elements.preservationIndicators].forEach((node) => {
        if (!node) return;
        new MutationObserver(schedulePremiumDashboardUpdate).observe(node, {
            childList: true,
            subtree: true,
            characterData: true
        });
    });
});
