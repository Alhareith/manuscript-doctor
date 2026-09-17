"use strict";

function operationHasInlineParameters(operationId) {
    return Boolean(operationId && Array.isArray(operationParameters?.[operationId]) && operationParameters[operationId].length);
}

function syncOperationDisclosure(operationId) {
    document.querySelectorAll("[data-operation-card]").forEach((button) => {
        const selected = button.dataset.operationCard === operationId;
        const hasParameters = operationHasInlineParameters(button.dataset.operationCard);
        button.setAttribute("aria-expanded", String(selected && hasParameters));

        if (button.classList.contains("operation-row")) {
            const arrow = button.querySelector(":scope > i:last-child");
            if (arrow) {
                arrow.className = selected && hasParameters
                    ? "bi bi-chevron-down operation-disclosure-icon"
                    : "bi bi-chevron-left operation-disclosure-icon";
            }
        }
    });
}

function mountInlineOperationParameters(operationId) {
    const parameters = elements.manualParameters;
    if (!parameters) return;

    syncOperationDisclosure(operationId);
    const button = document.querySelector(`[data-operation-card="${CSS.escape(operationId || "")}"]`);
    const hasParameters = operationHasInlineParameters(operationId);

    parameters.classList.add("inline-operation-parameters");
    parameters.classList.toggle("hidden", !button || !hasParameters);
    if (!button || !hasParameters) return;

    if (parameters.previousElementSibling !== button) {
        button.insertAdjacentElement("afterend", parameters);
    }
}

function bindInlineOperationParameters() {
    document.querySelectorAll("[data-operation-card]").forEach((button) => {
        button.addEventListener("click", () => {
            requestAnimationFrame(() => mountInlineOperationParameters(button.dataset.operationCard));
        });
    });

    elements.manualOperation?.addEventListener("change", () => {
        requestAnimationFrame(() => mountInlineOperationParameters(elements.manualOperation.value));
    });

    if (elements.manualParameters) {
        new MutationObserver(() => {
            requestAnimationFrame(() => mountInlineOperationParameters(elements.manualOperation?.value || ""));
        }).observe(elements.manualParameters, { childList: true });
    }

    requestAnimationFrame(() => mountInlineOperationParameters(elements.manualOperation?.value || ""));
}

let comparePointerId = null;

function updateCompareFromPointer(event) {
    const wrap = document.querySelector("[data-compare-wrap]");
    const range = document.querySelector("[data-compare-range]");
    if (!wrap || !range) return;
    const rect = wrap.getBoundingClientRect();
    if (!rect.width) return;
    const percent = clamp(((event.clientX - rect.left) / rect.width) * 100, 0, 100);
    range.value = String(percent);
    setCompareSplit(percent);
}

function bindCompareImageDrag() {
    const stage = document.querySelector("[data-compare-stage]");
    const wrap = document.querySelector("[data-compare-wrap]");
    if (!stage || !wrap || stage.dataset.dragBound === "true") return;
    stage.dataset.dragBound = "true";

    [elements.comparisonOriginal, elements.resultPreview].forEach((image) => {
        if (image) image.draggable = false;
    });

    stage.addEventListener("pointerdown", (event) => {
        if (event.button !== undefined && event.button !== 0) return;
        comparePointerId = event.pointerId;
        stage.setPointerCapture?.(event.pointerId);
        updateCompareFromPointer(event);
        stage.classList.add("is-dragging");
        event.preventDefault();
    });

    stage.addEventListener("pointermove", (event) => {
        if (comparePointerId !== event.pointerId) return;
        updateCompareFromPointer(event);
        event.preventDefault();
    });

    const finish = (event) => {
        if (comparePointerId !== event.pointerId) return;
        stage.releasePointerCapture?.(event.pointerId);
        comparePointerId = null;
        stage.classList.remove("is-dragging");
    };
    stage.addEventListener("pointerup", finish);
    stage.addEventListener("pointercancel", finish);
}

document.addEventListener("DOMContentLoaded", () => {
    bindInlineOperationParameters();
    bindCompareImageDrag();
});
