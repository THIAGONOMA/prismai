from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "PRISMAI_", "env_file": ".env", "extra": "ignore"}

    database_url: str = "postgresql+psycopg://prismai_app:prismai_app@localhost:5432/prismai"
    database_url_admin: str = "postgresql+psycopg://postgres:postgres@localhost:5432/prismai"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expires_min: int = 60
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    openalex_api_key: str = ""
    saq_queue_url: str = "postgres://postgres:postgres@localhost:5432/prismai"
    saq_concurrency: int = 5
    screening_timeout_s: int = 120
    stopping_threshold: float = 0.95
    stopping_min_sample: int = 50
    pdf_storage_path: str = "./data/pdfs"
    grobid_url: str = "http://localhost:8070"
    grobid_timeout_s: int = 120
    fulltext_fetch_timeout_s: int = 60
    ocr_confidence_threshold: float = 0.8
    cors_origins: str = "http://localhost:3000"


settings = Settings()
