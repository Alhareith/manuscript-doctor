<div dir="rtl" align="right">

# طبقة CSS

يُستخدم `static/css/style.css` كنقطة تجميع، بينما تُحفظ قواعد التصميم داخل `static/css/parts/` بحسب المنطقة والمسؤولية. هذا التقسيم يقلل أثر التعديل ويجعل مراجعة التخطيط المتجاوب والثيم أكثر وضوحاً.

## ترتيب الأجزاء

| الملف | نطاقه |
| --- | --- |
| `01-foundation-header.css` | الأساس، الخطوط، وHeader |
| `02-workflow-main.css` | شريط سير العمل والتخطيط الرئيسي |
| `03-upload-buttons.css` | الرفع والأزرار |
| `04-processing-analysis.css` | التحليل ولوحات المؤشرات |
| `05-treatment-manual.css` | العمليات اليدوية والمحرر |
| `06-crop-history-footer.css` | Crop والسجل والفوتر |
| `07-theme-layout.css` | الثيم والتخطيط العام |
| `08-manual-studio.css` | مساحة العمل اليدوية |
| `09-preview-dashboard.css` | Preview وDashboard |
| `10-icons-responsive.css` | الأيقونات والاستجابة للشاشات |

يُحافظ `style.css` على هذا الترتيب، ويحتوي في نهايته على override خاص بخلفية Header لضمان ظهور الصورة العريضة كاملة داخل `.app-header`. لا توجد صورة Hero منفصلة في الواجهة الحالية.

## قواعد التعديل

يجب أن يبقى التصميم متوافقاً مع RTL وDesktop وMobile، وأن تُجمع قواعد المنطقة في الجزء المناسب بدلاً من إضافة CSS عشوائي إلى نقطة التجميع. عند تغيير ID أو حالة واجهة، راجع ملفات JavaScript والقالب معاً.

</div>
