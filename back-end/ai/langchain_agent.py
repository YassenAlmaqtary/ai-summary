"""
وكيل LangChain الذكي للتعامل مع الوثائق والملخصات
يدعم البحث في الوثائق، إنشاء الملخصات، والإجابة على الأسئلة
"""
import logging
from typing import List, Optional, Dict, Any, AsyncIterator
from pathlib import Path

# محاولة استيراد LangChain components
ChatGoogleGenerativeAI = None
HumanMessage = None
AIMessage = None
SystemMessage = None
ConversationBufferMemory = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from langchain.memory import ConversationBufferMemory
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    logging.warning(f"LangChain dependencies not fully available: {e}")
    LANGCHAIN_AVAILABLE = False

from core.infra import get_genai_client, get_embedding_model
from core.services import AgentService
from uploads.config import DEFAULT_MODEL

log = logging.getLogger("ai-summary.langchain_agent")


class LangChainAgent:
    """وكيل LangChain الذكي للتعامل مع الوثائق"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key
        self.model = model
        self.llm = None
        self.memory: Dict[str, Any] = {}  # memory لكل session
        
        if not LANGCHAIN_AVAILABLE:
            log.warning("LangChain not available, agent will use fallback mode")
            return
            
        if ChatGoogleGenerativeAI:
            try:
                self.llm = ChatGoogleGenerativeAI(
                    model=model,
                    google_api_key=api_key,
                    temperature=0.7,
                    streaming=True
                )
            except Exception as e:
                log.error(f"Failed to initialize LLM: {e}")
    
    def _get_memory(self, session_id: str) -> Any:
        """الحصول على أو إنشاء memory للجلسة"""
        if session_id not in self.memory:
            if ConversationBufferMemory:
                try:
                    self.memory[session_id] = ConversationBufferMemory(
                        memory_key="chat_history",
                        return_messages=True,
                        output_key="output"
                    )
                except Exception as e:
                    log.warning(f"Failed to create memory: {e}")
                    # استخدام memory بسيط كبديل
                    self.memory[session_id] = {"messages": []}
            else:
                # memory بسيط كبديل
                self.memory[session_id] = {"messages": []}
        return self.memory[session_id]
    
    def _search_documents(self, query: str, session_id: str, agent_service: AgentService, 
                         core_text: Optional[str] = None) -> str:
        """البحث في الوثيقة"""
        try:
            if agent_service.adapter and agent_service.adapter.has_index(session_id):
                results = agent_service.retrieve(session_id, query, k=5)
                if results:
                    return "\n\n---\n\n".join(results)
            # إذا لم يكن هناك فهرس، استخدم النص الأساسي
            if core_text:
                # بحث بسيط في النص
                query_lower = query.lower()
                lines = core_text.split('\n')
                relevant = [line for line in lines if query_lower in line.lower()][:5]
                if relevant:
                    return "\n\n".join(relevant)
            return "لم أجد معلومات متعلقة بهذا السؤال في الوثيقة."
        except Exception as e:
            log.error(f"Search error: {e}")
            return f"حدث خطأ أثناء البحث: {str(e)}"
    
    async def stream_response(self, query: str, session_id: str, 
                            agent_service: AgentService,
                            core_text: Optional[str] = None) -> AsyncIterator[str]:
        """بث استجابة الوكيل بشكل تدريجي"""
        try:
            # محاولة استخدام البحث أولاً
            retrieved = None
            if session_id and agent_service.adapter and agent_service.adapter.has_index(session_id):
                try:
                    retrieved = agent_service.retrieve(session_id, query, k=5)
                except Exception as e:
                    log.warning(f"Retrieval failed: {e}")
            
            # بناء prompt محسّن
            context_parts = []
            if retrieved:
                context_parts.append("## معلومات من الوثيقة:\n" + "\n\n---\n\n".join(retrieved))
            if core_text and len(core_text) < 3000:
                context_parts.append(f"## النص الكامل:\n{core_text}")
            
            context = "\n\n".join(context_parts) if context_parts else (core_text or "")
            
            system_prompt = """أنت وكيل ذكي متخصص في مساعدة الطلاب على فهم الدروس والوثائق التعليمية.

مهمتك:
1. فهم أسئلة المستخدم حول الوثيقة
2. استخدام المعلومات المقدمة من الوثيقة للإجابة
3. تقديم إجابات واضحة ومفيدة
4. إنشاء ملخصات عند الطلب
5. شرح المفاهيم المعقدة بطريقة مبسطة

تعليمات:
- استخدم المعلومات من الوثيقة للإجابة على الأسئلة
- كن واضحاً ومفيداً في إجاباتك
- استخدم اللغة العربية الفصحى
- إذا لم تجد المعلومات في الوثيقة، قل ذلك بوضوح
- قدم أمثلة وتوضيحات عند الحاجة"""
            
            user_prompt = f"""المستخدم يسأل: {query}

