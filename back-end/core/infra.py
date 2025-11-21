import os
from dotenv import load_dotenv

load_dotenv()

try:
    from google import genai
except Exception:  # pragma: no cover - optional dependency
    genai = None


def get_genai_client():
    """Return a genai.Client if API key present, else None.

    This centralizes client creation in one place (infrastructure/adapter layer),
    avoiding import-time failures when the key is missing.
    """
    if genai is None:
        return None
    key = os.getenv("Gemnikey", "")
    if not key:
        return None
    try:
        return genai.Client(api_key=key)
    except Exception:
        return None


# Cache for a chosen embedding model to avoid repeated probing
_cached_embedding_model: str | None = None


def get_embedding_model(preferred: str | None = None) -> str | None:
    """Return a working embedding model name.

    Strategy:
    - If a preferred model is given (or via ENV EMBEDDING_MODEL), try it first.
    - Otherwise probe a short candidate list by calling `embed_content` with a tiny test.
    - Cache the successful model name for future calls.
    """
    global _cached_embedding_model
    if _cached_embedding_model:
        return _cached_embedding_model

    client = get_genai_client()
    if client is None:
        return None

    # respect explicit preference if provided
    candidates = []
    if preferred:
        candidates.append(preferred)
    # allow env override
    env_pref = os.getenv("EMBEDDING_MODEL")
    if env_pref and env_pref not in candidates:
        candidates.append(env_pref)

    # safe default candidates (order matters)
    defaults = [
        "models/text-embedding-004",
        "models/gemini-embedding-001",
        "models/text-embedding-003",
        "textembedding-gecko-001",
        "models/embedding-gecko-001",
    ]
    for d in defaults:
        if d not in candidates:
            candidates.append(d)

    test_input = ["test"]
    for model_name in candidates:
        try:
            # try contents then input forms
            try:
                resp = client.models.embed_content(model=model_name, contents=test_input)
            except TypeError:
                resp = client.models.embed_content(model=model_name, input=test_input)
            # check for embeddings presence
            if hasattr(resp, "embeddings") and resp.embeddings:
                _cached_embedding_model = model_name
                return _cached_embedding_model
            if isinstance(resp, dict) and resp.get("embeddings"):
                _cached_embedding_model = model_name
                return _cached_embedding_model
        except Exception:
            # model unsupported or call failed — try next
            continue

    return None
