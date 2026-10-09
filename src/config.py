"""Central configuration. Values can be overridden through a .env file."""
import os
from pathlib import Path
 
try:
    from dotenv import load_dotenv
 
    load_dotenv()
except ImportError:  # python-dotenv is optional at import time
    pass
 
ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR = ROOT / "data" / "reports"  # put annual report PDFs here
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
 
# Local embedding model (free, runs on CPU, no API key needed)
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
 
# Chunking
CHUNK_CHARS = int(os.getenv("CHUNK_CHARS", "1200"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
 
# LLM providers
DEFAULT_MODELS = {
    "anthropic": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
    "openai": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    "gemini": os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
}
ENV_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}
 
