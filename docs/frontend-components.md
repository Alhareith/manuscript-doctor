# Frontend Components — Manuscript Doctor

يحدد هذا الملف المكونات الأساسية لصفحة HTML الواحدة، قبل كتابة الكود.
كل مكون له معرف (ID) ووصف وظيفي فقط. لا يتضمن كودًا.

---

## قائمة المكونات

| # | اسم المكون | ID مقترح | الوصف | الحالة الافتراضية |
|---|-----------|----------|-------|-------------------|
| 1 | Header | `header-section` | عنوان التطبيق ووصف قصير | ظاهر دائمًا |
| 2 | Upload Area | `upload-section` | منطقة السحب والإفلات + زر اختيار ملف + معاينة + زر "رفع وتحليل" | ظاهر |
| 3 | Image Preview | `upload-preview` | صورة المعاينة قبل الرفع | مخفي |
| 4 | Upload Button | `upload-btn` | زر "رفع وتحليل الصورة" | ظاهر |
| 5 | Analysis Section | `analysis-section` | بطاقات قياس السطوع والتباين والضوضاء + أبعاد الصورة | مخفي |
| 6 | Diagnosis Section | `diagnosis-section` | قائمة المشكلات البصرية المكتشفة | مخفي |
| 7 | Recommendation Section | `recommendation-section` | نص التوصية + زر "تطبيق التحسين المقترح" | مخفي |
| 8 | Smart Enhancement | `smart-section` | خطة المعالجة المقترحة + زر "تحسين تلقائي" | مخفي |
| 9 | Manual Tools | `manual-tools-section` | مجموعات أدوات أكورديون حسب المشكلة | مخفي |
| 10 | Comparison Section | `comparison-section` | عرض Before/After جنبًا إلى جنب | مخفي |
| 11 | Original Image | `original-img` | صورة الأصل في المقارنة | مخفي |
| 12 | Result Image | `result-img` | صورة النتيجة في المقارنة | مخفي |
| 13 | Summary Section | `summary-section` | ملخص العملية: الاسم، الغرض، الملاحظة | مخفي |
| 14 | Download Button | `download-section` | زر "تنزيل النتيجة" | مخفي/معطل |
| 15 | Message Area | `message-area` | منطقة عرض الأخطاء ورسائل الحالة | ظاهر |
| 16 | Loading Overlay | `loading-overlay` | يغطي الأزرار أثناء الرفع/المعالجة مع مؤشر تحميل | مخفي |

---

## ملاحظات

- جميع المكونات في صفحة HTML واحدة.
- JavaScript تتولى إظهار وإخفاء المكونات حسب الحالة (راجع `ui-states.md`).
- لا نستخدم مكتبات خارجية (Bootstrap/Tailwind) حاليًا.
- التصميم النهائي مخصص بـ CSS فقط.
