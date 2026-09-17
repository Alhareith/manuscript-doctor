"use strict";

function downloadFilenameFromHeaders(response, fallbackName) {
    const disposition = response.headers.get("content-disposition") || "";
    const utf8 = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (utf8?.[1]) {
        try { return decodeURIComponent(utf8[1].replace(/["']/g, "")); } catch { /* use fallback parsing */ }
    }
    const plain = disposition.match(/filename="?([^";]+)"?/i);
    return plain?.[1]?.trim() || fallbackName;
}

async function downloadResultWithoutNavigation(resultId, fallbackName, button) {
    if (!resultId) return;
    clearError();
    const previousDisabled = button?.disabled;
    const previousHtml = button?.innerHTML;
    if (button) {
        button.disabled = true;
        button.setAttribute("aria-busy", "true");
        button.innerHTML = '<i class="bi bi-arrow-down-circle"></i> جارٍ تجهيز التنزيل';
    }

    try {
        const response = await fetch(`/api/results/${encodeURIComponent(resultId)}/download`, {
            method: "GET",
            headers: { "Accept": "image/png,application/octet-stream;q=0.9,*/*;q=0.8" }
        });
        if (!response.ok) {
            let message = `تعذر تنزيل النتيجة (${response.status}).`;
            try {
                const payload = await response.json();
                message = payload?.message || payload?.error?.message || message;
            } catch { /* keep generic message */ }
            throw new Error(message);
        }

        const blob = await response.blob();
        const objectUrl = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = objectUrl;
        anchor.download = downloadFilenameFromHeaders(response, fallbackName);
        anchor.style.display = "none";
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1500);
    } catch (error) {
        showError(error.message || "تعذر تنزيل النتيجة.");
    } finally {
        if (button) {
            button.removeAttribute("aria-busy");
            button.innerHTML = previousHtml;
            button.disabled = Boolean(previousDisabled);
        }
    }
}

downloadCurrentResult = function downloadCurrentResultNoNavigation() {
    if (!state.resultId) return;
    return downloadResultWithoutNavigation(
        state.resultId,
        `manuscript-result-${state.resultId.slice(0, 8)}.png`,
        elements.downloadResultButton
    );
};

downloadApprovedManualResult = function downloadApprovedManualResultNoNavigation() {
    const resultId = state.manualApprovedResult?.id;
    if (!resultId) return;
    return downloadResultWithoutNavigation(
        resultId,
        `manuscript-manual-${resultId.slice(0, 8)}.png`,
        elements.manualManualDownloadButton
    );
};
