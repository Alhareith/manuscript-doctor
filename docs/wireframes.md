
# Wireframes — Manuscript Doctor

## 1. هيكل الصفحة العام (Desktop + Mobile)

```mermaid
graph TD
    A[Header - Manuscript Doctor] --> B[Upload Area]
    B --> C[Image Overview]
    C --> D[Diagnosis]
    D --> E[Recommended Action]
    E --> F[Smart Enhancement]
    F --> G[Manual Tools]
    G --> H[Comparison - Before/After]
    H --> I[Processing Summary]
    I --> J[Download Button]
    
    style A fill:#2c3e50,color:#fff
    style B fill:#3498db,color:#fff
    style C fill:#ecf0f1,color:#000
    style D fill:#e74c3c,color:#fff
    style E fill:#f39c12,color:#fff
    style F fill:#27ae60,color:#fff
    style G fill:#9b59b6,color:#fff
    style H fill:#1abc9c,color:#fff
    style I fill:#34495e,color:#fff
    style J fill:#e67e22,color:#fff
```

## 2. تدفق المستخدم (User Flow)

```mermaid
flowchart TD
    Start([بداية]) --> Upload[رفع الصورة]
    Upload --> Analyze[تحليل الصورة]
    Analyze --> Diagnose[تشخيص الحالة]
    Diagnose --> Choice{اختر نوع المعالجة}
    Choice -->|تلقائي| Smart[تحسين تلقائي - Smart Pipeline]
    Choice -->|يدوي| Manual[أدوات يدوية]
    Smart --> Process[تنفيذ المعالجة]
    Manual --> Process
    Process --> Compare[مقارنة Before/After]
    Compare --> Evaluate[تقييم النتيجة]
    Evaluate --> Decision{ماذا تريد؟}
    Decision -->|تجربة أخرى| Choice
    Decision -->|تنزيل| Download[تنزيل النتيجة]
    Download --> End([نهاية])
    
    style Start fill:#2ecc71,color:#fff
    style End fill:#2ecc71,color:#fff
    style Analyze fill:#3498db,color:#fff
    style Diagnose fill:#e74c3c,color:#fff
    style Smart fill:#27ae60,color:#fff
    style Manual fill:#9b59b6,color:#fff
    style Compare fill:#1abc9c,color:#fff
    style Download fill:#e67e22,color:#fff
```

## 3. Desktop Layout (عرض شاشة الحاسوب)

```mermaid
block-beta
    columns 1
    
    block:header["Header - Manuscript Doctor"]
        headercontent["تحليل وتحسين صور المخطوطات باستخدام تقنيات معالجة الصور"]
    end
    
    block:upload["Upload Area"]
        uploadcontent["اسحب صورة المخطوطة هنا\nأو [اختيار صورة]\n(JPG, JPEG, PNG)"]
    end
    
    block:analysis["Image Analysis - يظهر بعد التحليل"]
        columns 3
        metric1["السطوع\n73/255\nمنخفض"]
        metric2["التباين\nمنخفض"]
        metric3["الضوضاء\nمتوسطة"]
    end
    
    block:diagnosis["Diagnosis - يظهر بعد التحليل"]
        diagnosislist["⚠ تباين منخفض بين النص والخلفية\n⚠ إضاءة غير متجانسة\n⚠ ضوضاء متوسطة"]
    end
    
    block:recommendation["Recommended Action - يظهر بعد التحليل"]
        recotext["يوصى بتحسين التباين المحلي (CLAHE) لأن الإضاءة متفاوتة"]
        recobutton["[تطبيق التحسين المقترح]"]
    end
    
    block:smart["Smart Enhancement - يظهر بعد التحليل"]
        smartplan["الخطة المقترحة: تقليل الضوضاء ← CLAHE ← Threshold"]
        smartbutton["[تحسين الصورة تلقائيًا]"]
    end
    
    block:manual["Manual Tools - أدوات المعالجة اليدوية"]
        categories["▸ تحسين الإضاءة والتباين ▼\n▸ تقليل الضوضاء ▼\n▸ فصل النص عن الخلفية ▼\n▸ تنظيف البنية ▼\n▸ تحليل الحواف ▼"]
        note["كل معالجة يدوية تطبق على الصورة الأصلية"]
    end
    
    block:comparison["Comparison - المقارنة"]
        columns 2
        original["قبل المعالجة\n(Original)"]
        result["بعد المعالجة\n(Result)"]
    end
    
    block:summary["Processing Summary - ملخص المعالجة"]
        details["العملية: CLAHE\nالغرض: تحسين التباين المحلي\nالتباين قبل: منخفض → بعد: أفضل نسبيًا\nملاحظة: قد تزيد بعض التفاصيل في المناطق الداكنة"]
    end
    
    block:download["Download Area"]
        downloadbutton["[تنزيل النتيجة] - يظهر بعد المعالجة"]
    end
    
    style header fill:#2c3e50,color:#fff
    style upload fill:#3498db,color:#fff
    style analysis fill:#ecf0f1,color:#000
    style diagnosis fill:#e74c3c,color:#fff
    style recommendation fill:#f39c12,color:#fff
    style smart fill:#27ae60,color:#fff
    style manual fill:#9b59b6,color:#fff
    style comparison fill:#1abc9c,color:#fff
    style summary fill:#34495e,color:#fff
    style download fill:#e67e22,color:#fff
```

