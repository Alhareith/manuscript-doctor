<div align="center">

# 🩺 Manuscript Doctor

### طبيب الوثائق · Diagnose · Treat · Preserve · Verify

**نظام ويب عربي لتشخيص صور الوثائق ومعالجتها والتحقق من أثر المعالجة قبل اعتمادها**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-Backend-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![OpenCV](https://img.shields.io/badge/OpenCV-Image%20Processing-5C3EE8?logo=opencv&logoColor=white)](https://opencv.org/)
[![NumPy](https://img.shields.io/badge/NumPy-Numerical%20Processing-013243?logo=numpy&logoColor=white)](https://numpy.org/)
[![Tests](https://img.shields.io/badge/Tests-333%20passed-0B7A62)](#التحقق)

</div>

<p align="center">
  <img src="static/assets/header-workspace-background.png" alt="هوية طبيب الوثائق ومعالجة الوثائق" width="100%">
</p>

<p align="center">
  <a href="https://manuscript-doctor.onrender.com/" target="_blank" rel="noopener noreferrer">
    <img src="static/assets/live-demo-button.svg" alt="جرّب الموقع الحي الآن — افتح Manuscript Doctor" width="720">
  </a>
</p>

<div dir="rtl" align="right">

> **سبب تأخر بعض النتائج:** المعاينة الخفيفة تظهر محلياً، أما الاعتماد والعمليات الثقيلة فتمر عبر Flask/OpenCV؛ لذلك يتأثر زمن النتيجة بحجم الصورة وتعقيد العملية وزمن استجابة الخادم.

> **الفكرة:** لا نطبق المعالجة لمجرد تغيير الصورة؛ نقرأ حالتها، نختار العملية، نراجع before/after، ثم نعتمد النتيجة بعد التحقق.

<p align="center">
  <img src="static/assets/document-before.png" alt="قبل المعالجة: وثيقة مائلة فوق طاولة" width="31%">
  &nbsp;
  <img src="static/assets/document-edges.png" alt="توضيح الحواف المكتشفة بخط أخضر نحيف" width="31%">
  &nbsp;
  <img src="static/assets/document-after.png" alt="بعد المعالجة: وثيقة مستقيمة ومقصوصة أوضح قراءة" width="31%">
</p>

<p align="center">
  <strong>بعد المعالجة</strong>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <strong>الحواف المكتشفة</strong>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <strong>قبل المعالجة</strong>
</p>

> **قراءة التسلسل:** تُظهر الصورة الأولى وثيقة مائلة على سطح تصوير، وتوضح الصورة الوسطى حدود الوثيقة التي يمكن استخدامها لاكتشاف الميل، بينما تعرض الصورة الأخيرة نتيجة مستقيمة ومقصوصة مع تحسين محافظ لوضوح الكتابة.

---

## نظرة سريعة

| العنصر | الحالة الحالية |
| --- | --- |
| الواجهة | HTML/CSS/JavaScript عربية RTL ومقسمة ومتجاوبة |
| المعالجة | Flask + Python + OpenCV + NumPy |
| المعاينة | Canvas محلي للعمليات الخفيفة، وPreview خادمي مضغوط للعمليات الثقيلة |
| الاعتماد | Flask/OpenCV ينشئ نتيجة حقيقية قابلة للحفظ والتنزيل |
| المسار الذكي | Analyze → Recommend → Apply → Preserve → Verify |
| العملية المضافة | Super Resolution اختيارية بتكبير Lanczos وUnsharp Masking |
| الاختبارات | 333 ناجحاً و16 متجاوزاً |

## كيف يعمل؟

```mermaid
flowchart LR
    A["رفع الوثيقة"] --> B["فحص وتشخيص"]
    B --> C{"اختيار المسار"}
    C -->|"يدوي"| D["معاينة محلية أو خادمية"]
    C -->|"ذكي"| E["Smart Pipeline محافظ"]
    D --> F["مراجعة before / after"]
    E --> F
    F --> G["اعتماد Flask + OpenCV"]
    G --> H["تحقق وتنزيل"]
```

## ما الذي يطبقه؟

| المجموعة | أمثلة |
| --- | --- |
| تجهيز الوثيقة | Deskew، اقتصاص تلقائي محافظ، اقتصاص يدوي، تدوير، قلب |
| الإضاءة والتباين | Intensity، Gamma، CLAHE، Histogram Equalization، Illumination Normalization |
| إزالة الضوضاء | Median، Bilateral، Non-Local Means |
| النص والبنية | Global/Otsu/Adaptive Threshold، Opening، Closing، Top-Hat، Black-Hat |
| التفاصيل والدقة | Sharpen، Faded Text Enhancement، Super Resolution |

## المعاينة والنتيجة النهائية

المعاينة ليست بديلاً عن الاعتماد. العمليات الخفيفة مثل التدوير والقلب وضبط الشدة وتصحيح جاما تُعرض محلياً بسرعة داخل Canvas. العمليات الثقيلة، ومنها Super Resolution، تُعاين عبر Flask على نسخة مصغرة. عند الاعتماد يعيد الخادم تنفيذ العملية على المصدر الصحيح ويضيف artifact جديداً إلى السلسلة.

> **حد Super Resolution:** قد تزيد قابلية قراءة النص الصغير، لكنها لا تستعيد حروفاً فُقدت تماماً بسبب الضبابية أو نقص المعلومات.

## المعمارية المختصرة

```mermaid
flowchart LR
    UI["HTML + CSS Parts + JS Parts"] --> API["Flask / app.py"]
    API --> A["Analyzer"]
    API --> R["Operations Registry"]
    API --> P["Preparation + Smart Pipeline"]
    R --> CV["OpenCV / NumPy"]
    P --> CV
    CV --> V["Preservation Verification"]
    V --> API
```

## التشغيل المحلي

```bash
cd manuscript-doctor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m flask --app 'app:create_app()' run --host 0.0.0.0 --port 5002
```

ثم افتح `http://127.0.0.1:5002/`. لا يحتاج المشروع إلى Docker.

## التحقق

```bash
PYTHONPATH=. pytest -q tests
for f in static/js/parts/*.js; do node --check "$f"; done
```

## بنية المشروع
</div>

```text

manuscript-doctor/
├── app.py
├── templates/index.html
├── static/
│   ├── css/style.css
│   ├── css/parts/
│   ├── js/app.js
│   ├── js/parts/
│   └── assets/
├── processing/
│   ├── analyzer.py
│   ├── pipeline.py
│   ├── preservation.py
│   └── ops/
├── tests/
├── evaluation/
└── docs/
```
<div dir="rtl" align="right">

## التوثيق

ابدأ من [دليل التوثيق](docs/README.md)، ثم راجع [خريطة التحديث والاتساق](docs/documentation-update-map.md) لفهم العلاقة بين كل ملف، والقرار الذي يثبته، والرسم المناسب له.

| الغرض | الوثيقة |
| --- | --- |
| الفكرة والنطاق | [`docs/overview.md`](docs/overview.md) |
| المتطلبات | [`docs/requirements.md`](docs/requirements.md) |
| المعمارية | [`docs/architecture.md`](docs/architecture.md) |
| سير العمل | [`docs/workflow.md`](docs/workflow.md) |
| الاختبارات | [`docs/testing.md`](docs/testing.md) |
| تقييم العمليات | [`docs/operation-evaluation.md`](docs/operation-evaluation.md) |
| سجل القرارات | [`docs/decisions.md`](docs/decisions.md) |

## الحدود العلمية

المشروع أداة لمعالجة الصور ودعم قرار المعالجة، وليس OCR أو ترميماً توليدياً. مؤشرات الجودة وPreservation أدوات مساعدة قابلة للمراجعة، ولا تعني أن كل تغير بصري يمثل فقداً أو استعادة لحرف تاريخي.

<div align="center">

**Enhance what is hidden. Preserve what matters.**

</div>

</div>
