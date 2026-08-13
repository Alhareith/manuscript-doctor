docs/decisions.md

<div dir="rtl" align="right">

# 📌 Manuscript Doctor — سجل القرارات الهندسية

> **الغرض من الوثيقة:** تسجيل القرارات التي تؤثر فعليًا على تصميم المشروع أو تنفيذه، مع توضيح سبب كل قرار وحدوده.
> **لا تستخدم هذه الوثيقة كقائمة متطلبات أو شرح معماري؛ المتطلبات في `requirements.md` والمعمارية في `architecture.md`.**

---

## 🧭 طريقة قراءة السجل

كل قرار يستخدم البنية التالية:

| الحقل      | المعنى                                      |
| ---------- | ------------------------------------------- |
| **الحالة** | هل القرار معتمد، مؤقت، مؤجل، أو ملغى        |
| **القرار** | ما الذي تم اختياره تحديدًا                  |
| **السبب**  | لماذا تم اختياره                            |
| **الأثر**  | ما الذي يتأثر به داخل المشروع               |
| **الحدود** | ما الذي لا يعنيه القرار أو متى يمكن مراجعته |

### حالات القرارات

* `✅ معتمد` — قرار ساري ويجب الالتزام به.
* `🟡 معتمد مؤقتًا` — قرار عملي حالي يحتاج معايرة أو تقييم لاحق.
* `⏳ مؤجل` — فكرة صحيحة لكن ليست ضمن التنفيذ الحالي.
* `❌ ملغى` — قرار سابق لم يعد مستخدمًا.

---

# 1. هوية المشروع ونطاقه

## DEC-001 — تعريف Manuscript Doctor

**الحالة:** ✅ معتمد

### القرار

Manuscript Doctor هو:

> نظام ويب لتشخيص ومعالجة صور المخطوطات، يختار المعالجة بناءً على حالة الصورة، ثم يتحقق من أثرها على التفاصيل الأصلية قبل اعتماد النتيجة.

### السبب

المشروع يجب أن يقدم قيمة تتجاوز تطبيق مجموعة فلاتر تقليدية.

### الأثر

يجب أن تخدم جميع الوظائف المسار:

```text id="dec001-flow"
Diagnose
   ↓
Treat
   ↓
Preserve
   ↓
Verify
```

### الحدود

لا يعني ذلك أن النظام:

* يفهم النص لغويًا.
* يعيد الحالة التاريخية الأصلية للمخطوطة.
* يضمن عدم فقد أي معلومة.

---

## DEC-002 — اعتماد فلسفة Diagnose → Treat → Preserve → Verify

**الحالة:** ✅ معتمد

### القرار

تعتمد هوية النظام على أربع مراحل مفاهيمية:

1. **Diagnose** — تشخيص حالة الصورة.
2. **Treat** — تطبيق معالجة مناسبة.
3. **Preserve** — مراعاة المحافظة على التفاصيل.
4. **Verify** — تقييم أثر المعالجة بعد التنفيذ.

### السبب

هذه الفلسفة تعبر بوضوح عن القيمة الأساسية للمشروع وتمنع تحوله إلى محرر صور تقليدي.

---

## DEC-003 — المشروع Rule-Based وليس AI

**الحالة:** ✅ معتمد

### القرار

Diagnosis وRecommendation وSmart Pipeline تعتمد في الـMVP على قواعد واضحة ومقاييس معالجة صور تقليدية.

### السبب

لا يوجد نموذج تعلم آلي داخل النسخة الحالية.

### الأثر

لا تستخدم عبارات مثل:

```text id="dec003-no"
AI Diagnosis
AI Enhancement
AI Recommendation
```

إلا إذا تمت إضافة نموذج فعلي مستقبلًا وتقييمه بصورة مستقلة.

---

## DEC-004 — OCR خارج نطاق الـMVP

**الحالة:** ⏳ مؤجل

### القرار

لا يتم تنفيذ OCR أو استخراج النص في النسخة الأساسية.

### السبب

OCR يضيف مشكلة مستقلة تشمل:

* اختيار محرك أو نموذج.
* بيانات لغوية.
* تقييم CER/WER.
* معالجة أخطاء التعرف.

وهذا لا يخدم الهدف الأساسي الحالي مباشرة.

---

## DEC-005 — YOLO وDeep Learning خارج نطاق الـMVP

**الحالة:** ⏳ مؤجل

### القرار

لا تستخدم نماذج YOLO أو Deep Learning داخل Manuscript Doctor في النسخة الأساسية.

### السبب

قيمة المشروع الحالية يمكن تحقيقها بوضوح باستخدام معالجة الصور التقليدية، وإضافة نموذج تعلم آلي الآن ستزيد النطاق دون ضرورة.

---

## DEC-006 — لا توجد قاعدة بيانات أو حسابات مستخدمين

**الحالة:** ✅ معتمد

### القرار

الـMVP لا يحتوي:

* Authentication.
* User Accounts.
* Database.
* Permanent History.

### السبب

التطبيق محلي وتجريبي، ولا توجد حاجة وظيفية حقيقية لهذه الطبقات حاليًا.

---

# 2. التقنيات الأساسية

## DEC-007 — استخدام Python + Flask

**الحالة:** ✅ معتمد

### القرار

يستخدم Backend:

```text id="dec007-stack"
Python
+
Flask
```

### السبب

