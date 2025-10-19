
"""الملف الرئيسي لتطبيق واجهة برمجة API المسؤول عن:
1. رفع ملفات PDF واستخراج النصوص.
2. بث (Streaming) التلخيص عبر SSE بشكل تدريجي شبيه ChatGPT.
3. التخزين المؤقت للنصوص والتلخيصات لتقليل الزمن عند التكرار.
4. تهيئة النموذج (Warmup) لتقليل تأخير أول استجابة.
"""

# ============== الإستيرادات الأساسية ==============
import uuid  # لإنشاء معرفات فريدة للجلسات والملفات المؤقتة
import time  # لحساب فترات إنتهاء الصلاحية (TTL)
import asyncio  # لتنفيذ عمليات الإدخال/الإخراج بشكل غير متزامن
import hashlib  # لإنشاء مفاتيح تجزئة (Hash) فريدة من محتوى النص
from pathlib import Path  # للتعامل مع المسارات بشكل آمن
from typing import AsyncGenerator  # لتحديد نوع الدوال المولِّدة غير المتزامنة
import logging

import PyPDF2  # مكتبة لاستخراج النصوص من ملفات PDF
from fastapi import FastAPI, UploadFile, HTTPException, Query  # FastAPI لبناء واجهة الAPI
from fastapi.responses import StreamingResponse, JSONResponse  # للرد ببث SSE أو JSON عادي
from fastapi.middleware.cors import CORSMiddleware
import pypdfium2 

## تم الاستغناء عن Ollama، الربط الآن مع Gemini فقط
from uploads.config import (
    MAX_PDF_SIZE,
    DEFAULT_MODEL,
    gemini_models,
    client,
    FRONTEND_ORIGINS,
    ALLOW_ORIGIN_REGEX,
)

# ============== إنشاء تطبيق FastAPI ==============
app = FastAPI(title="AI PDF Summarizer API", version="1.1.0")

# إعداد لوج بسيط مع الوقت والمستوى
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("ai-summary")
# حدث تشغيل مبدئي للتسخين (Warmup) لتسريع أول استجابة
@app.on_event("startup")
async def _warmup():
    """Warmup model with a tiny request to reduce first-token latency."""
    sample_text = "اختبار تمهيدي صغير"  # very short
    try:
        # run sync streaming in executor to avoid blocking event loop
        def _do_warmup():
            stream = client.models.generate_content_stream(
                model=DEFAULT_MODEL,
                contents=[sample_text]
            )
            # consume a couple of chunks then stop
            taken = 0
            for chunk in stream:
                if getattr(chunk, "text", None):
                    taken += 1
                if taken >= 2:
                    break

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _do_warmup)
    except Exception:
        # ignore warmup errors
        pass
    
# ============== هياكل التخزين داخل الذاكرة ==============
text_storage: dict[str, str] = {}  # تخزين النص الخام المستخرج لكل جلسة session_id -> text
summary_cache: dict[str, tuple[float, str]] = {}  # تخزين التلخيص النهائي (زمن التخزين, التلخيص)
CACHE_TTL = 60 * 10  # مدة صلاحية التلخيص في الذاكرة (ثوانٍ) = 10 دقائق

# مهام استخراج قيد التنفيذ لكل جلسة
pending_extractions: dict[str, asyncio.Task] = {}

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


async def _extract_and_store(session_id: str, pdf_path: Path) -> None:
    """تشغيل استخراج النص في منفذ (ThreadPool) ثم تخزينه وحذف الملف المؤقت."""
    start = time.time()
    loop = asyncio.get_running_loop()
    try:
        text = await loop.run_in_executor(None, extract_text_from_pdf, pdf_path)
        # حذف الملف المؤقت بعد الاستخراج
        try:
            pdf_path.unlink(missing_ok=True)
        except Exception:
            pass
        text_storage[session_id] = text or ""
        log.info("extracted text for %s in %.2fs (chars=%d)", session_id, time.time()-start, len(text or ""))
    except Exception as e:
        text_storage[session_id] = ""
        log.exception("failed to extract text for %s: %s", session_id, e)
    finally:
        pending_extractions.pop(session_id, None)

