"""Centralised settings — reads from .env automatically."""
import os
from pathlib import Path
from functools import lru_cache

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings  # pydantic v1 fallback


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Property AI Master"
    VERSION: str = "2.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_PATH: str = "backend/app/database/property_ai.db"

    # Security
    JWT_SECRET_KEY: str = "change-me-in-production-please"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24

    # Pinecone
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = "us-east-1-aws"
    PINECONE_INDEX: str = "property-ai"

    # External APIs
    UNSPLASH_ACCESS_KEY: str = ""
    HF_TOKEN: str = ""
    REPLICATE_API_TOKEN: str = ""

    # File Upload
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024
    UPLOAD_FOLDER: str = "dataset/uploads"

    # AI Models
    FAKE_DETECTOR_MODEL: str = "backend/app/models/fake_detector_final.pt"
    CLIP_MODEL: str = "clip-ViT-B-32"

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"

    class Config:
        env_file = str(Path(__file__).parent.parent.parent / "backend" / ".env")
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
