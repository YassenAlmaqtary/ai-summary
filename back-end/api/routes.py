"""
API Routes - Presentation Layer
يحتوي على جميع endpoints للواجهة البرمجية
"""
import uuid
import asyncio
import time
from pathlib import Path
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, UploadFile, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse

from application.dependencies import (
    get_pdf_extraction_use_case,
    get_summary_use_case,
    get_lesson_agent_use_case,
    get_chat_agent_use_case,
    get_session_repository,
    get_index_status_repository,
    get_vector_store_repository,
    get_agent_service,
    get_history_use_case,
)
from application.use_cases import PDFExtractionUseCase
from domain.entities import Session, IndexStatus
from uploads.config import MAX_PDF_SIZE, DEFAULT_MODEL, gemini_models
from core.config import UPLOAD_DIR, INDEX_ROOT
from core.infra import get_genai_client
import logging

log = logging.getLogger("ai-summary.api")

router = APIRouter()

# Global state for pending extractions (will be moved to repository)
pending_extractions: dict[str, asyncio.Task] = {}

# File cleanup
FILE_TTL_SECONDS = 60 * 30  # 30 minutes


def _encode_sse_chunk(text: str) -> bytes:
    """Encode text as SSE chunk"""
    if not text:
        return b"data: \n\n"
    sanitized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = sanitized.split("\n")
    payload = "".join(f"data: {line}\n" for line in lines)
    return (payload + "\n").encode("utf-8")


def _cleanup_old_files() -> None:
    """Clean up old files"""
    now = time.time()
    for p in Path(UPLOAD_DIR).glob("*.pdf"):
        try:
            if now - p.stat().st_mtime > FILE_TTL_SECONDS:
                p.unlink(missing_ok=True)
        except OSError:
            pass


@router.post("/upload")
async def upload_pdf(file: UploadFile):
    """Upload PDF file and extract text"""
    try:
        # Validate content type
        if file.content_type not in {"application/pdf", "application/octet-stream"}:
            raise HTTPException(status_code=415, detail="Unsupported file type. Must be PDF.")
        
        # Read file data
        data = await file.read()
        if len(data) > MAX_PDF_SIZE:
            raise HTTPException(status_code=413, detail="File too large.")
        
        # Ensure upload directory exists
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        pdf_path = Path(UPLOAD_DIR) / f"{session_id}.pdf"
        
        # Save file
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, pdf_path.write_bytes, data)
        except PermissionError as e:
            log.error(f"Permission error saving file: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Server error: Permission denied to save file. Check server user permissions on {UPLOAD_DIR} directory."
            )
        except Exception as e:
            log.exception(f"Error saving file: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Server I/O error during file save: {type(e).__name__}: {str(e)}"
            )
        
        # Compute quick stats (pages)
        pages = None
        try:
            import pypdfium2
            pdf_doc = pypdfium2.PdfDocument(str(pdf_path))
            pages = len(pdf_doc)
        except Exception as e:
            log.debug(f"Unable to read PDF for stats: {e}")
        
        # Start extraction in background
        try:
            use_case = get_pdf_extraction_use_case()
            vector_repo = get_vector_store_repository()
            index_status_repo = get_index_status_repository()
            history_use_case = get_history_use_case()

            await history_use_case.record_upload(
                session_id=session_id,
                filename=file.filename or "ملف بدون اسم",
                model=None,
                agent_mode=False,
                pages=pages,
                file_size=len(data),
            )
            
            task = asyncio.create_task(
                use_case.extract_and_store(session_id, pdf_path, vector_repo, index_status_repo)
            )
            pending_extractions[session_id] = task
        except Exception as e:
            log.exception(f"Error starting extraction: {e}")
            # Try to clean up the file
            try:
                pdf_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise HTTPException(
                status_code=500,
                detail=f"Error starting extraction: {str(e)}"
            )
        
        _cleanup_old_files()
        log.info(f"Accepted upload session={session_id} size={len(data)/1024:.2f}KB")
        
        return {"session_id": session_id, "characters": 0, "pages": pages, "file_size": len(data)}
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Unexpected error in upload endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/health")
async def health():
    """Health check endpoint"""
    session_repo = get_session_repository()
    # Count sessions (would need async method)
    return {"status": "ok"}


