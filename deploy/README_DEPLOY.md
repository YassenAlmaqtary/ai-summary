# دليل نشر مشروع تلخيص الدروس على خادم VPS

هذا الدليل يوضح كيفية تجهيز الخادم (Ubuntu 22.04 كمثال) وتشغيل الواجهة الخلفية (FastAPI) والواجهة الأمامية (Vue) خلف Nginx مع خدمة systemd للتشغيل التلقائي.

## 1. تحديث الخادم وتثبيت المتطلبات
```bash
sudo apt update && sudo apt -y upgrade
sudo apt install -y python3 python3-venv python3-pip git nginx curl unzip
# اختيارياً (لبناء الواجهة الأمامية)
sudo apt install -y nodejs npm
```

تحقق من نسخة Node (إن كانت قديمة جداً، ثبّت واحدة أحدث من موقع NodeSource):
```bash
node -v
npm -v
```

## 2. إنشاء مستخدم (اختياري لكنه أفضل أماناً)
```bash
sudo adduser --disabled-password --gecos "AI Summary" aisummary
sudo usermod -aG sudo aisummary
```

## 3. جلب الكود إلى الخادم
```bash
sudo mkdir -p /opt/ai-summary
sudo chown aisummary:aisummary /opt/ai-summary
cd /opt/ai-summary
git clone <REPO_URL> .
```

## 4. إعداد البيئة الافتراضية للبايثون وتشغيل التثبيت
```bash
cd back-end
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

أنشئ ملف البيئة `.env` (مثال موجود: `back-end/.env.example`):
```bash
cp .env.example .env
nano .env
```
عدّل القيم حسب بيئتك.

## 5. اختبار التشغيل اليدوي
```bash
cd /opt/ai-summary/back-end
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 9000 --workers 2 --proxy-headers
```
اختبر: `curl http://SERVER_IP:9000/health`

## 6. بناء الواجهة الأمامية (Vue)
```bash
cd /opt/ai-summary/front-end
npm install
npm run build
```
سيتم إنشاء مجلد `dist/`.

انسخ الناتج إلى مسار سيستضيفه Nginx:
```bash
sudo mkdir -p /var/www/ai-summary
sudo rsync -a dist/ /var/www/ai-summary/
sudo chown -R www-data:www-data /var/www/ai-summary
```

لاحقاً بعد أي تعديل: `npm run build && rsync -a dist/ /var/www/ai-summary/`.

## 7. إعداد خدمة systemd للباك إند
حرّر الملف `deploy/backend.service` إذا احتجت تغيير المسارات ثم انسخه إلى systemd:
```bash
sudo cp /opt/ai-summary/deploy/backend.service /etc/systemd/system/ai-summary.service
sudo systemctl daemon-reload
sudo systemctl enable ai-summary --now
systemctl status ai-summary
```

## 8. إعداد Nginx كـ Reverse Proxy + ملفات ثابتة
انسخ الملف: `deploy/nginx.conf.example` إلى `/etc/nginx/sites-available/ai-summary` ثم:
```bash
sudo cp /opt/ai-summary/deploy/nginx.conf.example /etc/nginx/sites-available/ai-summary
sudo ln -s /etc/nginx/sites-available/ai-summary /etc/nginx/sites-enabled/ai-summary
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

اختبر من المتصفح: `http://your-domain/`

## 9. تفعيل HTTPS (Let's Encrypt)
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```
تأكد من وجود كتلة `ssl_certificate` في ملف Nginx بعد الإعداد.

## 10. التحديثات (Deploy جديد)
```bash
cd /opt/ai-summary
git pull
cd back-end
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart ai-summary
# إعادة بناء الواجهة الأمامية إذا لزم
cd ../front-end
npm run build
sudo rsync -a dist/ /var/www/ai-summary/
```

## 11. ضبط الجدار الناري (UFW)
```bash
sudo apt install -y ufw
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

## 12. متغيرات البيئة المهمة
| المتغير | الوصف |
|---------|-------|
| OLLAMA_API_URL | عنوان خدمة نموذج Ollama أو API آخر |
| OLLAMA_MODEL | النموذج الافتراضي (مثلاً gemma:2b) |
| OLLAMA_MODELS | قائمة نماذج مفصولة بفواصل لاختيارها من الواجهة |
| MAX_PDF_SIZE | الحد الأقصى لحجم PDF بالبايت (مثلاً 15728640 = 15MB) |

## 13. النسخ الاحتياطي
- احفظ نسخة من: `.env`, وملفات `deploy/` وأي محتوى مستقبلي.
- إن أضفت قاعدة بيانات لاحقاً (Redis / Postgres) أضف مهام cron للنسخ.

## 14. تحسينات اختيارية
- إضافة Redis للكاش بدل الذاكرة (للاستخدامات المتعددة).
- إعداد مراقبة باستخدام `pm2 logrotate` أو `prometheus node exporter`.
- إضافة ضغط Gzip / Brotli في Nginx.

## 15. فحص سريع بعد النشر
```bash
curl -I http://your-domain/
curl http://your-domain/api/health || curl http://your-domain/health
```

## 16. معالجة مشاكل شائعة
| المشكلة | السبب المحتمل | الحل |
|---------|---------------|------|
| 502 Bad Gateway | خدمة uvicorn متوقفة | `systemctl status ai-summary` ثم مراجعة السجل |
| CORS في المتصفح | خطأ تهيئة Nginx أو المنافذ | تأكد من تمرير الطلبات للمنفذ 9000 وإبقاء allow_origins في FastAPI |
| بطء أول استجابة | التسخين الأولي | يوجد warmup في الكود؛ يمكن زيادة عدد الـ workers |

---
تم — يمكنك الآن الدخول للنظام عبر الدومين. لأي تحسين إضافي (Docker / CI) أضفه لاحقاً.