Flask بسيط وخفيف ومناسب لربط HTTP مع OpenCV دون إضافة طبقات غير ضرورية.

---

## DEC-008 — استخدام OpenCV + NumPy لمعالجة الصور

**الحالة:** ✅ معتمد

### القرار

يتم تنفيذ التحليل والمعالجة باستخدام:

```text id="dec008-stack"
OpenCV
+
NumPy
```

### السبب

يوفران العمليات والمصفوفات المطلوبة للمشروع دون الحاجة إلى إطار أكبر.

---

## DEC-009 — استخدام HTML + CSS + JavaScript للواجهة

**الحالة:** ✅ معتمد

### القرار

Frontend يعتمد:

```text id="dec009-stack"
HTML
+
CSS
+
JavaScript
```

دون React أو Vue أو Angular.

### السبب

الواجهة المطلوبة لا تحتاج Framework Frontend، والحل المباشر أبسط وأكثر وضوحًا للمشروع.

---

## DEC-010 — CSS مخصص هو الخيار الافتراضي

**الحالة:** ✅ معتمد

### القرار

يستخدم المشروع CSS مخصصًا في الواجهة الأساسية.

### السبب

التصميم المطلوب يمكن تنفيذه دون الاعتماد على Framework إضافي.

### الحدود

يمكن اعتماد Bootstrap أو Tailwind مستقبلًا فقط إذا ظهرت حاجة واضحة ومبررة، ولا يستخدم الاثنان معًا.

---

# 3. مبادئ المعمارية

## DEC-011 — Backend هو Source of Truth

**الحالة:** ✅ معتمد

### القرار

Backend هو المصدر الوحيد لـ:

* Metrics.
* Diagnostic Thresholds.
* Diagnosis.
* Preservation Profile.
* Recommendation Rules.
* Operation Registry.
* Pipeline Rules.
* Preservation Metrics.
* Preservation Assessment.
* Warnings.

### السبب

منع اختلاف المنطق بين Python وJavaScript.

### الأثر

لا تكرر قواعد التشخيص أو التوصية داخل `main.js`.

---

## DEC-012 — فصل المسؤوليات بين وحدات المعالجة

**الحالة:** ✅ معتمد

### القرار

توزع المسؤوليات كالتالي:

| الملف             | المسؤولية                                      |
| ----------------- | ---------------------------------------------- |
| `app.py`          | HTTP والتحقق وتنسيق الطلبات                    |
| `analyzer.py`     | Examination + Diagnosis + Preservation Profile |
| `recommender.py`  | Recommendation                                 |
| `operations.py`   | عمليات معالجة الصور                            |
| `pipeline.py`     | Smart Pipeline                                 |
| `preservation.py` | Preservation Verification                      |

### السبب

الحفاظ على وضوح الكود وقابلية الاختبار والتوسع.

---

## DEC-013 — لا خوارزميات معالجة داخل `app.py`

**الحالة:** ✅ معتمد

### القرار

لا يحتوي `app.py` على خوارزميات OpenCV الخاصة بالتحليل أو المعالجة.

### السبب

`app.py` منسق HTTP وليس Processing Module.

---

## DEC-014 — Analyzer لا يقرر Treatment

**الحالة:** ✅ معتمد

### القرار

`analyzer.py` يجيب عن:

> ماذا نلاحظ في الصورة؟

ولا يجيب عن:

> ماذا يجب أن نطبق؟

### السبب

التوصية مسؤولية `recommender.py`.

### مثال غير مسموح

```python id="dec014-bad"
if low_contrast:
    return "clahe"
```

داخل Analyzer.

---

## DEC-015 — Preservation Verification منفصلة عن Analyzer

**الحالة:** ✅ معتمد

### القرار

تحليل الصورة الأصلية يتم داخل `analyzer.py`.

أما مقارنة:

```text id="dec015-flow"
Original
+
Processed Result
```

فتتم داخل `preservation.py`.

### السبب

الوظيفتان مختلفتان:

```text id="dec015-difference"
Analyzer
→ حالة الأصل

Preservation
→ أثر المعالجة
```

---

# 4. إدارة الصور والهوية

## DEC-016 — الصورة الأصلية Immutable

**الحالة:** ✅ معتمد

### القرار

لا يتم الكتابة فوق Original في أي مرحلة.

### السبب

الحفاظ على مرجع ثابت للمقارنة والتقييم وإعادة تجربة العمليات.

### الأثر

كل Result تحفظ كملف مستقل.

---

## DEC-017 — كل Manual Operation تبدأ من Original

**الحالة:** ✅ معتمد

### القرار

إذا طبق المستخدم عمليتين منفصلتين:

```text id="dec017-correct"
Original → CLAHE → Result A
Original → Median → Result B
```

وليس:

```text id="dec017-wrong"
Original
→ CLAHE
→ Median
→ Result
```

إلا إذا كانت السلسلة جزءًا معلنًا من Smart Pipeline.

### السبب

منع تراكم تأثيرات غير مقصودة وجعل المقارنة عادلة.

---

## DEC-018 — Smart Pipeline سلسلة مقصودة

**الحالة:** ✅ معتمد

### القرار

Smart Pipeline هي الاستثناء الوحيد الذي يسمح بتطبيق عمليات متتابعة على ناتج الخطوة السابقة.

### السبب

السلسلة هنا مخططة ومفسرة وليست نتيجة نقرات يدوية متراكمة.

