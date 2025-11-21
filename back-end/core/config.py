import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project root (back-end)
ROOT = Path(__file__).resolve().parents[1]

# Uploads and indexes
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(ROOT / "uploads")))
INDEX_ROOT = Path(os.getenv("INDEX_ROOT", str(ROOT / "temp" / "indexes")))

# GenAI settings
GEMNIKEY = os.getenv("Gemnikey", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
DEFAULT_MODEL = os.getenv("gemini_model", "gemini-2.5-flash")

# Frontend
FRONTEND_ORIGINS = [o.strip() for o in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(',') if o.strip()]