{context if context else 'لا توجد معلومات متاحة من الوثيقة.'}

أجب على سؤال المستخدم بناءً على المعلومات المتاحة أعلاه."""
            
            # استخدام LLM مباشرة للبث
            if not self.llm:
                # Fallback: استخدام genai client مباشرة
                client = get_genai_client()
                if not client:
                    yield "❌ تعذر تهيئة النموذج. تأكد من إعدادات API."
                    return
                
                # استخدام genai client مباشرة
                try:
                    prompt = f"""{system_prompt}

{user_prompt}"""
                    
                    stream = client.models.generate_content_stream(
                        model=self.model,
                        contents=[prompt]
                    )
                    
                    full_response = ""
                    for chunk in stream:
                        token = getattr(chunk, "text", None)
                        if token:
                            full_response += token
                            yield token
                    
                    # حفظ في memory
                    memory = self._get_memory(session_id)
                    if isinstance(memory, dict):
                        if 'messages' not in memory:
                            memory['messages'] = []
                        memory['messages'].append({"role": "user", "content": query})
                        memory['messages'].append({"role": "assistant", "content": full_response})
                    
                    return
                except Exception as e:
                    log.error(f"Fallback genai error: {e}")
                    yield f"❌ حدث خطأ: {str(e)}"
                    return
            
            try:
                # استخدام streaming مباشر من LLM
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ]
                
                # الحصول على memory للجلسة
                memory = self._get_memory(session_id)
                chat_history = []
                if hasattr(memory, 'chat_memory'):
                    chat_history = memory.chat_memory.messages
                elif isinstance(memory, dict) and 'messages' in memory:
                    chat_history = memory['messages']
                
                # إضافة التاريخ إلى الرسائل
                all_messages = list(chat_history) + messages
                
                # جمع الاستجابة للبث
                full_response = ""
                async for chunk in self.llm.astream(all_messages):
                    if hasattr(chunk, 'content'):
                        content = chunk.content
                        if content:
                            full_response += content
                            yield content
                    elif isinstance(chunk, str):
                        full_response += chunk
                        yield chunk
                
                # حفظ في memory بعد اكتمال الاستجابة
                if hasattr(memory, 'chat_memory'):
                    memory.chat_memory.add_user_message(query)
                    memory.chat_memory.add_ai_message(full_response)
                elif isinstance(memory, dict):
                    if 'messages' not in memory:
                        memory['messages'] = []
                    if HumanMessage:
                        memory['messages'].append(HumanMessage(content=query))
                    if AIMessage:
                        memory['messages'].append(AIMessage(content=full_response))
                
            except Exception as e:
                log.error(f"LLM streaming error: {e}")
                # محاولة بدون streaming
                try:
                    messages = [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=user_prompt)
                    ]
                    response = await self.llm.ainvoke(messages)
                    output = response.content if hasattr(response, 'content') else str(response)
                    
                    # حفظ في memory
                    memory = self._get_memory(session_id)
                    if hasattr(memory, 'chat_memory'):
                        memory.chat_memory.add_user_message(query)
                        memory.chat_memory.add_ai_message(output)
                    elif isinstance(memory, dict):
                        if 'messages' not in memory:
                            memory['messages'] = []
                        if HumanMessage:
                            memory['messages'].append(HumanMessage(content=query))
                        if AIMessage:
                            memory['messages'].append(AIMessage(content=output))
                    
                    # تقسيم النص للبث
                    chunk_size = 50
                    for i in range(0, len(output), chunk_size):
                        yield output[i:i+chunk_size]
                        import asyncio
                        await asyncio.sleep(0.01)
                except Exception as e2:
                    log.error(f"Non-streaming invoke error: {e2}")
                    yield f"❌ حدث خطأ: {str(e2)}"
                    
        except Exception as e:
            log.exception(f"Agent response error: {e}")
            yield f"❌ حدث خطأ أثناء معالجة طلبك: {str(e)}"
    
    def clear_memory(self, session_id: str):
        """مسح memory للجلسة"""
        if session_id in self.memory:
            del self.memory[session_id]


def get_langchain_agent(api_key: Optional[str] = None, model: str = DEFAULT_MODEL) -> Optional[LangChainAgent]:
    """إنشاء وكيل LangChain"""
    try:
        if not api_key:
            client = get_genai_client()
            if client:
                # محاولة استخراج API key من client
                api_key = getattr(client, '_api_key', None) or getattr(client, 'api_key', None)
        
        if not api_key:
            # محاولة من متغيرات البيئة
            import os
            api_key = os.getenv("Gemnikey", "")
        
        if not api_key:
            log.warning("No API key available for LangChain agent")
            return None
        
        return LangChainAgent(api_key=api_key, model=model)
    except Exception as e:
        log.error(f"Failed to create LangChain agent: {e}")
        return None

