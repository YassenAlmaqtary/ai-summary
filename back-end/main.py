"""
Main Application Entry Point
Clean Architecture Implementation
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from uploads.config import FRONTEND_ORIGINS, ALLOW_ORIGIN_REGEX, DEFAULT_MODEL
from core.infra import get_genai_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("ai-summary")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    log.info("Starting application...")
    await _warmup()
    yield
    # Shutdown
    log.info("Shutting down gracefully...")


async def _warmup():
    """Warmup model with a tiny request to reduce first-token latency"""
    sample_text = "اختبار تمهيدي صغير"
    try:
        client = get_genai_client()
        if client is None:
            log.info("GenAI client not available, skipping warmup")
            return

        def _do_warmup():
            try:
                stream = client.models.generate_content_stream(
                    model=DEFAULT_MODEL,
                    contents=[sample_text]
                )
                taken = 0
                for chunk in stream:
                    if getattr(chunk, "text", None):
                        taken += 1
                    if taken >= 2:
                        break
            except Exception as e:
                log.debug(f"Warmup stream error (ignored): {e}")

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _do_warmup)
        log.info("Warmup completed successfully")
    except Exception as e:
        log.debug(f"Warmup error (ignored): {e}")


# Create FastAPI app
app = FastAPI(
    title="AI PDF Summarizer API",
    version="2.0.0",
    description="Clean Architecture implementation with LangChain agent support",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_origin_regex=ALLOW_ORIGIN_REGEX or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, tags=["api"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000, reload=True)
