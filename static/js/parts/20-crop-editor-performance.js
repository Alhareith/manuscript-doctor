"use strict";

const CROP_LOCAL_PREVIEW_MAX_DIMENSION = 960;
let localPreviewSourceKey = null;
let localPreviewSourcePromise = null;

function getLocalPreviewSource() {
    const key = currentManualSourceUrl();
    if (key !== localPreviewSourceKey || !localPreviewSourcePromise) {
        localPreviewSourceKey = key;
        const pending = loadCanvasImage(key).then(image => {
            const scale = Math.min(1, CROP_LOCAL_PREVIEW_MAX_DIMENSION / Math.max(image.naturalWidth, image.naturalHeight));
            const canvas = document.createElement("canvas");
            canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
            canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
            canvas.getContext("2d").drawImage(image, 0, 0, canvas.width, canvas.height);
            return canvas;
        });
        localPreviewSourcePromise = pending;
        pending.catch(() => { if (localPreviewSourcePromise === pending) localPreviewSourcePromise = null; });
    }
    return localPreviewSourcePromise;
}

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

    const image = await getLocalPreviewSource();
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

    syncCropEditorMode();
}

document.addEventListener("DOMContentLoaded", bindCropEditorEnhancements);


/* ---------- Manual four-corner perspective scanner ---------- */
let perspectiveCorners = null;
let perspectiveDragState = null;
let perspectiveSourceSize = null;

function perspectiveGuideElement() {
    return document.getElementById("manualPerspectiveGuide");
}

function defaultPerspectiveCorners(dimensions) {
    const insetX = Math.max(1, dimensions.width * 0.05);
    const insetY = Math.max(1, dimensions.height * 0.05);
    return [
        { x: insetX, y: insetY },
        { x: dimensions.width - insetX, y: insetY },
        { x: dimensions.width - insetX, y: dimensions.height - insetY },
        { x: insetX, y: dimensions.height - insetY }
    ];
}

function isPerspectiveConvex(corners) {
    if (!Array.isArray(corners) || corners.length !== 4) return false;
    let sign = 0;
    for (let i = 0; i < 4; i += 1) {
        const a = corners[i];
        const b = corners[(i + 1) % 4];
        const c = corners[(i + 2) % 4];
        const cross = ((b.x - a.x) * (c.y - b.y)) - ((b.y - a.y) * (c.x - b.x));
        if (Math.abs(cross) < 1e-6) return false;
        const current = Math.sign(cross);
        if (sign && current !== sign) return false;
        sign = current;
    }
    return true;
}

function getPerspectiveParameters() {
    const dimensions = cropDimensions();
    if (!dimensions.width || !dimensions.height) return {};
    if (!perspectiveCorners || !perspectiveSourceSize
        || perspectiveSourceSize.width !== dimensions.width
        || perspectiveSourceSize.height !== dimensions.height) {
        perspectiveCorners = defaultPerspectiveCorners(dimensions);
        perspectiveSourceSize = { ...dimensions };
    }

    return {
        x1: Math.round(perspectiveCorners[0].x), y1: Math.round(perspectiveCorners[0].y),
        x2: Math.round(perspectiveCorners[1].x), y2: Math.round(perspectiveCorners[1].y),
        x3: Math.round(perspectiveCorners[2].x), y3: Math.round(perspectiveCorners[2].y),
        x4: Math.round(perspectiveCorners[3].x), y4: Math.round(perspectiveCorners[3].y)
    };
}

function markPerspectiveDraft() {
    if (elements.manualOperation?.value !== "perspective_crop" || !state.imageId || state.isBusy) return;
    if (!perspectiveCorners || !isPerspectiveConvex(perspectiveCorners)) {
        state.manualPreviewCandidate = null;
        if (elements.manualPreviewNote) {
            elements.manualPreviewNote.textContent = "النقاط الأربع يجب أن تكوّن حدود وثيقة رباعية بدون تقاطع.";
        }
        updateManualApprovalUI();
        return;
    }

    const parameters = getPerspectiveParameters();
    state.manualPreviewCandidate = {
        result: null,
        operation: { id: "perspective_crop", parameters },
        data: { draft: true, perspective: true }
    };
    if (elements.manualPreviewNote) {
        elements.manualPreviewNote.textContent = "الحدود جاهزة — حرّك أي زاوية إن احتجت، ثم اعتمد المسح لتصحيح المنظور.";
    }
    updateManualApprovalUI();
}

