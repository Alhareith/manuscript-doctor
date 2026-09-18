"use strict";

let clinicAutoExamTicket = 0;

function installCompactUploadHero() {
    const intro = document.querySelector(".upload-intro");
    if (!intro || intro.querySelector(".upload-hero-glyph")) return;
    const glyph = document.createElement("span");
    glyph.className = "upload-hero-glyph";
    glyph.setAttribute("aria-hidden", "true");
    glyph.innerHTML = '<i class="bi bi-file-earmark-medical-fill"></i>';
    intro.appendChild(glyph);
}

function setExamButtonState(mode = "idle") {
    const button = elements.startExaminationButton;
    if (!button) return;

    const states = {
        idle: ['<i class="bi bi-activity"></i> فحص الوثيقة', !state.selectedFile],
        pending: ['<i class="bi bi-clock-history"></i> سيبدأ الفحص تلقائيًا', true],
        running: ['<span class="processing-spinner exam-button-spinner"></span> جارٍ الفحص', true],
        ready: ['<i class="bi bi-arrow-repeat"></i> إعادة الفحص', false],
        retry: ['<i class="bi bi-arrow-clockwise"></i> إعادة محاولة الفحص', false]
    };

    const [html, disabled] = states[mode] || states.idle;
    button.innerHTML = html;
    button.disabled = Boolean(disabled);
    button.dataset.examState = mode;
}

function scheduleAutomaticExamination(file) {
    if (!file) return;
    const ticket = ++clinicAutoExamTicket;
    setExamButtonState("pending");

    window.setTimeout(async () => {
        if (ticket !== clinicAutoExamTicket) return;
        if (state.selectedFile !== file || state.imageId || state.isBusy) return;
        setExamButtonState("running");
        try {
            await startExamination();
            setExamButtonState(state.analysis ? "ready" : "retry");
        } catch {
            setExamButtonState("retry");
        }
    }, 220);
}

function bindAutomaticExamination() {
    elements.imageInput?.addEventListener("change", (event) => {
        const file = event.target.files?.[0];
        if (file) scheduleAutomaticExamination(file);
    });

    elements.dropZone?.addEventListener("drop", (event) => {
        const file = event.dataTransfer?.files?.[0];
        if (file) scheduleAutomaticExamination(file);
    });

    elements.removeImageButton?.addEventListener("click", () => {
        clinicAutoExamTicket += 1;
        setExamButtonState("idle");
    });

    elements.startExaminationButton?.addEventListener("click", () => {
        if (state.imageId && !state.isBusy) {
            window.setTimeout(() => setExamButtonState("running"), 0);
            window.setTimeout(() => setExamButtonState(state.analysis ? "ready" : "retry"), 350);
        }
    });

    const processing = elements.processingSection;
    if (processing) {
        new MutationObserver(() => {
            if (!state.selectedFile) {
                setExamButtonState("idle");
                return;
            }
            if (!processing.classList.contains("hidden")) {
                setExamButtonState("running");
            } else if (state.analysis) {
                setExamButtonState("ready");
            } else if (state.imageId) {
                setExamButtonState("retry");
            }
        }).observe(processing, { attributes: true, attributeFilter: ["class"] });
    }
}

function bindUsageGuidePlaceholder() {
    const button = document.getElementById("usageGuideButton");
    if (!button) return;
    button.addEventListener("click", () => {
        // Reserved intentionally. A full usage guide/document will be wired here later.
    });
}

document.addEventListener("DOMContentLoaded", () => {
    installCompactUploadHero();
    bindAutomaticExamination();
    bindUsageGuidePlaceholder();
    setExamButtonState("idle");
});
