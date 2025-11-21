from pathlib import Path
import pickle
import logging
from typing import List

log = logging.getLogger("ai-summary.agent")

try:
    import faiss  # type: ignore
    import numpy as np
    from sentence_transformers import SentenceTransformer
except Exception as e:  # pragma: no cover - optional deps
    faiss = None  # type: ignore
    np = None  # type: ignore
    SentenceTransformer = None  # type: ignore
    log.warning("Optional retrieval dependencies not available: %s", e)

from uploads.config import DEFAULT_MODEL
from core.infra import get_genai_client, get_embedding_model

import os
from pathlib import Path
import pickle

# Do not fix the embedding model at import time; resolve at call time using infra
EMBEDDING_MODEL = None


class VectorStoreManager:
    """Load FAISS indexes stored under a root `indexes/` directory.

    Each index folder is expected to contain `index.faiss` and `index.pkl`.
    The pickle file should contain a list of document texts or a dict with key 'texts'.
    """

    def __init__(self, index_root: Path):
        self.index_root = Path(index_root)
        self._model = None
        self._cache = {}

    def _ensure_embedder(self):
        if SentenceTransformer is None:
            # local embedder not available; fall back to cloud embeddings
            return
        if self._model is None:
            self._model = SentenceTransformer("all-MiniLM-L6-v2")

    def has_index(self, key: str) -> bool:
        folder = self.index_root / key
        return folder.is_dir()

    def _load_index(self, key: str):
        if key in self._cache:
            return self._cache[key]
        folder = self.index_root / key
        if not folder.exists():
            raise FileNotFoundError("index not found")
        idx_path = folder / "index.faiss"
        meta_path = folder / "index.pkl"
        if not idx_path.exists() or not meta_path.exists():
            raise FileNotFoundError("index files missing")

        if faiss is None:
            raise RuntimeError("faiss is not installed")

        index = faiss.read_index(str(idx_path))
        with open(meta_path, "rb") as f:
            meta = pickle.load(f)

        # meta may be dict or list
        if isinstance(meta, dict) and "texts" in meta:
            texts = meta["texts"]
        elif isinstance(meta, list):
            texts = meta
        else:
            # try to find a reasonable attribute
            texts = getattr(meta, "texts", None) or getattr(meta, "docs", None) or []

        self._cache[key] = (index, texts)
        return index, texts

    def query(self, key: str, query: str, k: int = 4) -> List[str]:
        index, texts = self._load_index(key)
        # compute embedding either locally or via cloud
        if SentenceTransformer is not None and self._model is not None:
            emb = self._model.encode([query], convert_to_numpy=True)
            if emb.dtype != np.float32:
                emb = emb.astype(np.float32)
        else:
            # use cloud embeddings
            emb_vecs = _cloud_embeddings([query])
            emb = np.array(emb_vecs, dtype=np.float32)
        distances, idxs = index.search(emb, k)
        results: List[str] = []
        for idx in idxs[0]:
            if idx < 0 or idx >= len(texts):
                continue
            results.append(texts[idx])
        return results


def _cloud_embeddings(texts: List[str]) -> List[List[float]]:
    """Request embeddings from configured cloud client (Google GenAI).

    Returns a list of float vectors.
    """
    client = get_genai_client()
    if client is None:
        raise RuntimeError("No cloud client configured for embeddings")
    # resolve embedding model dynamically (tries env, cached, and fallback candidates)
    model_name = get_embedding_model(preferred=os.getenv("EMBEDDING_MODEL"))
    if not model_name:
        raise RuntimeError("No embedding model available")
    vecs: List[List[float]] = []
    # Try primary GenAI call shape(s)
    resp = None
    try:
        try:
            resp = client.models.embed_content(model=model_name, contents=texts)
        except TypeError:
            # some client versions use 'input' instead of 'contents'
            resp = client.models.embed_content(model=model_name, input=texts)
    except Exception as e:
        # If embed_content fails, try the older embeddings.create surface if present
        if hasattr(client, 'embeddings') and hasattr(client.embeddings, 'create'):
            try:
                resp = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
            except Exception as e2:
                log.exception("embed_content and embeddings.create both failed: %s / %s", e, e2)
                raise RuntimeError("Cloud embeddings call failed: %s" % e)
        else:
            log.exception("embed_content failed and no fallback available: %s", e)
            raise RuntimeError("Cloud embeddings call failed: %s" % e)

    # Normalize known response shapes to a list of float lists
    try:
        # Preferred: resp.embeddings (google.genai EmbedContentResponse)
        if hasattr(resp, 'embeddings') and resp.embeddings:
            for item in resp.embeddings:
                vals = getattr(item, 'values', None) or getattr(item, 'embedding', None)
                if vals is None and hasattr(item, '__dict__'):
                    vals = item.__dict__.get('values') or item.__dict__.get('embedding')
                if vals is None:
                    continue
                vecs.append(list(vals))

        # Older shape: resp.data -> list of items with .embedding or ['embedding']
        elif hasattr(resp, 'data') and resp.data:
            for item in resp.data:
                emb = getattr(item, 'embedding', None) or (item.get('embedding') if isinstance(item, dict) else None)
                if emb is None:
                    emb = getattr(item, 'value', None) or (item.get('value') if isinstance(item, dict) else None)
                if emb is None:
                    continue
                vecs.append(list(emb))

        # Dict-like: {'embeddings': [{'embedding': [...]}, ...]}
        elif isinstance(resp, dict) and 'embeddings' in resp:
            for item in resp['embeddings']:
                if isinstance(item, dict) and 'embedding' in item:
                    vecs.append(list(item['embedding']))

        else:
            # Last resort: try to introspect common attributes
            embeddings = getattr(resp, 'embeddings', None) or getattr(resp, 'embedding', None) or getattr(resp, 'data', None)
            if embeddings:
                for item in embeddings:
                    vals = getattr(item, 'values', None) or getattr(item, 'embedding', None) or (item.get('embedding') if isinstance(item, dict) else None)
                    if vals:
                        vecs.append(list(vals))

        return vecs
    except Exception as e:  # pragma: no cover - network/parsing
        log.exception("failed to parse cloud embeddings response: %s", e)
        raise