# ============== إعداد CORS للسماح لتطبيق الواجهة الأمامية بالاتصال ==============
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_origin_regex=ALLOW_ORIGIN_REGEX or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# def extract_text_from_pdf(file_path: Path) -> str:
#     """استخراج النص من ملف PDF صفحة بصفحة.

#     ملاحظات:
#     - PyPDF2 قد يفشل في بعض الصفحات التالفة، لذا نحاول ونتجاهل الصفحة إن فشل.
#     - يتم دمج النصوص في سلسلة واحدة مفصولة بأسطر جديدة.
#     - يمكن لاحقاً تحسين الأداء بتقسيم محتوى كبير إلى أجزاء للتلخيص المرحلي.
#     """
#     reader = PyPDF2.PdfReader(str(file_path))
#     parts: list[str] = []  # تجميع النصوص هنا
#     for page in reader.pages:
#         try:
#             page_text = page.extract_text() or ""  # قد تعيد الدالة None
#         except Exception:  # في حالة صفحة تالفة أو خطأ داخلي
#             page_text = ""
#         if page_text:
#             parts.append(page_text)
#     return "\n".join(parts).strip()  # دمج كل الصفحات في نص واحد

def extract_text_from_pdf(file_path: Path) -> str:
    pdf = pypdfium2.PdfDocument(file_path)
    return "\n".join(page.get_textpage().get_text_range() for page in pdf)


def _encode_sse_chunk(text: str) -> bytes:
    """تهيئة نص خام ليكون متوافقاً مع صيغة SSE (data: ...)."""
    if not text:
        return b"data: \n\n"
    sanitized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = sanitized.split("\n")
    payload = "".join(f"data: {line}\n" for line in lines)
    return (payload + "\n").encode("utf-8")



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

    # اسم فريد للملف المؤقت
    session_id = str(uuid.uuid4())
    pdf_path = UPLOAD_DIR / f"{session_id}.pdf"

    # كتابة الملف على القرص باستخدام منفذ (Executor) لتجنب حظر الحدث الرئيسي
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, pdf_path.write_bytes, data)
    except PermissionError:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Server error: Permission denied to save file. "
                f"Check server user permissions on {UPLOAD_DIR} directory."
            ),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Server I/O error during file save: {type(e).__name__}.",
        )

    # بدء الاستخراج في الخلفية لتقليل زمن انتظار العميل
    task = asyncio.create_task(_extract_and_store(session_id, pdf_path))
    pending_extractions[session_id] = task
    _cleanup_old_files()  # تنظيف الملفات القديمة بشكل دوري
    log.info("accepted upload session=%s size=%.2fKB", session_id, len(data)/1024)
    # نعيد session_id فوراً؛ الواجهة ستفتح SSE وسيتم الانتظار هناك إن لم يكتمل الاستخراج بعد
    return {"session_id": session_id, "characters": 0}




# تم إلغاء نقطة /stream القديمة. استخدم /summarize-gemini فقط.

@app.get("/health")
async def health():
    """فحص حالة الخدمة وإرجاع عدد الجلسات الحالية في الذاكرة."""
    return {"status": "ok", "sessions": len(text_storage)}

@app.get("/models")
async def models():
    """إرجاع النموذج الافتراضي وقائمة النماذج المدعومة للاختيار من الواجهة."""
    return {"default": DEFAULT_MODEL, "models":gemini_models}

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """حذف جلسة وتفريغ النص المخزن الخاص بها من الذاكرة لتقليل الاستخدام."""
    removed = text_storage.pop(session_id, None)
    return JSONResponse({"removed": bool(removed)})


