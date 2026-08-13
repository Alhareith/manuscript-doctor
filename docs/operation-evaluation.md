# Operation Evaluation

## Purpose

تهدف هذه المرحلة إلى تقييم عمليات معالجة الصور المنفذة في Phase 7 على مجموعة ممثلة من صور المخطوطات، وتحديد حدود استخدامها وإعداداتها الأولية قبل السماح باستخدامها داخل Recommendation Engine أو Smart Pipeline.

لا يمثل التحسن العددي في Metric واحدة دليلًا كافيًا على نجاح المعالجة.

يتم الاعتماد على:

- quantitative indicators
- visual comparison
- behavior across multiple images
- preliminary detail-loss observations

Preservation Verification الرسمية لم تنفذ بعد.

---

## Evaluation Images

| Image | Main Condition |
|---|---|
| 01_normal | Normal |
| 02_dark | Low brightness |
| 03_low_contrast | Low contrast |
| 04_noisy | Visible noise |
| 05_uneven_lighting | Uneven illumination |
| 06_fine_details | Fine textual details |

---

## Decision Categories

### auto_candidate
العملية مرشحة للاستخدام التلقائي بعد اجتياز Preservation Verification.

### manual_only
العملية مفيدة، لكن لا توجد أدلة كافية لاستخدامها تلقائيًا.

### limited
العملية مناسبة فقط لحالات محددة.

### reject
لا توجد قيمة كافية حاليًا لتبرير إبقائها ضمن المسار الأساسي.

---

## CLAHE

### Tested Parameters

- clipLimit 1.5
- clipLimit 2.0
- clipLimit 2.5
- tileGridSize 8

### Observations

يتم تعبئتها بعد التجربة.

### Provisional Default

غير معتمد بعد.

### Status

غير معتمد بعد.

---

## Histogram Equalization

### Observations

يتم تعبئتها بعد التجربة.

### Status

غير معتمد بعد.

---

## Median Denoising

### Tested Parameters

- kernel 3
- kernel 5

### Observations

يتم تعبئتها بعد التجربة.

### Provisional Default

غير معتمد بعد.

### Status

غير معتمد بعد.

---

## Sharpening

### Tested Parameters

- amount 0.25
- amount 0.50
- amount 0.75

### Observations

يتم تعبئتها بعد التجربة.

### Provisional Default

غير معتمد بعد.

### Status

غير معتمد بعد.

---

## Global Threshold

### Tested Parameters

- 100
- 127
- 160

### Observations

يتم تعبئتها بعد التجربة.

### Status

غير معتمد بعد.

---

## Otsu Threshold

### Observations

يتم تعبئتها بعد التجربة.

### Status

غير معتمد بعد.

---

## Adaptive Threshold

### Tested Parameters

- block 25 / C 7
- block 35 / C 11
- block 51 / C 15

### Observations

يتم تعبئتها بعد التجربة.

### Provisional Default

غير معتمد بعد.

### Status

غير معتمد بعد.

---

## Morphological Opening

### Tested Parameters

- kernel 3
- kernel 5

### Observations

يتم تعبئتها بعد التجربة.

### Status

غير معتمد بعد.

---

## Morphological Closing

### Tested Parameters

- kernel 3
- kernel 5

### Observations

يتم تعبئتها بعد التجربة.

### Status

غير معتمد بعد.

---

## Final Operation Matrix

| Operation | Default | Automatic | Manual | Main Use | Risk |
|---|---|---|---|---|---|
| CLAHE | TBD | TBD | TBD | Contrast | TBD |
| Histogram Equalization | — | TBD | TBD | Contrast | TBD |
| Median Denoising | TBD | TBD | TBD | Noise | TBD |
| Sharpening | TBD | TBD | TBD | Detail | TBD |
| Global Threshold | TBD | TBD | TBD | Separation | TBD |
| Otsu | — | TBD | TBD | Separation | TBD |
| Adaptive Threshold | TBD | TBD | TBD | Separation | TBD |
| Opening | TBD | TBD | TBD | Structure | TBD |
| Closing | TBD | TBD | TBD | Structure | TBD |

---

## Important Limitation

القرارات الناتجة من هذه المرحلة تظل Provisional حتى تمر العمليات لاحقًا عبر Preservation Verification التي تقارن الصورة الأصلية بالنتيجة باستخدام مؤشرات بنيوية مستقلة.