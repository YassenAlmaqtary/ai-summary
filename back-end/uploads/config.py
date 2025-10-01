import os
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://31.97.61.156:11434/api/generate")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Optional: model name can be overridden
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "gemma:2b")
OLLAMA_MODELS = [m.strip() for m in os.getenv("OLLAMA_MODELS", DEFAULT_MODEL).split(",") if m.strip()]

# Maximum PDF size in bytes (e.g., 15 MB)
MAX_PDF_SIZE = int(os.getenv("MAX_PDF_SIZE", str(15 * 1024 * 1024)))
