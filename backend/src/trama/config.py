from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Shared .env lives at the repo root; fall back to cwd for in-repo runs.
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str
    pool_min: int = 1
    pool_max: int = 10
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    # Empty = deny all origins.
    cors_origins: str = ""
    session_ttl_days: int = 30
    # Dev default False so the cookie works over plain HTTP localhost.
    cookie_secure: bool = False
    storage_path: Path = Path("./storage")
    llm_provider: str = "gemini"
    llm_model: str = "gemini-2.5-flash"
    google_api_key: str | None = None


settings = Settings()