def build_and_persist_faiss(session_id: str, text: str, index_root: Path, chunk_size: int = 1000, chunk_overlap: int = 200):
    """Split text into chunks, compute cloud embeddings, build FAISS index and save it under index_root/session_id.

    Saves `index.faiss` and `index.pkl` (pickle of texts list).
    """
    if faiss is None or np is None:
        log.warning("faiss or numpy not available; skipping index build")
        return
    index_root = Path(index_root)
    dest = index_root / session_id
    dest.mkdir(parents=True, exist_ok=True)

    # naive chunking by characters
    chunks = []
    i = 0
    L = len(text)
    while i < L:
        chunk = text[i : i + chunk_size]
        chunks.append(chunk)
        i += chunk_size - chunk_overlap

    # compute embeddings via cloud
    vecs = _cloud_embeddings(chunks)
    if not vecs:
        log.warning("no embeddings produced; skipping index persist")
        return

    arr = np.array(vecs, dtype=np.float32)
    dim = arr.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(arr)

    faiss.write_index(index, str(dest / "index.faiss"))
    with open(dest / "index.pkl", "wb") as f:
        pickle.dump(chunks, f)
    log.info("built faiss index for session %s (chunks=%d dim=%d)", session_id, len(chunks), dim)


def build_lesson_prompt(core_text: str, retrieved_chunks: List[str] | None = None, language: str = "العربية") -> str:
    """Construct a pedagogical prompt asking the model to produce an interactive lesson.

    The output should include: title, learning objectives, lesson body (with short paragraphs),
    examples, and exercises (with answers hidden) plus a short Q&A section.
    """
    retrieved = "\n\n---\n\n".join(retrieved_chunks or [])
    prompt = (
        f"أنت معلم ذكي ومصمم محتوى تعليمي باللغة {language}. "
        "قدم درساً تفاعلياً ومنظماً يعتمد على النص المرفق. "
        "الإخراج يجب أن يكون بتنسيق Markdown باستعمال عناوين واضحة (#, ##) وقوائم نقطية حيث يلزم.\n\n"
        "التعليمات التفصيلية:\n"
        "1) ابدأ بعنوان واضح وموجز.\n"
        "2) اكتب قسم أهداف التعلم (3 نقاط على الأكثر).\n"
        "3) اشرح الفكرة الرئيسية في 3-6 فقرات قصيرة (كل فقرة لا تتجاوز 3 جمل).\n"
        "4) أعطِ مثال تطبيقي واحد مبسّط خطوة بخطوة.\n"
        "5) أدرج قسم \"دروس مستفادة\" مع 3 نقاط.\n"
        "6) أضف \"## أسئلة وتمارين\" مع 4 أسئلة متنوعة، ثم قسم \"## إجابات\" منفصل مختصر.\n"
        "7) إذا توافر نص مسترجع ذَكِر إشارة صغيرة 'المراجع' مع مقتطفات ذات صلة.\n\n"
        f"## النص الأساسي:\n{core_text}\n\n"
        f"## مقاطع مُسترجعة (إن وُجدت):\n{retrieved}\n\n"
        "اكتب الدرس الآن بالترتيب المطلوب، وركز على البساطة والوضوح للطلاب.")
    return prompt


async def stream_agent_response(prompt: str, model: str | None = None):
    """Stream model tokens via the configured `client` (genai client expected).

    Yields raw text chunks (strings). Caller can convert to SSE bytes.
    """
    client = get_genai_client()
    if client is None:
        raise RuntimeError("No cloud client configured for generation")
    model_key = model or DEFAULT_MODEL
    stream = client.models.generate_content_stream(model=model_key, contents=[prompt])
    for chunk in stream:
        token = getattr(chunk, "text", None)
        if token:
            yield token
