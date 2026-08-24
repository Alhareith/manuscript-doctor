<div dir="rtl" align="right">

# 🧩 Manuscript Doctor — Wireframes

> **غرض الوثيقة:** توثيق التخطيط البنيوي للواجهة كما هو منفذ حالياً، مع توضيح مواقع الصور واللوحات والحالات الرئيسية دون الدخول في تفاصيل CSS الدقيقة.
>
> المصطلحات هنا تصف **مكان العنصر وعلاقته بالعناصر الأخرى**. السلوك الزمني في [`workflow.md`](workflow.md)، والحالات في [`ui-states.md`](ui-states.md)، وتقسيم الملفات في [`split-structure.md`](split-structure.md).

---

## 1. مبدأ التخطيط

الواجهة عبارة عن **Single-Page Progressive Workspace**: صفحة واحدة تتكشف أقسامها حسب حالة الصورة، مع بقاء شريط المراحل ثابتاً ليسهل التنقل.

```mermaid
flowchart LR
    A["Header"] --> B["Workflow Bar"]
    B --> C["Upload Entry"]
    C --> D["Image + Analysis Workspace"]
    D --> E["Treatment Studio"]
    E --> F["Verification + Output"]
```

الأولوية البصرية ليست لعرض أكبر عدد من الأدوات، بل لهذا الترتيب:

```text
الصورة
  ↓
ما الذي فُحص؟
  ↓
ما المعالجة المناسبة؟
  ↓
ما أثرها؟
  ↓
هل أعتمدها أو أنزلها؟
```

---

## 2. التخطيط العام للصفحة

```mermaid
flowchart TD
    H["Header: هوية + Theme"]
    W["Workflow Bar: 01 رفع · 02 تهيئة · 03 تشخيص · 04 معالجة · 05 تحقق · 06 إخراج"]
    U["uploadSection: رفع الوثيقة"]
    P["documentPreviewSection: الصورة ونتائج الفحص"]
    A["examinationSection: Dashboard"]
    T["treatmentSection: Treatment Studio"]
    E["verificationSection: Preservation"]
    D["downloadSection: Output"]
    F["Footer"]

    H --> W --> U --> P --> A --> T --> E --> D --> F
```

لا تظهر الأقسام التحليلية والمعالجة والنتيجة قبل نجاح الرفع والفحص. عند اختيار صورة جديدة، تصفر الواجهة النتائج السابقة وتعود إلى حالة الرفع والفحص.

---

## 3. Header وشريط المراحل

### Header

```mermaid
flowchart LR
    L["doctor-logo.svg"] --- B["Manuscript Doctor<br/>Diagnose · Treat · Preserve · Verify"]
    B --- N["Theme Toggle"]
```

يستخدم Header الصورة:

```text
static/assets/header-workspace-background.png
```

كخلفية كاملة فقط. لا توجد صورة before/after مستقلة داخل المقدمة، ولا عنصر Hero مكرر. يحافظ التخطيط على تكوين الصورة العريضة داخل مساحة الرأس دون قص جانبي مقصود.

### Workflow Bar

```mermaid
flowchart LR
    S1["01<br/>رفع"] --> S2["02<br/>تهيئة"] --> S3["03<br/>تشخيص"] --> S4["04<br/>معالجة"] --> S5["05<br/>تحقق"] --> S6["06<br/>إخراج"]
```

شريط المراحل `#workflow` ثابت أثناء التمرير، وتنتقل الروابط إلى الأقسام ذات الصلة. في العرض الضيق يسمح الشريط بالتمرير الأفقي بدلاً من تكسير العناصر أو إخفائها.

---

## 4. منطقة الرفع

```mermaid
flowchart TD
    H["uploadSection"] --> I["Drop Zone + imageInput"]
    I --> S["selectedFile: الاسم والحجم"]
    S --> A["تغيير الصورة"]
    S --> B["فحص الوثيقة"]
    B --> C["processingStateSection"]
    C --> D["Workspace بعد النجاح"]
```

في الحالة الأولى يظهر Drop Zone وزر اختيار الصورة. بعد الاختيار تظهر بطاقة الملف وزرا **تغيير الصورة** و**فحص الوثيقة**. لا تظهر Dashboard أو أدوات المعالجة قبل نجاح الرفع والتحقق.

---

## 5. مساحة الصورة ونتائج الفحص

```mermaid
flowchart LR
    subgraph WORKSPACE["documentPreviewSection"]
        V["document-viewer-main<br/>originalPreview"]
        R["after-exam-deck"]
        R1["ملخص الحالة"]
        R2["diagnosisSection"]
        R3["preservationProfileSection"]
        R4["treatmentPlanSection"]
        R1 --> R2 --> R3 --> R4
    end
    V --- R
```