---

## DEC-019 — استخدام `image_id` بدل File Path

**الحالة:** ✅ معتمد

### القرار

Frontend يتعامل مع معرف مثل:

```text id="dec019-id"
917a66f45b08454c9ab34cb7658f4060
```

ولا يتعامل مع:

```text id="dec019-path"
C:\...
storage\uploads\...
```

### السبب

فصل واجهة المستخدم عن نظام الملفات وتقليل مخاطر الوصول غير المسموح.

---

## DEC-020 — استخدام `result_id` مستقل لكل نتيجة

**الحالة:** ✅ معتمد

### القرار

كل Result تحصل على معرف مستقل.

### السبب

السماح بوجود أكثر من نتيجة لنفس الصورة دون الكتابة فوق نتائج سابقة.

---

## DEC-021 — استخدام UUID لأسماء الملفات الداخلية

**الحالة:** ✅ معتمد

### القرار

يولد Backend أسماء التخزين باستخدام UUID.

### السبب

* منع تصادم الأسماء.
* عدم الاعتماد على Filename القادم من المستخدم.
* توفير معرفات غير مرتبطة بمسارات الجهاز.

---

## DEC-022 — عدم استخدام Global Current Image

**الحالة:** ✅ معتمد

### القرار

لا يستخدم النظام:

```python id="dec022-bad"
current_image = ...
```

كحالة عامة للتطبيق.

### السبب

المتغير العالمي:

* غير آمن مع أكثر من Request.
* يجعل الاختبار أصعب.
* يسبب خلطًا بين الصور.

الهوية تعتمد على `image_id`.

---

# 5. رفع الصور والتحقق منها

## DEC-023 — قبول JPG وJPEG وPNG فقط في الـMVP

**الحالة:** ✅ معتمد

### القرار

الامتدادات المدعومة:

```text id="dec023-types"
.jpg
.jpeg
.png
```

### السبب

هذه الصيغ تغطي الاستخدام الأساسي دون توسيع نطاق التحقق بلا حاجة.

---

## DEC-024 — الامتداد وحده لا يثبت صحة الصورة

**الحالة:** ✅ معتمد

### القرار

بعد التحقق من Extension يجب محاولة فك الصورة بواسطة OpenCV.

### السبب

يمكن تغيير اسم ملف عادي إلى:

```text id="dec024-fake"
fake.jpg
```

دون أن يصبح صورة.

---

## DEC-025 — التحقق من الصورة قبل حفظها

**الحالة:** ✅ معتمد

### القرار

المسار:

```text id="dec025-flow"
Receive Bytes
    ↓
Decode
    ↓
Validate
    ↓
Save Original
```

### السبب

عدم إدخال ملفات تالفة أو مزيفة إلى Runtime Storage.

---

## DEC-026 — حفظ Original Bytes دون إعادة Encoding

**الحالة:** ✅ معتمد

### القرار

بعد نجاح التحقق تحفظ البايتات التي رفعها المستخدم نفسها.

### السبب

إعادة Encoding قد:

* تغير جودة JPEG.
* تغير Metadata.
* تنتج اختلافًا قبل بدء المعالجة.

وهذا يخالف مبدأ Original Immutable.

---

## DEC-027 — استخدام حدين لحماية رفع الصور

**الحالة:** ✅ معتمد

### القرار

يطبق النظام:

```text id="dec027-limits"
MAX_UPLOAD_SIZE = 20 MB

MAX_IMAGE_PIXELS = 30,000,000
```

### السبب

حجم الملف المضغوط لا يمثل وحده مقدار الذاكرة المستخدمة بعد فك الصورة.

### الحدود

يمكن تعديل القيم لاحقًا إذا أظهرت الاختبارات حاجة حقيقية لذلك.

---

## DEC-028 — عدم استخدام قاعدة بيانات لربط IDs بالملفات

**الحالة:** ✅ معتمد

### القرار

في الـMVP يتم البحث عن الملف داخل مجلد Runtime المسموح باستخدام UUID.

### السبب

هذا الحل:

* بسيط.
* كافٍ للمشروع المحلي.
* لا يحتاج Database فقط من أجل Metadata صغيرة.

### متى يراجع؟

إذا احتاج المشروع:

* تاريخ نتائج دائم.
* مستخدمين.
* Metadata كثيرة.
* نشر متعدد المستخدمين.

---

# 6. API والعقود

## DEC-029 — اعتماد Unified JSON Response

**الحالة:** ✅ معتمد

### القرار

كل API Response تستخدم:

```json id="dec029-response"
{
  "success": true,
  "message": "...",
  "data": {},
  "error": null
}
```

أو عند الفشل:

```json id="dec029-error"
{
  "success": false,
  "message": "...",
  "data": null,
  "error": {
    "code": "...",
    "details": null
  }
}
```

### السبب

تبسيط تعامل Frontend مع جميع Endpoints.

---

## DEC-030 — عدم إنشاء Route لكل Operation

**الحالة:** ✅ معتمد

### القرار

تستخدم العمليات Route واحدة:

```text id="dec030-route"
POST /api/images/<image_id>/operations
```

ويحدد الطلب:

```json id="dec030-request"
{
  "operation": "clahe"
}
```

### السبب

منع تضخم Routes وإبقاء إضافة العمليات مستقلة عن هيكل الـAPI.

---

## DEC-031 — استخدام Operation Registry

