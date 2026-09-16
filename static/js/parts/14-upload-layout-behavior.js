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

function scheduleAutomaticExamination(file) {
    if (!file) return;
    const ticket = ++clinicAutoExamTicket;
    window.setTimeout(() => {
        if (ticket !== clinicAutoExamTicket) return;
        if (state.selectedFile !== file || state.imageId || state.isBusy) return;
        startExamination();
    }, 180);
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
    });
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
});
