# Operation Evaluation

## Purpose
<div dir="rtl">

تهدف هذه المرحلة إلى تقييم عمليات معالجة الصور المنفذة في Phase 7 على مجموعة ممثلة من صور الوثائق والمخطوطات، وتحديد حدود استخدامها وإعداداتها الأولية قبل السماح باستخدامها داخل Recommendation Engine أو Smart Pipeline.

لا يمثل التحسن العددي في Metric واحدة دليلًا كافيًا على نجاح المعالجة.

تم الاعتماد في هذه المرحلة على:

* quantitative indicators
* behavior across multiple document conditions
* comparison between candidate parameters
* preliminary structural observations
* نتائج Preservation Verification الأولية عند الحاجة

لا تمثل القرارات الناتجة من هذه المرحلة قيمًا مثالية لجميع الوثائق، وإنما Provisional Decisions مبنية على مجموعة التقييم الحالية.

---

## Evaluation Images

| Image                  | Main Condition              |
| ---------------------- | --------------------------- |
| 01_normal.jpg          | Normal document             |
| 02_dark.jpg            | Low brightness              |
| 03_low_contrast.jpg    | Low contrast                |
| 04_noisy.jpg           | Visible noise               |
| 05_uneven_lighting.jpg | Uneven illumination         |
| 06_fine_details.jpg    | Fine textual details        |
| 07_bleed_through.jpg   | Bleed-through boundary case |

---

## Decision Categories

### auto_candidate

العملية مرشحة للاستخدام التلقائي، ولكنها لا تعتبر آمنة بصورة مطلقة ويجب أن تمر لاحقًا عبر Preservation Verification.

### limited

العملية مفيدة في ظروف محددة فقط، ولا يجب تطبيقها بصورة عامة على جميع الوثائق.

### manual_only

العملية قد تكون مفيدة، لكن اختيارها أو اختيار Parameters الخاصة بها يحتاج قرارًا يدويًا أو سياقًا أكثر من المتاح حاليًا.

### reject

لا توجد أدلة كافية لتبرير استخدامها في الـMVP، أو أن مخاطرها أعلى من فائدتها الحالية.

---

# 1. CLAHE

## Purpose

تحسين التباين المحلي بصورة أكثر تحفظًا من Histogram Equalization العالمي.

## Tested Parameters

* `clipLimit=1.5`
* `clipLimit=2.0`
* `clipLimit=2.5`
* `tileGridSize=8`

## Observations

أظهر CLAHE تحسنًا واضحًا في الصور المظلمة ومنخفضة التباين.

في `02_dark.jpg` ارتفع التباين من:

`24.446`

إلى:

* `41.363` عند `clipLimit=1.5`
* `45.737` عند `clipLimit=2.0`
* `49.930` عند `clipLimit=2.5`

لكن زيادة `clipLimit` أدت أيضًا إلى زيادة Edge Density من:

`0.1157`

إلى:

* `0.1671`
* `0.1878`
* `0.2110`

وفي `04_noisy.jpg` ارتفع Noise Indicator من:

`1.0`

إلى:

`3.0`

عند الإعدادات الأقوى.

وفي `06_fine_details.jpg` ارتفعت Edge Density من:

`0.0467`

إلى:

* `0.0883` عند `1.5`
* `0.1359` عند `2.0`
* `0.1873` عند `2.5`

مما يشير إلى أن الإعدادات الأقوى قد تضخم التفاصيل والضوضاء والبنية غير المرغوبة.

وفي `07_bleed_through.jpg` زادت Edge Density تدريجيًا مع زيادة القوة، مما يعني أن CLAHE قد يعزز أيضًا النص المتسرب من الجهة الخلفية.

## Provisional Default

```text
clipLimit = 1.5
tileGridSize = 8
```

## Useful When

* low contrast
* dark documents
* moderate local illumination problems

## Avoid / Use Carefully When

* high noise
* strong bleed-through
* preservation-sensitive fine details

## Status

`auto_candidate`

ولكن بصورة مشروطة فقط.

## Risk

`medium`

---

# 2. Histogram Equalization

## Purpose

تحسين التباين بصورة عالمية.

