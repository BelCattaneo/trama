from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Look in cwd first, then one level up — backend may be invoked from its own
    # dir or from the repo root, and the shared .env lives at the repo root.
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str
    pool_min: int = 1
    pool_max: int = 10
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    # Comma-separated origins for CORSMiddleware. Empty = no origin allowed
    # (prod-safe default); dev should set this to the Vite origin.
    cors_origins: str = ""
    session_ttl_days: int = 30
    # Dev default is False so the cookie works over plain HTTP localhost; prod must override.
    cookie_secure: bool = False
    storage_path: Path = Path("./storage")


settings = Settings()
