import os
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    ENV: str = "dev"
    API_PORT: int = 8003
    API_PREFIX: str = "/api"
    CORS_ORIGINS: str = "http://localhost:5175"
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/applylens"

    # Database table creation (disabled in test env to avoid import-time connections)
    CREATE_TABLES_ON_STARTUP: bool = (
        os.getenv(
            "CREATE_TABLES_ON_STARTUP", "0" if os.getenv("ENV") == "test" else "1"
        )
        == "1"
    )

    # Gmail single-user quick start (optional)
    GMAIL_CLIENT_ID: Optional[str] = None
    GMAIL_CLIENT_SECRET: Optional[str] = None
    GMAIL_REFRESH_TOKEN: Optional[str] = None
    GMAIL_USER: Optional[str] = None

    # OAuth (required for multi-user)
    OAUTH_REDIRECT_URI: Optional[str] = None
    OAUTH_STATE_SECRET: Optional[str] = None
    DEFAULT_USER_EMAIL: Optional[str] = None
    GOOGLE_CREDENTIALS: Optional[str] = None
    GOOGLE_OAUTH_SCOPES: Optional[str] = None

    # Google OAuth credentials (client ID and secret)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # Google OAuth redirect URIs
    # GOOGLE_REDIRECT_URI for production (e.g., https://api.applylens.app/auth/google/callback)
    # GOOGLE_REDIRECT_URI_DEV for local development (e.g., http://localhost:8003/auth/google/callback)
    GOOGLE_REDIRECT_URI: Optional[str] = None
    GOOGLE_REDIRECT_URI_DEV: str = "http://localhost:8003/auth/google/callback"

    @property
    def effective_redirect_uri(self) -> str:
        """Return the effective redirect URI based on environment"""
        return self.GOOGLE_REDIRECT_URI or self.GOOGLE_REDIRECT_URI_DEV

    # PostgreSQL
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None

    # Web frontend
    WEB_PORT: Optional[int] = None
    CORS_ALLOW_ORIGINS: Optional[str] = None

    # Elasticsearch
    ES_ENABLED: bool = True
    ES_URL: str = "http://es:9200"
    ES_RECREATE_ON_START: bool = False
    ELASTICSEARCH_INDEX: str = "gmail_emails"
    KIBANA_PORT: Optional[int] = None

    # PDF parsing
    GMAIL_PDF_PARSE: bool = False
    GMAIL_PDF_MAX_BYTES: int = 2 * 1024 * 1024  # 2MB default

    # Testing/Mocking
    USE_MOCK_GMAIL: bool = False

    @property
    def is_test_env(self) -> bool:
        """Check if running in test environment."""
        return self.ENV == "test"

    @property
    def safe_es_url(self) -> str:
        """Return ES URL, or unreachable URL in test mode to prevent accidental connections."""
        if self.is_test_env and self.ES_ENABLED:
            return "http://127.0.0.1:0"  # Unreachable on purpose
        return self.ES_URL

    class Config:
        env_file = "../../infra/.env"
        extra = "ignore"  # Allow extra fields from .env


settings = Settings()
