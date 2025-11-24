import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    ENV: str = "dev"
    APP_VERSION: str = "0.6.1"  # Follow-up draft feature
    API_PORT: int = 8003
    API_PREFIX: str = "/api"
    CORS_ORIGINS: str = "http://localhost:5175"

    # Database URL - can be overridden by APPLYLENS_DEV_DB for local dev
    # NOTE: Prefer using POSTGRES_* env vars in production to avoid special char issues
    DATABASE_URL: Optional[str] = Field(
        default=None,
        validation_alias="APPLYLENS_DEV_DB",
    )

    # PostgreSQL connection components (preferred for production)
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: str = "applylens"

    @property
    def sql_database_url(self) -> str:
        """
        Build database URL from components or use DATABASE_URL if set.

        Preferred approach: Use POSTGRES_* env vars (especially in production)
        to avoid URL encoding issues with special characters in passwords.

        Fallback: Use DATABASE_URL if set (for local dev/backwards compatibility).
        """
        # Backward compatibility: use DATABASE_URL if explicitly set
        if self.DATABASE_URL:
            return self.DATABASE_URL

        # Production approach: build from components
        if not self.POSTGRES_PASSWORD:
            # Default for local dev without password
            return f"postgresql://{self.POSTGRES_USER}:postgres@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

        # Build URL with password (no encoding needed - Python handles it)
        return (
            f"postgresql://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_DB}"
        )

    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite database."""
        return "sqlite" in self.sql_database_url.lower()

    # Database table creation (disabled in test env and SQLite to avoid import-time connections)
    CREATE_TABLES_ON_STARTUP: bool = False  # Will be computed based on env

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Disable table creation for test env or SQLite (use migrations instead)
        if os.getenv("ENV") == "test" or self.is_sqlite:
            self.CREATE_TABLES_ON_STARTUP = False
        else:
            self.CREATE_TABLES_ON_STARTUP = (
                os.getenv("CREATE_TABLES_ON_STARTUP", "1") == "1"
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

    # Web frontend
    WEB_PORT: Optional[int] = None
    CORS_ALLOW_ORIGINS: Optional[str] = None

    # Elasticsearch
    ES_ENABLED: bool = True
    ES_URL: str = "http://es:9200"
    ES_RECREATE_ON_START: bool = False
    ELASTICSEARCH_INDEX: str = "gmail_emails"
    KIBANA_PORT: Optional[int] = None

    # Feature flags
    CHAT_STREAMING_ENABLED: bool = True  # Canary toggle for SSE streaming

    # PDF parsing
    GMAIL_PDF_PARSE: bool = False
    GMAIL_PDF_MAX_BYTES: int = 2 * 1024 * 1024  # 2MB default

    # Testing/Mocking
    USE_MOCK_GMAIL: bool = False

    # Phase 4: Agent Governance
    HMAC_SECRET: Optional[str] = None  # For approval signatures

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