@router.get("/models")
async def models():
    """Get available models"""
    return {"default": DEFAULT_MODEL, "models": gemini_models}


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete session"""
    session_repo = get_session_repository()
    removed = await session_repo.delete(session_id)
    return JSONResponse({"removed": removed})


@router.get("/summarize-gemini")
async def summarize_gemini(
    session_id: str = Query(...),
    model: Optional[str] = None,
    language: str = Query("العربية")
):
    """Generate summary endpoint"""
    async def sse_gen() -> AsyncGenerator[bytes, None]:
        yield b"event: status\ndata: START\n\n"
        
        try:
            use_case = get_summary_use_case()
            
            # Check if extraction is pending
            if session_id in pending_extractions:
                yield b"event: status\ndata: EXTRACTING\n\n"
                try:
                    await pending_extractions[session_id]
                except Exception:
                    pass
            
            # Generate summary
            async for token in use_case.generate_summary(session_id, model, language):
                yield _encode_sse_chunk(token)
            
            yield b"event: status\ndata: DONE\n\n"
        except HTTPException as he:
            yield f"event: error\ndata: {he.detail}\n\n".encode("utf-8")
        except Exception as e:
            log.exception(f"SSE error: {e}")
            yield f"event: error\ndata: {str(e)}\n\n".encode("utf-8")
    
    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(sse_gen(), media_type="text/event-stream", headers=headers)


@router.get("/agent")
async def lesson_agent(
    session_id: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    model: Optional[str] = None,
    language: str = Query("العربية")
):
    """Lesson agent endpoint"""
    async def sse() -> AsyncGenerator[bytes, None]:
        yield b"event: status\ndata: START\n\n"
        try:
            use_case = get_lesson_agent_use_case()
            
            # Wait for extraction if pending
            if session_id and session_id in pending_extractions:
                try:
                    await pending_extractions[session_id]
                except Exception:
                    pass
            
            async for token in use_case.generate_lesson(session_id, q, model, language):
                yield _encode_sse_chunk(token)
            
            yield b"event: status\ndata: DONE\n\n"
        except Exception as e:
            log.exception(f"Agent error: {e}")
            yield f"event: error\ndata: {str(e)}\n\n".encode("utf-8")
    
    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return StreamingResponse(sse(), media_type="text/event-stream", headers=headers)


@router.get("/index-status/{session_id}")
async def get_index_status(session_id: str):
    """Get index status"""
    index_status_repo = get_index_status_repository()
    status = await index_status_repo.get(session_id)
    if status is None:
        return JSONResponse({"status": "not_found"}, status_code=404)
    return JSONResponse({
        "status": status.status,
        "info": {"chunks": status.chunks} if status.chunks else {}
    })


@router.get("/chat")
async def chat_agent(
    session_id: Optional[str] = Query(None),
    q: str = Query(...),
    model: Optional[str] = None,
    language: str = Query("العربية")
):
    """Chat agent endpoint"""
    async def sse() -> AsyncGenerator[bytes, None]:
        yield b"event: status\ndata: START\n\n"
        try:
            use_case = get_chat_agent_use_case()
            
            # Wait for extraction if pending
            if session_id and session_id in pending_extractions:
                try:
                    await pending_extractions[session_id]
                except Exception:
                    pass
            
            async for token in use_case.chat(session_id, q, model):
                yield _encode_sse_chunk(token)
            
            yield b"event: status\ndata: DONE\n\n"
        except Exception as e:
            log.exception(f"Chat agent error: {e}")
            yield f"event: error\ndata: {str(e)}\n\n".encode("utf-8")
    
    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return StreamingResponse(sse(), media_type="text/event-stream", headers=headers)


@router.delete("/chat/{session_id}")
async def clear_chat_memory(session_id: str):
    """Clear chat memory"""
    from ai.langchain_agent import get_langchain_agent
    agent = get_langchain_agent()
    if agent:
        agent.clear_memory(session_id)
    return JSONResponse({"cleared": True})


@router.get("/sessions")
async def list_sessions(limit: int = Query(10, ge=1, le=50)):
    """List recent session history entries"""
    history_use_case = get_history_use_case()
    sessions = await history_use_case.list_history(limit=limit)
    return {"sessions": sessions}