## 4. Mobile Layout (عرض الهاتف)

```mermaid
block-beta
    columns 1
    
    block:header_m
        columns 1
        h1["Header"]
        h2["Manuscript Doctor"]
        h3["تحليل وتحسين المخطوطات"]
    end
    
    block:upload_m
        columns 1
        u1["Upload Area"]
        u2["اسحب صورة المخطوطة هنا"]
        u3["أو [اختيار صورة]"]
    end
    
    block:analysis_m
        columns 1
        a1["Image Analysis"]
        a2["السطوع: 73/255 - منخفض"]
        a3["التباين: منخفض"]
        a4["الضوضاء: متوسطة"]
        a5["الأبعاد: 1920×1080"]
        a6["القنوات: 3"]
    end
    
    block:diagnosis_m
        columns 1
        d1["Diagnosis"]
        d2["⚠ تباين منخفض"]
        d3["⚠ إضاءة غير متجانسة"]
        d4["⚠ ضوضاء متوسطة"]
    end
    
    block:recommendation_m
        columns 1
        r1["Recommended Action"]
        r2["يوصى بتحسين التباين المحلي"]
        r3["[تطبيق التحسين المقترح]"]
    end
    
    block:smart_m
        columns 1
        s1["Smart Enhancement"]
        s2["الخطة: Denoise → CLAHE → Thr."]
        s3["[تحسين تلقائي]"]
    end
    
    block:manual_m
        columns 1
        m1["Manual Tools"]
        m2["▸ الإضاءة والتباين"]
        m3["▸ تقليل الضوضاء"]
        m4["▸ فصل النص"]
        m5["▸ تنظيف البنية"]
        m6["▸ تحليل الحواف"]
    end
    
    block:comparison_m
        columns 1
        c1["Comparison"]
        c2["قبل المعالجة (Original)"]
        c3["بعد المعالجة (Result)"]
    end
    
    block:summary_m
        columns 1
        sm1["Processing Summary"]
        sm2["العملية: CLAHE"]
        sm3["الغرض: تحسين التباين"]
        sm4["..."]
    end
    
    block:download_m
        columns 1
        dl1["[تنزيل النتيجة]"]
    end
    
    style header_m fill:#2c3e50,color:#fff
    style upload_m fill:#3498db,color:#fff
    style analysis_m fill:#ecf0f1,color:#000
    style diagnosis_m fill:#e74c3c,color:#fff
    style recommendation_m fill:#f39c12,color:#fff
    style smart_m fill:#27ae60,color:#fff
    style manual_m fill:#9b59b6,color:#fff
    style comparison_m fill:#1abc9c,color:#fff
    style summary_m fill:#34495e,color:#fff
    style download_m fill:#e67e22,color:#fff
```

## 5. حالات الواجهة (UI States Transitions)