## Tested Parameters

لا توجد Parameters متغيرة.

## Observations

أعطت Histogram Equalization زيادات كبيرة جدًا في Contrast وSharpness وEdge Density.

في `01_normal.jpg`:

```text
Contrast:
31.497 → 74.389

Sharpness:
1635.904 → 19121.109

Edge Density:
0.0742 → 0.2555
```

وفي `04_noisy.jpg`:

```text
Edge Density:
0.1029 → 0.2763
```

وفي `06_fine_details.jpg`:

```text
Edge Density:
0.0467 → 0.2418
```

وفي `07_bleed_through.jpg`:

```text
Edge Density:
0.0761 → 0.2714
```

هذه النتائج تشير إلى أن العملية شديدة القوة مقارنة بـCLAHE، وقد تضخم Texture الورق والضوضاء وBleed-through إضافة إلى النص.

## Provisional Default

لا يوجد.

## Useful When

قد تكون مفيدة يدويًا في حالات محددة تحتاج Contrast عالمي قوي.

## Avoid When

* normal images
* noisy images
* bleed-through
* fine-detail-sensitive documents

## Status

`manual_only`

## Risk

`high`

---

# 3. Median Denoising

## Purpose

تقليل بعض أنواع الضوضاء النقطية مع محاولة المحافظة على الحواف.

## Tested Parameters

* `kernel_size=3`
* `kernel_size=5`

## Observations

في `04_noisy.jpg`:

### Kernel 3

```text
Sharpness:
1051.394 → 651.299

Edge Density:
0.1029 → 0.0933
```

### Kernel 5

```text
Sharpness:
1051.394 → 456.462

Edge Density:
0.1029 → 0.0764
```

وفي `06_fine_details.jpg`:

### Kernel 3

```text
Sharpness:
723.920 → 392.662

Edge Density:
0.0467 → 0.0394
```

### Kernel 5

```text
Sharpness:
723.920 → 291.983

Edge Density:
0.0467 → 0.0326
```

أثبتت النتائج أن `kernel=5` يزيل بنية أكثر من `kernel=3`.

كما أن Median لم يزل جميع نقاط الضوضاء بصريًا في بعض الحالات، لكن رفع حجم Kernel يؤدي إلى خسارة أكبر في التفاصيل.

لذلك لا يعتبر بقاء بعض الضوضاء فشلًا إذا كان البديل هو فقد بنية أصلية.

## Provisional Default

```text
kernel_size = 3
```

## Useful When

* visible local noise
* salt-and-pepper-like degradation
* عندما تكون الضوضاء فعلًا مشكلة رئيسية

## Avoid / Use Carefully When

* fine details are highly important
* image is already clean
* weak text strokes

## Status

`limited`

## Risk

`medium-high`

---

# 4. Sharpening

## Purpose

زيادة وضوح التفاصيل باستخدام Unsharp Masking.

## Tested Parameters

* `amount=0.25`
* `amount=0.50`
* `amount=0.75`
* `kernel_size=3`

## Observations

في `06_fine_details.jpg`:

### Amount 0.25

```text
Sharpness:
723.920 → 992.809

Edge Density:
0.0467 → 0.0482
```

### Amount 0.50

```text
Sharpness:
723.920 → 1306.270

Edge Density:
0.0467 → 0.0497
```

زيادة Sharpness كانت واضحة، بينما بقيت Edge Density قريبة نسبيًا من الأصل.

لكن في `04_noisy.jpg` ارتفع Noise Indicator مع زيادة Amount:

```text
1.0 → 2.0 → 3.0
```

كما أن Bleed-through قد يصبح أكثر وضوحًا مع Sharpening.

لذلك تم اختيار أقل قيمة حققت تحسنًا واضحًا.

## Provisional Default

```text
amount = 0.25
kernel_size = 3
```

## Useful When

* low sharpness
* blurred-looking details
* no strong noise

## Avoid / Use Carefully When

* high noise
* strong bleed-through
* already sharp images

## Status

`limited`

## Risk

`medium`

---

# 5. Global Threshold

## Purpose

تحويل الصورة إلى Binary باستخدام قيمة Threshold ثابتة.

