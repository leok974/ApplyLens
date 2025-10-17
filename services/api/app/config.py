"""Configuration for agent system providers and features.

Controls which provider implementations are used (mock vs real)
and provides settings for real integrations.
"""

from __future__ import annotations

import os
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
