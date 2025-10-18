"""
Environment-specific configuration for release channels.

Supports: dev, staging, canary, prod
"""

import os
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class DeployEnv(str, Enum):
    """Deployment environment identifier."""
    DEV = "dev"
    STAGING = "staging"
    CANARY = "canary"
    PROD = "prod"


class EnvConfig(BaseModel):
    """Environment-specific configuration."""
    
    env: DeployEnv = Field(default=DeployEnv.DEV, description="Deployment environment")
    database_url: str = Field(..., description="Database connection string")
    redis_url: Optional[str] = Field(None, description="Redis connection string")
    
    # Secret management
    hmac_secret: str = Field(..., description="HMAC signing secret")
    jwt_secret: str = Field(..., description="JWT signing secret")
    
    # External services
    gmail_credentials_path: Optional[str] = None
    bigquery_credentials_path: Optional[str] = None
    elasticsearch_url: Optional[str] = None
    
    # Feature flags
    enable_telemetry: bool = True
    enable_incidents: bool = True
    enable_approvals: bool = True
    enable_policies: bool = True
    
    # Traffic control
    canary_percentage: int = Field(default=0, ge=0, le=100, description="Canary traffic percentage")
    
    # Rate limits
    rate_limit_per_minute: int = 60
    max_concurrent_requests: int = 100
    
    # Timeouts
    request_timeout_seconds: int = 30
    agent_timeout_seconds: int = 60
    
    class Config:
        env_prefix = "APPLYLENS_"


def get_env_config() -> EnvConfig:
    """
    Load environment-specific configuration.
    
    Environment variables:
    - APPLYLENS_ENV: Deployment environment (dev/staging/canary/prod)
    - APPLYLENS_DATABASE_URL: Database connection string
    - APPLYLENS_HMAC_SECRET: HMAC signing secret
    - APPLYLENS_JWT_SECRET: JWT signing secret
    - APPLYLENS_CANARY_PERCENTAGE: Canary traffic percentage (0-100)
    
    Returns:
        EnvConfig: Environment configuration
    """
    env = os.getenv("APPLYLENS_ENV", "dev")
    
    # Environment-specific defaults
    config_defaults = {
        DeployEnv.DEV: {
            "database_url": os.getenv("DATABASE_URL", "postgresql://localhost/applylens_dev"),
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            "canary_percentage": 0,
            "rate_limit_per_minute": 1000,  # Relaxed for dev
        },
        DeployEnv.STAGING: {
            "database_url": os.getenv("DATABASE_URL", "postgresql://localhost/applylens_staging"),
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/1"),
            "canary_percentage": 0,
            "rate_limit_per_minute": 300,
        },
        DeployEnv.CANARY: {
            "database_url": os.getenv("DATABASE_URL", "postgresql://localhost/applylens_prod"),
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/2"),
            "canary_percentage": int(os.getenv("APPLYLENS_CANARY_PERCENTAGE", "10")),
            "rate_limit_per_minute": 60,
        },
        DeployEnv.PROD: {
            "database_url": os.getenv("DATABASE_URL", "postgresql://localhost/applylens_prod"),
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/2"),
            "canary_percentage": 100,  # Full prod traffic
            "rate_limit_per_minute": 60,
        },
    }
    
    env_enum = DeployEnv(env)
    defaults = config_defaults[env_enum]
    
    return EnvConfig(
        env=env_enum,
        database_url=defaults["database_url"],
        redis_url=defaults.get("redis_url"),
        hmac_secret=os.getenv("APPLYLENS_HMAC_SECRET", "dev-secret-change-in-prod"),
        jwt_secret=os.getenv("APPLYLENS_JWT_SECRET", "dev-jwt-secret-change-in-prod"),
        gmail_credentials_path=os.getenv("GMAIL_CREDENTIALS_PATH"),
        bigquery_credentials_path=os.getenv("BIGQUERY_CREDENTIALS_PATH"),
        elasticsearch_url=os.getenv("ELASTICSEARCH_URL"),
        enable_telemetry=os.getenv("ENABLE_TELEMETRY", "true").lower() == "true",
        enable_incidents=os.getenv("ENABLE_INCIDENTS", "true").lower() == "true",
        enable_approvals=os.getenv("ENABLE_APPROVALS", "true").lower() == "true",
        enable_policies=os.getenv("ENABLE_POLICIES", "true").lower() == "true",
        canary_percentage=defaults["canary_percentage"],
        rate_limit_per_minute=defaults["rate_limit_per_minute"],
        max_concurrent_requests=int(os.getenv("MAX_CONCURRENT_REQUESTS", "100")),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")),
        agent_timeout_seconds=int(os.getenv("AGENT_TIMEOUT_SECONDS", "60")),
    )


# Global config instance
current_config: Optional[EnvConfig] = None


def init_config() -> EnvConfig:
    """Initialize global configuration."""
    global current_config
    current_config = get_env_config()
    return current_config


def get_config() -> EnvConfig:
    """Get current configuration."""
    if current_config is None:
        return init_config()
    return current_config


def is_production() -> bool:
    """Check if running in production environment."""
    config = get_config()
    return config.env in (DeployEnv.CANARY, DeployEnv.PROD)


def is_canary() -> bool:
    """Check if running in canary mode."""
    config = get_config()
    return config.env == DeployEnv.CANARY or (
        config.env == DeployEnv.PROD and 0 < config.canary_percentage < 100
    )


def get_canary_percentage() -> int:
    """Get current canary traffic percentage."""
    config = get_config()
    return config.canary_percentage
