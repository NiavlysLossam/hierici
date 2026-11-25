from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "HierIci"
    ENVIRONMENT: str = "development"
    DEFAULT_TERRITORY_SLUG: str = "territoire-pilote"
    SECRET_KEY: str = "hierici-default-insecure-secret-key-change-in-prod"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 heures par défaut
    
    # Compte administrateur initial par défaut
    ADMIN_EMAIL: str = "admin@hierici.local"
    ADMIN_PASSWORD: str = "admin_hierici_2026"
    ADMIN_FULL_NAME: str = "Super Administrateur"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://hierici:hierici_secret_password@hierici-db:5432/hierici"
    
    # Storage
    STORAGE_DRIVER: str = "local"
    LOCAL_STORAGE_PATH: str = "/app/uploads"
    S3_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None
    S3_BUCKET_NAME: str | None = None
    S3_REGION: str = "fr-par"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:80",
        "http://localhost",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

