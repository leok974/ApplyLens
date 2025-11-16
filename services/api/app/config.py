"""Configuration for agent system providers and features.

Controls which provider implementations are used (mock vs real)
and provides settings for real integrations.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic_settings import BaseSettings


class AgentSettings(BaseSettings):
    """Agent system configuration.

    Environment variables can be prefixed with APPLYLENS_ (e.g., APPLYLENS_PROVIDERS).
    """

    # Provider mode: "mock" for testing, "real" for production
    PROVIDERS: Literal["mock", "real"] = "mock"

    # Gmail provider settings
    GMAIL_OAUTH_SECRETS_PATH: str | None = None
    GMAIL_OAUTH_TOKEN_PATH: str | None = None

    # BigQuery provider settings
    BQ_PROJECT: str | None = None
    BQ_CREDENTIALS_PATH: str | None = None

    # Elasticsearch provider settings
    ES_HOST: str = "http://elasticsearch:9200"
    ES_INDEX_EMAILS: str = "emails"
    ES_TIMEOUT: int = 30

    # dbt provider settings
    DBT_CMD: str = "dbt"
    DBT_PROFILES_DIR: str | None = None
    DBT_PROJECT_DIR: str = "analytics/dbt"

    # Audit logging
    AGENT_AUDIT_ENABLED: bool = True

    # SSE events
    AGENT_EVENTS_ENABLED: bool = True

    # Phase 5: Planning intelligence
    PLANNER_MODE: Literal["heuristic", "llm", "auto"] = "heuristic"
    PLANNER_CONFIDENCE_THRESHOLD: float = 0.7
    PLANNER_USE_MOCK_LLM: bool = True  # Use mock LLM in CI/dev

    # Phase 5.1: Canary routing & auto-rollback
    PLANNER_CANARY_PCT: float = 0.0  # Percentage of traffic to route to V2 (0-100)
    PLANNER_KILL_SWITCH: bool = False  # Emergency rollback to V1

    # Phase 5.4/5.5: Companion autofill bandit learning
    COMPANION_BANDIT_ENABLED: bool = (
        True  # Global kill-switch for Companion bandit style selection
    )

    # Phase 5: Evaluation & Quality Gates
    EVAL_BUDGETS_ENABLED: bool = True  # Enable budget enforcement
    EVAL_GATE_LOOKBACK_DAYS: int = 7  # Days to evaluate
    EVAL_GATE_BASELINE_DAYS: int = 14  # Days for baseline comparison
    EVAL_FAIL_ON_WARNING: bool = False  # Fail CI on warnings (default: only critical)

    # Phase 5: Intelligence Reports
    INTELLIGENCE_REPORT_ENABLED: bool = True  # Enable weekly reports
    INTELLIGENCE_SLACK_WEBHOOK: Optional[str] = None  # Slack webhook for reports
    INTELLIGENCE_EMAIL_RECIPIENTS: Optional[str] = None  # Comma-separated email list
    INTELLIGENCE_REPORT_DAY: str = "monday"  # Day of week to send reports
    INTELLIGENCE_SAVE_TO_FILE: bool = True  # Save reports to file system
    INTELLIGENCE_REPORTS_DIR: str = "reports"  # Directory for saved reports

    # Warehouse & Analytics (BigQuery)
    USE_WAREHOUSE: bool = False  # Enable BigQuery warehouse queries
    GCP_PROJECT: str | None = (
        None  # GCP project ID (fallback to BQ_PROJECT or "applylens-app")
    )
    GCP_BQ_LOCATION: str = "US"  # BigQuery dataset location
    GCP_CREDENTIALS_PATH: str | None = (
        None  # Path to service account JSON (uses ADC if not set)
    )

    # Archive & Auto-Delete Retention Policies
    AUTO_ARCHIVE_REJECTED_AFTER_DAYS: int = (
        14  # Auto-archive rejected apps after X days
    )
    AUTO_DELETE_ARCHIVED_AFTER_DAYS: int = 90  # Auto-delete archived apps after Y days
    ARCHIVE_GRACE_UNDO_HOURS: int = 48  # Grace period to undo archive (hours)

    # Authentication & Session Management
    GOOGLE_CLIENT_ID: str | None = None  # Google OAuth client ID
    GOOGLE_CLIENT_SECRET: str | None = None  # Google OAuth client secret
    OAUTH_REDIRECT_URI: str = (
        "http://localhost:5175/auth/google/callback"  # OAuth callback URL
    )
    SESSION_SECRET: str = "change_me_in_production"  # Secret for session signing
    COOKIE_DOMAIN: str = "localhost"  # Cookie domain (set to apex domain in prod)
    COOKIE_SECURE: str = "0"  # Set to "1" for HTTPS-only cookies
    COOKIE_SAMESITE: str = "lax"  # SameSite cookie policy
    ALLOW_DEMO: bool = True  # Allow demo mode login
    DEMO_READONLY: bool = True  # Demo accounts are read-only

    # Token Encryption (AES-GCM or GCP KMS)
    ENCRYPTION_ENABLED: int = 1  # Enable token encryption at rest
    AES_KEY_BASE64: str | None = None  # 32-byte key, base64 URL-safe encoded
    KMS_ENABLED: int = 0  # Enable GCP KMS envelope encryption
    KMS_PROJECT: str | None = None  # GCP project for KMS
    KMS_LOCATION: str | None = None  # GCP location (e.g., "us-central1")
    KMS_KEYRING: str | None = None  # KMS key ring name
    KMS_KEY: str | None = None  # KMS key name

    # CSRF Protection
    CSRF_ENABLED: int = 1  # Enable CSRF middleware
    CSRF_COOKIE_NAME: str = "csrf_token"  # CSRF token cookie name
    CSRF_HEADER_NAME: str = "X-CSRF-Token"  # CSRF token header name

    # Rate Limiting
    RATE_LIMIT_ENABLED: int = 1  # Enable rate limiting on /auth/* endpoints
    RATE_LIMIT_WINDOW_SEC: int = 60  # Rate limit window in seconds
    RATE_LIMIT_MAX_REQ: int = 60  # Max requests per window per IP
    RATE_LIMIT_REDIS_URL: str | None = None  # Redis URL for distributed rate limiting

    # reCAPTCHA Protection
    RECAPTCHA_ENABLED: int = 0  # Enable reCAPTCHA verification (disabled by default)
    RECAPTCHA_SITE_KEY: str | None = None  # reCAPTCHA v3 site key
    RECAPTCHA_SECRET_KEY: str | None = None  # reCAPTCHA v3 secret key
    RECAPTCHA_MIN_SCORE: float = 0.5  # Minimum score for reCAPTCHA v3 (0.0-1.0)

    class Config:
        env_prefix = "APPLYLENS_"
        case_sensitive = True


# Global settings instance
agent_settings = AgentSettings()


def get_agent_settings() -> AgentSettings:
    """Get agent settings instance.

    Returns:
        Agent settings configuration
    """
    return agent_settings
