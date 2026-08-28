function metricValue(metrics, key) { return Number(metrics?.[key]?.value); }

function humanMetric(key, value) {
    if (!Number.isFinite(value)) return "غير متاح";
    if (key === "brightness") {
        if (value < 55) return "منخفض جدًا";
        if (value < 85) return "منخفض";
        if (value > 220) return "مرتفع جدًا";
        if (value > 200) return "مرتفع";
        return "مناسب";
    }
    if (key === "contrast") return value < 20 ? "منخفض جدًا" : value < 35 ? "منخفض" : "مقبول";
    if (key === "noise") return value > 20 ? "مرتفعة" : value > 12 ? "متوسطة" : "منخفضة";
    if (key === "sharpness") return value < 25 ? "منخفضة جدًا" : value < 60 ? "منخفضة" : "مقبولة";
    if (key === "illumination") return value > 0.18 ? "غير متجانسة بوضوح" : value > 0.10 ? "غير متجانسة" : "متجانسة نسبيًا";
    if (key === "edges") return value >= 0.12 ? "كثيفة" : "طبيعية";
    return "مقروء";
}

function metricPosition(key, value) {
    if (!Number.isFinite(value)) return 0;
    const max = { brightness: 255, contrast: 100, noise: 30, sharpness: 150, illumination: 0.30, edges: 0.20 }[key] || 1;
    return clamp((value / max) * 100, 3, 97);
}

function updateMetricCard(key, value, digits = 3) {
    const rawId = { brightness: "brightnessMetric", contrast: "contrastMetric", noise: "noiseMetric", sharpness: "sharpnessMetric", illumination: "illuminationMetric", edges: "edgeDensityMetric" }[key];
    const raw = byId(rawId);
    if (raw) raw.textContent = formatNumber(value, digits);
    const human = document.querySelector(`[data-human-metric="${key}"]`);
    if (human) human.textContent = humanMetric(key, value);
    const card = document.querySelector(`[data-metric="${key}"]`);
    const scale = card?.querySelector(".health-scale span");
    if (scale) scale.style.width = `${metricPosition(key, value)}%`;
    const meter = card?.querySelector(".metric-ring");
    if (meter) meter.style.setProperty("--meter", `${metricPosition(key, value)}%`);
}

function updateQualityScales(metrics) {
    const keys = ["brightness", "contrast", "noise", "sharpness"];
    document.querySelectorAll(".quality-scale-row").forEach((row, index) => {
        const key = keys[index];
        const backendKey = key;
        const value = metricValue(metrics, backendKey);
        const marker = row.querySelector(".quality-track i");
        if (marker) marker.style.insetInlineStart = `${metricPosition(key, value)}%`;
    });
}

function cssVariable(name, fallback) {
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || fallback;
}

function chartFontFamily() {
    return getComputedStyle(document.body).fontFamily || 'IBM Plex Sans Arabic, sans-serif';
}

function destroyDashboardCharts() {
    if (tonalChartInstance) {
        tonalChartInstance.destroy();
        tonalChartInstance = null;
    }
    if (qualityChartInstance) {
        qualityChartInstance.destroy();
        qualityChartInstance = null;
    }
}

function chartMetricPercent(key, value) {
    if (!Number.isFinite(value)) return 0;
    const max = { brightness: 255, contrast: 100, noise: 30, sharpness: 150, illumination: 0.30, edges: 0.20 }[key] || 1;
    return clamp((value / max) * 100, 0, 100);
}