تعرض `originalPreview` الصورة المرفوعة، بينما تعرض المنطقة الجانبية أو اللاحقة ملخص الحالة والتشخيص وPreservation Profile والتوصية. يظل التشخيص منفصلاً عن ملف المحافظة؛ الأول يصف المشكلة، والثاني يحدد مستوى الحذر.

### Dashboard

```mermaid
flowchart TD
    A["examinationSection"] --> M["Metric Cards"]
    M --> M1["السطوع"]
    M --> M2["التباين"]
    M --> M3["الضوضاء"]
    M --> M4["الحدة"]
    M --> M5["تجانس الإضاءة"]
    M --> M6["كثافة الحواف"]
    A --> C1["توازن الظلال والإضاءات<br/>رسم خطي"]
    A --> C2["مستويات المؤشرات المقننة"]
    A --> N["قراءة تفسيرية"]
```

يعرض الرسم الخطي لتوازن الظلال والإضاءات على أنه قراءة لنطاقات الصورة، وليس بديلاً عن المؤشرات الرقمية أو Histogram كاملاً.

---

## 6. Treatment Studio

```mermaid
flowchart TD
    T["treatmentSection"] --> M["treatment-mode-grid"]
    M --> S["Smart Mode<br/>تشغيل المعالجة الذكية"]
    M --> H["Manual Mode<br/>ابدأ يدوياً"]
    T --> E["manualEditor"]
```

تظهر بطاقتا Smart وManual داخل Treatment Studio. زر Smart يرسل طلب المسار الذكي بعد توفر صورة صالحة، بينما تنقل بطاقة Manual إلى المحرر اليدوي.

---

## 7. محرر المعالجة اليدوية

```mermaid
flowchart LR
    subgraph EDITOR["manualEditor"]
        P["manual-preview-pane"]
        C["manual-controls-pane"]
    end
    P --> B["manualPreviewPair"]
    B --> O["manualOriginalPreview"]
    B --> A["manualLivePreview + Crop Guide"]
    P --> H["Undo / Redo + Chain Status"]
    C --> G["Operation Category Strip"]
    G --> L["Operation Browser"]
    L --> Q["Selected Operation + Parameters"]
    Q --> X["manual-change-chart-inline"]
    X --> Y["اعتماد العملية وإضافتها للسلسلة"]
```

### المعاينة

المحرر هو قلب التجربة، ويقسم إلى:

| المنطقة | الوظيفة |
| --- | --- |
| `manual-preview-pane` | عرض before/after، حالة المعاينة، Undo/Redo |
| `manualOriginalPreview` | الصورة السابقة للخطوة النشطة |
| `manualLivePreview` | المرشح أو النتيجة الحالية؛ وتُحفظ الخطوات في `state.manualChain` ويحدد `manualActiveIndex` الخطوة المعروضة |
| `manualCropGuide` | إطار القص ومقابضه عند اختيار Crop |
| `manual-controls-pane` | مجموعات العمليات والعملية المختارة ومعاملاتها |
| `manual-change-chart-inline` | أثر المعاينة داخل لوحة العملية نفسها |
| `manualApprovalButton` | نقطة الاعتماد الوحيدة |
| `manualManualDownloadButton` | تنزيل النتيجة اليدوية عند توفرها |

يُستخدم زر اعتماد واحد فقط لإضافة المرشح إلى السلسلة، ولا يظهر إجراء تنفيذ إضافي موازٍ. وجود مرشح صالح هو الذي يفعّل زر الاعتماد.

### مجموعات العمليات

```text
تجهيز الوثيقة
الإضاءة
التباين
الضوضاء
التفاصيل
فصل النص
البنية
الخلفية
```

يظهر **تجهيز الوثيقة** أول مجموعة، ويضم تصحيح الميل والاقتصاص اليدوي وأزرار الاتجاه. تظهر العملية `super_resolution` داخل مجموعة التفاصيل بوصفها خياراً خادمياً متقدماً.

---

## 8. Crop Wireframe

```mermaid
flowchart TD
    A["اختيار crop"] --> B["إطار ابتدائي بهامش 5%"]
    B --> C["سحب Move أو المقابض"]
    C --> D["تحديث x/y/width/height"]
    D --> E["معاينة crop"]
    E --> F["اعتماد فقط"]
```

يظهر `manualCropGuide` فوق `manualLivePreview`، وتعمل المقابض للحواف والزوايا مع إمكانية تحريك الإطار. يجب أن تبقى النتيجة المرئية داخل حدود الصورة وأن تطابق النتيجة المعتمدة القيم المرسلة إلى Flask/OpenCV.

