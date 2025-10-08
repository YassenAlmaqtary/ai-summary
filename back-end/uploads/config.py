import os
from dotenv import load_dotenv
from google import genai

# Load environment variables from a .env file if present
load_dotenv()

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://31.97.61.156:11434/api/generate")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
Gemnikey = os.getenv("Gemnikey", "")

# Optional: model name can be overridden
DEFAULT_MODEL = os.getenv("gemini_model", "gemini-2.5-flash")
OLLAMA_MODELS = [m.strip() for m in os.getenv("OLLAMA_MODELS", DEFAULT_MODEL).split(",") if m.strip()]
gemini_models = [m.strip() for m in os.getenv("gemini_models", DEFAULT_MODEL).split(",") if m.strip()]
# Maximum PDF size in bytes (e.g., 15 MB)
MAX_PDF_SIZE = int(os.getenv("MAX_PDF_SIZE", str(15 * 1024 * 1024)))
client = genai.Client(api_key=Gemnikey)

# Frontend origins allowed for CORS (comma-separated)
# FRONTEND_ORIGINS = [
# 	o.strip() for o in os.getenv(
# 		"FRONTEND_ORIGINS",
# 		"http://localhost:5173,https://summary-ai.deliciousdemo.site"
# 	).split(",") if o.strip()
# ]

# Optional: allow origin regex (useful for subdomains), leave empty to disable
ALLOW_ORIGIN_REGEX = os.getenv("ALLOW_ORIGIN_REGEX", "")
