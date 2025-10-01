
"""الملف الرئيسي لتطبيق واجهة برمجة API المسؤول عن:
1. رفع ملفات PDF واستخراج النصوص.
2. بث (Streaming) التلخيص عبر SSE بشكل تدريجي شبيه ChatGPT.
3. التخزين المؤقت للنصوص والتلخيصات لتقليل الزمن عند التكرار.
4. تهيئة النموذج (Warmup) لتقليل تأخير أول استجابة.
"""

# ============== الإستيرادات الأساسية ==============
import os  # قد يُستخدم مستقبلاً في التعامل مع متغيرات البيئة
import uuid  # لإنشاء معرفات فريدة للجلسات والملفات المؤقتة
import time  # لحساب فترات إنتهاء الصلاحية (TTL)
import asyncio  # لتنفيذ عمليات الإدخال/الإخراج بشكل غير متزامن
import hashlib  # لإنشاء مفاتيح تجزئة (Hash) فريدة من محتوى النص
from pathlib import Path  # للتعامل مع المسارات بشكل آمن
from typing import AsyncGenerator  # لتحديد نوع الدوال المولِّدة غير المتزامنة

import PyPDF2  # مكتبة لاستخراج النصوص من ملفات PDF
from fastapi import FastAPI, UploadFile, HTTPException, Query  # FastAPI لبناء واجهة الAPI
from fastapi.responses import StreamingResponse, JSONResponse  # للرد ببث SSE أو JSON عادي
from fastapi.middleware.cors import CORSMiddleware  # للسماح للواجهة الأمامية بالوصول من دومينات مختلفة

from ai.ollama import stream_summary  # الدالة التي تتولى بث التلخيص من نموذج Ollama
from uploads.config import MAX_PDF_SIZE, DEFAULT_MODEL, OLLAMA_MODELS  # الإعدادات العامة من ملف التهيئة

# ============== إنشاء تطبيق FastAPI ==============
app = FastAPI(title="AI PDF Summarizer API", version="1.1.0")

# حدث تشغيل مبدئي للتسخين (Warmup) لتسريع أول استجابة
@app.on_event("startup")
async def _warmup():
    """Warmup model with a tiny request to reduce first-token latency."""
    sample_text = "اختبار تمهيدي صغير"  # very short
    try:
        # consume a few tokens then break
        gen = stream_summary(sample_text, model=DEFAULT_MODEL, add_status=False)
        count = 0
        async for chunk in gen:
            if chunk.startswith("data: "):
                count += 1
            if count > 3:
                break
    except Exception:
        pass
    
# ============== هياكل التخزين داخل الذاكرة ==============
text_storage: dict[str, str] = {}  # تخزين النص الخام المستخرج لكل جلسة session_id -> text
summary_cache: dict[str, tuple[float, str]] = {}  # تخزين التلخيص النهائي (زمن التخزين, التلخيص)
CACHE_TTL = 60 * 10  # مدة صلاحية التلخيص في الذاكرة (ثوانٍ) = 10 دقائق

# مجلد الملفات المؤقتة (النسخ المرفوعة من المستخدم)
UPLOAD_DIR = Path("temp")
UPLOAD_DIR.mkdir(exist_ok=True)  # إنشاء المجلد إن لم يكن موجوداً

FILE_TTL_SECONDS = 60 * 30  # حذف ملفات الـ PDF المؤقتة الأقدم من 30 دقيقة

def _cleanup_old_files() -> None:
    """تنظيف الملفات القديمة من المجلد المؤقت لتوفير المساحة."""
    now = time.time()
    for p in UPLOAD_DIR.glob("*.pdf"):
        try:
            # إذا مر وقت أكبر من حد TTL نحذف الملف
            if now - p.stat().st_mtime > FILE_TTL_SECONDS:
                p.unlink(missing_ok=True)
        except OSError:
            # نتجاهل الأخطاء (مثلاً عند حذف متزامن أو صلاحيات)
            pass

