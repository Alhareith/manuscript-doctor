"use strict";

const MAX_DIMENSION = 640;
const MAX_PIXELS = 300000;

function percentileFromHistogram(histogram, total, ratio) {
    const target = Math.max(0, Math.min(total - 1, Math.floor(total * ratio)));
    let seen = 0;
    for (let i = 0; i < histogram.length; i += 1) {
        seen += histogram[i];
        if (seen > target) return i;
    }
    return histogram.length - 1;
}

async function parseDimensions(file) {
    const limit = Math.min(file.size, 1024 * 1024);
    const bytes = new Uint8Array(await file.slice(0, limit).arrayBuffer());

    if (
        bytes.length >= 24 &&
        bytes[0] === 0x89 && bytes[1] === 0x50 &&
        bytes[2] === 0x4e && bytes[3] === 0x47
    ) {
        const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
        return {
            width: view.getUint32(16, false),
            height: view.getUint32(20, false)
        };
    }

    if (bytes.length >= 4 && bytes[0] === 0xff && bytes[1] === 0xd8) {
        let offset = 2;
        while (offset + 9 < bytes.length) {
            if (bytes[offset] !== 0xff) {
                offset += 1;
                continue;
            }

            const marker = bytes[offset + 1];
            offset += 2;

            if (marker === 0xd8 || marker === 0xd9 || (marker >= 0xd0 && marker <= 0xd7)) {
                continue;
            }

            if (offset + 2 > bytes.length) break;
            const length = (bytes[offset] << 8) | bytes[offset + 1];
            if (length < 2 || offset + length > bytes.length) break;

            const isSof = [
                0xc0, 0xc1, 0xc2, 0xc3,
                0xc5, 0xc6, 0xc7,
                0xc9, 0xca, 0xcb,
                0xcd, 0xce, 0xcf
            ].includes(marker);

            if (isSof && length >= 7) {
                return {
                    height: (bytes[offset + 3] << 8) | bytes[offset + 4],
                    width: (bytes[offset + 5] << 8) | bytes[offset + 6]
                };
            }

            offset += length;
        }
    }

    return null;
}

function targetSize(width, height) {
    const pixelScale = Math.sqrt(MAX_PIXELS / Math.max(1, width * height));
    const dimensionScale = MAX_DIMENSION / Math.max(width, height);
    const scale = Math.min(1, pixelScale, dimensionScale);
    return {
        width: Math.max(1, Math.round(width * scale)),
        height: Math.max(1, Math.round(height * scale))
    };
}

function metric(value, unit) {
    return { value: Number(value), unit };
}