function renderTonalDistributionChart(metrics) {
    if (!elements.tonalDistributionChart || typeof Chart === "undefined") return;
    if (tonalChartInstance) tonalChartInstance.destroy();

    const darkRatio = clamp(metricValue(metrics, "dark_clipped_ratio") || 0, 0, 1);
    const brightRatio = clamp(metricValue(metrics, "bright_clipped_ratio") || 0, 0, 1);
    const middleRatio = clamp(1 - darkRatio - brightRatio, 0, 1);
    const values = [darkRatio * 100, middleRatio * 100, brightRatio * 100];

    const muted = cssVariable("--text-muted", "#846f65");
    const border = cssVariable("--border", "#e7ddd6");
    const primary = cssVariable("--primary", "#0b7a62");
    const accent = cssVariable("--accent", "#bd740d");
    const context = elements.tonalDistributionChart.getContext("2d");
    const tonalGradient = context.createLinearGradient(0, 0, 0, 260);
    tonalGradient.addColorStop(0, "rgba(11, 122, 98, .42)");
    tonalGradient.addColorStop(.58, "rgba(85, 156, 127, .16)");
    tonalGradient.addColorStop(1, "rgba(189, 116, 13, .03)");

    tonalChartInstance = new Chart(elements.tonalDistributionChart, {
        type: "line",
        data: {
            labels: ["الظلال الشديدة", "النطاق الوسطي", "الإضاءات الشديدة"],
            datasets: [{
                label: "النسبة من الصورة",
                data: values,
                backgroundColor: tonalGradient,
                borderColor: primary,
                borderWidth: 3,
                pointBackgroundColor: [primary, "#75ad90", accent],
                pointBorderColor: "#fffefa",
                pointBorderWidth: 3,
                pointRadius: 6,
                pointHoverRadius: 8,
                fill: true,
                tension: .42
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 450 },
            layout: { padding: { top: 8, right: 4, left: 4, bottom: 0 } },
            plugins: {
                legend: { display: false },
                tooltip: {
                    rtl: true,
                    textDirection: "rtl",
                    titleFont: { family: chartFontFamily() },
                    bodyFont: { family: chartFontFamily() },
                    callbacks: { label: (context) => `${context.raw.toFixed(2)}%` }
                }
            },
            scales: {
                x: {
                    grid: { color: border, borderDash: [3, 4] },
                    border: { display: false },
                    ticks: { color: muted, font: { family: chartFontFamily(), size: 11, weight: "600" } }
                },
                y: {
                    beginAtZero: true,
                    max: 100,
                    border: { display: false },
                    grid: { color: border, borderDash: [3, 4] },
                    ticks: {
                        color: muted,
                        font: { family: chartFontFamily(), size: 10 },
                        stepSize: 10,
                        callback: (value) => `${value}%`
                    }
                }
            }
        }
    });
}



function focusDashboardMetric(metricKey) {
    if (!dashboardMetricLabels[metricKey]) return;

    activeDashboardMetric = metricKey;
    document.querySelectorAll(".metric-card[data-metric]").forEach((card) => {
        const active = card.dataset.metric === metricKey;
        card.classList.toggle("is-active", active);
        card.setAttribute("aria-pressed", String(active));
    });

    const sourceKey = dashboardMetricSourceKeys[metricKey];
    const rawValue = metricValue(dashboardMetricValues, sourceKey);
    const card = document.querySelector(`.metric-card[data-metric="${CSS.escape(metricKey)}"]`);
    const humanValue = card?.querySelector("[data-human-metric]")?.textContent?.trim();
    const readableValue = humanValue && humanValue !== "بانتظار الفحص"
        ? humanValue
        : formatNumber(rawValue, metricKey === "illumination" || metricKey === "edges" ? 4 : 2);

    if (elements.dashboardInterpretation) {
        elements.dashboardInterpretation.textContent = `القياس المحدد: ${dashboardMetricLabels[metricKey]}. القراءة الحالية: ${readableValue}. استخدم هذه القراءة مع التشخيص والتوصيات، ولا تعتبرها وحدها قرارًا للمعالجة.`;
    }
}

function bindDashboardMetricCards() {
    document.querySelectorAll(".metric-card[data-metric]").forEach((card) => {
        const metricKey = card.dataset.metric;
        card.setAttribute("role", "button");
        card.setAttribute("tabindex", "0");
        card.setAttribute("aria-pressed", "false");
        card.addEventListener("click", () => focusDashboardMetric(metricKey));
        card.addEventListener("keydown", (event) => {
            if (event.key !== "Enter" && event.key !== " ") return;
            event.preventDefault();
            focusDashboardMetric(metricKey);
        });
    });
}

function renderQualityMetricsChart(metrics) {
    if (!elements.qualityMetricsChart || typeof Chart === "undefined") return;
    if (qualityChartInstance) qualityChartInstance.destroy();

    const rows = [
        ["السطوع", "brightness", metricValue(metrics, "brightness")],
        ["التباين", "contrast", metricValue(metrics, "contrast")],
        ["الضوضاء", "noise", metricValue(metrics, "noise")],
        ["الحدة", "sharpness", metricValue(metrics, "sharpness")],
        ["تفاوت الإضاءة", "illumination", metricValue(metrics, "illumination_variation")],
        ["كثافة الحواف", "edges", metricValue(metrics, "edge_density")]
    ];
    const values = rows.map(([, key, value]) => chartMetricPercent(key, value));

    const muted = cssVariable("--text-muted", "#846f65");
    const border = cssVariable("--border", "#e7ddd6");
    const primary = cssVariable("--primary", "#0b7a62");
    const context = elements.qualityMetricsChart.getContext("2d");
    const qualityGradient = context.createLinearGradient(0, 0, 260, 0);
    qualityGradient.addColorStop(0, "rgba(11, 122, 98, .35)");
    qualityGradient.addColorStop(.7, primary);
    qualityGradient.addColorStop(1, "#bd740d");

    qualityChartInstance = new Chart(elements.qualityMetricsChart, {
        type: "bar",
        data: {
            labels: rows.map(([label]) => label),
            datasets: [{
                label: "قراءة مقننة",
                data: values,
                backgroundColor: qualityGradient,
                borderRadius: 8,
                borderSkipped: false,
                barThickness: 13
            }]
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 300 },
            plugins: {
                legend: { display: false },
                tooltip: {
                    rtl: true,
                    textDirection: "rtl",
                    titleFont: { family: chartFontFamily() },
                    bodyFont: { family: chartFontFamily() },
                    callbacks: {
                        label: (context) => {
                            const source = rows[context.dataIndex]?.[2];
                            return `القراءة الأصلية: ${formatNumber(source, 4)}`;
                        }
                    }
                }
            },
            onClick: (_event, activeElements) => {
                const point = activeElements?.[0];
                if (point) focusDashboardMetric(rows[point.index][1]);
            },
            onHover: (_event, activeElements) => {
                const canvas = elements.qualityMetricsChart;
                if (canvas) canvas.style.cursor = activeElements?.length ? "pointer" : "default";
            },
            scales: {
                x: {
                    beginAtZero: true,
                    max: 100,
                    border: { display: false },
                    grid: { color: border },
                    ticks: { display: false }
                },
                y: {
                    border: { display: false },
                    grid: { display: false },
                    ticks: { color: muted, font: { family: chartFontFamily(), size: 11, weight: "600" } }
                }
            }
        }
    });
}