# ============== إعداد CORS للسماح لتطبيق الواجهة الأمامية بالاتصال ==============
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # يمكن تقييد النطاقات في بيئة الإنتاج
    allow_credentials=True,
    allow_methods=["*"],  # السماح بكل أنواع الطلبات (GET/POST/DELETE...)
    allow_headers=["*"],
)


# def extract_text_from_pdf(file):
#     reader = PyPDF2.PdfReader(file.file)
#     text = ""
#     for page in reader.pages:
#         if page.extract_text():
#             text += page.extract_text() + "\n"
#     return text.strip()


def extract_text_from_pdf(file_path: Path) -> str:
    """استخراج النص من ملف PDF صفحة بصفحة.

    ملاحظات:
    - PyPDF2 قد يفشل في بعض الصفحات التالفة، لذا نحاول ونتجاهل الصفحة إن فشل.
    - يتم دمج النصوص في سلسلة واحدة مفصولة بأسطر جديدة.
    - يمكن لاحقاً تحسين الأداء بتقسيم محتوى كبير إلى أجزاء للتلخيص المرحلي.
    """
    reader = PyPDF2.PdfReader(str(file_path))
    parts: list[str] = []  # تجميع النصوص هنا
    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""  # قد تعيد الدالة None
        except Exception:  # في حالة صفحة تالفة أو خطأ داخلي
            page_text = ""
        if page_text:
            parts.append(page_text)
    return "\n".join(parts).strip()  # دمج كل الصفحات في نص واحد



@app.post("/upload")
async def upload_pdf(file: UploadFile):
    """نقطة نهاية لرفع ملف PDF ثم استخراج النص وتخزينه وإرجاع session_id.

    خطوات التنفيذ:
    1. التحقق من نوع الملف.
    2. قراءة البيانات في الذاكرة والتحقق من الحجم.
    3. حفظ نسخة مؤقتة على القرص.
    4. استخراج النص من النسخة المؤقتة.
    5. توليد معرف جلسة وتخزين النص في الذاكرة.
    6. إعادة المعرف للواجهة الأمامية لطلب التلخيص لاحقاً.
    """
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail="Unsupported file type. Must be PDF.")  # نوع غير مدعوم

    data = await file.read()  # قراءة كل الملف داخل الذاكرة
    if len(data) > MAX_PDF_SIZE:
        raise HTTPException(status_code=413, detail="File too large.")  # الملف أكبر من الحد المسموح

    pdf_path = UPLOAD_DIR / f"{uuid.uuid4()}.pdf"  # اسم فريد للملف المؤقت
    # كتابة الملف على القرص باستخدام منفذ (Executor) لتجنب حظر الحدث الرئيسي
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, pdf_path.write_bytes, data)

    try:
        text = extract_text_from_pdf(pdf_path)
    except Exception as e:  # فشل في التحليل أو القراءة
        raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {e}")

    if not text.strip():  # ملف فارغ أو لا يحتوي نص مستخرج
        raise HTTPException(status_code=422, detail="No extractable text found in PDF.")

    session_id = str(uuid.uuid4())  # إنشاء معرف جلسة فريد
    text_storage[session_id] = text  # تخزين النص في الذاكرة
    _cleanup_old_files()  # تنظيف الملفات القديمة بشكل دوري
    return {"session_id": session_id, "characters": len(text)}  # إرجاع عدد المحارف للمعلومة

