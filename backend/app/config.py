"""Central configuration. Everything is read from environment variables so the
same code runs locally (SQLite, no AI key) and in deployment (Postgres + AI key)."""
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./brandcanon.db")
# Render/Neon give "postgres://" URLs; SQLAlchemy needs "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_HOURS = int(os.getenv("JWT_HOURS", "12"))

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")

# --- AI provider (any OpenAI-compatible API). Defaults target Google Gemini's
# OpenAI-compatible endpoint, which has a free tier. Leave LLM_API_KEY empty to
# run with the Verified lane only (the app still works end to end).
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]
