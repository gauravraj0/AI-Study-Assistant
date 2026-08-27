"""Application settings.

Everything is overridable via environment variables (or a `.env` file next to
the backend). The defaults are chosen so the app runs fully out-of-the-box:

* ``sqlite`` database + embedded persistent vector store
* local (deterministic) AI engine for generation
* local JWT authentication

Set ``OPENAI_API_KEY`` or ``GEMINI_API_KEY`` to upgrade the AI engine to a real
LLM, ``DATABASE_URL`` to ``postgresql://...`` for PostgreSQL, and
``FIREBASE_SERVICE_ACCOUNT_FILE`` to enable Firebase auth.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Study Assistant API"
    version: str = "1.0.0"

    # --- storage -----------------------------------------------------------
    database_url: str = "sqlite:///./data/app.db"
    data_dir: str = "./data"
    # Where the vector store persists its partition files. Defaults to
    # <data_dir>/vectors when left empty.
    vector_store_path: str = ""

    # --- auth ---------------------------------------------------------------
    jwt_secret: str = "dev-secret-change-me-in-production-0123456789"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week
    firebase_service_account_file: str = ""

    # --- AI providers --------------------------------------------------------
    # "auto" -> openai if key present, else gemini if key present, else local
    llm_provider: str = "auto"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embed_model: str = "text-embedding-3-small"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # --- misc -----------------------------------------------------------------
    cors_origins: str = "*"
    seed_demo: bool = True  # seed demo@study.ai + sample documents on first start
    max_upload_bytes: int = 25 * 1024 * 1024

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def resolved_vector_path(self) -> str:
        return self.vector_store_path or f"{self.data_dir.rstrip('/')}/vectors"

    @property
    def firebase_enabled(self) -> bool:
        return bool(self.firebase_service_account_file)


settings = Settings()
