import asyncio
import json
import httpx
from contextlib import asynccontextmanager
from uploads.config import OLLAMA_API_URL, DEFAULT_MODEL

REQUEST_TIMEOUT = 300  # seconds

@asynccontextmanager
async def _client():
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as c:
        yield c

def _normalize_markdown_fragment(s: str) -> str:
    """Lightweight markdown cleanup for streaming tokens.

    - Collapse repeated asterisks
    - Convert markdown bullets to readable dash if needed
    - Avoid trailing spaces
    """
    if not s:
        return s
    s = s.replace("•", "-")
    while "***" in s:
        s = s.replace("***", "**")
    return s.rstrip()

async def stream_summary(text: str, model: str | None = None, language: str = "العربية", add_status: bool = True):
    """Stream summary tokens from Ollama compatible API as Server-Sent Events chunks.

    Parameters:
        text: Source text to summarize.
        model: Override model name (defaults to DEFAULT_MODEL).
        language: Output language label injected in prompt.
    Yields:
        Pre-formatted SSE lines (ending with double newline) with incremental response data.
    """
    model_name = model or DEFAULT_MODEL
    prompt = (
        f"لخص هذا النص بدقة وبأسلوب واضح موجز باللغة {language} مع إبراز أهم النقاط:\n"
        f"{text}"
    )
    payload = {"model": model_name, "prompt": prompt, "stream": True}

    # Initial event
    if add_status:
        yield "event: status\ndata: STARTING\n\n"
    try:
        async with _client() as c:
            async with c.stream("POST", OLLAMA_API_URL, json=payload) as resp:
                if resp.status_code != 200:
                    detail = await resp.aread()
                    yield f"event: error\ndata: API_ERROR {resp.status_code} {detail.decode(errors='ignore')}\n\n"
                    return
                async for raw_line in resp.aiter_lines():
                    if not raw_line:
                        continue
                    try:
                        obj = json.loads(raw_line)
                    except json.JSONDecodeError:
                        # pass through raw if decode fails
                        yield f"data: {raw_line}\n\n"
                        continue
                    token = obj.get("response") or obj.get("message") or ""
                    if token:
                        token = _normalize_markdown_fragment(token)
                        yield f"data: {token}\n\n"
                    if obj.get("done"):
                        break
        if add_status:
            yield "event: status\ndata: DONE\n\n"
    except httpx.ConnectTimeout:
        yield "event: error\ndata: CONNECT_TIMEOUT\n\n"
    except httpx.ReadTimeout:
        yield "event: error\ndata: READ_TIMEOUT\n\n"
    except httpx.HTTPError as e:
        yield f"event: error\ndata: HTTP_ERROR {str(e)}\n\n"
    except Exception as e:  # noqa
        yield f"event: error\ndata: INTERNAL_ERROR {type(e).__name__}:{str(e)}\n\n"


## Removed hierarchical streaming (fast strategy) for simplicity.
          