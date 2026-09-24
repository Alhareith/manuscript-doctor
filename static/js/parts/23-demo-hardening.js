"use strict";

(function hardenDemoInterface() {
    const q = (selector, root = document) => root.querySelector(selector);
    const qa = (selector, root = document) => [...root.querySelectorAll(selector)];

    function removeReferenceOnlyControls() {
        q(".command-studio-nav")?.remove();
        q(".ref-premium-button")?.remove();
        q(".ref-theme-icons")?.remove();
        q(".ref-preview-separator")?.remove();
        qa(".ref-image-footer").forEach((node) => node.remove());

        const modes = q(".command-preview-modes");
        if (modes) {
            modes.innerHTML = "";
            modes.hidden = true;
        }

        const originalCopy = q(".manual-preview-toolbar > div:first-child");
        originalCopy?.classList.remove("ref-preview-copy-hidden");

        const guide = document.getElementById("usageGuideButton");
        if (guide) guide.hidden = true;
    }

    function restoreRealHeader() {
        const brandTitle = q(".brand-copy strong");
        const brandSub = q(".brand-copy small");
        if (brandTitle) brandTitle.textContent = "طبيب الوثائق";
        if (brandSub) brandSub.textContent = "ترميم · تحسين · حفظ";

        const guide = document.getElementById("usageGuideButton");
        if (guide) guide.hidden = true;
    }

    function rebuildActualUploadSummary() {
        const meta = q(".command-upload-meta");
        if (!meta) return;
        meta.dataset.referenceReady = "demo-real";
        meta.innerHTML = `
            <div class="demo-current-file-title">
                <strong><i class="bi bi-file-earmark-image"></i> الملف الحالي</strong>
                <span data-demo-file-state>بانتظار وثيقة</span>
            </div>
            <article class="demo-current-file">
                <img data-demo-file-thumb alt="معاينة الملف الحالي">
                <div>
                    <strong data-demo-file-name>لم يتم اختيار ملف</strong>
                    <small data-demo-file-meta>ارفع صورة لبدء المعالجة</small>
                </div>
            </article>
        `;
    }

    function rebuildRealActions() {
        const bar = document.getElementById("commandActionBar");
        if (!bar) return;

        const realRun = document.getElementById("runPipelineButton");
        const approve = document.getElementById("manualApprovalButton");
        const undo = document.getElementById("manualUndoButton");
        const redo = document.getElementById("manualRedoButton");
        const manualDownload = document.getElementById("manualManualDownloadButton");
        const resultDownload = document.getElementById("downloadResultButton");
        const startOver = document.getElementById("startOverButton");

        [realRun, approve, undo, redo, manualDownload, resultDownload, startOver]
            .filter(Boolean)
            .forEach((node) => node.remove());

        bar.innerHTML = `
            <div class="demo-action-title">
                <strong><i class="bi bi-sliders2"></i> أدوات التنفيذ</strong>
                <small>كل الأزرار مرتبطة بوظائف المشروع الفعلية</small>
            </div>
            <div class="demo-action-main"></div>
            <div class="demo-action-export">
                <span>الحفظ والنتيجة</span>
                <div></div>
            </div>
        `;

        const main = q(".demo-action-main", bar);
        const output = q(".demo-action-export > div", bar);

        if (realRun) {
            realRun.className = "demo-action demo-action-primary";
            realRun.innerHTML = '<i class="bi bi-stars"></i><span>المعالجة الذكية</span>';
            main.appendChild(realRun);
        }

        if (approve) {
            approve.className = "demo-action demo-action-approve";
            approve.innerHTML = '<i class="bi bi-check2-circle"></i><span>اعتماد العملية</span>';
            main.appendChild(approve);
        }

        if (undo) {
            undo.className = "demo-action demo-action-history";
            undo.innerHTML = '<i class="bi bi-arrow-counterclockwise"></i><span>تراجع</span>';
            undo.title = "التراجع عن آخر عملية معتمدة";
            main.appendChild(undo);
        }

        if (redo) {
            redo.className = "demo-action demo-action-history";
            redo.innerHTML = '<i class="bi bi-arrow-clockwise"></i><span>إعادة</span>';
            redo.title = "إعادة العملية التي تم التراجع عنها";
            main.appendChild(redo);
        }

        if (manualDownload) {
            manualDownload.className = "demo-action demo-action-output";
            manualDownload.innerHTML = '<i class="bi bi-download"></i><span>تنزيل آخر خطوة</span>';
            output.appendChild(manualDownload);
        }

        if (resultDownload) {
            resultDownload.className = "demo-action demo-action-output";
            resultDownload.innerHTML = '<i class="bi bi-file-earmark-arrow-down"></i><span>تنزيل النتيجة</span>';
            output.appendChild(resultDownload);
        }

        if (startOver) {
            startOver.className = "demo-action demo-action-reset";
            startOver.innerHTML = '<i class="bi bi-arrow-repeat"></i><span>بدء من جديد</span>';
            output.appendChild(startOver);
        }
    }

    function rebuildActualResultsHeader() {
        const dock = document.getElementById("commandResultsDock");
        if (!dock) return;
        const strip = q("[data-ref-thumbnails]", dock);
        dock.innerHTML = `
            <div class="demo-results-head">
                <strong><i class="bi bi-clock-history"></i> سلسلة المعالجة</strong>
                <small>الخطوات المعتمدة فقط</small>
            </div>
        `;
        if (strip) dock.appendChild(strip);
    }

    function removeFakeThumbnailAddButton() {
        q(".ref-add-thumb")?.remove();
    }

    function localizeInfoPanel() {
        const panel = document.getElementById("commandInfoPanel");
        if (!panel) return;
        panel.innerHTML = `
            <div class="ref-info-head">
                <strong>معلومات الصورة</strong>
                <button type="button" class="ref-info-details" aria-label="فتح تفاصيل التحقق"><i class="bi bi-info-circle-fill"></i></button>
            </div>
            <div class="ref-info-grid">
                <span>الملف:</span><strong data-command-info-name>—</strong>
                <span>الأبعاد:</span><strong data-command-info-dimensions>—</strong>
                <span>الحجم:</span><strong data-command-info-size>—</strong>
                <span>الصيغة:</span><strong data-ref-info-format>—</strong>
            </div>
        `;
        q(".ref-info-details", panel)?.addEventListener("click", () => {
            document.body.classList.add("command-results-open");
        });
    }

    function localizeVisibleLabels() {
        const mapping = new Map([
            ["1. Upload & Input", "1. رفع الوثيقة"],
            ["2. Preview & Comparison", "2. المعاينة والمقارنة"],
            ["3. Processing Parameters", "3. أدوات المعالجة"],
            ["4. Crop & Edit (Optional)", "4. القص والتحرير"],
            ["5. Processing Actions", "5. إجراءات المعالجة"],
            ["6. Thumbnails / Results", "6. سلسلة النتائج"],
        ]);

        qa(".command-panel-heading strong, .ref-lower-heading strong, .ref-action-title strong, .ref-results-head strong").forEach((node) => {
            const exact = node.textContent.trim();
            for (const [english, arabic] of mapping) {
                if (exact.includes(english)) {
                    node.textContent = arabic;
                    break;
                }
            }
        });

        qa(".manual-preview-card figcaption span").forEach((node, index) => {
            node.textContent = index === 0 ? "الأصل" : "المعاينة المعالجة";
        });

        const presetLabel = q(".ref-preset-row > label");
        if (presetLabel) presetLabel.textContent = "العمليات المتاحة";
    }

    function syncRealFileSummary() {
        const fileName = elements.selectedFileName?.textContent?.trim();
        const fileMeta = elements.selectedFileMeta?.textContent?.trim();
        const preview = elements.manualOriginalPreview?.src || elements.originalPreview?.src || "";

        const name = q("[data-demo-file-name]");
        const meta = q("[data-demo-file-meta]");
        const stateLabel = q("[data-demo-file-state]");
        const thumb = q("[data-demo-file-thumb]");

        if (name) name.textContent = fileName && fileName !== "—" ? fileName : "لم يتم اختيار ملف";
        if (meta) meta.textContent = fileMeta && fileMeta !== "—" ? fileMeta : "ارفع صورة لبدء المعالجة";
        if (stateLabel) stateLabel.textContent = state?.imageId ? "جاهز للمعالجة" : "بانتظار وثيقة";
        if (thumb) {
            if (preview) {
                thumb.src = preview;
                thumb.hidden = false;
            } else {
                thumb.removeAttribute("src");
                thumb.hidden = true;
            }
        }
    }

    function enforceRealButtonContracts() {
        const buttons = qa("button");
        buttons.forEach((button) => {
            if (button.classList.contains("ref-add-thumb")) button.remove();
        });

        const toolbarActions = q(".manual-preview-toolbar-actions");
        if (toolbarActions) toolbarActions.hidden = true;
    }

    function bindDemoSync() {
        const observer = new MutationObserver(() => requestAnimationFrame(() => {
            syncRealFileSummary();
            removeFakeThumbnailAddButton();
        }));

        [elements.selectedFileName, elements.selectedFileMeta, elements.manualOriginalPreview, elements.originalPreview]
            .filter(Boolean)
            .forEach((node) => observer.observe(node, {
                attributes: true,
                childList: true,
                subtree: true,
                characterData: true
            }));

        document.addEventListener("click", () => window.setTimeout(() => {
            syncRealFileSummary();
            removeFakeThumbnailAddButton();
        }, 80));
    }

    function boot() {
        removeReferenceOnlyControls();
        restoreRealHeader();
        rebuildActualUploadSummary();
        rebuildRealActions();
        rebuildActualResultsHeader();
        localizeInfoPanel();
        localizeVisibleLabels();
        enforceRealButtonContracts();
        bindDemoSync();
        syncRealFileSummary();
        removeFakeThumbnailAddButton();
        document.body.classList.add("demo-hardened");
    }

    document.addEventListener("DOMContentLoaded", () => {
        requestAnimationFrame(() => requestAnimationFrame(boot));
    });
})();
