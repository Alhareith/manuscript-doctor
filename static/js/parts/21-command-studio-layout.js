"use strict";

(function installPremiumCommandStudio() {
    function bySelector(selector) {
        return document.querySelector(selector);
    }

    function make(tag, className, html = "") {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (html) node.innerHTML = html;
        return node;
    }

    function clickOperation(operationId) {
        const pageTab = document.querySelector('[data-operation-group="page"]');
        const target = document.querySelector(`[data-operation-card="${operationId}"]`);
        if (!target) return;
        if (["document_prepare", "crop", "perspective_crop", "rotate_right", "rotate_left", "flip_vertical", "flip_horizontal", "deskew"].includes(operationId)) {
            pageTab?.click();
        }
        window.requestAnimationFrame(() => target.click());
    }


    function ensurePanelHeading(parent, icon, title, subtitle) {
        if (!parent || parent.querySelector(":scope > .command-panel-heading")) return;
        const heading = make("div", "command-panel-heading");
        heading.innerHTML = `
            <div><i class="bi ${icon}"></i><strong>${title}</strong></div>
            <small>${subtitle || ""}</small>
        `;
        parent.insertBefore(heading, parent.firstChild);
    }

    function installPanelHeadings() {
        ensurePanelHeading(
            document.getElementById("uploadSection"),
            "bi-cloud-arrow-up",
            "رفع وإدخال الوثيقة",
            "Upload & Input"
        );
        ensurePanelHeading(
            document.querySelector(".manual-preview-pane"),
            "bi-images",
            "المعاينة والمقارنة",
            "Preview & Comparison"
        );
        ensurePanelHeading(
            document.querySelector(".manual-controls-pane"),
            "bi-sliders2",
            "معاملات المعالجة",
            "Processing Parameters"
        );
    }

    function installPreviewModes() {
        const toolbar = document.querySelector(".manual-preview-toolbar");
        const pair = document.querySelector(".manual-preview-pair");
        if (!toolbar || !pair || toolbar.querySelector(".command-preview-modes")) return;

        const modes = make("div", "command-preview-modes");
        modes.innerHTML = `
            <button type="button" class="is-active" data-command-preview-mode="side"><i class="bi bi-layout-split"></i><span>جنبًا إلى جنب</span></button>
            <button type="button" data-command-preview-mode="before"><i class="bi bi-image"></i><span>قبل</span></button>
            <button type="button" data-command-preview-mode="after"><i class="bi bi-stars"></i><span>بعد</span></button>
            <button type="button" data-command-refresh-preview><i class="bi bi-arrow-repeat"></i><span>تحديث</span></button>
        `;
        toolbar.appendChild(modes);

        modes.addEventListener("click", (event) => {
            const button = event.target.closest("button");
            if (!button) return;

            if (button.hasAttribute("data-command-refresh-preview")) {
                const operationId = state?.manualPreviewCandidate?.operation?.id || elements.manualOperation?.value;
                if (operationId) clickOperation(operationId);
                return;
            }

            const mode = button.dataset.commandPreviewMode;
            if (!mode) return;
            pair.dataset.commandPreviewMode = mode;
            modes.querySelectorAll("[data-command-preview-mode]").forEach((item) => {
                item.classList.toggle("is-active", item === button);
            });
        });
    }

    function installOperationSuperTabs() {
        const pane = document.querySelector(".manual-controls-pane");
        const categories = pane?.querySelector(".operation-category-strip");
        if (!pane || !categories || pane.querySelector(".command-control-tabs")) return;

        const superTabs = make("div", "command-control-tabs");
        superTabs.innerHTML = `
            <button type="button" class="is-active" data-command-toolset="basic">أساسي</button>
            <button type="button" data-command-toolset="advanced">متقدم</button>
            <button type="button" data-command-toolset="restoration">ترميم</button>
        `;
        categories.insertAdjacentElement("beforebegin", superTabs);

        const groups = {
            basic: ["page", "lighting", "contrast", "noise"],
            advanced: ["detail", "threshold"],
            restoration: ["structure", "background"]
        };

        function activate(toolset) {
            const allowed = groups[toolset] || groups.basic;
            const categoryButtons = [...categories.querySelectorAll("[data-operation-group]")];
            categoryButtons.forEach((button) => {
                button.hidden = !allowed.includes(button.dataset.operationGroup);
            });

            const current = categoryButtons.find((button) => button.classList.contains("is-active") && !button.hidden);
            if (!current) categoryButtons.find((button) => !button.hidden)?.click();

            superTabs.querySelectorAll("[data-command-toolset]").forEach((button) => {
                button.classList.toggle("is-active", button.dataset.commandToolset === toolset);
            });
        }

        superTabs.addEventListener("click", (event) => {
            const button = event.target.closest("[data-command-toolset]");
            if (button) activate(button.dataset.commandToolset);
        });

        activate("basic");
    }

    function installHeaderNav() {
        const inner = bySelector(".app-header-inner");
        if (!inner || bySelector(".command-studio-nav")) return;

        const nav = make("nav", "command-studio-nav");
        nav.setAttribute("aria-label", "أقسام مساحة العمل");
        nav.innerHTML = `
            <button type="button" class="is-active" data-command-focus="preview"><i class="bi bi-house-door-fill"></i><span>مساحة العمل</span></button>
            <button type="button" data-command-focus="controls"><i class="bi bi-sliders2"></i><span>الأدوات</span></button>
            <button type="button" data-command-focus="results"><i class="bi bi-images"></i><span>النتائج</span></button>
            <button type="button" data-command-results><i class="bi bi-shield-check"></i><span>التحقق</span></button>
        `;
        inner.insertBefore(nav, inner.querySelector(".header-actions"));

        nav.addEventListener("click", (event) => {
            const button = event.target.closest("button");
            if (!button) return;
            if (button.hasAttribute("data-command-results")) {
                document.body.classList.toggle("command-results-open");
                return;
            }
            nav.querySelectorAll("button").forEach((item) => item.classList.toggle("is-active", item === button));
            const area = button.dataset.commandFocus;
            const target = area === "controls"
                ? bySelector(".manual-controls-pane")
                : area === "results"
                    ? bySelector(".command-results-dock")
                    : bySelector(".manual-preview-pane");
            target?.animate?.([
                { boxShadow: "0 0 0 1px rgba(239,182,63,.75), 0 0 0 rgba(239,182,63,0)" },
                { boxShadow: "0 0 0 1px rgba(239,182,63,0), 0 0 28px rgba(239,182,63,0)" }
            ], { duration: 560, easing: "ease-out" });
        });
    }

    function installUploadMeta() {
        const upload = document.getElementById("uploadSection");
        if (!upload || upload.querySelector(".command-upload-meta")) return;

        const meta = make("div", "command-upload-meta");
        meta.innerHTML = `
            <div class="command-section-title"><span><i class="bi bi-file-earmark-image"></i> الملف الحالي</span><small data-command-file-status>بانتظار ملف</small></div>
            <div class="command-file-stack">
                <article class="command-file-row">
                    <img class="command-file-thumb" data-command-file-thumb alt="">
                    <div class="command-file-copy"><strong data-command-file-name>لم يتم اختيار صورة</strong><small data-command-file-meta>JPG · JPEG · PNG</small></div>
                    <span class="command-file-state"><i class="bi bi-image"></i></span>
                </article>
            </div>
        `;
        upload.appendChild(meta);
    }

    function installCropPanel(workspace) {
        if (document.getElementById("commandCropPanel")) return;
        const panel = make("section", "command-crop-panel");
        panel.id = "commandCropPanel";
        panel.innerHTML = `
            <div class="command-section-title"><span><i class="bi bi-crop"></i> القص والتحرير</span><small>اختياري</small></div>
            <div class="command-crop-actions">
                <button type="button" class="is-emphasis" data-command-operation="crop">قص</button>
                <button type="button" data-command-operation="document_prepare">تلقائي</button>
                <button type="button" data-command-operation="perspective_crop">منظور</button>
                <button type="button" data-command-operation="deskew">ميل</button>
                <button type="button" data-command-operation="rotate_right">يمين</button>
                <button type="button" data-command-operation="rotate_left">يسار</button>
                <button type="button" data-command-operation="flip_horizontal">عكس</button>
                <button type="button" data-command-reset>إعادة</button>
            </div>
            <div class="command-crop-preview">
                <img data-command-crop-thumb alt="معاينة مصغرة للوثيقة">
                <div><strong data-command-crop-label>الوثيقة الأصلية</strong><small>استخدم الأدوات أعلاه؛ المعاينة لا تُحفظ حتى الاعتماد.</small></div>
            </div>
        `;
        workspace.appendChild(panel);

        panel.addEventListener("click", (event) => {
            const operationButton = event.target.closest("[data-command-operation]");
            if (operationButton) {
                clickOperation(operationButton.dataset.commandOperation);
                return;
            }
            if (event.target.closest("[data-command-reset]")) {
                clickOperation("crop");
                window.setTimeout(() => {
                    document.querySelector(".manual-live-image-wrap")?.dispatchEvent(
                        new MouseEvent("dblclick", { bubbles: true })
                    );
                }, 0);
            }
        });
    }

    function moveActionButton(button, target, label) {
        if (!button || !target) return;
        button.classList.add("command-action-item");
        if (label) {
            const span = button.querySelector("span");
            if (span) span.textContent = label;
        }
        target.appendChild(button);
    }

    function installActionBar(workspace) {
        if (document.getElementById("commandActionBar")) return;
        const bar = make("section", "command-action-bar");
        bar.id = "commandActionBar";
        bar.innerHTML = `
            <div class="command-section-title"><span><i class="bi bi-play-fill"></i> إجراءات المعالجة</span></div>
            <div class="command-action-buttons"></div>
            <div class="command-action-status"><strong data-command-chain-title>لا توجد عملية معتمدة</strong><span data-command-chain-text>اختر عملية وشاهد المعاينة قبل الاعتماد.</span></div>
        `;
        workspace.appendChild(bar);
        const target = bar.querySelector(".command-action-buttons");

        moveActionButton(document.getElementById("runPipelineButton"), target);
        moveActionButton(document.getElementById("manualApprovalButton"), target);
        moveActionButton(document.getElementById("manualUndoButton"), target);
        moveActionButton(document.getElementById("manualRedoButton"), target);
        moveActionButton(document.getElementById("manualManualDownloadButton"), target);

        const details = make("button", "button button-ghost", '<i class="bi bi-layout-split"></i><span>التحقق والنتيجة</span>');
        details.type = "button";
        details.addEventListener("click", () => document.body.classList.add("command-results-open"));
        target.appendChild(details);

        moveActionButton(document.getElementById("downloadResultButton"), target);
        moveActionButton(document.getElementById("startOverButton"), target);
    }

    function installResultsDock(workspace) {
        if (document.getElementById("commandResultsDock")) return;
        const dock = make("section", "command-results-dock");
        dock.id = "commandResultsDock";
        dock.innerHTML = '<div class="command-section-title"><span><i class="bi bi-clock-history"></i> النتائج / سلسلة المعالجة</span><small>السجل الفعلي</small></div>';
        workspace.appendChild(dock);

        const history = document.querySelector("[data-treatment-history]");
        if (history) dock.appendChild(history);
    }

    function installInfoPanel(workspace) {
        if (document.getElementById("commandInfoPanel")) return;
        const panel = make("section", "command-info-panel");
        panel.id = "commandInfoPanel";
        panel.innerHTML = `
            <div class="command-section-title"><span><i class="bi bi-info-circle"></i> معلومات الصورة</span><small data-command-state>جاهز</small></div>
            <div class="command-info-grid">
                <div class="command-info-row"><span>اسم الملف</span><strong data-command-info-name>—</strong></div>
                <div class="command-info-row"><span>الأبعاد</span><strong data-command-info-dimensions>—</strong></div>
                <div class="command-info-row"><span>الحجم</span><strong data-command-info-size>—</strong></div>
                <div class="command-info-row"><span>النتيجة</span><strong data-command-info-result>لا توجد نتيجة معتمدة</strong></div>
                <div class="command-info-actions"><button type="button" data-command-results>تفاصيل التحقق</button><button type="button" data-command-guide>دليل الاستخدام</button></div>
            </div>
        `;
        workspace.appendChild(panel);
        panel.querySelector("[data-command-results]")?.addEventListener("click", () => document.body.classList.add("command-results-open"));
        panel.querySelector("[data-command-guide]")?.addEventListener("click", () => document.getElementById("usageGuideButton")?.click());
    }

    function installResultOverlay() {
        if (document.getElementById("commandResultOverlay")) return;
        const overlay = make("aside", "command-result-overlay");
        overlay.id = "commandResultOverlay";
        overlay.setAttribute("aria-label", "تفاصيل التحقق والنتيجة");
        overlay.innerHTML = `
            <div class="command-result-overlay-head">
                <div><strong>التحقق والنتيجة</strong><small>Preservation · Comparison · Output</small></div>
                <button type="button" aria-label="إغلاق"><i class="bi bi-x-lg"></i></button>
            </div>
        `;
        document.body.appendChild(overlay);
        overlay.querySelector("button")?.addEventListener("click", () => document.body.classList.remove("command-results-open"));

        ["verificationSection", "decisionSection", "binarizationSection", "comparisonSection", "downloadSection"].forEach((id) => {
            const node = document.getElementById(id);
            if (node) overlay.appendChild(node);
        });
    }

    function syncStudioData() {
        const fileName = elements.selectedFileName?.textContent?.trim();
        const fileMeta = elements.selectedFileMeta?.textContent?.trim();
        const previewSrc = elements.manualLivePreview?.getAttribute("src") || elements.manualOriginalPreview?.getAttribute("src") || elements.originalPreview?.getAttribute("src") || "";

        document.querySelectorAll("[data-command-file-name], [data-command-info-name]").forEach((node) => {
            node.textContent = fileName && fileName !== "—" ? fileName : "لم يتم اختيار صورة";
        });
        const fileMetaNode = document.querySelector("[data-command-file-meta]");
        if (fileMetaNode) fileMetaNode.textContent = fileMeta && fileMeta !== "—" ? fileMeta : "JPG · JPEG · PNG";

        document.querySelectorAll("[data-command-file-thumb], [data-command-crop-thumb]").forEach((img) => {
            if (previewSrc) {
                img.src = previewSrc;
                img.style.opacity = "1";
            } else {
                img.removeAttribute("src");
                img.style.opacity = ".3";
            }
        });

        const imageData = typeof state !== "undefined" ? state.imageData : null;
        const dimensions = document.querySelector("[data-command-info-dimensions]");
        if (dimensions) {
            const width = imageData?.width ?? state?.currentResult?.width;
            const height = imageData?.height ?? state?.currentResult?.height;
            dimensions.textContent = width && height ? `${width} × ${height}` : "—";
        }

        const size = document.querySelector("[data-command-info-size]");
        if (size) size.textContent = fileMeta || "—";

        const result = document.querySelector("[data-command-info-result]");
        if (result) result.textContent = state?.resultId ? "نتيجة معتمدة ومتاحة للتنزيل" : "لا توجد نتيجة معتمدة";

        const status = document.querySelector("[data-command-file-status]");
        if (status) status.textContent = state?.imageId ? "تم الرفع والفحص" : state?.selectedFile ? "جارٍ التجهيز" : "بانتظار ملف";

        const chainTitle = document.querySelector("[data-command-chain-title]");
        const chainText = document.querySelector("[data-command-chain-text]");
        if (chainTitle) chainTitle.textContent = elements.manualChainStatus?.textContent?.trim() || "لا توجد عملية معتمدة";
        if (chainText) chainText.textContent = elements.manualChainList?.textContent?.trim() || "اختر عملية وشاهد المعاينة قبل الاعتماد.";
    }

    function bindSyncObservers() {
        const nodes = [
            elements.selectedFileName,
            elements.selectedFileMeta,
            elements.manualLivePreview,
            elements.manualOriginalPreview,
            elements.originalPreview,
            elements.manualChainStatus,
            elements.manualChainList,
            elements.processingSection
        ].filter(Boolean);

        const observer = new MutationObserver(syncStudioData);
        nodes.forEach((node) => observer.observe(node, {
            attributes: true,
            childList: true,
            subtree: true,
            characterData: true,
            attributeFilter: node.tagName === "IMG" ? ["src"] : undefined
        }));

        document.addEventListener("click", () => window.setTimeout(syncStudioData, 80));
        document.addEventListener("change", () => window.setTimeout(syncStudioData, 80));
    }

    function boot() {
        const workspace = document.getElementById("workspace");
        if (!workspace || document.body.classList.contains("command-studio-active")) return;

        document.body.classList.add("command-studio-active");
        installHeaderNav();
        installPanelHeadings();
        installPreviewModes();
        installOperationSuperTabs();
        installUploadMeta();
        installCropPanel(workspace);
        installActionBar(workspace);
        installResultsDock(workspace);
        installInfoPanel(workspace);
        installResultOverlay();
        bindSyncObservers();
        syncStudioData();
    }

    document.addEventListener("DOMContentLoaded", boot);
})();
