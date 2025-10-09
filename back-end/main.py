
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

import PyPDF2  # مكتبة لاستخراج النصوص من ملفات PDF
from fastapi import FastAPI, UploadFile, HTTPException, Query  # FastAPI لبناء واجهة الAPI
from fastapi.responses import StreamingResponse, JSONResponse  # للرد ببث SSE أو JSON عادي
from fastapi.middleware.cors import CORSMiddleware  # للسماح للواجهة الأمامية بالوصول من دومينات مختلفة

## تم الاستغناء عن Ollama، الربط الآن مع Gemini فقط
from uploads.config import (
    MAX_PDF_SIZE,
    DEFAULT_MODEL,
    gemini_models,
    OLLAMA_MODELS,
    client,
    FRONTEND_ORIGINS,
    ALLOW_ORIGIN_REGEX,
)

# ============== إنشاء تطبيق FastAPI ==============
app = FastAPI(title="AI PDF Summarizer API", version="1.1.0")
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
    allow_origins=FRONTEND_ORIGINS,
    allow_origin_regex=ALLOW_ORIGIN_REGEX or None,
    allow_credentials=True,
    allow_methods=["*"],
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
    
   # ============= عزل أخطاء الكتابة (السبب المحتمل للخطأ 500) =============
    try:
        # كتابة الملف على القرص باستخدام منفذ (Executor)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, pdf_path.write_bytes, data)
    except PermissionError:
        # خطأ أذونات واضحة
        raise HTTPException(
            status_code=500, 
            detail=f"Server error: Permission denied to save file. Check server user permissions on {UPLOAD_DIR} directory."
        )
    except Exception as e:
        # خطأ I/O عام (مثل مسار غير موجود)
        raise HTTPException(
            status_code=500, 
            detail=f"Server I/O error during file save: {type(e).__name__}."
        )
    # ======================================================================

    # استخراج النص ثم حذف الملف المؤقت من القرص بأي حال
    # exc = None
    # try:
    text = extract_text_from_pdf(pdf_path)
    # except Exception as e:  # فشل في التحليل أو القراءة
        # exc = e
    # finally:
        # try:
            # pdf_path.unlink(missing_ok=True)  # حذف الملف المؤقت
        # except Exception:
            # pass  # نتجاهل أخطاء الحذف

    # if exc is not None:
        # raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {exc}")

    if not text.strip():  # ملف فارغ أو لا يحتوي نص مستخرج
        raise HTTPException(status_code=422, detail="No extractable text found in PDF.")

    session_id = str(uuid.uuid4())  # إنشاء معرف جلسة فريد
    text_storage[session_id] = text  # تخزين النص في الذاكرة
    _cleanup_old_files()  # تنظيف الملفات القديمة بشكل دوري
    return {"session_id": session_id, "characters": len(text)}  # إرجاع عدد المحارف للمعلومة




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


# @app.post("/summarize/")
# async def summarize(file: UploadFile):
#     text = extract_text_from_pdf(file)
#     print(text)
#     if not text:
#         return {"error": "الملف فارغ أو لم يتم استخراج النص"}
#     return StreamingResponse(stream_summary(text), media_type="text/event-stream")


@app.get("/summarize-gemini")
async def summarize_gemini(session_id: str = Query(...), model: str | None = None, language: str = Query("العربية")):
    model_key = model or DEFAULT_MODEL
    text = text_storage.get(session_id)
    if not text:
        raise HTTPException(status_code=404, detail="الجلسة غير موجودة أو انتهت صلاحيتها")
    prompt = (
        f"أنت خبير في تلخيص الدروس الأكاديمية. مهمتك إنشاء ملخص احترافي منظم وواضح للطالب، بتنسيق عالمي مثل المواقع التعليمية الكبرى."
        f"\n\n**التعليمات:**"
        f"\n1. استخدم تنسيق Markdown الكامل: عناوين رئيسية (`#` أو `##`)، فقرات منفصلة وواضحة، قوائم نقطية ومرقمة، إبراز الكلمات المهمة (`**bold**`)، وروابط عند الحاجة."
        f"\n2. لكل فكرة رئيسية، استخدم عنوان من المستوى الثاني (`##`) يصف الفكرة بوضوح."
        f"\n3. تحت كل عنوان، اكتب شرحًا أكاديميًا مبسطًا على شكل فقرات منفصلة، ثم أضف قائمة نقطية (`-`) للنقاط الفرعية أو التفاصيل المهمة."
        f"\n4. إذا وجدت مصطلحات أو مفاهيم مهمة، أبرزها بخط عريض (`**المصطلح**`)."
        f"\n5. إذا كان هناك مثال أو تطبيق عملي، أضفه في فقرة منفصلة أو قائمة مرقمة."
        f"\n6. إذا وردت روابط أو مراجع، أضفها باستخدام تنسيق الروابط في Markdown."
        f"\n7. لا تكتب أي مقدمات أو تعليقات خارجية، فقط الملخص المنسق."
        f"\n8. اجعل الناتج النهائي منسقًا وجاهزًا للعرض مباشرة في موقع تعليمي عالمي."
        f"\n9. في نهاية الملخص، أضف قسم خاص بعنوان `## أسئلة وأجوبة`، واستخرج من الدرس 3 إلى 7 أسئلة مهمة مع إجاباتها، كل سؤال في سطر منفصل، والإجابة تحته، بتنسيق Markdown."
        f"\n\nالنص الأصلي:\n{text}"
    )
    def sse_gen():
        yield b"event: status\ndata: START\n\n"
        try:
            stream = client.models.generate_content_stream(
                model=model_key,
                contents=[prompt]
            )
            print(stream)
            for chunk in stream:
                token = getattr(chunk, "text", None)
                if token:
                    yield f"data: {token}\n\n".encode("utf-8")
            yield b"event: status\ndata: DONE\n\n"
        except Exception as e:
            yield f"event: error\ndata: {str(e)}\n\n".encode("utf-8")
    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(sse_gen(), media_type="text/event-stream", headers=headers)
  