"""
Application Layer - Use Cases
يحتوي على منطق الأعمال (Business Logic) للاستخدامات المختلفة
"""
import asyncio
import hashlib
import logging
from typing import AsyncIterator, Optional
from pathlib import Path
from datetime import datetime

from domain.entities import Session, IndexStatus
from domain.repositories import (
    SessionRepository,
    CacheRepository,
    VectorStoreRepository,
    IndexStatusRepository
)
from core.infra import get_genai_client
from ai.agent import build_lesson_prompt, stream_agent_response
from ai.langchain_agent import get_langchain_agent
from uploads.config import DEFAULT_MODEL

log = logging.getLogger("ai-summary.use_cases")


class PDFExtractionUseCase:
    """Use case for extracting text from PDF files"""
    
    def __init__(self, session_repo: SessionRepository):
        self.session_repo = session_repo
    
    async def extract_text(self, pdf_path: Path) -> str:
        """Extract text from PDF file"""
        import pypdfium2
        pdf = pypdfium2.PdfDocument(pdf_path)
        return "\n".join(page.get_textpage().get_text_range() for page in pdf)
    
    async def extract_and_store(
        self, 
        session_id: str, 
        pdf_path: Path,
        vector_repo: VectorStoreRepository,
        index_status_repo: IndexStatusRepository
    ) -> None:
        """Extract text and store in session, then build index in background"""
        try:
            # Extract text
            text = await self.extract_text(pdf_path)
            
            # Delete temporary PDF file
            try:
                pdf_path.unlink(missing_ok=True)
            except Exception:
                pass
            
            # Save session
            session = Session(
                session_id=session_id,
                text=text or "",
                created_at=datetime.now(),
                extracted=True
            )
            await self.session_repo.save(session)
            
            log.info(f"Extracted text for {session_id} (chars={len(text or '')})")
            
            # Build index in background
            if text:
                asyncio.create_task(
                    self._build_index_background(session_id, text, vector_repo, index_status_repo)
                )
        except Exception as e:
            log.exception(f"Failed to extract text for {session_id}: {e}")
            # Save empty session on error
            session = Session(
                session_id=session_id,
                text="",
                created_at=datetime.now(),
                extracted=False
            )
            await self.session_repo.save(session)
    
    async def _build_index_background(
        self,
        session_id: str,
        text: str,
        vector_repo: VectorStoreRepository,
        index_status_repo: IndexStatusRepository
    ) -> None:
        """Build FAISS index in background"""
        try:
            # Mark as pending
            status = IndexStatus(
                session_id=session_id,
                status="pending"
            )
            await index_status_repo.set(status)
            
            # Mark as building
            status.status = "building"
            await index_status_repo.set(status)
            
            # Build index in executor (blocking operation)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, vector_repo.build_index, session_id, text)
            
            # Mark as ready
            status.status = "ready"
            await index_status_repo.set(status)
            
            log.info(f"Index built successfully for {session_id}")
        except Exception as e:
            log.exception(f"Index build failed for {session_id}: {e}")
            status = IndexStatus(
                session_id=session_id,
                status="failed",
                error=str(e)
            )
            await index_status_repo.set(status)


