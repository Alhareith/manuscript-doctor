"use strict";

(function installReferenceFidelityLayer() {
    const q = (selector, root = document) => root.querySelector(selector);
    const qa = (selector, root = document) => [...root.querySelectorAll(selector)];

    function clickOperationReference(operationId) {
        const target = q(`[data-operation-card="${operationId}"]`);
        if (!target) return;
        const group = target.closest("[data-operation-group-panel]")?.dataset.operationGroupPanel;
        const toolset = ["page", "lighting", "contrast", "noise"].includes(group)
            ? "basic"
            : ["detail", "threshold"].includes(group)
                ? "advanced"
                : "restoration";
        q(`[data-command-toolset="${toolset}"]`)?.click();
        window.setTimeout(() => {
            if (group) q(`[data-operation-group="${group}"]`)?.click();
            requestAnimationFrame(() => target.click());
        }, 0);
    }

    function setReferenceParameter(operationId, parameter, value) {
        clickOperationReference(operationId);
        window.setTimeout(() => {
            const input = document.getElementById(`parameter-${parameter}`);
            if (!input) return;
            input.value = String(value);
            input.dispatchEvent(new Event("input", { bubbles: true }));
            input.dispatchEvent(new Event("change", { bubbles: true }));
        }, 0);
    }

    function updateBrandAndHeader() {
        const logo = q(".brand-mark img");
        const brandTitle = q(".brand-copy strong");
        const brandSub = q(".brand-copy small");
        if (logo) {
            logo.src = "/static/assets/reference-studio-logo.png";
            logo.alt = "";
        }
        if (brandTitle) brandTitle.textContent = "Manuscript Doctor";
        if (brandSub) brandSub.textContent = "Restore  ·  Enhance  ·  Preserve";

        const nav = q(".command-studio-nav");
        if (nav) {
            nav.innerHTML = `
                <button type="button" class="is-active" data-ref-nav="workspace"><i class="bi bi-house-door-fill"></i><span>Workspace</span></button>
                <button type="button" data-ref-nav="batch"><i class="bi bi-files"></i><span>Batch</span></button>
                <button type="button" data-ref-nav="gallery"><i class="bi bi-image-fill"></i><span>Gallery</span></button>
                <button type="button" data-ref-nav="tools"><i class="bi bi-tools"></i><span>Tools</span></button>
                <button type="button" data-ref-nav="settings"><i class="bi bi-gear-fill"></i><span>Settings</span></button>
                <button type="button" data-ref-nav="help"><i class="bi bi-question-circle-fill"></i><span>Help</span></button>
            `;
            nav.addEventListener("click", (event) => {
                const button = event.target.closest("[data-ref-nav]");
                if (!button) return;
                const key = button.dataset.refNav;
                qa("[data-ref-nav]", nav).forEach((item) => item.classList.toggle("is-active", item === button));
                if (key === "gallery") q("#commandResultsDock")?.animate([{opacity:.5},{opacity:1}], {duration:300});
                if (key === "tools") q(".manual-controls-pane")?.animate([{opacity:.55},{opacity:1}], {duration:300});
                if (key === "help") document.getElementById("usageGuideButton")?.click();
                if (key === "settings") document.getElementById("themeToggleButton")?.focus();
            });
        }

        const actions = q(".header-actions");
        if (actions && !q(".ref-theme-icons", actions)) {
            const guide = document.getElementById("usageGuideButton");
            if (guide) guide.classList.add("ref-hidden-guide");

            const themeIcons = document.createElement("span");
            themeIcons.className = "ref-theme-icons";
            themeIcons.innerHTML = '<i class="bi bi-sun-fill"></i><i class="bi bi-moon-fill"></i>';
            actions.insertBefore(themeIcons, actions.firstChild);

            const premium = document.createElement("button");
            premium.type = "button";
            premium.className = "ref-premium-button";
            premium.textContent = "Premium Studio";
            premium.addEventListener("click", () => q(".manual-preview-pane")?.animate([{filter:"brightness(1.14)"},{filter:"brightness(1)"}], {duration:420}));
            actions.appendChild(premium);
        }
    }

    function retitlePanels() {
        const headings = [
            ["#uploadSection > .command-panel-heading", "bi-cloud-arrow-up", "1. Upload & Input", ""],
            [".manual-preview-pane > .command-panel-heading", "bi-images", "2. Preview & Comparison", "Compare original and processed images with interactive tools"],
            [".manual-controls-pane > .command-panel-heading", "bi-gear-fill", "3. Processing Parameters", ""]
        ];
        headings.forEach(([selector, icon, title, subtitle]) => {
            const heading = q(selector);
            if (!heading) return;
            heading.innerHTML = `<div><i class="bi ${icon}"></i><strong>${title}</strong></div><small>${subtitle}</small>`;
        });
    }

    function rebuildDropZone() {
        const zone = document.getElementById("dropZone");
        const input = document.getElementById("imageInput");
        if (!zone || !input || zone.dataset.referenceReady === "true") return;
        zone.dataset.referenceReady = "true";
        [...zone.children].forEach((child) => {
            if (child !== input) child.remove();
        });
        const body = document.createElement("div");
        body.className = "ref-drop-body";
        body.innerHTML = `
            <i class="bi bi-upload ref-upload-symbol"></i>
            <strong>Drag & drop your manuscript here</strong>
            <span>or click to browse</span>
            <button type="button" class="ref-choose-button"><i class="bi bi-cloud-arrow-up-fill"></i> Choose Files</button>
            <small>Supports: JPG, PNG · Max size: 100 MB</small>
        `;
        zone.appendChild(body);
        q(".ref-choose-button", body)?.addEventListener("click", (event) => {
            event.stopPropagation();
            input.click();
        });
    }

    function rebuildRecentFiles() {
        const meta = q(".command-upload-meta");
        if (!meta || meta.dataset.referenceReady === "true") return;
        meta.dataset.referenceReady = "true";
        meta.innerHTML = `
            <div class="ref-recent-head"><strong>Recent Files</strong><button type="button">Clear All</button></div>
            <div class="ref-recent-list" data-ref-recent-list></div>
        `;
        q(".ref-recent-head button", meta)?.addEventListener("click", () => {
            const list = q("[data-ref-recent-list]");
            if (list) list.innerHTML = "";
        });
    }

    function rebuildPreviewToolbar() {
        const toolbar = q(".manual-preview-toolbar");
        const modes = q(".command-preview-modes", toolbar);
        if (!toolbar || !modes || modes.dataset.referenceReady === "true") return;
        modes.dataset.referenceReady = "true";
        const oldCopy = toolbar.firstElementChild;
        if (oldCopy) oldCopy.classList.add("ref-preview-copy-hidden");
        modes.innerHTML = `
            <div class="ref-view-tools">
                <button type="button" data-ref-view="zoom"><i class="bi bi-zoom-in"></i><span>Zoom</span></button>
                <button type="button" data-ref-view="pan"><i class="bi bi-hand-index-thumb"></i><span>Pan</span></button>
                <button type="button" data-ref-view="fit"><i class="bi bi-bounding-box"></i><span>Fit</span></button>
                <button type="button" data-ref-view="one"><i class="bi bi-aspect-ratio"></i><span>1:1</span></button>
                <button type="button" class="is-active" data-ref-view="side"><i class="bi bi-layout-split"></i><span>Side by Side</span></button>
                <button type="button" data-ref-view="split"><i class="bi bi-layout-sidebar-inset"></i><span>Split</span></button>
                <button type="button" data-ref-view="overlay"><i class="bi bi-layers"></i><span>Overlay</span></button>
            </div>
            <div class="ref-preview-controls">
                <div><small>Enhancement Preview</small><label><input type="checkbox" checked><span></span> Auto Update</label></div>
                <button type="button" data-ref-refresh><i class="bi bi-arrow-clockwise"></i> Refresh Preview</button>
            </div>
        `;
        const pair = q(".manual-preview-pair");
        modes.addEventListener("click", (event) => {
            const button = event.target.closest("button");
            if (!button) return;
            if (button.hasAttribute("data-ref-refresh")) {
                const op = state?.manualPreviewCandidate?.operation?.id || elements.manualOperation?.value;
                if (op) clickOperationReference(op);
                return;
            }
            const view = button.dataset.refView;
            if (!view || !pair) return;
            qa("[data-ref-view]", modes).forEach((item) => item.classList.toggle("is-active", item === button));
            pair.classList.remove("ref-zoom", "ref-one", "ref-overlay", "ref-split", "ref-pan");
            pair.dataset.commandPreviewMode = "side";
            if (view === "zoom") pair.classList.add("ref-zoom");
            if (view === "one") pair.classList.add("ref-one");
            if (view === "overlay") pair.classList.add("ref-overlay");
            if (view === "split") pair.classList.add("ref-split");
            if (view === "pan") pair.classList.add("ref-pan");
        });

        const cards = qa(".manual-preview-card");
        if (cards[0]) cards[0].querySelector("figcaption").innerHTML = '<span>Original</span><i class="bi bi-arrows-fullscreen"></i>';
        if (cards[1]) cards[1].querySelector("figcaption").innerHTML = '<span>Processed Preview</span><i class="bi bi-arrows-fullscreen"></i>';
    }


    function installReferencePreviewChrome() {
        const pair = q(".manual-preview-pair");
        if (!pair || pair.dataset.referenceChrome === "true") return;
        pair.dataset.referenceChrome = "true";

        const separator = document.createElement("button");
        separator.type = "button";
        separator.className = "ref-preview-separator";
        separator.setAttribute("aria-label", "التبديل بين قبل وبعد");
        separator.innerHTML = '<i class="bi bi-chevron-right"></i>';
        separator.addEventListener("click", () => {
            const cards = qa(".manual-preview-card", pair);
            cards.forEach((card) => card.classList.toggle("ref-swap-highlight"));
        });
        pair.appendChild(separator);

        qa(".manual-preview-card", pair).forEach((card, index) => {
            if (q(".ref-image-footer", card)) return;
            const footer = document.createElement("div");
            footer.className = "ref-image-footer";
            footer.innerHTML = `
                <span data-ref-image-meta>—</span>
                <div>
                    <button type="button" data-ref-zoom-out aria-label="تصغير">−</button>
                    <strong data-ref-zoom-value>45%</strong>
                    <button type="button" data-ref-zoom-in aria-label="تكبير">+</button>
                    <button type="button" data-ref-fullscreen aria-label="ملء الشاشة"><i class="bi bi-arrows-fullscreen"></i></button>
                </div>
            `;
            card.appendChild(footer);

            const image = q("img", card);
            let zoom = 45;
            const applyZoom = () => {
                const target = q("[data-ref-zoom-value]", footer);
                if (target) target.textContent = `${zoom}%`;
                if (image) image.style.setProperty("--ref-image-scale", String(Math.max(.35, zoom / 45)));
            };
            q("[data-ref-zoom-out]", footer)?.addEventListener("click", () => { zoom = Math.max(20, zoom - 5); applyZoom(); });
            q("[data-ref-zoom-in]", footer)?.addEventListener("click", () => { zoom = Math.min(100, zoom + 5); applyZoom(); });
            q("[data-ref-fullscreen]", footer)?.addEventListener("click", () => card.requestFullscreen?.());
            applyZoom();

            const updateMeta = () => {
                const meta = q("[data-ref-image-meta]", footer);
                if (!meta || !image) return;
                const w = image.naturalWidth || state?.imageData?.width || 0;
                const h = image.naturalHeight || state?.imageData?.height || 0;
                const sizeText = elements.selectedFileMeta?.textContent?.trim() || "";
                meta.textContent = w && h ? `${w} × ${h}${sizeText ? "  |  " + sizeText : ""}` : "Preview";
            };
            image?.addEventListener("load", updateMeta);
            updateMeta();
        });
    }

    function installPresetRow() {
        const pane = q(".manual-controls-pane");
        const tabs = q(".command-control-tabs", pane);
        if (!pane || !tabs || q(".ref-preset-row", pane)) return;
        const wrap = document.createElement("div");
        wrap.className = "ref-preset-row";
        const options = qa("#manualOperation option").map((option) => {
            const value = option.value;
            const label = value ? (operationNames?.[value]?.[1] || option.textContent) : "Custom (Manual)";
            return `<option value="${value}">${label}</option>`;
        }).join("");
        wrap.innerHTML = `
            <label>Presets</label>
            <div><select data-ref-operation-select>${options}</select><button type="button" title="Save preset"><i class="bi bi-floppy"></i></button><button type="button" title="Expand tools"><i class="bi bi-arrows-fullscreen"></i></button></div>
        `;
        tabs.insertAdjacentElement("beforebegin", wrap);
        q("[data-ref-operation-select]", wrap)?.addEventListener("change", (event) => {
            if (event.target.value) clickOperationReference(event.target.value);
        });
    }

    function quickRow(label, value, min, max, step, operation, parameter, mapper = (v) => v) {
        return `
            <label class="ref-param-row">
                <span>${label}</span>
                <input type="range" min="${min}" max="${max}" step="${step}" value="${value}" data-ref-operation="${operation}" data-ref-parameter="${parameter}">
                <output>${Number(value).toFixed(step < 1 ? 2 : 0)}</output>
            </label>
        `;
    }

    function installBasicParameters() {
        const pane = q(".manual-controls-pane");
        const browser = q(".operation-browser", pane);
        const tabs = q(".command-control-tabs", pane);
        if (!pane || !browser || !tabs || q(".ref-basic-stack", pane)) return;

        qa("[data-command-toolset]", tabs).forEach((button) => {
            const key = button.dataset.commandToolset;
            button.textContent = key === "basic" ? "Basic" : key === "advanced" ? "Advanced" : "Restoration";
        });

        const stack = document.createElement("div");
        stack.className = "ref-basic-stack";
        stack.innerHTML = `
            <section class="ref-param-group">
                <h4><i class="bi bi-gear-fill"></i> Preprocessing</h4>
                ${quickRow("Denoise", .30, .10, 1, .10, "median_denoise", "kernel_size")}
                ${quickRow("Contrast", 1.20, .50, 2, .05, "intensity_adjust", "alpha")}
                ${quickRow("Brightness", .05, -.30, .30, .01, "intensity_adjust", "beta")}
            </section>
            <section class="ref-param-group">
                <h4><i class="bi bi-brightness-high-fill"></i> Color & Tone</h4>
                ${quickRow("Gamma", 1.00, .20, 3, .05, "gamma_correct", "gamma")}
                ${quickRow("Local Tone", 1.40, .10, 5, .10, "faded_text_enhance", "clip_limit")}
            </section>
            <section class="ref-param-group">
                <h4><i class="bi bi-bullseye"></i> Sharpening</h4>
                ${quickRow("Sharpen", .40, 0, 2, .05, "sharpen", "amount")}
                ${quickRow("Edge Enhance", .20, .10, 2, .05, "laplacian_sharpen", "amount")}
            </section>
            <section class="ref-param-group">
                <h4><i class="bi bi-input-cursor-text"></i> Binarization (Optional)</h4>
                <label class="ref-method-row"><span>Method</span><select data-ref-threshold-method><option value="adaptive_threshold">Adaptive</option><option value="otsu_threshold">Otsu</option><option value="global_threshold">Global</option></select></label>
                ${quickRow("Threshold", .50, 0, 1, .01, "adaptive_threshold", "c")}
            </section>
        `;
        browser.insertAdjacentElement("beforebegin", stack);

        const applyToolset = (toolset) => {
            pane.dataset.refToolset = toolset;
            stack.hidden = toolset !== "basic";
        };
        applyToolset("basic");
        tabs.addEventListener("click", (event) => {
            const button = event.target.closest("[data-command-toolset]");
            if (button) window.setTimeout(() => applyToolset(button.dataset.commandToolset), 0);
        });

        qa(".ref-param-row input", stack).forEach((input) => {
            const syncRangePaint = () => {
                const min = Number(input.min || 0);
                const max = Number(input.max || 100);
                const value = Number(input.value);
                const pct = max > min ? ((value - min) / (max - min)) * 100 : 0;
                input.style.setProperty("--ref-range-pct", `${Math.max(0, Math.min(100, pct))}%`);
            };
            syncRangePaint();
            input.addEventListener("input", () => {
                syncRangePaint();
                const out = input.parentElement.querySelector("output");
                if (out) out.value = Number(input.value).toFixed(Number(input.step) < 1 ? 2 : 0);
            });
            input.addEventListener("change", () => {
                let value = Number(input.value);
                const op = input.dataset.refOperation;
                const parameter = input.dataset.refParameter;
                if (op === "median_denoise" && parameter === "kernel_size") {
                    value = Math.max(3, Math.min(15, Math.round(3 + value * 12)));
                    if (value % 2 === 0) value += 1;
                } else if (op === "intensity_adjust" && parameter === "beta") {
                    value = Math.round(value * 100);
                } else if (op === "adaptive_threshold" && parameter === "c") {
                    value = Math.round((value - .5) * 40);
                }
                setReferenceParameter(op, parameter, value);
            });
        });

        q("[data-ref-threshold-method]", stack)?.addEventListener("change", (event) => clickOperationReference(event.target.value));
    }

    function rebuildCropPanel() {
        const panel = document.getElementById("commandCropPanel");
        if (!panel) return;
        panel.innerHTML = `
            <div class="ref-lower-heading"><strong><i class="bi bi-crop"></i> 4. Crop & Edit <small>(Optional)</small></strong></div>
            <div class="ref-crop-buttons">
                <button class="is-active" type="button" data-ref-crop="crop">Crop</button>
                <button type="button" data-ref-crop="rotate_right">Rotate</button>
                <button type="button" data-ref-crop="flip_horizontal">Flip</button>
                <button type="button" data-ref-crop="reset">Reset</button>
            </div>
            <div class="ref-crop-stage"><img data-command-crop-thumb alt="Crop preview"><span class="ref-crop-frame"><i></i><i></i><i></i><i></i></span></div>
        `;
        panel.addEventListener("click", (event) => {
            const button = event.target.closest("[data-ref-crop]");
            if (!button) return;
            qa("[data-ref-crop]", panel).forEach((item) => item.classList.toggle("is-active", item === button));
            const action = button.dataset.refCrop;
            if (action === "reset") {
                clickOperationReference("crop");
                window.setTimeout(() => q(".manual-live-image-wrap")?.dispatchEvent(new MouseEvent("dblclick", {bubbles:true})), 0);
            } else {
                clickOperationReference(action);
            }
        });
    }

    function rebuildActions() {
        const bar = document.getElementById("commandActionBar");
        if (!bar) return;

        const realRun = document.getElementById("runPipelineButton");
        const realApprove = document.getElementById("manualApprovalButton");
        const realDownload = document.getElementById("downloadResultButton");
        const manualDownload = document.getElementById("manualManualDownloadButton");
        const undo = document.getElementById("manualUndoButton");
        const redo = document.getElementById("manualRedoButton");
        const startOver = document.getElementById("startOverButton");

        [realRun, realApprove, realDownload, manualDownload, undo, redo, startOver].filter(Boolean).forEach((node) => node.remove());

        bar.innerHTML = `
            <div class="ref-action-title"><strong><i class="bi bi-play-btn-fill"></i> 5. Processing Actions</strong></div>
            <div class="ref-action-main"></div>
            <div class="ref-export"><span>Export & Save</span><div></div></div>
            <div class="ref-preserved-actions" aria-hidden="true"></div>
        `;

        const main = q(".ref-action-main", bar);
        const exportBox = q(".ref-export > div", bar);
        const preserved = q(".ref-preserved-actions", bar);

        if (realRun) {
            realRun.className = "ref-run";
            realRun.innerHTML = '<i class="bi bi-play-fill"></i><span>Run Processing</span>';
            main.appendChild(realRun);
        }

        const preview = document.createElement("button");
        preview.type = "button";
        preview.innerHTML = '<i class="bi bi-eye-fill"></i><span>Preview</span>';
        preview.addEventListener("click", () => q('[data-ref-view="after"]')?.click());
        main.appendChild(preview);

        const compare = document.createElement("button");
        compare.type = "button";
        compare.innerHTML = '<i class="bi bi-layout-split"></i><span>Compare</span>';
        compare.addEventListener("click", () => q('[data-ref-view="side"]')?.click());
        main.appendChild(compare);

        if (realApprove) {
            realApprove.className = "";
            realApprove.innerHTML = '<i class="bi bi-layers-fill"></i><span>Apply Step</span>';
            main.appendChild(realApprove);
        }

        if (realDownload) {
            realDownload.className = "";
            realDownload.innerHTML = '<i class="bi bi-download"></i><span>Download Result</span>';
            exportBox.appendChild(realDownload);
        }
        if (manualDownload) {
            manualDownload.className = "";
            manualDownload.innerHTML = '<i class="bi bi-floppy"></i><span>Save Step</span>';
            exportBox.appendChild(manualDownload);
        }

        [undo, redo, startOver].filter(Boolean).forEach((node) => preserved.appendChild(node));
    }

    function rebuildResultsDock() {
        const dock = document.getElementById("commandResultsDock");
        if (!dock) return;
        dock.innerHTML = `
            <div class="ref-results-head"><strong><i class="bi bi-play-circle"></i> 6. Thumbnails / Results</strong><div>View: <button class="is-active"><i class="bi bi-grid-fill"></i></button><button><i class="bi bi-list"></i></button></div></div>
            <div class="ref-thumbnail-strip" data-ref-thumbnails></div>
        `;
    }

    function rebuildInfoPanel() {
        const panel = document.getElementById("commandInfoPanel");
        if (!panel) return;
        panel.innerHTML = `
            <div class="ref-info-head"><strong>1. Image Info</strong><button type="button" class="ref-info-details" aria-label="Open verification details"><i class="bi bi-info-circle-fill"></i></button></div>
            <div class="ref-info-grid">
                <span>Filename:</span><strong data-command-info-name>—</strong>
                <span>Dimensions:</span><strong data-command-info-dimensions>—</strong>
                <span>Size:</span><strong data-command-info-size>—</strong>
                <span>Format:</span><strong data-ref-info-format>—</strong>
            </div>
        `;
        q(".ref-info-details", panel)?.addEventListener("click", () => document.body.classList.add("command-results-open"));
    }

    function syncReferenceData() {
        const fileName = elements.selectedFileName?.textContent?.trim();
        const fileMeta = elements.selectedFileMeta?.textContent?.trim();
        const original = elements.manualOriginalPreview?.src || elements.originalPreview?.src || "";
        const after = elements.manualLivePreview?.src || original;

        const list = q("[data-ref-recent-list]");
        if (list) {
            const rows = [];
            if (fileName && fileName !== "—") rows.push({name:fileName, meta:fileMeta || "Current file", src:original});
            const chain = Array.isArray(state?.manualChain) ? state.manualChain : [];
            chain.slice(-3).reverse().forEach((entry, index) => rows.push({
                name: operationNames?.[entry.operation?.id]?.[1] || `Result ${index+1}`,
                meta: `Approved step ${Math.max(1, chain.length-index)}`,
                src: entry.previewDataUrl || (entry.result?.id ? `/api/results/${encodeURIComponent(entry.result.id)}` : after)
            }));
            list.innerHTML = rows.map((row) => `
                <article class="ref-recent-row"><img src="${row.src || ""}" alt=""><div><strong>${row.name}</strong><small>${row.meta}</small></div><i class="bi bi-trash3"></i></article>
            `).join("");
        }

        const thumb = q("[data-command-crop-thumb]");
        if (thumb && after) thumb.src = after;

        q('[data-command-info-name]') && (q('[data-command-info-name]').textContent = fileName && fileName !== "—" ? fileName : "—");
        const dimensions = q('[data-command-info-dimensions]');
        if (dimensions) {
            const width = state?.currentResult?.width || state?.imageData?.width;
            const height = state?.currentResult?.height || state?.imageData?.height;
            dimensions.textContent = width && height ? `${width} × ${height}` : "—";
        }
        const size = q('[data-command-info-size]');
        if (size) size.textContent = fileMeta || "—";
        const format = q('[data-ref-info-format]');
        if (format) format.textContent = (fileName?.split(".").pop() || "—").toUpperCase();

        const preset = q("[data-ref-operation-select]");
        if (preset && elements.manualOperation?.value && [...preset.options].some((o) => o.value === elements.manualOperation.value)) {
            preset.value = elements.manualOperation.value;
        }

        const strip = q("[data-ref-thumbnails]");
        if (strip) {
            const thumbs = [{label:"Original",src:original,current:state?.manualActiveIndex < 0}];
            (state?.manualChain || []).forEach((entry, index) => thumbs.push({
                label: operationNames?.[entry.operation?.id]?.[1] || `Step ${index+1}`,
                src: entry.previewDataUrl || (entry.result?.id ? `/api/results/${encodeURIComponent(entry.result.id)}` : after),
                current:index === state.manualActiveIndex
            }));
            if (state?.manualPreviewCandidate && after) thumbs.push({label:"Preview",src:after,current:true});
            strip.innerHTML = thumbs.slice(-6).map((item) => `
                <figure class="${item.current ? "is-current" : ""}"><img src="${item.src || ""}" alt=""><figcaption>${item.label}</figcaption></figure>
            `).join("") + '<button class="ref-add-thumb" type="button">+</button>';
        }
    }

    function bindReferenceSync() {
        const observer = new MutationObserver(() => window.requestAnimationFrame(syncReferenceData));
        [elements.selectedFileName, elements.selectedFileMeta, elements.manualOriginalPreview, elements.manualLivePreview, elements.manualChainStatus].filter(Boolean).forEach((node) => {
            observer.observe(node, {attributes:true,childList:true,subtree:true,characterData:true});
        });
        document.addEventListener("click", () => window.setTimeout(syncReferenceData, 100));
        document.addEventListener("change", () => window.setTimeout(syncReferenceData, 100));
    }

    function bootReference() {
        if (document.body.classList.contains("reference-target-active")) return;
        document.body.classList.add("reference-target-active");
        updateBrandAndHeader();
        retitlePanels();
        rebuildDropZone();
        rebuildRecentFiles();
        rebuildPreviewToolbar();
        installReferencePreviewChrome();
        installPresetRow();
        installBasicParameters();
        rebuildCropPanel();
        rebuildActions();
        rebuildResultsDock();
        rebuildInfoPanel();
        bindReferenceSync();
        syncReferenceData();
    }

    document.addEventListener("DOMContentLoaded", () => window.requestAnimationFrame(bootReference));
})();