---

## 9. Smart Pipeline داخل التخطيط

لا تُعرض نتيجة Smart في صفحة منفصلة. بعد نجاح المسار، تُعرض النتيجة داخل مساحة المعالجة نفسها ويمكن إضافة عمليات يدوية فوقها.

```mermaid
flowchart LR
    S["تشغيل Smart"] --> P["Preparation Decision"]
    P --> R["Smart Result"]
    R --> E["manualEditor"]
    E --> N["Manual Step لاحقة"]
```

إذا قبل التحقق تجهيز الوثيقة، يظهر في الملخص كخطوة `document_prepare` مقبولة. وإذا كان القرار `deferred`، تبقى الصورة الأصلية مرجعاً للمسار ولا تعرض الواجهة قصاً أو منظوراً غير موثوق.

---

## 10. النتيجة والتحقق والتنزيل

```mermaid
flowchart TD
    A["manualEditor / Smart Result"] --> H["treatment-history"]
    A --> V["verificationSection"]
    V --> D["decisionSection"]
    V --> B["binarizationSection عند وجود Candidates"]
    D --> O["downloadSection"]
```

### مناطق النتائج

| المنطقة | محتواها |
| --- | --- |
| `treatment-history` | الخطوات والنتائج التي أنشأها النظام فعلياً |
| `verificationSection` | Edge Retention وComponent Retention والتشابه البنيوي وEdge Inflation والتحذيرات |
| `decisionSection` | Acceptable أو Caution أو High Risk ورسالة القرار |
| `binarizationSection` | مرشحو فصل النص في مسار مستقل |
| `downloadSection` | تنزيل النتيجة الحالية أو بدء وثيقة جديدة |

لا يظهر زر التنزيل كإجراء فعال قبل وجود `result_id` حقيقي محفوظ.

---

## 11. الحالات البصرية الأساسية

```mermaid
stateDiagram-v2
    [*] --> Empty
    Empty --> ImageSelected: اختيار صورة
    ImageSelected --> Examining: فحص الوثيقة
    Examining --> WorkspaceReady: نجاح الرفع والتحليل
    WorkspaceReady --> TreatmentReady: ظهور التوصية
    TreatmentReady --> PreviewCandidate: اختيار عملية
    PreviewCandidate --> ApprovedResult: اعتماد
    ApprovedResult --> TreatmentReady: عملية لاحقة
    ApprovedResult --> Verification: نتيجة جاهزة
    Verification --> Output: قرار وتنزيل
    PreviewCandidate --> Error: فشل المعاينة
    Examining --> Error: فشل الرفع أو الفحص
```

التفاصيل الدقيقة للحالات الانتقالية في [`ui-states.md`](ui-states.md).

---

## 12. التخطيط المتجاوب

### Desktop

```mermaid
flowchart LR
    subgraph DESKTOP["شاشة عريضة"]
        MP["Preview<br/>before / after"]
        MC["Controls<br/>operations + parameters"]
        MP --- MC
    end
```

في الشاشة العريضة، يحتفظ المحرر بالمعاينة في مساحة أكبر من لوحة التحكم، مع ظهور العملية المختارة والرسم داخل لوحة التحكم. تعرض المقارنة الأصل والنتيجة جنباً إلى جنب.

### Mobile

```mermaid
flowchart TD
    H["Header + Workflow horizontal scroll"]
    U["Upload"]
    A["Analysis"]
    P["Preview before / after"]
    C["Controls"]
    R["Verification + Output"]
    H --> U --> A --> P --> C --> R
```

في العرض الضيق تصبح مناطق المحرر عمودية، وتتحول المقارنة إلى صفوف متتابعة، وتُصغر البطاقات مع إبقاء النص والأزرار قابلين للقراءة. يبقى Workflow قابلاً للتمرير، ولا يسمح التخطيط بخروج الأزرار أو الفوتر خارج الشاشة.

---

## 13. قاعدة التحقق البصري

عند تعديل HTML أو CSS يجب فحص هذه النقاط:

| النقطة | المتوقع |
| --- | --- |
| Header | الخلفية كاملة ولا توجد صورة Hero مكررة |
| Workflow | ثابت وقابل للتمرير في العرض الضيق |
| Manual Editor | before/after ظاهر ومنظم |
| Crop | المقابض قابلة للإمساك ولا تتجاوز الصورة |
| Chart | داخل selected-operation panel |
| Approval | زر اعتماد واحد فقط |
| Smart Result | يظهر داخل المحرر نفسه |
| Footer | متجاوب ولا يخفي المحتوى |

</div>