## Tested Parameters

* `100`
* `127`
* `160`

## Observations

أظهرت النتائج أن Threshold ثابت لا يعمم جيدًا عبر الوثائق.

في `03_low_contrast.jpg`:

```text
threshold=100
brightness_after = 255.0
contrast_after = 0.0
edge_density_after = 0.0
```

أي أن معظم المعلومات اختفت تقريبًا.

وفي `02_dark.jpg`:

```text
threshold=127
brightness_after = 5.691

threshold=160
brightness_after = 0.189
```

وهو سلوك شديد الحساسية للصورة المستخدمة.

هذا يثبت أن نفس القيمة لا تصلح كقرار عام لمجموعة وثائق مختلفة.

## Provisional Default

لا يوجد.

## Useful When

* manual experimentation
* user-controlled binary separation

## Avoid When

* automatic processing
* varying illumination
* diverse document collections

## Status

`manual_only`

## Risk

`high`

---

# 6. Otsu Threshold

## Purpose

اختيار Threshold عالمي تلقائي اعتمادًا على توزيع شدة الصورة.

## Tested Parameters

لا توجد Parameters يدوية.

## Observations

كان Otsu أكثر قابلية للتعميم من Global Threshold الثابت.

في `03_low_contrast.jpg` استطاع الاحتفاظ ببنية أكثر من Thresholds الثابتة.

لكن في الصور ذات Uneven Illumination لا يوجد دليل كافٍ لاعتباره حلًا عامًا، لأن Otsu ما يزال يعتمد Threshold عالميًا واحدًا.

## Provisional Default

Automatic Otsu selection.

## Useful When

* relatively uniform illumination
* binary separation when a single global threshold is reasonable

## Avoid / Use Carefully When

* strong uneven illumination
* complex backgrounds
* preservation-sensitive details

## Status

`limited`

## Risk

`medium`

---

# 7. Adaptive Threshold

## Purpose

إنشاء Threshold محلي لكل منطقة من الصورة، خصوصًا عند تغير الإضاءة.

## Tested Parameters

* `block_size=25`, `c=7`
* `block_size=35`, `c=11`
* `block_size=51`, `c=15`

## Observations

في `05_uneven_lighting.jpg` كان Illumination Variation في الأصل:

`0.5882`

وبعد Adaptive Threshold:

```text
25/7  → 0.1041
35/11 → 0.1036
51/15 → 0.1043
```

وكانت Edge Density:

```text
Original = 0.1479

25/7  = 0.1566
35/11 = 0.1281
51/15 = 0.1122
```

وفي `04_noisy.jpg`:

```text
Original = 0.1029

25/7  = 0.1305
35/11 = 0.1134
51/15 = 0.1053
```

مما يشير إلى أن `25/7` أكثر عرضة لتحويل Noise إلى بنية ثنائية.

وفي `06_fine_details.jpg`:

```text
Original = 0.0467

25/7  = 0.1315
35/11 = 0.0825
51/15 = 0.0612
```

وهذا يوضح أن الإعداد الأكثر حساسية محليًا قد يخلق كمية كبيرة من التفاصيل الثنائية الإضافية.

الإعداد `35/11` أعطى أفضل compromise حالي بين Uneven Illumination وNoise وFine Details.

## Provisional Default

```text
block_size = 35
c = 11
```

## Useful When

* uneven illumination
* local text/background separation
* binarization-oriented processing

## Avoid / Use Carefully When

* noisy images
* fine-detail-sensitive images
* when a normal enhanced color/grayscale image is desired

## Status

`limited`

ويعتبر Candidate للاستخدام التلقائي فقط داخل **Binarization Path** وليس كعملية Enhancement عامة.

## Risk

`medium-high`

---

# 8. Morphological Opening

## Purpose

إزالة مكونات صغيرة من البنية.

## Tested Parameters

* `kernel_size=3`
* `kernel_size=5`

## Observations

في `06_fine_details.jpg`:

### Kernel 3

```text
Sharpness:
723.920 → 429.367

Edge Density:
0.0467 → 0.0375
```

### Kernel 5