function buildDiagnoses(metrics) {
    const diagnoses = [];
    const brightness = metrics.brightness.value;
    const contrast = metrics.contrast.value;
    const sharpness = metrics.sharpness.value;
    const noise = metrics.noise.value;
    const impulse = metrics.noise.impulse_ratio;
    const illumination = metrics.illumination_variation.value;

    if (brightness < 55) {
        diagnoses.push({ code: "very_dark", label: "إضاءة منخفضة جدًا", severity: "high", message: "تشير القياسات إلى أن الصورة مظلمة بدرجة واضحة." });
    } else if (brightness < 85) {
        diagnoses.push({ code: "dark", label: "إضاءة منخفضة", severity: "medium", message: "تشير القياسات إلى انخفاض مستوى الإضاءة." });
    }

    if (brightness > 220) {
        diagnoses.push({ code: "very_bright", label: "إضاءة مرتفعة جدًا", severity: "high", message: "تشير القياسات إلى سطوع مرتفع قد يخفي بعض التفاصيل." });
    } else if (brightness > 200) {
        diagnoses.push({ code: "bright", label: "إضاءة مرتفعة", severity: "medium", message: "تشير القياسات إلى ارتفاع مستوى الإضاءة." });
    }

    if (contrast < 20) {
        diagnoses.push({ code: "very_low_contrast", label: "تباين منخفض جدًا", severity: "high", message: "تظهر الصورة فرقًا محدودًا جدًا بين درجاتها البصرية." });
    } else if (contrast < 35) {
        diagnoses.push({ code: "low_contrast", label: "تباين منخفض", severity: "medium", message: "تشير القياسات إلى انخفاض التباين في الصورة." });
    }

    if (sharpness < 25) {
        diagnoses.push({ code: "very_low_sharpness", label: "حدة منخفضة جدًا", severity: "high", message: "تشير القياسات إلى ضعف واضح في الحواف والتفاصيل." });
    } else if (sharpness < 60) {
        diagnoses.push({ code: "low_sharpness", label: "حدة منخفضة", severity: "medium", message: "تشير القياسات إلى انخفاض نسبي في حدة التفاصيل." });
    }

    if (noise > 20) {
        diagnoses.push({ code: "high_noise", label: "ضوضاء مرتفعة", severity: "high", message: "تشير القياسات إلى تغيرات محلية قوية قد تمثل ضوضاء." });
    } else if (noise > 12 || impulse >= 0.004) {
        diagnoses.push({ code: "moderate_noise", label: impulse >= 0.004 ? "ضوضاء نبضية" : "ضوضاء متوسطة", severity: "medium", message: "تشير القياسات إلى وجود قدر متوسط من التغيرات المحلية." });
    }

    if (illumination > 0.18) {
        diagnoses.push({ code: "strong_uneven_illumination", label: "إضاءة غير متجانسة بوضوح", severity: "high", message: "توجد فروق واضحة في توزيع الإضاءة عبر الصورة." });
    } else if (illumination > 0.10) {
        diagnoses.push({ code: "uneven_illumination", label: "إضاءة غير متجانسة", severity: "medium", message: "تشير القياسات إلى تفاوت في توزيع الإضاءة عبر الصورة." });
    }

    return diagnoses;
}

function buildPreservation(metrics) {
    const indicators = [];
    let points = 0;

    if (metrics.edge_density.value >= 0.12) {
        points += 2;
        indicators.push({ code: "dense_edge_structure", message: "تحتوي الصورة على كثافة حواف مرتفعة نسبيًا، لذلك يفضل تجنب المعالجة العدوانية." });
    }
    if (metrics.contrast.value < 35) {
        points += 1;
        indicators.push({ code: "weak_contrast_details", message: "قد تكون بعض التفاصيل ضعيفة التباين وأكثر عرضة للاختفاء أثناء المعالجة القوية." });
    }
    if (metrics.sharpness.value < 60) {
        points += 1;
        indicators.push({ code: "weak_edge_definition", message: "الحواف الحالية ضعيفة نسبيًا، لذلك ينبغي التعامل بحذر مع العمليات التي قد تزيل التفاصيل." });
    }
    if (metrics.dynamic_range.value < 60) {
        points += 1;
        indicators.push({ code: "limited_dynamic_range", message: "النطاق البصري محدود نسبيًا، وقد توجد تفاصيل متقاربة في الشدة." });
    }

    const level = points >= 3 ? "high" : points >= 1 ? "moderate" : "low";
    const messages = {
        low: "لا تظهر المؤشرات الحالية حساسية مرتفعة للمعالجة، مع بقاء التحقق بعد المعالجة ضروريًا.",
        moderate: "توجد مؤشرات تستدعي استخدام معالجة متوازنة ومراقبة أثرها على التفاصيل.",
        high: "توجد مؤشرات تستدعي معالجة محافظة وتجنب العمليات القوية دون تحقق."
    };

    return {
        level,
        indicators,
        message: messages[level],
        interpretation: "instant_client_proxy"
    };
}

