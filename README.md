# AI PDF Arabic Summarizer

منصة تلخيص عربية تعتمد FastAPI (Back-end) + Vue 3 (Front-end) مع بث حي (Server-Sent Events) للملخص أثناء توليده.

## ⭐ المزايا الرئيسية
- رفع PDF واستخراج النص تلقائياً (PyPDF2)
- تلخيص متدفق لحظي (SSE) يشبه ChatGPT
- واجهة عربية RTL + أوضاع عرض (جانبي / متراكم / تركيز)
- نسخ / تنزيل / تفريغ الملخص + إلغاء العملية
- كاش داخلي للتلخيص لتسريع الطلبات المكررة
- تنظيف دوري للملفات المؤقتة + حد حجم ملف
- دعم اختيار النموذج ديناميكياً عبر `/models`
- تسخين (Warmup) عند بدء التشغيل لتقليل تأخير أول توكن

## 📂 بنية المشروع
```
back-end/        كود FastAPI + منطق التلخيص + استخراج PDF
front-end/       واجهة Vue 3 (Vite)
deploy/          ملفات النشر (systemd + nginx + سكربت)
```

## 🧪 المتطلبات
- Python 3.10+
- Node.js ^20

## ⚙️ الإعداد السريع (محلي)
### Back-end
```bash
cd back-end
python -m venv venv
source venv/bin/activate        # Windows: .\\venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env            # عدّل الإعدادات داخله
uvicorn main:app --host 0.0.0.0 --port 9000 --reload
```

### Front-end
```bash
cd front-end
npm install
npm run dev
```
زر: http://localhost:5173

## 🌍 متغيرات البيئة (back-end/.env)
| المتغير | مثال | الوصف |
|---------|-------|-------|
| OLLAMA_API_URL | http://localhost:11434/api/generate | مسار خدمة النموذج |
| OLLAMA_MODEL | gemma:2b | النموذج الافتراضي |
| OLLAMA_MODELS | gemma:2b,gemma:7b,phi3:mini | قائمة الاختيار في الواجهة |
| MAX_PDF_SIZE | 15728640 | حد الحجم (15MB) |

## 🚀 نشر على VPS (مختصر)
تفاصيل موسعة في: `deploy/README_DEPLOY.md`
```bash
git clone <repo>
cd back-end && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && cp .env.example .env
cd ../front-end && npm install && npm run build
sudo rsync -a dist/ /var/www/ai-summary/
sudo cp ../deploy/backend.service /etc/systemd/system/ai-summary.service && sudo systemctl enable ai-summary --now
sudo cp ../deploy/nginx.conf.example /etc/nginx/sites-available/ai-summary && sudo ln -s /etc/nginx/sites-available/ai-summary /etc/nginx/sites-enabled/ai-summary && sudo systemctl restart nginx
```

## 🧪 CI (GitHub Actions)
عند الدفع إلى main:
- يبني الواجهة الأمامية
- يفحص استيراد الـ Back-end + lint (ruff)
الملف: `.github/workflows/ci.yml`

## ✅ مهام صيانة مقترحة
- إضافة Redis للكاش بدل الذاكرة.
- إضافة اختبار وحدات (pytest) لاستخراج النص ودالة التلخيص الوهمية.
- تفعيل ضغط Gzip/Brotli في Nginx.
- إضافة مراقبة (Prometheus / Grafana) لاحقاً.

## 🔒 أمان
- لا ترفع `.env` (موجود في `.gitignore`).
- حدّث الحزم دورياً.
- راقب حجم مجلد temp أو استخدم تخزين متطاير (tmpfs) عند الحاجة.

## 📝 رخصة
لم تُحدد بعد. أضف ملف LICENSE إذا رغبت في الفتح أو التقييد.

## 🙌 مساهمة
أنشئ فرع feature/اسم-الميزة ثم افتح Pull Request.

---
جاهز للعمل. استمتع ✨