**الحالة:** ✅ معتمد

### القرار

يرسل المستخدم `operation_id` فقط.

ويتم تحويله داخل Backend إلى Function معتمدة.

### السبب

منع تنفيذ دالة عشوائية قادمة من Request.

---

## DEC-032 — Frontend لا يرسل Python Function Name

**الحالة:** ✅ معتمد

### القرار

لا يقبل Backend Requests مثل:

```json id="dec032-bad"
{
  "function": "some_python_function"
}
```

### السبب

التحكم الكامل بالوظائف المسموحة يجب أن يبقى داخل Backend.

---

# 7. تجربة المستخدم

## DEC-033 — واجهة الصفحة تتمحور حول التشخيص لا الفلاتر

**الحالة:** ✅ معتمد

### القرار

الأولوية البصرية:

```text id="dec033-flow"
Upload
↓
Examination
↓
Diagnosis
↓
Preservation Profile
↓
Treatment Plan
↓
Treatment
↓
Preservation Verification
↓
Comparison
```

ولا تبدأ الصفحة بـFilter Gallery.

### السبب

القيمة الأساسية للمشروع هي دعم قرار المعالجة.

---

## DEC-034 — استخدام Single-Page Workflow

**الحالة:** ✅ معتمد

### القرار

المسار الأساسي للمستخدم يتم داخل صفحة واحدة.

### السبب

تقليل التنقل والحفاظ على وضوح Before/After وحالة الصورة الحالية.

---

## DEC-035 — تنظيم Manual Operations حسب المشكلة

**الحالة:** ✅ معتمد

### القرار

تعرض العمليات مستقبلًا ضمن مجموعات مثل:

* Contrast & Lighting.
* Noise Reduction.
* Detail Enhancement.
* Thresholding.
* Morphology.

### السبب

المستخدم يحتاج فهم **لماذا يستخدم العملية** أكثر من رؤية قائمة أسماء تقنية.

---

## DEC-036 — Preservation Verification جزء أساسي من UX

**الحالة:** ✅ معتمد

### القرار

بعد كل معالجة مكتملة يجب أن تحتوي تجربة المستخدم على مساحة لعرض Preservation Assessment عند توفرها.

### السبب

هذه الوظيفة جزء من هوية Manuscript Doctor وليست إضافة ثانوية.

---

## DEC-037 — Manual Operations تخضع للتقييم أيضًا

**الحالة:** ✅ معتمد

### القرار

Preservation Verification لا تقتصر على Smart Pipeline.

المسار:

```text id="dec037-flow"
Original
↓
Manual Operation
↓
Result
↓
Preservation Verification
```

### السبب

يمكن أن تكون Manual Operation عدوانية أيضًا.

---

# 8. Examination & Diagnosis

## DEC-038 — استخدام Grayscale كأساس للمقاييس الحالية

**الحالة:** ✅ معتمد

### القرار

تحسب المقاييس الحالية على نسخة Grayscale من الصورة.

### السبب

Brightness وContrast وSharpness والحواف الحالية تعتمد أساسًا على شدة الإضاءة ولا تحتاج معلومات اللون.

### الحدود

لا يعني القرار أن اللون غير مهم دائمًا.

يمكن إضافة Color Metrics مستقبلًا إذا ظهرت حاجة مبررة.

---

## DEC-039 — اعتماد مجموعة Metrics محدودة وواضحة

**الحالة:** ✅ معتمد

### القرار

المقاييس الأساسية الحالية:

1. Brightness.
2. Contrast.
3. Dynamic Range.
4. Sharpness Indicator.
5. Noise Indicator.
6. Illumination Variation.
7. Edge Density.

### السبب

الأولوية لمقاييس يمكن تعريفها وشرحها واختبارها بدل إضافة عدد كبير من المؤشرات.

---

## DEC-040 — Brightness باستخدام Mean Grayscale

**الحالة:** ✅ معتمد

### القرار

يحسب Brightness كمعدل قيم Grayscale.

### السبب

مقياس مباشر وبسيط للسلوك المطلوب في هذه المرحلة.

### الحدود

متوسط السطوع لا يكشف وحده عدم تجانس الإضاءة.

لهذا يوجد Illumination Variation كمقياس منفصل.

---

## DEC-041 — Contrast باستخدام Standard Deviation

**الحالة:** ✅ معتمد

### القرار

يستخدم Standard Deviation لقيم Grayscale كمؤشر Contrast.

### السبب

يعبر عن مقدار انتشار درجات الصورة حول المتوسط بطريقة بسيطة وقابلة للاختبار.

---

## DEC-042 — Dynamic Range باستخدام P95 − P5

**الحالة:** ✅ معتمد

### القرار

يحسب Dynamic Range من:

```text id="dec042-formula"
95th percentile
-
5th percentile
```

### السبب

أكثر مقاومة للقيم الشاذة من استخدام:

```text id="dec042-bad"
max - min
```

---

## DEC-043 — Sharpness باستخدام Variance of Laplacian

**الحالة:** ✅ معتمد

### القرار

يستخدم:

```text id="dec043-method"
Variance of Laplacian
```

كمؤشر تقريبي للحدة.

### السبب

حل بسيط وشائع لاكتشاف انخفاض الحدة والحواف.

### الحدود

القيمة تتأثر أيضًا:

* بمحتوى الصورة.
* بالدقة.
* بالضوضاء.