async def _sse_generator(text: str, model: str | None) -> AsyncGenerator[bytes, None]:
    """مولِّد (Generator) يبث التلخيص بآلية Server-Sent Events.

    آلية العمل:
    1. يُحسب مفتاح تجزئة يعتمد على النص + النموذج لتفادي إعادة الحساب.
    2. إذا وُجد تلخيص مخزون ضمن فترة TTL يُعاد مباشرة (CACHE_HIT).
    3. خلاف ذلك يتم استدعاء النموذج وإرسال الرموز (Tokens) تدريجياً للواجهة.
    4. بعد الانتهاء يُخزن التلخيص النهائي في الذاكرة للتسريع مستقبلاً.
    """
    model_key = model or DEFAULT_MODEL  # استخدام النموذج الافتراضي إن لم يُحدد
    # نصنع مفتاحاً فريداً يعتمد على: النموذج + طول النص + قيمة hash الديناميكية للنص
    cache_key = hashlib.sha256(f"{model_key}:full:{len(text)}:{hash(text)}".encode()).hexdigest()
    now = time.time()
    cached = summary_cache.get(cache_key)
    if cached and now - cached[0] < CACHE_TTL:
        # إبلاغ الواجهة أن النتيجة من الكاش ثم بث التلخيص النهائي دفعة واحدة
        yield b"event: status\ndata: CACHE_HIT\n\n"
        yield f"data: {cached[1]}\n\n".encode("utf-8")
        yield b"event: status\ndata: DONE\n\n"
        return
    collected: list[str] = []  # لتجميع التوكنات لإعادة بناء النص النهائي وتنظيفه
    async for chunk in stream_summary(text, model=model_key):  # تدفق الرموز من النموذج
        if chunk.startswith("data: "):
            token = chunk[6:].rstrip("\n")  # إزالة بادئة data: و نهاية السطر
            collected.append(token)
        yield chunk.encode("utf-8")  # بث نفس القطعة للمتصفح كما هي
    if collected:
        raw = "".join(collected)  # دمج التوكنات كما وصلت
        import re  # استخدام التعبيرات النمطية للتنظيف
        text_norm = re.sub(r"\s+", " ", raw).strip()  # تقليص المسافات المتكررة
        text_norm = re.sub(r"\*{2,}", "**", text_norm)  # دمج النجوم المكررة
        text_norm = re.sub(r"\s+([،؛,.!?])", r"\1", text_norm)  # إزالة مسافة قبل علامات الترقيم
        text_norm = re.sub(r"([،؛,.!?])(\S)", r"\1 \2", text_norm)  # ضمان مسافة بعد الترقيم
        if text_norm:
            summary_cache[cache_key] = (time.time(), text_norm)  # تخزين التلخيص في الكاش

@app.get("/stream/{session_id}")
async def stream(session_id: str, model: str | None = Query(default=None, description="Override model")):
    """بث التلخيص الخاص بجلسة معينة باستخدام SSE.

    - تتلقى الواجهة الأمامية معرف الجلسة من /upload ثم تنشئ اتصال SSE.
    - يمكن اختيار نموذج مختلف عبر بارامتر الاستعلام model.
    - يتم إرسال التوكنات فور وصولها من النموذج لتجربة تفاعلية.
    """
    text = text_storage.get(session_id)
    if text is None:
        raise HTTPException(status_code=404, detail="Session not found")  # جلسة غير موجودة
    headers = {
        "Cache-Control": "no-cache",  # منع التخزين المؤقت الوسيط
        "X-Accel-Buffering": "no",  # لتعطيل Buffering في Nginx إن وُجد
    }
    return StreamingResponse(_sse_generator(text, model), media_type="text/event-stream", headers=headers)

@app.get("/health")
async def health():
    """فحص حالة الخدمة وإرجاع عدد الجلسات الحالية في الذاكرة."""
    return {"status": "ok", "sessions": len(text_storage)}

@app.get("/models")
async def models():
    """إرجاع النموذج الافتراضي وقائمة النماذج المدعومة للاختيار من الواجهة."""
    return {"default": DEFAULT_MODEL, "models": OLLAMA_MODELS}

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """حذف جلسة وتفريغ النص المخزن الخاص بها من الذاكرة لتقليل الاستخدام."""
    removed = text_storage.pop(session_id, None)
    return JSONResponse({"removed": bool(removed)})


# @app.post("/summarize/")
# async def summarize(file: UploadFile):
#     text = extract_text_from_pdf(file)
#     print(text)
#     if not text:
#         return {"error": "الملف فارغ أو لم يتم استخراج النص"}
#     return StreamingResponse(stream_summary(text), media_type="text/event-stream")