function renderDashboardCharts(metrics) {
    renderTonalDistributionChart(metrics);
    renderQualityMetricsChart(metrics);
}

function renderDashboard(analysis, diagnoses = []) {
    const metrics = analysis?.metrics || {};
    dashboardMetricValues = metrics;
    updateMetricCard("brightness", metricValue(metrics, "brightness"));
    updateMetricCard("contrast", metricValue(metrics, "contrast"));
    updateMetricCard("noise", metricValue(metrics, "noise"));
    updateMetricCard("sharpness", metricValue(metrics, "sharpness"));
    updateMetricCard("illumination", metricValue(metrics, "illumination_variation"), 4);
    updateMetricCard("edges", metricValue(metrics, "edge_density"), 4);
    updateQualityScales(metrics);
    renderDashboardCharts(metrics);
    const problems = diagnoses.slice(0, 3).map((item) => item.label || humanizeCode(item.code));
    if (elements.dashboardInterpretation) elements.dashboardInterpretation.textContent = problems.length ? `أبرز ما كشفه الفحص: ${problems.join("، ")}. تُختار المعالجة بناءً على الأولوية ثم يُتحقق من أثرها قبل قبولها.` : "لا تظهر القياسات الحالية مشكلة واضحة تستدعي معالجة تلقائية. يمكن مراجعة التفاصيل أو استخدام الأدوات المتقدمة عند الحاجة.";
    show(elements.examinationSection);
}

