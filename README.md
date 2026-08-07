
# Manuscript Doctor

نظام ذكي لمعالجة وتحليل المخطوطات والوثائق التاريخية باستخدام تقنيات معالجة الصور والتعلم الآلي.

---

## 📁 هيكلية المشروع (Project Structure)

```text
manuscript-doctor/
│
├── .venv/               # بيئة Python الافتراضية (محلية فقط)
├── processing/          # خوارزميات معالجة الصور (OpenCV & NumPy)
├── templates/           # واجهات المستخدم (HTML Templates)
├── static/              # الملفات الثابتة (CSS / JS / Images)
├── storage/             # مخزن المخطوطات والنتائج
├── tests/               # الاختبارات التلقائية (pytest)
├── docs/                # التوثيق والقرارات المعمارية
├── app.py               # نقطة انطلاق تطبيق Flask
├── requirements.txt     # الاعتماديات المعتمدة للمشروع
└── README.md            # دليل الإعداد والتشغيل

```

---

## 📋 المتطلبات الأساسية (Prerequisites)

* **Python:** `3.12.x`

---

## 🚀 دليل إعداد بيئة التطوير (Development Setup)

### 1. إنشاء البيئة الافتراضية

من جذر المشروع داخل الـ Terminal:

```cmd
py -3.12 -m venv .venv
```

### 2. تفعيل البيئة الافتراضية

على نظام Windows (CMD):

```cmd
.venv\Scripts\activate
```

*تأكد من ظهور `(.venv)` في بداية السطر.*

### 3. تحديث مدير الحزم pip

```cmd
python -m pip install --upgrade pip
```

### 4. تثبيت مكتبات المشروع

```cmd
python -m pip install -r requirements.txt
```

---

## ✅ التحقق من صحة البيئة (Environment Verification)

لتأكيد سلامة البيئة واستيراد جميع المكتبات الأساسية بنجاح، نفّذ:

```cmd
python -c "import flask, cv2, numpy; print('Environment OK')"
```

للتحقق من أداة الاختبارات `pytest`:

```cmd
python -m pytest --version
```

---