لذلك لا تستخدم كحقيقة مطلقة عن جودة الصورة.

---

## DEC-044 — Noise Metric هي Indicator وليست قياسًا مطلقًا

**الحالة:** ✅ معتمد

### القرار

يستخدم الفرق المحلي بين Original Grayscale وMedian-smoothed version كمؤشر تقريبي للضوضاء.

### السبب

الحل بسيط ويعطي إشارة قابلة للمقارنة دون بناء Noise Model معقد.

### الحدود

قد تعتبر بعض التفاصيل الدقيقة تغيرات محلية أيضًا.

لذلك يستخدم المصطلح:

> **Noise Indicator**

---

## DEC-045 — قياس Illumination Variation منفصل عن Brightness

**الحالة:** ✅ معتمد

### القرار

ينشئ النظام خريطة إضاءة منخفضة التردد باستخدام Gaussian Blur واسع، ثم يقيس تغيرها النسبي.

### السبب

قد يكون متوسط Brightness طبيعيًا رغم وجود:

```text id="dec045-example"
جانب مظلم
+
جانب شديد الإضاءة
```

في الصفحة نفسها.

---

## DEC-046 — Edge Density مؤشر بنيوي فقط

**الحالة:** ✅ معتمد

### القرار

تستخدم Canny Edge Density كمؤشر على كثافة الحواف.

### السبب

تساعد في تكوين وصف أولي للبنية والتفاصيل.

### الحدود

Edge Density:

* لا تعني نسبة النص.
* لا تحدد معنى الحافة.
* يمكن أن تتأثر بالضوضاء والخلفية.

---

# 9. Thresholds والتشخيص

## DEC-047 — فصل Metrics عن Diagnosis Rules

**الحالة:** ✅ معتمد

### القرار

يتم:

```text id="dec047-flow"
Calculate Metrics
       ↓
Diagnosis Rules
```

في مرحلتين منفصلتين منطقيًا.

### السبب

يسمح بتعديل Thresholds دون تغيير خوارزمية القياس.

---

## DEC-048 — Diagnostic Thresholds الحالية Initial Heuristics

**الحالة:** 🟡 معتمد مؤقتًا

### القرار

القيم المستخدمة حاليًا لتصنيف:

* Brightness.
* Contrast.
* Sharpness.
* Noise.
* Illumination Variation.

هي **عتبات أولية**.

### السبب

يحتاج النظام إلى سلوك مبدئي قابل للاختبار قبل اكتمال التقييم التجريبي.

### الشرط

يجب تقييمها لاحقًا على صور المخطوطات الفعلية قبل تثبيتها نهائيًا.

---

## DEC-049 — لا تعدل Threshold لمجرد إصلاح صورة واحدة

**الحالة:** ✅ معتمد

### القرار

أي تعديل للعتبات يجب أن يعتمد على سلوك مجموعة صور متنوعة.

### السبب

منع Overfitting يدوي للخوارزمية على صورة محددة.

### التسلسل الصحيح

```text id="dec049-flow"
هل Metric تتصرف منطقيًا؟
       ↓
اختبار عدة صور
       ↓
مراجعة Threshold
       ↓
تعديل مبرر
```

---

# 10. Preservation Profile

## DEC-050 — Preservation Profile تقدير قبل المعالجة

**الحالة:** ✅ معتمد

### القرار

يتم تكوين Preservation Profile من خصائص الصورة الأصلية.

### الهدف

الإجابة تقريبًا عن:

> ما مقدار الحذر المقترح أثناء معالجة هذه الصورة؟

### المستويات الحالية

```text id="dec050-levels"
low
moderate
high
```

---

## DEC-051 — Preservation Profile ليس Preservation Verification

**الحالة:** ✅ معتمد

### القرار

لا يتم استخدام المصطلحين بالتبادل.

```text id="dec051-difference"
Profile
→ Before Treatment

Verification
→ After Treatment
```

### السبب

الأول تقدير مسبق.

الثاني مقارنة فعلية بين Original وResult.

---

## DEC-052 — Preservation Profile يستخدم Heuristic Interpretation

**الحالة:** ✅ معتمد

### القرار

تحتوي النتيجة على معنى واضح بأنها:

```text id="dec052-value"
heuristic
```

### السبب

لا توجد Ground Truth تسمح باعتبار المستوى قياسًا مطلقًا لحساسية المخطوطة.

---

# 11. Recommendation Engine

## DEC-053 — Recommendation منفصلة عن Diagnosis

**الحالة:** ✅ معتمد

### القرار

لا تربط Operation مباشرة داخل Analyzer.

المسار:

```text id="dec053-flow"
Metrics
↓
Diagnosis
↓
Preservation Profile
↓
Recommender
↓
Treatment Recommendation
```

### السبب

التشخيص يصف الحالة، بينما Recommendation تقترح الإجراء.

---

## DEC-054 — كل Recommendation يجب أن تكون Explainable

**الحالة:** ✅ معتمد

### القرار

أي Recommendation يجب أن تحتوي على:

* `operation_id`
* عنوان.
* سبب.
* Priority عند الحاجة.

### السبب

المستخدم يجب أن يعرف لماذا تم اقتراح العملية.

---

## DEC-055 — Preservation Profile يمكن أن يؤثر على التوصية

**الحالة:** ✅ معتمد

### القرار

إذا كانت الصورة ذات حساسية مرتفعة، يمكن للـRecommender:

* اختيار Operation أكثر تحفظًا.
* خفض قوة Parameters.
* إظهار Warning.
* تجنب Operation قوية.

### السبب

هذا هو جوهر Preservation-Aware Processing.

---

# 12. Preservation Verification

## DEC-056 — Preservation Verification تقييم بنيوي

**الحالة:** ✅ معتمد

### القرار

المحرك يقيم مؤشرات التغير البنيوي بين Original وResult.

### لا يقيّم

* معنى النص.
* صحة الحروف لغويًا.
* صحة محتوى المخطوطة تاريخيًا.

---

## DEC-057 — Structural Difference لا يساوي Text Loss

**الحالة:** ✅ معتمد

### القرار

لا يعتبر كل اختلاف بين Original وResult دليلًا على فقد نص.

### السبب

أي Enhancement ناجحة ستغير Pixels بصورة طبيعية.

---

## DEC-058 — لا يستخدم Pixel Difference وحده لتقييم الفقد

**الحالة:** ✅ معتمد

### القرار

فرق Pixels المباشر لا يكفي وحده لبناء Preservation Assessment.

### السبب

مثلاً:

```text id="dec058-example"
Contrast Enhancement
```

قد تغير عددًا كبيرًا من Pixels دون حذف البنية.

### الاتجاه المعتمد

الاعتماد على مؤشرات أكثر ارتباطًا بالبنية مثل:

* Edges.
* Components.
* Local Structure.
* Fine Details.

---

## DEC-059 — عدم استخدام Preservation Score كحقيقة مطلقة

**الحالة:** ✅ معتمد

### القرار

إذا استخدم Score مركب مستقبلًا، يعرض كـ:

> **Structural Preservation Indicator**

ولا يعرض على أنه:

> نسبة النص المحفوظ.

### السبب

لا توجد Ground Truth تسمح بهذا الادعاء.

---

## DEC-060 — حالات Assessment تكون محافظة في صياغتها

**الحالة:** ✅ معتمد

### القرار

يمكن استخدام:

```text id="dec060-values"
acceptable
caution
high_risk
```

أو صياغة مكافئة تعتمد لاحقًا.

### ممنوع

```text id="dec060-no"
perfect
100% safe
zero loss
guaranteed
```

---

## DEC-061 — فشل Preservation Check لا يعني دائمًا فشل Processing

**الحالة:** ✅ معتمد

### القرار

إذا نجحت المعالجة وفشل Preservation Verification تقنيًا:

```text id="dec061-flow"
Processing
   ✓

Verification
   ✗
```

يمكن إرجاع Result مع Warning بأن التقييم غير متاح.

### السبب

فشل وحدة التقييم لا يعني أن ملف النتيجة نفسه غير صالح.

### القيد

لا يجوز وصف Result بأنها آمنة عند غياب التقييم.

---

# 13. Smart Pipeline

## DEC-062 — Smart Pipeline Rule-Based

**الحالة:** ✅ معتمد

### القرار

الـPipeline تختار خطواتها باستخدام قواعد واضحة وليست نموذج AI.

---

## DEC-063 — Pipeline لا تكون سلسلة ثابتة لجميع الصور

**الحالة:** ✅ معتمد

### القرار

لا تعتمد:

```text id="dec063-bad"
Grayscale
→ Median
→ CLAHE
→ Threshold
→ Morphology
```

لكل صورة دون النظر إلى حالتها.

### الاتجاه الصحيح

```text id="dec063-correct"
Diagnosis
+
Preservation Profile
        ↓
Treatment Plan
        ↓
Relevant Steps Only
```

---

## DEC-064 — النسخة الأولى لا تحتاج Multi-Candidate Search

**الحالة:** ✅ معتمد

### القرار

في الـMVP الأول:

```text id="dec064-mvp"
Plan
↓
Process
↓
Verify
↓
Assessment
```

بدل:

```text id="dec064-advanced"
Generate many candidates
↓
Evaluate all
↓
Optimize
↓
Select best
```

### السبب

الحل الأول أبسط وأكثر قابلية للاختبار.

### المستقبل

Candidate Selection يمكن إضافتها دون تغيير فلسفة المشروع.

---

# 14. الميزات الاختيارية

## DEC-065 — Lost Detail Map ميزة اختيارية

**الحالة:** ⏳ مؤجل بعد الوظائف الأساسية

### القرار

يمكن تطوير خريطة تظهر مناطق تغير بنيوي محتملة.

### السبب في التأجيل

Preservation Metrics الأساسية يجب أن تثبت فائدتها أولًا.

---

## DEC-066 — Treatment Report ميزة اختيارية

**الحالة:** ⏳ مؤجل بعد الوظائف الأساسية

### القرار

يمكن إنشاء تقرير يحتوي:

* Diagnosis.
* Treatment.
* Reasons.
* Preservation Assessment.

### السبب في التأجيل

لا تعتمد قيمة الـMVP على وجود تقرير قابل للتنزيل.

---

## DEC-067 — Regional Preservation ميزة مستقبلية

**الحالة:** ⏳ مؤجل

### القرار

يمكن مستقبلًا تحليل حساسية مناطق مختلفة داخل الصورة.

مثال:

```text id="dec067-future"
Fine Text
→ Conservative Treatment

Background
→ Stronger Correction
```

### السبب في التأجيل