function resetDashboard() {
    activeDashboardMetric = null;
    dashboardMetricValues = {};
    document.querySelectorAll(".metric-card[data-metric]").forEach((card) => {
        card.classList.remove("is-active");
        card.setAttribute("aria-pressed", "false");
    });
    destroyDashboardCharts();
    ["brightness", "contrast", "noise", "sharpness", "illumination", "edges"].forEach((key) => {
        const raw = byId({ brightness: "brightnessMetric", contrast: "contrastMetric", noise: "noiseMetric", sharpness: "sharpnessMetric", illumination: "illuminationMetric", edges: "edgeDensityMetric" }[key]);
        if (raw) raw.textContent = "—";
        const human = document.querySelector(`[data-human-metric="${key}"]`);
        if (human) human.textContent = "بانتظار الفحص";
        const scale = document.querySelector(`[data-metric="${key}"] .health-scale span`);
        if (scale) scale.style.width = "0%";
        const meter = document.querySelector(`[data-metric="${key}"] .metric-ring`);
        if (meter) meter.style.setProperty("--meter", "0%");
    });
    if (elements.dashboardInterpretation) elements.dashboardInterpretation.textContent = "سيظهر هنا تفسير مختصر مبني على نتائج التشخيص الفعلية دون ادعاء تحسن غير مثبت.";
}

function renderDiagnoses(diagnoses) {
    elements.diagnosisList.innerHTML = "";
    if (!Array.isArray(diagnoses) || diagnoses.length === 0) {
        elements.diagnosisList.innerHTML = '<div class="empty-state"><span>✓</span>لم يحدد محرك التشخيص مشكلة واضحة تحتاج معالجة.</div>';
        return;
    }
    diagnoses.forEach((diagnosis) => {
        const item = document.createElement("article");
        item.className = "diagnosis-item";
        item.innerHTML = `<div class="item-heading"><strong></strong><span></span></div><p></p>`;
        item.querySelector("strong").textContent = diagnosis.label || humanizeCode(diagnosis.code);
        item.querySelector("span").textContent = severityLabel(diagnosis.severity || "detected");
        item.querySelector("p").textContent = diagnosis.message || diagnosis.description || diagnosis.reason || "";
        elements.diagnosisList.appendChild(item);
    });
}

function renderPreservationProfile(profile) {
    const safe = profile || {};
    const level = String(safe.level || "moderate").toLowerCase();
    elements.preservationLevelBadge.className = `preservation-badge ${safeStatusClass(level)}`;
    const strong = elements.preservationLevelBadge.querySelector("strong");
    if (strong) strong.textContent = level === "high" ? "عالية" : level === "moderate" ? "متوسطة" : "منخفضة";
    elements.preservationMessage.textContent = safe.message || "لا تتوفر تفاصيل كافية عن حساسية الوثيقة.";
    elements.preservationIndicators.innerHTML = "";
    const indicators = Array.isArray(safe.indicators) ? safe.indicators : [];
    indicators.forEach((indicator) => {
        const line = document.createElement("div");
        line.className = "preservation-indicator";
        line.textContent = typeof indicator === "string" ? indicator : indicator.message || humanizeCode(indicator.code);
        elements.preservationIndicators.appendChild(line);
    });
}

function renderRecommendations(recommendations, summary) {
    elements.recommendationList.innerHTML = "";
    if (!Array.isArray(recommendations) || recommendations.length === 0) {
        const message = summary?.message || "لا توجد معالجة تلقائية موصى بها حاليًا.";
        elements.recommendationList.innerHTML = `<div class="empty-state"><span>✓</span>${message}</div>`;
        return;
    }
    recommendations.forEach((rec) => {
        const item = document.createElement("article");
        item.className = "recommendation-item";
        const title = operationLabel(rec.operation_id);
        const technical = rec.operation_id ? technicalOperationLabel(rec.operation_id) : "Manual review";
        item.innerHTML = `<div class="item-heading"><div><strong></strong><small></small></div><span></span></div><p></p>`;
        item.querySelector("strong").textContent = title;
        item.querySelector("small").textContent = technical;
        item.querySelector(".item-heading > span").textContent = rec.mode === "manual_review" ? "مراجعة يدوية" : (rec.risk ? `مخاطرة ${severityLabel(rec.risk)}` : "مرشح");
        item.querySelector("p").textContent = rec.reason || "مرشح وفق نتائج التشخيص الحالية.";
        elements.recommendationList.appendChild(item);
    });
}

