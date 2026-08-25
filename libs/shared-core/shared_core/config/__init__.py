from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""
    database_url: str = ""
    internal_api_key: str = ""
    allowed_origins: str = "http://localhost:3000,http://localhost:8081"
    max_request_bytes: int = 6_000_000
    max_face_image_bytes: int = 5_000_000
    rate_limit_per_minute: int = 120

    @property
    def allowed_origin_list(self) -> list[str]:
        return [x.strip() for x in self.allowed_origins.split(',') if x.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