يتطلب تحديد مناطق موثوقًا وتقييمًا أكثر تعقيدًا.

---

# 15. الاختبارات والجودة

## DEC-068 — Unit Tests قبل الاعتماد على الواجهة

**الحالة:** ✅ معتمد

### القرار

تختبر الوحدات الأساسية مباشرة:

```text id="dec068-tests"
analyzer.py
operations.py
pipeline.py
preservation.py
```

ولا يعتمد التحقق فقط على النقر داخل Browser.

---

## DEC-069 — اختبارات Flask تستخدم Temporary Storage

**الحالة:** ✅ معتمد

### القرار

تستخدم اختبارات Backend مجلدات مؤقتة مثل `tmp_path`.

### السبب

منع تلويث:

```text id="dec069-storage"
storage/uploads
storage/results
```

ببيانات الاختبار.

---

## DEC-070 — نجاح الاختبار الاصطناعي لا يكفي لتثبيت Metric

**الحالة:** ✅ معتمد

### القرار

Synthetic Tests تثبت صحة السلوك البرمجي فقط.

أما صلاحية Metric للمخطوطات فتحتاج صورًا واقعية متنوعة.

### مثال

```text id="dec070-flow"
Unit Test
→ Algorithm behaves as coded

Real Image Evaluation
→ Metric is useful for manuscripts
```

---

# 16. Scientific Honesty

## DEC-071 — لا ادعاء بفهم النص دون OCR

**الحالة:** ✅ معتمد

### القرار

لا يقول النظام:

> فقد حرفًا.

بل يمكن أن يقول:

> ظهرت مؤشرات على فقد تفاصيل بنيوية دقيقة.

---

## DEC-072 — لا ادعاء باستعادة الأصل التاريخي

**الحالة:** ✅ معتمد

### القرار

النتيجة تسمى:

```text id="dec072-good"
Processed Result
Enhanced Result
Treatment Result
```

ولا تسمى:

```text id="dec072-bad"
Original Restored Manuscript
True Original
Recovered Historical Original
```

---

## DEC-073 — لا ادعاء بأن المعالجة هي الأفضل مطلقًا

**الحالة:** ✅ معتمد

### القرار

الصياغة المقبولة:

> النتيجة الأكثر توازنًا وفق المؤشرات المستخدمة.

أو:

> المعالجة المقترحة لهذه الحالة.

وليس:

> أفضل معالجة ممكنة.

---

# 17. البساطة الهندسية

## DEC-074 — Simple Until Complexity Is Justified

**الحالة:** ✅ معتمد

### القرار

لا تضاف طبقة أو مكتبة أو Pattern إلا إذا حلت مشكلة فعلية.

### لذلك لا نستخدم حاليًا

```text id="dec074-no"
Microservices
Repository Pattern
Service لكل دالة
Celery
Message Queue
SQLAlchemy
Cloud Storage
Complex Configuration System
```

### السبب

تعقيد المشروع ليس مقياسًا للاحتراف.

---

## DEC-075 — عدم تقسيم الملفات قبل الحاجة

**الحالة:** ✅ معتمد

### القرار

يبقى `app.py` ملفًا واحدًا طالما حجمه ومسؤولياته ما زالت قابلة للفهم.

### السبب

إنشاء:

```text id="dec075-no"
routes/
services/
repositories/
validators/
controllers/
```

دون حاجة فعلية يضيف عبئًا أكثر من القيمة.

---

# 18. قواعد تغيير القرارات

## DEC-076 — لا يغيّر قرار معتمد بصمت

**الحالة:** ✅ معتمد

### القرار

إذا ظهر أن قرارًا سابقًا غير مناسب:

```text id="dec076-flow"
Detect Problem
      ↓
Explain Impact
      ↓
Propose Alternative
      ↓
Approve Change
      ↓
Update Decision Record
      ↓
Update Requirements
      ↓
Update Architecture
      ↓
Update Tests
      ↓
Implement
```

### السبب

منع الوثائق والكود من التحرك في اتجاهات مختلفة.

---

## DEC-077 — الإضافات مسموحة دون تغيير فلسفة المشروع

**الحالة:** ✅ معتمد

### القرار

يمكن إضافة Metrics أو Operations أو Features جديدة إذا رفعت قيمة النظام.

لكن يجب أن تبقى الفلسفة:

---

## DEC — عمليات المعالجة Pure Image Functions

**الحالة:** معتمد

### القرار

تستقبل عمليات المعالجة صورة في الذاكرة وتعيد صورة جديدة دون حفظ ملفات أو التعامل مع HTTP.

### السبب

فصل خوارزميات معالجة الصور عن طبقة Flask والتخزين يجعلها أسهل في الاختبار وإعادة الاستخدام.

---

## DEC — المحافظة على اللون عند تحسين التباين

**الحالة:** معتمد

### القرار

عند تطبيق CLAHE أو Histogram Equalization على صورة ملونة، يتم تعديل قناة الإضاءة بدل تحويل الصورة بالكامل إلى Grayscale.

### السبب

تحتوي صور المخطوطات على معلومات لونية قد تكون مفيدة ولا توجد حاجة إلى فقدها لتنفيذ تحسين التباين.

---

## DEC — عدم اعتماد Gaussian Smoothing كعملية أساسية حاليًا

**الحالة:** معتمد مؤقتًا

### القرار