function syncPerspectiveGuide() {
    const guide = perspectiveGuideElement();
    const active = elements.manualOperation?.value === "perspective_crop";
    const preview = elements.manualLivePreview;
    const dimensions = cropDimensions();

    if (!guide || !active || !preview || !dimensions.width || !dimensions.height) {
        guide?.classList.add("hidden");
        return;
    }

    if (!perspectiveCorners || !perspectiveSourceSize
        || perspectiveSourceSize.width !== dimensions.width
        || perspectiveSourceSize.height !== dimensions.height) {
        perspectiveCorners = defaultPerspectiveCorners(dimensions);
        perspectiveSourceSize = { ...dimensions };
    }

    const wrap = preview.parentElement;
    const wrapRect = wrap?.getBoundingClientRect();
    const imageRect = getCropRenderRect(preview, dimensions);
    if (!wrapRect?.width || !wrapRect?.height || !imageRect?.width || !imageRect?.height) return;

    guide.setAttribute("viewBox", `0 0 ${wrapRect.width} ${wrapRect.height}`);

    const points = perspectiveCorners.map((point) => ({
        x: (imageRect.left - wrapRect.left) + ((point.x / dimensions.width) * imageRect.width),
        y: (imageRect.top - wrapRect.top) + ((point.y / dimensions.height) * imageRect.height)
    }));

    guide.querySelector(".perspective-polygon")?.setAttribute(
        "points",
        points.map((point) => `${point.x},${point.y}`).join(" ")
    );

    guide.querySelectorAll("[data-edge]").forEach((edge, index) => {
        const a = points[index];
        const b = points[(index + 1) % 4];
        edge.setAttribute("x1", a.x);
        edge.setAttribute("y1", a.y);
        edge.setAttribute("x2", b.x);
        edge.setAttribute("y2", b.y);
    });

    guide.querySelectorAll("[data-perspective-corner]").forEach((handle) => {
        const index = Number(handle.dataset.perspectiveCorner);
        const point = points[index];
        handle.setAttribute("cx", point.x);
        handle.setAttribute("cy", point.y);
    });

    guide.classList.remove("hidden");
}

function initializePerspectiveGuide() {
    if (elements.manualOperation?.value !== "perspective_crop") {
        perspectiveGuideElement()?.classList.add("hidden");
        return;
    }

    const dimensions = cropDimensions();
    if (!dimensions.width || !dimensions.height) return;

    if (!perspectiveCorners || !perspectiveSourceSize
        || perspectiveSourceSize.width !== dimensions.width
        || perspectiveSourceSize.height !== dimensions.height) {
        perspectiveCorners = defaultPerspectiveCorners(dimensions);
        perspectiveSourceSize = { ...dimensions };
    }

    syncPerspectiveGuide();
    markPerspectiveDraft();
}

function perspectivePointFromEvent(event, rect, dimensions) {
    return {
        x: clamp(((event.clientX - rect.left) / rect.width) * dimensions.width, 0, dimensions.width - 1),
        y: clamp(((event.clientY - rect.top) / rect.height) * dimensions.height, 0, dimensions.height - 1)
    };
}

function beginPerspectiveDrag(event) {
    if (elements.manualOperation?.value !== "perspective_crop" || state.isBusy) return;
    const target = event.target.closest("[data-perspective-corner]");
    if (!target) return;

    const dimensions = cropDimensions();
    const rect = getCropRenderRect(elements.manualLivePreview, dimensions);
    if (!rect?.width || !rect?.height) return;

    perspectiveDragState = {
        pointerId: event.pointerId,
        corner: Number(target.dataset.perspectiveCorner),
        rect,
        dimensions
    };
    target.setPointerCapture?.(event.pointerId);
    event.preventDefault();
}

function movePerspectiveDrag(event) {
    const drag = perspectiveDragState;
    if (!drag || drag.pointerId !== event.pointerId || !perspectiveCorners) return;

    const next = perspectivePointFromEvent(event, drag.rect, drag.dimensions);
    const candidate = perspectiveCorners.map((point) => ({ ...point }));
    candidate[drag.corner] = next;

    if (isPerspectiveConvex(candidate)) {
        perspectiveCorners = candidate;
        syncPerspectiveGuide();
        markPerspectiveDraft();
    }
    event.preventDefault();
}

function endPerspectiveDrag(event) {
    if (!perspectiveDragState || perspectiveDragState.pointerId !== event.pointerId) return;
    event.target.releasePointerCapture?.(event.pointerId);
    perspectiveDragState = null;
    markPerspectiveDraft();
}

function syncPerspectiveEditorMode() {
    const active = elements.manualOperation?.value === "perspective_crop";
    const guide = perspectiveGuideElement();
    guide?.classList.toggle("hidden", !active);
    if (active) requestAnimationFrame(initializePerspectiveGuide);
}

function bindPerspectiveScanner() {
    const guide = perspectiveGuideElement();
    if (guide && guide.dataset.bound !== "true") {
        guide.dataset.bound = "true";
        guide.addEventListener("pointerdown", beginPerspectiveDrag);
        guide.addEventListener("pointermove", movePerspectiveDrag);
        guide.addEventListener("pointerup", endPerspectiveDrag);
        guide.addEventListener("pointercancel", endPerspectiveDrag);
    }

    elements.manualOperation?.addEventListener("change", syncPerspectiveEditorMode);
    elements.manualLivePreview?.addEventListener("load", () => {
        if (elements.manualOperation?.value === "perspective_crop") {
            requestAnimationFrame(syncPerspectiveGuide);
        }
    });

    window.addEventListener("resize", () => {
        if (elements.manualOperation?.value === "perspective_crop") {
            requestAnimationFrame(syncPerspectiveGuide);
        }
    });
}

document.addEventListener("DOMContentLoaded", bindPerspectiveScanner);