class SummaryUseCase:
    """Use case for generating summaries"""
    
    def __init__(
        self,
        session_repo: SessionRepository,
        cache_repo: CacheRepository
    ):
        self.session_repo = session_repo
        self.cache_repo = cache_repo
    
    async def wait_for_text(self, session_id: str) -> str:
        """Wait for text extraction to complete"""
        session = await self.session_repo.get(session_id)
        if session and session.text:
            return session.text
        
        # Check if there's a pending task (would need to be stored in repo)
        # For now, return empty if not found
        return ""
    
    async def generate_summary(
        self,
        session_id: str,
        model: Optional[str] = None,
        language: str = "العربية"
    ) -> AsyncIterator[str]:
        """Generate summary with caching"""
        # Get text
        text = await self.wait_for_text(session_id)
        if not text or not text.strip():
            yield "❌ لا يوجد نص متاح للتلخيص"
            return
        
        # Check cache
        cache_key = self.cache_repo.generate_key(text)
        cached = await self.cache_repo.get(cache_key)
        if cached:
            log.info(f"Cache hit for summary {cache_key[:8]}")
            # Stream cached content
            chunk_size = 800
            for i in range(0, len(cached), chunk_size):
                yield cached[i:i+chunk_size]
            return
        
        # Generate summary
        prompt = self._build_prompt(text)
        model_key = model or DEFAULT_MODEL
        client = get_genai_client()
        
        if not client:
            yield "❌ تعذر تهيئة العميل"
            return
        
        # Stream response and collect for caching
        full_response = ""
        try:
            stream = client.models.generate_content_stream(
                model=model_key,
                contents=[prompt]
            )
            for chunk in stream:
                token = getattr(chunk, "text", None)
                if token:
                    full_response += token
                    yield token
            
            # Cache the result
            await self.cache_repo.set(cache_key, full_response, ttl=600)
        except Exception as e:
            log.exception(f"Summary generation error: {e}")
            yield f"❌ حدث خطأ: {str(e)}"
    
    def _build_prompt(self, text: str) -> str:
        """Build prompt for summary generation"""
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
            "3. بعد ذلك، نظّم المحتوى إلى أقسام واضحة.\n"
            "4. أضف رموزًا أو عناوين فرعية مثل: ✨ **دروس مستفادة** أو 💡 **فكرة رئيسية** لإضفاء طابع تفاعلي.\n"
            "5. في نهاية النص، أنشئ قسمًا بعنوان `## أسئلة وأجوبة` يحتوي من 3 إلى 7 أسئلة تدريبية.\n"
            "6. اجعل الأسلوب **تعليميًا مبسطًا** وليس وعظيًا، مع لمسة إيمانية ملهمة.\n"
            "7. لا تكتب أي شروحات إضافية خارج النص.\n\n"
            f"### 🧾 النص المراد تلخيصه:\n{text}"
        )


class LessonAgentUseCase:
    """Use case for lesson agent"""
    
    def __init__(
        self,
        session_repo: SessionRepository,
        vector_repo: VectorStoreRepository
    ):
        self.session_repo = session_repo
        self.vector_repo = vector_repo
    
    async def generate_lesson(
        self,
        session_id: Optional[str],
        query: Optional[str],
        model: Optional[str] = None,
        language: str = "العربية"
    ) -> AsyncIterator[str]:
        """Generate interactive lesson"""
        # Get core text
        core_text = ""
        if session_id:
            session = await self.session_repo.get(session_id)
            if session:
                core_text = session.text or ""
        
        if not core_text and query:
            core_text = query
        
        if not core_text or not core_text.strip():
            yield "❌ لا يوجد نص متاح"
            return
        
        # Retrieve relevant chunks if index exists
        retrieved = None
        if session_id and self.vector_repo.has_index(session_id):
            try:
                retrieved = self.vector_repo.query(session_id, query or core_text, k=4)
            except Exception as e:
                log.warning(f"Retrieval failed: {e}")
        
        # Build prompt
        prompt = build_lesson_prompt(core_text, retrieved_chunks=retrieved, language=language)
        
        # Stream response
        async for token in stream_agent_response(prompt, model=model):
            yield token


class ChatAgentUseCase:
    """Use case for chat agent"""
    
    def __init__(
        self,
        session_repo: SessionRepository,
        vector_repo: VectorStoreRepository
    ):
        self.session_repo = session_repo
        self.vector_repo = vector_repo
    
    async def chat(
        self,
        session_id: Optional[str],
        query: str,
        model: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Chat with agent"""
        # Get core text
        core_text = ""
        if session_id:
            session = await self.session_repo.get(session_id)
            if session:
                core_text = session.text or ""
        
        if not core_text or not core_text.strip():
            yield "❌ لا توجد وثيقة متاحة. يرجى رفع ملف PDF أولاً."
            return
        
        # Get agent
        agent = get_langchain_agent(model=model or DEFAULT_MODEL)
        if not agent:
            yield "❌ تعذر تهيئة الوكيل الذكي. تأكد من إعدادات API."
            return
        
        # Create a simple adapter for agent service
        class SimpleAgentService:
            def __init__(self, vector_repo):
                self.adapter = type('Adapter', (), {
                    'has_index': lambda self, sid: vector_repo.has_index(sid),
                    'query': lambda self, sid, q, k=4: vector_repo.query(sid, q, k)
                })()
        
        simple_service = SimpleAgentService(self.vector_repo)
        
        # Stream response
        async for token in agent.stream_response(
            query=query,
            session_id=session_id or "default",
            agent_service=simple_service,
            core_text=core_text
        ):
            yield token