```text
Sharpness:
723.920 → 380.160

Edge Density:
0.0467 → 0.0341
```

وفي الصور الأخرى ظهر انخفاض مستمر في Sharpness وEdge Density مع زيادة حجم Kernel.

قد تساعد العملية في إزالة مكونات صغيرة، لكنها قد تزيل أيضًا نقاطًا أو خطوطًا أصلية دقيقة.

## Provisional Default

```text
kernel_size = 3
```

ولكن فقط في الاستخدام اليدوي.

## Useful When

* specific small structural noise
* controlled cleanup

## Avoid When

* fine-detail preservation is important
* automatic general treatment
* weak strokes

## Status

`manual_only`

## Risk

`high`

---

# 9. Morphological Closing

## Purpose

سد فجوات صغيرة وربط مكونات متجاورة.

## Tested Parameters

* `kernel_size=3`
* `kernel_size=5`

## Observations

في `01_normal.jpg`:

```text
Original Edge Density = 0.0742

K3 = 0.0466
K5 = 0.0008
```

وفي `05_uneven_lighting.jpg`:

```text
Original = 0.1479

K3 = 0.0978
K5 = 0.0449
```

وفي `04_noisy.jpg`:

```text
Original = 0.1029

K3 = 0.0853
K5 = 0.0409
```

وفي `06_fine_details.jpg`:

```text
Original = 0.0467

K3 = 0.0401
K5 = 0.0355
```

تظهر النتائج أن `kernel=5` قد يؤدي إلى تغير بنيوي قوي جدًا في بعض الوثائق.

حتى `kernel=3` يحتاج استخدامًا حذرًا بسبب احتمال دمج تفاصيل متجاورة.

## Provisional Default

```text
kernel_size = 3
```

للاستخدام اليدوي فقط.

## Useful When

* specific small gaps
* controlled manual intervention

## Avoid When

* fine details
* dense writing
* automatic treatment
* unknown document structure

## Status

### Kernel 3

`manual_only`

### Kernel 5

`reject` للاستخدام التلقائي في الـMVP.

## Risk

`high`

ويصبح `very high` مع Kernel أكبر.

---

# Noise Metric Limitation

أظهرت التجارب أن Noise Metric الحالية في `analyzer.py` ليست كافية لقياس كمية الضوضاء الفعلية بصورة دقيقة.

في عدة حالات أصبح:

```text
noise_after = 0
```

بعد Median أو Morphological Processing، مع بقاء بعض النقاط أو التشوهات بصريًا.

لذلك:

* لا يعني `noise=0` أن الصورة خالية فعليًا من الضوضاء.
* لا يجب معايرة Recommendation Engine اعتمادًا على هذه القيمة وحدها.
* يجب تحسين Noise Indicator في مرحلة لاحقة بدل الاكتفاء بتعديل Thresholds الحالية.

---

# Bleed-Through Boundary Case

تمت إضافة `07_bleed_through.jpg` كحالة Boundary Test وليس كحالة يدعي المشروع علاجها بصورة مستقلة.

أظهرت النتائج أن عمليات مثل CLAHE وHistogram Equalization وSharpening قد تزيد وضوح البنية الخلفية غير المرغوبة بالإضافة إلى النص الأمامي.

لذلك لا يدعي الـMVP وجود Bleed-Through Removal حقيقي.

تستخدم هذه الحالة لاكتشاف حدود عمليات Enhancement الحالية.

---

# Final Operation Matrix

| Operation                | Provisional Default     | Automatic              | Manual                | Main Use                    | Risk        |
| ------------------------ | ----------------------- | ---------------------- | --------------------- | --------------------------- | ----------- |
| CLAHE                    | `clip=1.5, grid=8`      | Conditional Candidate  | Yes                   | Contrast / dark images      | Medium      |
| Histogram Equalization   | —                       | No                     | Yes                   | Strong global contrast      | High        |
| Median Denoising         | `kernel=3`              | Limited / conditional  | Yes                   | Noise reduction             | Medium-High |
| Sharpening               | `amount=0.25, kernel=3` | Limited / conditional  | Yes                   | Low sharpness               | Medium      |
| Global Threshold         | —                       | No                     | Yes                   | Manual binary separation    | High        |
| Otsu Threshold           | Automatic               | Limited                | Yes                   | Uniform-light binarization  | Medium      |
| Adaptive Threshold       | `block=35, C=11`        | Binarization path only | Yes                   | Uneven illumination         | Medium-High |
| Morphological Opening    | `kernel=3`              | No                     | Yes                   | Specific structural cleanup | High        |
| Morphological Closing    | `kernel=3`              | No                     | Yes                   | Specific gap filling        | High        |
| Morphological Closing K5 | —                       | No                     | No for MVP automation | —                           | Very High   |

