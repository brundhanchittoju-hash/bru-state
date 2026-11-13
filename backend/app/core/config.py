import json
import os
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

FALLBACK_DEV_SECRET_KEY = "9a2b8e3d4c1f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b"
DEV_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]
DEV_PUBLIC_BASE_URL = "http://localhost:5173"

INSECURE_SECRET_KEYS = {
    FALLBACK_DEV_SECRET_KEY,
    "your-production-secret-key-here-minimum-32-chars",
    "your-secret-key-here",
    "your-secret-key",
    "change_this_secret_in_production",
    "<generate-with-openssl-rand-hex-32>",
    "change-me",
    "secret",
}


class Settings(BaseSettings):
    PROJECT_NAME: str = "STATE AUDIT AI"
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api"

    # Database
    DATABASE_URL: str = "sqlite:///./state_audit.db"
    DIRECT_URL: Optional[str] = None

    # Security & JWT
    SECRET_KEY: Optional[str] = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15

    # Storage
    STORAGE_DIR: str = "./storage"
    MAX_UPLOAD_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB
    STORAGE_BACKEND: str = "local"  # "local" or "supabase"
    SUPABASE_URL: Optional[str] = None
    NEXT_PUBLIC_SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_SECRET_KEY: Optional[str] = None
    SUPABASE_PUBLISHABLE_KEY: Optional[str] = None
    NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: Optional[str] = None
    SUPABASE_STORAGE_BUCKET: str = "audit-documents"

    # CORS
    CORS_ORIGINS: Optional[List[str]] = None

    # Localization and Governance
    DEFAULT_STATE: str = "Karnataka"
    RATE_LIMIT_PER_MINUTE: int = 600
    LLM_API_KEY: str = ""
    PUBLIC_BASE_URL: Optional[str] = None
    CSP_EXTRA: str = ""

    @field_validator("DATABASE_URL", "DIRECT_URL", mode="before")
    @classmethod
    def clean_db_urls(cls, v: Union[str, None]) -> Optional[str]:
        if not v:
            return v
        clean = v.strip().strip("'\"")
        for prefix in ("DATABASE_URL=", "DIRECT_URL="):
            if clean.startswith(prefix):
                clean = clean.split(prefix, 1)[1].strip().strip("'\"")
        return clean

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str], None]) -> Optional[List[str]]:
        if v is None:
            return None
        if isinstance(v, str):
            clean = v.strip()
            if not clean:
                return None
            if clean.startswith("[") and clean.endswith("]"):
                try:
                    parsed = json.loads(clean)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
            return [item.strip() for item in clean.split(",") if item.strip()]
        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        return v

    @model_validator(mode="after")
    def validate_production_and_defaults(self) -> "Settings":
        is_prod = self.ENVIRONMENT.lower() == "production"

        if is_prod:
            # 1. SECRET_KEY validation in production
            if not self.SECRET_KEY or not self.SECRET_KEY.strip():
                raise ValueError(
                    "Production configuration error: SECRET_KEY must be provided via environment variables in production."
                )
            clean_secret = self.SECRET_KEY.strip()
            if clean_secret in INSECURE_SECRET_KEYS or len(clean_secret) < 32:
                raise ValueError(
                    "Production configuration error: SECRET_KEY cannot be empty, match known fallback/example values, "
                    "or be shorter than 32 characters."
                )

            # 5. URLs validation in production
            if not self.PUBLIC_BASE_URL or not self.PUBLIC_BASE_URL.strip():
                raise ValueError(
                    "Production configuration error: PUBLIC_BASE_URL must be provided via environment variables in production."
                )
            if not self.CORS_ORIGINS or len(self.CORS_ORIGINS) == 0:
                raise ValueError(
                    "Production configuration error: CORS_ORIGINS must be provided via environment variables in production."
                )
        else:
            # Development fallbacks
            if not self.SECRET_KEY or not self.SECRET_KEY.strip():
                self.SECRET_KEY = FALLBACK_DEV_SECRET_KEY
            if not self.PUBLIC_BASE_URL or not self.PUBLIC_BASE_URL.strip():
                self.PUBLIC_BASE_URL = DEV_PUBLIC_BASE_URL
            if not self.CORS_ORIGINS or len(self.CORS_ORIGINS) == 0:
                self.CORS_ORIGINS = list(DEV_CORS_ORIGINS)

        # Storage Backend Validation
        backend_choice = (self.STORAGE_BACKEND or "local").lower().strip()
        if backend_choice not in ("local", "supabase"):
            raise ValueError(f"Invalid STORAGE_BACKEND '{self.STORAGE_BACKEND}'. Must be 'local' or 'supabase'.")
        self.STORAGE_BACKEND = backend_choice

        if self.STORAGE_BACKEND == "supabase":
            if not self.SUPABASE_URL and self.NEXT_PUBLIC_SUPABASE_URL:
                self.SUPABASE_URL = self.NEXT_PUBLIC_SUPABASE_URL
            if not self.SUPABASE_SERVICE_ROLE_KEY and (self.SUPABASE_SECRET_KEY or self.SUPABASE_PUBLISHABLE_KEY or self.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY):
                self.SUPABASE_SERVICE_ROLE_KEY = self.SUPABASE_SECRET_KEY or self.SUPABASE_PUBLISHABLE_KEY or self.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY

            if not self.SUPABASE_URL or not self.SUPABASE_URL.strip():
                raise ValueError("SUPABASE_URL must be provided in backend/.env when STORAGE_BACKEND=supabase")
            if not self.SUPABASE_SERVICE_ROLE_KEY or not self.SUPABASE_SERVICE_ROLE_KEY.strip():
                raise ValueError("SUPABASE_SERVICE_ROLE_KEY must be provided in backend/.env when STORAGE_BACKEND=supabase")

        return self

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
