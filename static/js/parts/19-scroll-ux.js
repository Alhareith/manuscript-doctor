"use strict";

function prefersReducedMotion() {
    return window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches === true;
}

function installScrollReveal() {
    if (prefersReducedMotion() || typeof IntersectionObserver === "undefined") return;

    const targets = [
        "#uploadSection",
        "#analysisMasterControl",
        "#documentPreviewSection",
        "#examinationSection",
        "#treatmentSection",
        "#manualEditor",
        "#verificationSection",
        "#downloadSection",
        ".treatment-history"
    ]
        .flatMap((selector) => [...document.querySelectorAll(selector)])
        .filter((node, index, list) => list.indexOf(node) === index);

    if (!targets.length) return;
    document.documentElement.classList.add("scroll-enhanced");

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            entry.target.classList.add("is-scroll-visible");
            observer.unobserve(entry.target);
        });
    }, {
        root: null,
        rootMargin: "0px 0px -7% 0px",
        threshold: 0.06
    });

    targets.forEach((target) => {
        target.classList.add("scroll-reveal-target");
        observer.observe(target);
    });
}

function scrollHeaderOffset() {
    const header = document.querySelector(".app-header");
    const workflow = document.querySelector(".workflow-bar");
    const headerHeight = header?.getBoundingClientRect().height || 0;
    const workflowSticky = workflow && getComputedStyle(workflow).position === "sticky";
    const workflowHeight = workflowSticky ? workflow.getBoundingClientRect().height : 0;
    return headerHeight + workflowHeight + 14;
}

function smoothScrollToTarget(target, options = {}) {
    if (!target) return;
    const behavior = prefersReducedMotion() ? "auto" : (options.behavior || "smooth");
    const top = Math.max(0, window.scrollY + target.getBoundingClientRect().top - scrollHeaderOffset());
    window.scrollTo({ top, behavior });
}

function bindStableAnchorScrolling() {
    document.addEventListener("click", (event) => {
        const anchor = event.target.closest('a[href^="#"]');
        if (!anchor) return;
        const href = anchor.getAttribute("href");
        if (!href || href === "#") return;
        let target;
        try { target = document.querySelector(href); }
        catch { return; }
        if (!target) return;

        /* Existing workflow/footer controllers may own application state. Only replace raw browser jumps. */
        if (anchor.hasAttribute("data-workflow-link") || anchor.hasAttribute("data-footer-nav")) return;
        event.preventDefault();
        smoothScrollToTarget(target);
        history.replaceState(null, "", href);
    });
}

function keepHorizontalSelectionVisible(containerSelector, activeSelector) {
    document.querySelectorAll(containerSelector).forEach((container) => {
        const sync = () => {
            const active = container.querySelector(activeSelector);
            if (!active) return;
            const c = container.getBoundingClientRect();
            const a = active.getBoundingClientRect();
            if (a.left < c.left || a.right > c.right) {
                active.scrollIntoView({
                    behavior: prefersReducedMotion() ? "auto" : "smooth",
                    block: "nearest",
                    inline: "center"
                });
            }
        };
        new MutationObserver(sync).observe(container, { subtree: true, attributes: true, attributeFilter: ["class"] });
        sync();
    });
}

function installResizeStability() {
    let frame = 0;
    const refresh = () => {
        cancelAnimationFrame(frame);
        frame = requestAnimationFrame(() => {
            if (typeof syncCropGuide === "function") syncCropGuide();
            tonalChartInstance?.resize?.();
            qualityChartInstance?.resize?.();
        });
    };

    window.addEventListener("resize", refresh, { passive: true });
    window.addEventListener("orientationchange", () => setTimeout(refresh, 80), { passive: true });
}

document.addEventListener("DOMContentLoaded", () => {
    installScrollReveal();
    bindStableAnchorScrolling();
    keepHorizontalSelectionVisible(".workflow-list", ".workflow-item.is-current");
    keepHorizontalSelectionVisible(".operation-category-strip", ".category-tab.is-active");
    installResizeStability();
});
