from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Application
    ENV: str = "dev"
    API_PORT: int = 8003
    API_PREFIX: str = "/api"
    CORS_ORIGINS: str = "http://localhost:5175"
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/applylens"
    
    # Gmail single-user quick start (optional)
    GMAIL_CLIENT_ID: Optional[str] = None
    GMAIL_CLIENT_SECRET: Optional[str] = None
    GMAIL_REFRESH_TOKEN: Optional[str] = None
    GMAIL_USER: Optional[str] = None
    
    # OAuth (required for multi-user)
    OAUTH_REDIRECT_URI: Optional[str] = None
    
    # PDF parsing
    GMAIL_PDF_PARSE: bool = False
    GMAIL_PDF_MAX_BYTES: int = 2 * 1024 * 1024  # 2MB default
    
    # Testing/Mocking
    USE_MOCK_GMAIL: bool = False

    class Config:
        env_file = "../../infra/.env"

settings = Settings()
