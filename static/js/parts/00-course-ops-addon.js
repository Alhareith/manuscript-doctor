"use strict";

Object.assign(operationParameters, {
    erosion: [
        { name: "kernel_size", label: "Kernel Size", type: "number", value: 3, min: 3, max: 15, step: 2 },
        { name: "iterations", label: "Iterations", type: "number", value: 1, min: 1, max: 5, step: 1 }
    ],
    dilation: [
        { name: "kernel_size", label: "Kernel Size", type: "number", value: 3, min: 3, max: 15, step: 2 },
        { name: "iterations", label: "Iterations", type: "number", value: 1, min: 1, max: 5, step: 1 }
    ],
    morphological_gradient: [
        { name: "kernel_size", label: "Kernel Size", type: "number", value: 3, min: 3, max: 15, step: 2 }
    ],
    gaussian_blur: [
        { name: "kernel_size", label: "Kernel Size", type: "number", value: 5, min: 3, max: 31, step: 2 },
        { name: "sigma", label: "Sigma (0 = Auto)", type: "number", value: 0, min: 0, max: 5, step: 0.1 }
    ],
    laplacian_sharpen: [
        { name: "amount", label: "Sharpen Amount", type: "number", value: 0.5, min: 0.1, max: 2, step: 0.05 },
        { name: "kernel_size", label: "Kernel Size", type: "number", value: 3, min: 1, max: 7, step: 2 }
    ],
    sobel_edges: [
        { name: "kernel_size", label: "Kernel Size", type: "number", value: 3, min: 1, max: 7, step: 2 }
    ],
    contrast_stretch: [
        { name: "low_percentile", label: "Low Percentile", type: "number", value: 2, min: 0, max: 20, step: 0.5 },
        { name: "high_percentile", label: "High Percentile", type: "number", value: 98, min: 80, max: 100, step: 0.5 }
    ],
    log_transform: [
        { name: "strength", label: "Strength", type: "number", value: 1.0, min: 0.2, max: 3, step: 0.05 }
    ]
});

Object.assign(operationNames, {
    erosion: ["تآكل بنيوي", "Erosion"],
    dilation: ["توسيع بنيوي", "Dilation"],
    morphological_gradient: ["حدود البنى المورفولوجية", "Morphological Gradient"],
    gaussian_blur: ["تمهيد غاوسي", "Gaussian Blur"],
    laplacian_sharpen: ["حدّة لابلاسيان", "Laplacian Sharpen"],
    sobel_edges: ["حواف سوبل", "Sobel Edges"],
    contrast_stretch: ["تمدد التباين المئيني", "Contrast Stretch"],
    log_transform: ["تحويل لوغاريتمي", "Log Transform"]
});
