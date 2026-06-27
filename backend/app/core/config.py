"""Application configuration, loaded from environment / .env file."""
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ---- LLM provider (openai | gemini | groq) ----
    llm_provider: str = "gemini"

    # OpenAI
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_embed_model: str = "text-embedding-3-small"

    # Google Gemini (via its OpenAI-compatible endpoint)
    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-2.0-flash"
    gemini_embed_model: str = "text-embedding-004"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    # Groq (OpenAI-compatible; free, no card). No embeddings endpoint -> local fallback.
    groq_api_key: str = ""
    groq_chat_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # Gmail OAuth
    google_client_secrets_file: str = "credentials.json"
    google_oauth_redirect_uri: str = "http://localhost:8000/api/gmail/oauth/callback"

    # Behaviour
    reply_mode: str = "approve"  # "approve" | "auto_send"
    confidence_threshold: float = 0.7
    angry_contact_threshold: int = 3

    # Storage
    database_url: str = f"sqlite:///{BACKEND_DIR / 'data' / 'app.db'}"

    @property
    def client_secrets_path(self) -> Path:
        p = Path(self.google_client_secrets_file)
        return p if p.is_absolute() else BACKEND_DIR / p

    @property
    def token_path(self) -> Path:
        return BACKEND_DIR / "token.json"

    # ---- Provider-agnostic accessors used by the AI client ----
    @property
    def llm_api_key(self) -> str:
        return {
            "gemini": self.gemini_api_key,
            "groq": self.groq_api_key,
            "openai": self.openai_api_key,
        }.get(self.llm_provider, self.openai_api_key)

    @property
    def llm_base_url(self) -> str | None:
        # OpenAI uses the SDK default (None); others override the base URL.
        return {
            "gemini": self.gemini_base_url,
            "groq": self.groq_base_url,
        }.get(self.llm_provider)

    @property
    def chat_model(self) -> str:
        return {
            "gemini": self.gemini_chat_model,
            "groq": self.groq_chat_model,
            "openai": self.openai_chat_model,
        }.get(self.llm_provider, self.openai_chat_model)

    @property
    def embed_model(self) -> str:
        return self.gemini_embed_model if self.llm_provider == "gemini" else self.openai_embed_model

    @property
    def provider_has_embeddings(self) -> bool:
        # Groq has no embeddings endpoint; RAG falls back to local embeddings.
        return self.llm_provider in ("gemini", "openai")

    @property
    def has_llm(self) -> bool:
        key = self.llm_api_key
        # Reject empty / placeholder keys (e.g. "...your-...-key-here") so failures are clear.
        return bool(key) and "your-" not in key


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
