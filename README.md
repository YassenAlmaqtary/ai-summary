# AI PDF Arabic Summarizer

نظام متكامل (FastAPI + Vue 3) لتلخيص ملفات PDF باللغة العربية مع بث حي (SSE) للناتج.

## المزايا
- رفع PDF واستخراج النص تلقائيًا
- تلخيص حي متدفق (Token Streaming)
- دعم إلغاء العملية ونسخ/تنزيل الملخص
- واجهة عصرية متجاوبة RTL
- إدارة جلسات عبر معرف Session ID
- فحص صحة الملف (الحجم والنوع)
- تنظيف تلقائي للملفات المؤقتة

## المتطلبات
- Python 3.10+
- Node.js 20+

## الإعداد (Back-end)
```bash
cd back-end
python -m venv venv
# تفعيل البيئة (Windows PowerShell)
./venv/Scripts/Activate.ps1
pip install -r requirements.txt

# ملف بيئة اختياري
copy .env.example .env  # ثم عدل القيم
uvicorn main:app --host 0.0.0.0 --port 9000 --reload
```

## الإعداد (Front-end)
```bash
cd front-end
npm install
npm run dev
```

افتح المتصفح على: http://localhost:5173

## متغيرات البيئة `.env`
```
OLLAMA_API_URL=http://31.97.61.156:11434/api/generate
OLLAMA_MODEL=gemma:2b
MAX_PDF_SIZE=15728640
```

## تحسينات مستقبلية مقترحة
- دعم Chunking للنصوص الطويلة جدًا
- إضافة Tailwind أو UnoCSS لتسريع التطوير
- دعم نماذج متعددة selectable من الواجهة
- إضافة مصادقة JWT لوضع SaaS
- نظام Queue لو ازدحمت الطلبات

## الرخصة
مفتوح للاستخدام الداخلي. أضف رخصتك لاحقًا.
