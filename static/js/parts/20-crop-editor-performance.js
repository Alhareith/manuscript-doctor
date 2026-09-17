"use strict";

const CROP_LOCAL_PREVIEW_MAX_DIMENSION = 1400;

function currentCropMetadata() {
    const activeEntry = Number.isInteger(state.manualActiveIndex) && state.manualActiveIndex >= 0
        ? state.manualChain[state.manualActiveIndex]
        : null;
    return activeEntry?.result
        || state.currentResult
        || state.manualApprovedResult
        || state.imageData
        || null;
}

function cropDimensions() {
    const metadata = currentCropMetadata();
    const source = elements.manualLivePreview?.naturalWidth && elements.manualLivePreview?.naturalHeight
        ? elements.manualLivePreview
        : elements.manualOriginalPreview;

    const width = Number(metadata?.width || state.imageData?.width || source?.naturalWidth || 0);
    const height = Number(metadata?.height || state.imageData?.height || source?.naturalHeight || 0);
    return { width, height };
}

function pointToCropSource(event, rect, dimensions) {
    return {
        x: clamp(((event.clientX - rect.left) / rect.width) * dimensions.width, 0, dimensions.width),
        y: clamp(((event.clientY - rect.top) / rect.height) * dimensions.height, 0, dimensions.height)
    };
}

let cropDrawState = null;

function beginCropSelection(event) {
    if (elements.manualOperation?.value !== "crop" || state.isBusy) return;
    if (event.button !== undefined && event.button !== 0) return;
    if (event.target.closest("#manualCropGuide")) return;

    const wrap = event.currentTarget;
    const preview = elements.manualLivePreview;
    const dimensions = cropDimensions();
    const rect = getCropRenderRect(preview, dimensions);
    if (!rect?.width || !rect?.height) return;

    const insideImage = event.clientX >= rect.left
        && event.clientX <= rect.left + rect.width
        && event.clientY >= rect.top
        && event.clientY <= rect.top + rect.height;
    if (!insideImage) return;

    const start = pointToCropSource(event, rect, dimensions);
    cropDrawState = {
        pointerId: event.pointerId,
        rect,
        dimensions,
        startX: start.x,
        startY: start.y
    };

    wrap.setPointerCapture?.(event.pointerId);
    setCropInputValue("x", start.x);
    setCropInputValue("y", start.y);
    setCropInputValue("width", 1);
    setCropInputValue("height", 1);
    syncCropGuide();
    event.preventDefault();
}

function moveCropSelection(event) {
    const draw = cropDrawState;
    if (!draw || event.pointerId !== draw.pointerId) return;

    const current = pointToCropSource(event, draw.rect, draw.dimensions);
    const minSize = Math.min(24, draw.dimensions.width, draw.dimensions.height);
    const left = Math.min(draw.startX, current.x);
    const top = Math.min(draw.startY, current.y);
    const width = Math.max(minSize, Math.abs(current.x - draw.startX));
    const height = Math.max(minSize, Math.abs(current.y - draw.startY));

    setCropInputValue("x", clamp(left, 0, Math.max(0, draw.dimensions.width - minSize)));
    setCropInputValue("y", clamp(top, 0, Math.max(0, draw.dimensions.height - minSize)));
    setCropInputValue("width", Math.min(width, draw.dimensions.width - cropInputValue("x")));
    setCropInputValue("height", Math.min(height, draw.dimensions.height - cropInputValue("y")));
    syncCropGuide();
    markCropDraft();
    event.preventDefault();
}

function finishCropSelection(event) {
    if (!cropDrawState || event.pointerId !== cropDrawState.pointerId) return;
    event.currentTarget.releasePointerCapture?.(event.pointerId);
    cropDrawState = null;
    markCropDraft();
}

function resetCropSelection() {
    if (elements.manualOperation?.value !== "crop") return;
    const dimensions = cropDimensions();
    if (!dimensions.width || !dimensions.height) return;
    setCropInputValue("x", 0);
    setCropInputValue("y", 0);
    setCropInputValue("width", dimensions.width);
    setCropInputValue("height", dimensions.height);
    syncCropGuide();
    markCropDraft();
}

function syncCropEditorMode() {
    const wrap = document.querySelector(".manual-live-image-wrap");
    const active = elements.manualOperation?.value === "crop";
    wrap?.classList.toggle("crop-editor-active", active);
    if (active) requestAnimationFrame(syncCropGuide);
}