---

# Automatic Recommendation Eligibility

بناءً على التقييم الحالي، العمليات المؤهلة للدخول لاحقًا في Recommendation Engine ليست جميع عمليات Phase 7.

## Eligible with conditions

### CLAHE

يمكن اقتراحها عند:

* low contrast
* dark image

مع استخدام إعداد محافظ.

### Median Denoising

يمكن اقتراحها فقط عند وجود دليل كافٍ على Noise.

يجب تجنب استخدامها بصورة تلقائية على الصور الحساسة للتفاصيل ما لم تكن الضوضاء مشكلة فعلية.

### Sharpening

يمكن اقتراحها عند:

* low sharpness

مع شرط عدم وجود Noise قوي أو مؤشرات تجعل تضخيم الحواف خطرًا.

### Otsu Threshold

يمكن اقتراحها بصورة محدودة في مسار Binarization عندما تكون الإضاءة متجانسة نسبيًا.

### Adaptive Threshold

يمكن اقتراحها في Binarization Path عند:

* uneven illumination

ولا تعتبر Enhancement عامة للصورة الأصلية.

---

# Manual-Only Operations

* Histogram Equalization
* Global Threshold
* Morphological Opening
* Morphological Closing

هذه العمليات لن يختارها Smart Pipeline بصورة عامة في الـMVP.

---

# Rejected Automatic Configuration

```text
Morphological Closing
kernel_size = 5
```

لا يستخدم تلقائيًا في الـMVP بسبب تغيرات بنيوية قوية ومتكررة ظهرت عبر مجموعة الاختبار.

---

# Core Evaluation Decision

تم اعتماد المبدأ التالي:

> الهدف ليس تحقيق أكبر Contrast أو أكبر Sharpness أو إزالة كل Noise، وإنما استخدام أقل معالجة تحقق فائدة واضحة مع أقل تغير بنيوي ممكن.

وبالتالي:

```text
More processing ≠ Better processing
```

وتعتبر المحافظة على التفاصيل شرطًا موازيًا للتحسين وليس مرحلة ثانوية بعده.

---

# Important Limitations

1. النتائج مبنية على مجموعة تقييم محدودة ولا تثبت التعميم على جميع المخطوطات والوثائق.

2. Provisional Defaults ليست Optimal Parameters عالمية.

3. المؤشرات العددية لا تستبدل الفحص البصري أو Preservation Verification.

4. Binarization تغير طبيعة الصورة بصورة أساسية، ولذلك لا تفسر Metrics الخاصة بها بنفس طريقة Enhancement التقليدية.

5. Connected Components وEdges لا تمثل حروفًا أو معنى لغويًا.

6. لا يوجد OCR أو فهم للنص داخل مرحلة التقييم.

7. لا يدعي المشروع حاليًا علاج Bleed-through بصورة مستقلة.

8. Noise Metric الحالية تحتاج تحسينًا قبل استخدامها كإشارة قوية لاتخاذ القرار.

---

# Phase 8 Conclusion

نجحت Phase 8 في تحويل قائمة Processing Operations من مجرد خوارزميات تعمل برمجيًا إلى عمليات ذات:

* purpose
* provisional parameters
* supported conditions
* known risks
* automatic-use eligibility
* manual-use restrictions

وبذلك أصبح من الممكن بناء Recommendation Engine دون افتراض أن كل عملية معالجة مناسبة لكل صورة.

العمليات التلقائية المستقبلية ستبقى خاضعة لـPreservation Verification قبل قبول النتيجة النهائية.