@app.get("/summarize-gemini")
async def summarize_gemini(session_id: str = Query(...), model: str | None = None, language: str = Query("العربية")):
    model_key = model or DEFAULT_MODEL

    # نبني الـ prompt لاحقاً بعد التأكد من توفر النص
    def build_prompt(text: str) -> str:
        return (
        "أنت خبير تربوي ومصمم محتوى أكاديمي متخصص في تحويل النصوص الإسلامية والعلمية إلى دروس تفاعلية جذابة.\n\n"
        "### 🎯 الهدف:\n"
        "أنشئ ملخصًا احترافيًا للنص التالي ليبدو كدرس تعليمي منظم للطلاب في موقع حديث.\n\n"
        "### 🧭 التعليمات:\n"
        "1. استخدم تنسيق **Markdown** الكامل:\n"
        "   - العنوان الرئيسي باستخدام `#`.\n"
        "   - العناوين الفرعية للأفكار باستخدام `##`.\n"
        "   - الفقرات القصيرة لا تتجاوز 4 أسطر.\n"
        "   - القوائم المنقطة والمرقمة لعرض النقاط بوضوح.\n"
        "   - استخدم **bold** للكلمات المفتاحية المهمة.\n\n"
        "2. ابدأ بفقرة تمهيدية جذابة بعنوان **ملخص سريع** تشرح الفكرة العامة للنص.\n"
        "3. بعد ذلك، نظّم المحتوى إلى أقسام واضحة (مثلاً: **أهمية القرآن**، **النتائج المترتبة على الإهمال**، **دروس من قصة آدم** ... إلخ).\n"
        "4. أضف رموزًا أو عناوين فرعية مثل: ✨ **دروس مستفادة** أو 💡 **فكرة رئيسية** لإضفاء طابع تفاعلي.\n"
        "5. في نهاية النص، أنشئ قسمًا بعنوان `## أسئلة وأجوبة` يحتوي من 3 إلى 7 أسئلة تدريبية تساعد الطالب على الفهم والمراجعة.\n"
        "6. اجعل الأسلوب **تعليميًا مبسطًا** وليس وعظيًا، مع لمسة إيمانية ملهمة.\n"
        "7. لا تكتب أي شروحات إضافية خارج النص.\n\n"
        f"### 🧾 النص المراد تلخيصه:\n{text}"
    )


    async def wait_for_text() -> str:
        text = text_storage.get(session_id)
        if text is not None:
            return text
        t = pending_extractions.get(session_id)
        if t is None:
            # لا يوجد نص ولا مهمة معلّقة
            raise HTTPException(status_code=404, detail="الجلسة غير موجودة أو انتهت صلاحيتها")
        # انتظر اكتمال الاستخراج ولكن لا نحجب الحدث الرئيسي؛ سيتم الانتظار داخل خيط البث
        try:
            await t
        except Exception:
            pass
        return text_storage.get(session_id, "")

    async def sse_gen() -> AsyncGenerator[bytes, None]:
        # بث فوري لحالة البدء
        yield b"event: status\ndata: START\n\n"
        # أخبر الواجهة أن الاستخراج قيد التحضير إن لم يكن النص جاهزاً
        if session_id in pending_extractions and session_id not in text_storage:
            yield b"event: status\ndata: EXTRACTING\n\n"
        try:
            text_ready = await wait_for_text()

            if not (text_ready and text_ready.strip()):
                yield b"event: error\ndata: No extractable text found in PDF.\n\n"
                return

            # التحقق من الكاش حسب تجزئة النص
            h = hashlib.sha256(text_ready.encode("utf-8")).hexdigest()
            now = time.time()
            cached = summary_cache.get(h)
            if cached and now - cached[0] < CACHE_TTL:
                log.info("cache hit for summary h=%s", h[:8])
                summary_text = cached[1]
                step = 800
                for i in range(0, len(summary_text), step):
                    chunk = summary_text[i:i+step]
                    yield _encode_sse_chunk(chunk)
                yield b"event: status\ndata: DONE\n\n"
                return

            # لا يوجد كاش: اطلب من النموذج مع تتبع الزمن واجمع الناتج للتخزين لاحقاً
            prompt = build_prompt(text_ready)
            t0 = time.time()
            stream = client.models.generate_content_stream(
                model=model_key,
                contents=[prompt]
            )
            buf_parts: list[str] = []
            for chunk in stream:
                token = getattr(chunk, "text", None)
                if token:
                    buf_parts.append(token)
                    yield _encode_sse_chunk(token)
            full = "".join(buf_parts)
            summary_cache[h] = (time.time(), full)
            log.info("summary generated len=%d in %.2fs (cache key=%s)", len(full), time.time()-t0, h[:8])
            yield b"event: status\ndata: DONE\n\n"
        except HTTPException as he:
            yield f"event: error\ndata: {he.detail}\n\n".encode("utf-8")
        except Exception as e:
            log.exception("sse error: %s", e)
            yield f"event: error\ndata: {str(e)}\n\n".encode("utf-8")
    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(sse_gen(), media_type="text/event-stream", headers=headers)
  