async function createFastLocalManualPreview(operationId, parameters = {}) {
    if (typeof LOCAL_PREVIEW_OPERATIONS === "undefined" || !LOCAL_PREVIEW_OPERATIONS.has(operationId)) {
        if (operationId !== "crop") return null;
    }

    const image = await loadCanvasImage(currentManualSourceUrl());
    const naturalWidth = image.naturalWidth || image.width;
    const naturalHeight = image.naturalHeight || image.height;
    if (!naturalWidth || !naturalHeight) return null;

    const sourceDimensions = cropDimensions();
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d", { willReadFrequently: true });
    if (!context) return null;

    if (operationId === "crop") {
        const logicalWidth = Math.max(1, Number(sourceDimensions.width || naturalWidth));
        const logicalHeight = Math.max(1, Number(sourceDimensions.height || naturalHeight));
        const scaleX = naturalWidth / logicalWidth;
        const scaleY = naturalHeight / logicalHeight;

        const x = clamp(Math.round((Number(parameters.x) || 0) * scaleX), 0, naturalWidth - 1);
        const y = clamp(Math.round((Number(parameters.y) || 0) * scaleY), 0, naturalHeight - 1);
        const width = clamp(Math.round((Number(parameters.width) || logicalWidth) * scaleX), 1, naturalWidth - x);
        const height = clamp(Math.round((Number(parameters.height) || logicalHeight) * scaleY), 1, naturalHeight - y);

        const previewScale = Math.min(1, CROP_LOCAL_PREVIEW_MAX_DIMENSION / Math.max(width, height));
        canvas.width = Math.max(1, Math.round(width * previewScale));
        canvas.height = Math.max(1, Math.round(height * previewScale));
        context.drawImage(image, x, y, width, height, 0, 0, canvas.width, canvas.height);
    } else {
        const previewScale = Math.min(1, CROP_LOCAL_PREVIEW_MAX_DIMENSION / Math.max(naturalWidth, naturalHeight));
        const workWidth = Math.max(1, Math.round(naturalWidth * previewScale));
        const workHeight = Math.max(1, Math.round(naturalHeight * previewScale));

        if (operationId === "rotate_right" || operationId === "rotate_left") {
            canvas.width = workHeight;
            canvas.height = workWidth;
            context.translate(canvas.width / 2, canvas.height / 2);
            context.rotate(operationId === "rotate_right" ? Math.PI / 2 : -Math.PI / 2);
            context.drawImage(image, 0, 0, naturalWidth, naturalHeight, -workWidth / 2, -workHeight / 2, workWidth, workHeight);
        } else {
            canvas.width = workWidth;
            canvas.height = workHeight;

            if (operationId === "flip_vertical" || operationId === "flip_horizontal") {
                context.translate(operationId === "flip_horizontal" ? workWidth : 0, operationId === "flip_vertical" ? workHeight : 0);
                context.scale(operationId === "flip_horizontal" ? -1 : 1, operationId === "flip_vertical" ? -1 : 1);
            }

            context.drawImage(image, 0, 0, naturalWidth, naturalHeight, 0, 0, workWidth, workHeight);

            if (operationId === "intensity_adjust" || operationId === "gamma_correct") {
                const pixels = context.getImageData(0, 0, workWidth, workHeight);
                const data = pixels.data;
                const alpha = Number(parameters.alpha ?? 1);
                const beta = Number(parameters.beta ?? 0);
                const gamma = Number(parameters.gamma ?? 1);
                for (let index = 0; index < data.length; index += 4) {
                    for (let channel = 0; channel < 3; channel += 1) {
                        const normalized = data[index + channel];
                        const adjusted = operationId === "gamma_correct"
                            ? 255 * Math.pow(normalized / 255, gamma)
                            : (normalized * alpha) + beta;
                        data[index + channel] = clamp(Math.round(adjusted), 0, 255);
                    }
                }
                context.putImageData(pixels, 0, 0);
            }
        }
    }

    return {
        data_url: canvas.toDataURL("image/jpeg", 0.84),
        width: canvas.width,
        height: canvas.height
    };
}

function bindCropEditorEnhancements() {
    const wrap = document.querySelector(".manual-live-image-wrap");
    if (wrap && wrap.dataset.cropEditorBound !== "true") {
        wrap.dataset.cropEditorBound = "true";
        wrap.addEventListener("pointerdown", beginCropSelection);
        wrap.addEventListener("pointermove", moveCropSelection);
        wrap.addEventListener("pointerup", finishCropSelection);
        wrap.addEventListener("pointercancel", finishCropSelection);
        wrap.addEventListener("dblclick", resetCropSelection);
    }

    elements.manualOperation?.addEventListener("change", syncCropEditorMode);
    elements.manualLivePreview?.addEventListener("load", () => {
        if (elements.manualOperation?.value === "crop") requestAnimationFrame(syncCropGuide);
    });

    if (typeof createLocalManualPreview === "function") {
        createLocalManualPreview = createFastLocalManualPreview;
    }

    syncCropEditorMode();
}

document.addEventListener("DOMContentLoaded", bindCropEditorEnhancements);
