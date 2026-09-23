from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]

    mongodb_uri: str
    mongodb_db: str = "patient_registration"

    retell_api_key: str = ""
    public_base_url: str = ""
    api_read_key: str = ""
    allow_unsigned_requests: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