function buildRecommendations(metrics, diagnoses, preservation) {
    const codes = new Set(diagnoses.map((item) => item.code));
    const recommendations = [];
    const excluded = [];

    if (codes.has("uneven_illumination") || codes.has("strong_uneven_illumination")) {
        recommendations.push({
            operation_id: "illumination_normalize",
            priority: 10,
            parameters: { kernel_size: 51, strength: preservation.level === "high" ? 0.45 : 0.65 },
            mode: "enhancement",
            risk: "medium",
            reason: "توجد إضاءة غير متجانسة، والمعالجة المحافظة للإضاءة يجب أن تسبق أي تعديل لوني أو تبايني."
        });
    } else if (codes.has("dark") || codes.has("very_dark")) {
        recommendations.push({
            operation_id: "gamma_correct",
            priority: 20,
            parameters: { gamma: codes.has("very_dark") ? 0.65 : 0.85 },
            mode: "enhancement",
            risk: "low",
            reason: "تشير القياسات إلى انخفاض الإضاءة، وGamma هو التصحيح اللوني المحافظ للحالة."
        });
    } else if (codes.has("bright") || codes.has("very_bright")) {
        recommendations.push({
            operation_id: "gamma_correct",
            priority: 25,
            parameters: { gamma: codes.has("very_bright") ? 1.35 : 1.15 },
            mode: "enhancement",
            risk: "low",
            reason: "تشير القياسات إلى ارتفاع الإضاءة، ويستخدم Gamma بقيمة معاكسة لتقليل السطوع."
        });
    }

    if (codes.has("low_contrast") || codes.has("very_low_contrast")) {
        recommendations.push({
            operation_id: "clahe",
            priority: 30,
            parameters: { clip_limit: codes.has("very_low_contrast") ? 1.2 : 1.5, tile_grid_size: 8 },
            mode: "enhancement",
            risk: "medium",
            reason: "تشير القياسات إلى انخفاض التباين، وCLAHE بإعداد محافظ هو المرشح الأنسب."
        });
    }

    const hasNoise = codes.has("moderate_noise") || codes.has("high_noise");
    const impulse = metrics.noise.impulse_ratio >= 0.012;
    if (hasNoise && impulse && preservation.level !== "high") {
        recommendations.push({
            operation_id: "median_denoise",
            priority: 40,
            parameters: { kernel_size: 3 },
            mode: "enhancement",
            risk: "medium-high",
            reason: "تظهر مؤشرات ضوضاء نبضية؛ Median kernel=3 هو الخيار المحافظ."
        });
    } else if (hasNoise) {
        excluded.push({
            operation_id: "bilateral_denoise",
            risk: "medium-high",
            reason: "نوع الضوضاء يحتاج مراجعة يدوية قبل اختيار مرشح قوي."
        });
    }

    if ((codes.has("low_sharpness") || codes.has("very_low_sharpness")) && !hasNoise && preservation.level !== "high") {
        recommendations.push({
            operation_id: "sharpen",
            priority: 50,
            parameters: { amount: 0.25, sigma: 1.0 },
            mode: "enhancement",
            risk: "medium",
            reason: "تشير القياسات إلى انخفاض الحدة، ويستخدم Sharpen بإعداد محافظ."
        });
    }

    [
        ["histogram_equalization", "لم يعتمد Histogram Equalization للاستخدام التلقائي بسبب قوته.", "high"],
        ["global_threshold", "القيمة الثابتة للThreshold لا تعمم جيدًا على كل الوثائق.", "high"],
        ["morphological_opening", "Opening قد يزيل تفاصيل بنيوية صغيرة.", "high"],
        ["morphological_closing", "Closing قد يدمج تفاصيل متجاورة.", "high"]
    ].forEach(([operation_id, reason, risk]) => {
        excluded.push({ operation_id, reason, risk });
    });

    recommendations.sort((a, b) => a.priority - b.priority);
    return {
        recommendations,
        excluded_from_automatic: excluded,
        recommendation_summary: recommendations.length
            ? { needs_treatment: true, message: `تم تحديد ${recommendations.length} توصية مبدئية من الفحص الفوري.` }
            : { needs_treatment: false, message: "لم تظهر القياسات الفورية حاجة واضحة إلى معالجة تلقائية." }
    };
}