```mermaid
stateDiagram-v2
    [*] --> State1_Empty
    
    State1_Empty: لا صورة مرفوعة
    State2_Selected: تم اختيار صورة
    State3_Loading: جاري الرفع والتحليل
    State4_Analysis: التحليل جاهز
    State5_Processing: جاري المعالجة
    State6_Result: النتيجة جاهزة
    State7_Error: خطأ
    
    State1_Empty --> State2_Selected: اختيار صورة
    State2_Selected --> State3_Loading: ضغط "رفع وتحليل"
    State2_Selected --> State1_Empty: إلغاء الاختيار
    State3_Loading --> State4_Analysis: نجاح التحليل
    State3_Loading --> State7_Error: فشل التحليل
    State4_Analysis --> State5_Processing: بدء المعالجة
    State4_Analysis --> State1_Empty: رفع صورة جديدة
    State5_Processing --> State6_Result: نجاح المعالجة
    State5_Processing --> State7_Error: فشل المعالجة
    State6_Result --> State5_Processing: معالجة جديدة
    State6_Result --> State1_Empty: رفع صورة جديدة
    State7_Error --> State1_Empty: إعادة المحاولة
    State7_Error --> State2_Selected: اختيار صورة أخرى
```

## 6. مكونات الواجهة (Components Hierarchy)

```mermaid
graph LR
    HTML[صفحة HTML واحدة] --> Header[Header Section]
    HTML --> Upload[Upload Section]
    HTML --> Analysis[Analysis Section]
    HTML --> Diagnosis[Diagnosis Section]
    HTML --> Recommendation[Recommendation Section]
    HTML --> Smart[Smart Enhancement]
    HTML --> Manual[Manual Tools]
    HTML --> Comparison[Comparison Section]
    HTML --> Summary[Summary Section]
    HTML --> Download[Download Section]
    HTML --> Message[Message Area]
    HTML --> Loading[Loading Overlay]
    
    Upload --> Preview[Image Preview]
    Upload --> UploadBtn[Upload Button]
    
    Analysis --> Brightness[السطوع]
    Analysis --> Contrast[التباين]
    Analysis --> Noise[الضوضاء]
    
    Manual --> Group1[الإضاءة والتباين]
    Manual --> Group2[تقليل الضوضاء]
    Manual --> Group3[فصل النص]
    Manual --> Group4[تنظيف البنية]
    Manual --> Group5[تحليل الحواف]
    
    Comparison --> OriginalImg[Original Image]
    Comparison --> ResultImg[Result Image]
    
    style HTML fill:#2c3e50,color:#fff,stroke:#000,stroke-width:2px
    style Upload fill:#3498db,color:#fff
    style Analysis fill:#ecf0f1,color:#000
    style Diagnosis fill:#e74c3c,color:#fff
    style Recommendation fill:#f39c12,color:#fff
    style Smart fill:#27ae60,color:#fff
    style Manual fill:#9b59b6,color:#fff
    style Comparison fill:#1abc9c,color:#fff
    style Summary fill:#34495e,color:#fff
    style Download fill:#e67e22,color:#fff
```

## 7. ملاحظات التصميم

```mermaid
mindmap
  root((تصميم Manuscript Doctor))
    المبادئ
      صفحة واحدة - Single Page
      مسار تحليلي وليس فلاتر
      المستخدم لا يحتاج معرفة OpenCV
      التشخيص قبل الأدوات
    التخطيط
      Desktop - عمودين للمقارنة
      Mobile - عمود واحد للمقارنة
      max-width محدد للحاوية
      centered container
    التفاعل
      ظهور تدريجي للأقسام
      تحميل معطل للأزرار
      Preview قبل الرفع
      كل معالجة من الأصل
    المرئيات
      خلفية هادئة
      الصورة هي العنصر الرئيسي
      Line accent واحد أو اثنان
      تباين جيد للنص
      RTL كامل للنصوص العربية
    القيود
      لا Bootstrap أو Tailwind
      لا مكتبة أيقونات حالياً
      CSS مخصص فقط
      object-fit contain للصور
```