function renderExclusions(exclusions) {
    elements.automaticExclusionList.innerHTML = "";
    if (!Array.isArray(exclusions) || exclusions.length === 0) { hide(elements.automaticExclusions); return; }
    exclusions.forEach((item) => {
        const row = document.createElement("div");
        row.className = "exclusion-item";
        row.innerHTML = `<strong></strong><small></small><p></p>`;
        row.querySelector("strong").textContent = operationLabel(item.operation_id);
        row.querySelector("small").textContent = technicalOperationLabel(item.operation_id);
        row.querySelector("p").textContent = item.reason || "مستبعد من التنفيذ التلقائي في الحالة الحالية.";
        elements.automaticExclusionList.appendChild(row);
    });
    show(elements.automaticExclusions);
}

function updateDocumentStatus(diagnoses, recommendations) {
    const high = diagnoses.filter((item) => item.severity === "high").length;
    const medium = diagnoses.filter((item) => item.severity === "medium").length;
    let title = "لا تظهر مشكلة واضحة";
    let message = "يمكن مراجعة الوثيقة أو استخدام الأدوات المتقدمة عند الحاجة.";
    if (high) { title = "تحتاج إلى معالجة واضحة"; message = "كشف الفحص مشكلة مرتفعة الشدة. راجع التوصية قبل تنفيذ أي معالجة."; }
    else if (medium) { title = "تحتاج إلى تحسين متوسط"; message = "كشف الفحص مشكلة أو أكثر بدرجة متوسطة ويمكن معالجتها بشكل محافظ."; }
    else if (recommendations.length) { title = "يوجد اقتراح معالجة"; message = "توجد معالجة مرشحة وفق القياسات الحالية."; }
    if (elements.documentStatusTitle) elements.documentStatusTitle.textContent = title;
    if (elements.documentStatusMessage) elements.documentStatusMessage.textContent = message;
}

function renderUploadData(data) {
    state.imageId = data.image?.image_id || null;
    state.imageData = data.image || null;
    state.analysis = data.analysis || null;
    state.diagnoses = Array.isArray(data.diagnoses) ? data.diagnoses : [];
    state.preservationProfile = data.preservation_profile || null;
    state.recommendations = Array.isArray(data.recommendations) ? data.recommendations : [];
    state.exclusions = Array.isArray(data.excluded_from_automatic) ? data.excluded_from_automatic : [];
    const originalUrl = `/api/images/${encodeURIComponent(state.imageId)}`;
    elements.originalPreview.src = originalUrl;
    if (elements.manualLivePreview) elements.manualLivePreview.src = originalUrl;
    if (elements.manualOriginalPreview) elements.manualOriginalPreview.src = originalUrl;
    if (elements.manualPreviewNote) elements.manualPreviewNote.textContent = "الصورة الأصلية — اختر عملية من المحرر.";
    if (state.imageData && elements.selectedFileMeta) elements.selectedFileMeta.textContent = `${state.imageData.width}×${state.imageData.height} · ${String(state.imageData.format || "").toUpperCase()}`;
    renderDashboard(state.analysis, state.diagnoses);
    renderDiagnoses(state.diagnoses);
    renderPreservationProfile(state.preservationProfile);
    renderRecommendations(state.recommendations, data.recommendation_summary);
    renderExclusions(state.exclusions);
    updateDocumentStatus(state.diagnoses, state.recommendations);
    showSection("diagnosisSection");
    showSection("preservationProfileSection");
    showSection("treatmentPlanSection");
        show(elements.treatmentSection);
    show(elements.treatmentHistory);
    setAnalysisPanelsCollapsed(true);
    setWorkflow("treat");
    updateTechnicalDetails();
    updateControls();
}