function analyzePixels(data, width, height) {
    const total = width * height;
    const gray = new Uint8Array(total);
    const histogram = new Uint32Array(256);
    let sum = 0;
    let sumSquares = 0;
    let darkClipped = 0;
    let brightClipped = 0;

    for (let i = 0, p = 0; i < data.length; i += 4, p += 1) {
        const value = Math.max(0, Math.min(255, Math.round(
            data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114
        )));
        gray[p] = value;
        histogram[value] += 1;
        sum += value;
        sumSquares += value * value;
        if (value <= 5) darkClipped += 1;
        if (value >= 250) brightClipped += 1;
    }

    const brightness = sum / Math.max(1, total);
    const variance = Math.max(0, (sumSquares / Math.max(1, total)) - brightness * brightness);
    const contrast = Math.sqrt(variance);
    const p5 = percentileFromHistogram(histogram, total, 0.05);
    const p50 = percentileFromHistogram(histogram, total, 0.50);
    const p95 = percentileFromHistogram(histogram, total, 0.95);

    let lapSum = 0;
    let lapSquares = 0;
    let lapCount = 0;
    let noiseSum = 0;
    let noiseP90Histogram = new Uint32Array(256);
    let noiseAffected = 0;
    let impulse = 0;
    let edgePixels = 0;

    for (let y = 1; y < height - 1; y += 1) {
        const row = y * width;
        for (let x = 1; x < width - 1; x += 1) {
            const p = row + x;
            const c = gray[p];
            const l = gray[p - 1];
            const r = gray[p + 1];
            const u = gray[p - width];
            const d = gray[p + width];

            const lap = (4 * c) - l - r - u - d;
            lapSum += lap;
            lapSquares += lap * lap;
            lapCount += 1;

            const localMean = (l + r + u + d) * 0.25;
            const residual = Math.min(255, Math.round(Math.abs(c - localMean)));
            noiseSum += residual;
            noiseP90Histogram[residual] += 1;
            if (residual >= 5) noiseAffected += 1;
            if (residual >= 100) impulse += 1;

            const gx = gray[p - width + 1] + 2 * r + gray[p + width + 1]
                - gray[p - width - 1] - 2 * l - gray[p + width - 1];
            const gy = gray[p + width - 1] + 2 * d + gray[p + width + 1]
                - gray[p - width - 1] - 2 * u - gray[p - width + 1];
            const magnitude = Math.abs(gx) + Math.abs(gy);
            const edgeThreshold = Math.max(70, Math.min(220, p50 * 0.9));
            if (magnitude >= edgeThreshold) edgePixels += 1;
        }
    }

    const interior = Math.max(1, lapCount);
    const lapMean = lapSum / interior;
    const sharpness = Math.max(0, (lapSquares / interior) - lapMean * lapMean);
    const noiseValue = noiseSum / interior;
    const noiseP90 = percentileFromHistogram(noiseP90Histogram, interior, 0.90);

    const gridCols = Math.min(12, Math.max(4, Math.round(width / 48)));
    const gridRows = Math.min(12, Math.max(4, Math.round(height / 48)));
    const blockMeans = [];

    for (let gy = 0; gy < gridRows; gy += 1) {
        const y0 = Math.floor(gy * height / gridRows);
        const y1 = Math.max(y0 + 1, Math.floor((gy + 1) * height / gridRows));
        for (let gx = 0; gx < gridCols; gx += 1) {
            const x0 = Math.floor(gx * width / gridCols);
            const x1 = Math.max(x0 + 1, Math.floor((gx + 1) * width / gridCols));
            let blockSum = 0;
            let blockCount = 0;
            for (let y = y0; y < y1; y += 1) {
                const offset = y * width;
                for (let x = x0; x < x1; x += 1) {
                    blockSum += gray[offset + x];
                    blockCount += 1;
                }
            }
            blockMeans.push(blockSum / Math.max(1, blockCount));
        }
    }

    const blockMean = blockMeans.reduce((a, b) => a + b, 0) / Math.max(1, blockMeans.length);
    const blockVariance = blockMeans.reduce((acc, value) => acc + (value - blockMean) ** 2, 0) / Math.max(1, blockMeans.length);
    const illuminationVariation = blockMean <= 1e-6 ? 0 : Math.sqrt(blockVariance) / blockMean;

    const metrics = {
        brightness: metric(Number(brightness.toFixed(3)), "gray_level"),
        contrast: metric(Number(contrast.toFixed(3)), "gray_level_std"),
        dynamic_range: metric(Number((p95 - p5).toFixed(3)), "gray_level"),
        sharpness: metric(Number(sharpness.toFixed(3)), "laplacian_variance_proxy"),
        noise: {
            value: Number(noiseValue.toFixed(3)),
            unit: "local_absolute_residual_proxy",
            p90: Number(noiseP90.toFixed(3)),
            affected_ratio: noiseAffected / interior,
            impulse_ratio: impulse / interior,
            interpretation: "instant_client_proxy"
        },
        illumination_variation: metric(Number(illuminationVariation.toFixed(4)), "coefficient_proxy"),
        edge_density: metric(Number((edgePixels / interior).toFixed(4)), "ratio_proxy"),
        dark_clipped_ratio: metric(Number((darkClipped / total).toFixed(4)), "ratio"),
        bright_clipped_ratio: metric(Number((brightClipped / total).toFixed(4)), "ratio"),
        weak_structure_ratio: metric(0, "ratio_proxy"),
        strong_structure_ratio: metric(0, "ratio_proxy"),
        weak_to_strong_ratio: metric(0, "ratio_proxy"),
        component_count: metric(0, "count_proxy"),
        small_component_ratio: metric(0, "ratio_proxy"),
        mean_component_area: metric(0, "pixels_proxy"),
        median_component_area: metric(0, "pixels_proxy"),
        foreground_ratio: metric(0, "ratio_proxy"),
        thin_structure_ratio: metric(0, "ratio_proxy"),
        skew_angle: metric(0, "degrees_proxy"),
        skew_confidence: metric(0, "ratio_proxy"),
        skew_line_count: metric(0, "count_proxy")
    };

    return metrics;
}