لن يضاف Gaussian Smoothing إلى قائمة العمليات الأساسية في المرحلة الحالية.

### السبب

يوجد Median Denoising ضمن العمليات الحالية، ولا يوجد بعد دليل تجريبي يبرر إضافة عملية تنعيم أخرى إلى الـMVP.

يمكن إعادة القرار في مرحلة تقييم العمليات.

---

## DEC — Morphology عملية عالية الحساسية

**الحالة:** معتمد

### القرار

وجود Morphological Opening وClosing في طبقة العمليات لا يعني السماح باستخدامهما تلقائيًا داخل Smart Pipeline.

### السبب

قد تؤدي هذه العمليات إلى إزالة تفاصيل دقيقة أو دمج مكونات نصية.

يجب تقييمها أولًا.

---

## DEC — Parameters الحالية Initial Defaults

**الحالة:** معتمد مؤقتًا

### القرار

Parameters الموجودة في عمليات المرحلة 7 توفر سلوكًا أوليًا قابلًا للاختبار وليست إعدادات نهائية للمخطوطات.

### السبب

اختيار القيم النهائية يجب أن يعتمد على تجارب المرحلة 8 وليس على افتراضات مسبقة.

---
## DEC — اعتماد العمليات التلقائية بعد التقييم فقط

**الحالة:** معتمد

### القرار

لا تصبح أي عملية Processing Operation مؤهلة للاستخدام التلقائي داخل Recommendation Engine أو Smart Pipeline لمجرد نجاحها البرمجي.

يجب أولًا أن تمر عبر تقييم Phase 8.

### السبب

نجاح تنفيذ الخوارزمية لا يعني أنها مناسبة لكل صور المخطوطات أو أنها لا تسبب آثارًا جانبية.

---

## DEC — Parameters تعتمد كتفضيلات أولية وليست قيمًا مثالية

**الحالة:** معتمد

### القرار

الإعدادات المختارة بعد Phase 8 تعتبر Provisional Defaults.

### السبب

مجموعة الاختبار محدودة ولا تكفي لادعاء وجود Parameters مثلى لجميع المخطوطات.

---

## DEC — التحسن البصري لا يكفي لاعتماد العملية

**الحالة:** معتمد

### القرار

لا يتم تقييم العملية من خلال الوضوح أو التباين وحدهما.

يجب النظر أيضًا إلى تغير التفاصيل والضوضاء والبنية وسلوك العملية على حالات متعددة.
---
<div align="center">

### Diagnose → Treat → Preserve → Verify

</div>

### السبب

التطوير مفتوح للإضافة، لكن هوية المشروع أصبحت ثابتة.

---

# 19. القرارات المؤقتة التي تحتاج مراجعة لاحقة

| القرار                             |   الحالة  | متى يراجع؟                         |
| ---------------------------------- | :-------: | ---------------------------------- |
| Diagnostic Thresholds              |  🟡 مؤقت  | بعد اختبار مجموعة الصور الواقعية   |
| Preservation Profile Thresholds    |  🟡 مؤقت  | بعد تقييم سلوك المؤشرات            |
| Parameters الخاصة بعمليات المعالجة | 🟡 لاحقًا | المرحلة الخاصة بتقييم العمليات     |
| Preservation Assessment Thresholds | 🟡 لاحقًا | بعد بناء `preservation.py` وتجربته |
| أسماء حالات Assessment النهائية    | 🟡 لاحقًا | عند تصميم UX النهائي               |

> وجود قرار مؤقت لا يعني تركه عشوائيًا؛ يعني أن لدينا قيمة عملية أولية لكننا نرفض اعتبارها نهائية قبل التقييم.

---

# 20. القرارات المؤجلة رسميًا

| الميزة                    |            الحالة            |
| ------------------------- | :--------------------------: |
| OCR                       |            ⏳ مؤجل            |
| YOLO                      |            ⏳ مؤجل            |
| Deep Learning             |            ⏳ مؤجل            |
| Database                  |            ⏳ مؤجل            |
| Authentication            |            ⏳ مؤجل            |
| Generative Restoration    |            ⏳ مؤجل            |
| Lost Detail Map           |         ⏳ بعد الـCore        |
| Treatment Report          |         ⏳ بعد الـCore        |
| Multi-Candidate Selection |         ⏳ بعد الـCore        |
| Regional Preservation     |           ⏳ مستقبل           |
| Region-Aware Processing   |           ⏳ مستقبل           |
| Cloud Deployment          | ⏳ بعد استقرار النسخة المحلية |

---

# 21. المبدأ الذي يحكم أي قرار جديد

قبل إضافة أي شيء، يجب الإجابة عن:

```text id="dec-final-check"
هل يحل مشكلة حقيقية؟
        ↓
هل يخدم Manuscript Doctor؟
        ↓
هل يوجد حل أبسط؟
        ↓
هل يمكن اختباره؟
        ↓
هل يمكن تفسيره؟
        ↓
هل يحافظ على Original؟
        ↓
هل يؤثر على Preservation؟
        ↓
هل يحتاج تحديث الوثائق؟
```

إذا لم يكن للقرار أثر واضح على قيمة المشروع:

> **لا يضاف الآن.**

---

<div align="center">

## 🩺 Manuscript Doctor

### Engineering Principle

**Simple enough to understand.**
**Structured enough to extend.**
**Measured enough to justify.**
**Conservative enough to preserve.**

</div>

</div>