self.onmessage = async (event) => {
    const { file, ticket } = event.data || {};
    const started = performance.now();

    try {
        if (!(file instanceof Blob)) throw new Error("INVALID_FILE");

        const parsed = await parseDimensions(file);
        let sourceWidth = parsed?.width || 0;
        let sourceHeight = parsed?.height || 0;

        let bitmap;
        if (sourceWidth && sourceHeight) {
            const target = targetSize(sourceWidth, sourceHeight);
            bitmap = await createImageBitmap(file, {
                resizeWidth: target.width,
                resizeHeight: target.height,
                resizeQuality: "high"
            });
        } else {
            const full = await createImageBitmap(file);
            sourceWidth = full.width;
            sourceHeight = full.height;
            const target = targetSize(sourceWidth, sourceHeight);
            if (target.width === sourceWidth && target.height === sourceHeight) {
                bitmap = full;
            } else {
                const canvas = new OffscreenCanvas(target.width, target.height);
                canvas.getContext("2d", { alpha: false }).drawImage(full, 0, 0, target.width, target.height);
                full.close?.();
                bitmap = await createImageBitmap(canvas);
            }
        }

        const width = bitmap.width;
        const height = bitmap.height;
        const canvas = new OffscreenCanvas(width, height);
        const context = canvas.getContext("2d", { alpha: false, willReadFrequently: true });
        context.drawImage(bitmap, 0, 0, width, height);
        bitmap.close?.();

        const imageData = context.getImageData(0, 0, width, height);
        const metrics = analyzePixels(imageData.data, width, height);
        const diagnoses = buildDiagnoses(metrics);
        const preservation = buildPreservation(metrics);
        const plan = buildRecommendations(metrics, diagnoses, preservation);

        self.postMessage({
            ticket,
            ok: true,
            data: {
                analysis: {
                    dimensions: {
                        width: sourceWidth || width,
                        height: sourceHeight || height,
                        channels: 3
                    },
                    metrics,
                    mode: "instant_worker_proxy",
                    elapsed_ms: Number((performance.now() - started).toFixed(1)),
                    proxy: { width, height }
                },
                diagnoses,
                preservation_profile: preservation,
                ...plan
            }
        });
    } catch (error) {
        self.postMessage({
            ticket,
            ok: false,
            error: error?.message || "INSTANT_ANALYSIS_FAILED"
        });
    }
};
