"""Provider factory for dependency injection.

Determines which provider implementation to use based on configuration.
Enables testing with mocks while supporting real providers in production.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..config import agent_settings

if TYPE_CHECKING:
    from typing import Protocol
    
    class GmailProviderProtocol(Protocol):
        def search_recent(self, days: int = 7): ...
    
    class BigQueryProviderProtocol(Protocol):
        def query(self, sql: str): ...
        def query_rows(self, sql: str): ...
        def query_scalar(self, sql: str): ...
    
    class DbtProviderProtocol(Protocol):
        def run(self, target: str = "prod", models: str | None = None): ...
    
    class ESProviderProtocol(Protocol):
        def search(self, query: dict, index: str | None = None): ...
        def aggregate_daily(self, index: str | None = None, days: int = 7): ...
        def latest_event_ts(self, index: str | None = None): ...


class ProviderFactory:
    """Factory for creating provider instances.
    
    Returns mock or real providers based on agent_settings.PROVIDERS.
    Mock providers are defined in tools modules for simplicity.
    Real providers are in the providers package.
    """
    
    def gmail(self) -> "GmailProviderProtocol":
        """Get Gmail provider.
        
        Returns:
            Gmail provider instance (mock or real)
        """
        if agent_settings.PROVIDERS == "real":
            from . import gmail_real
            return gmail_real.GmailProvider(
                secrets_path=agent_settings.GMAIL_OAUTH_SECRETS_PATH,
                token_path=agent_settings.GMAIL_OAUTH_TOKEN_PATH
            )
        
        # Mock provider
        from ..tools.gmail import _MockGmailProvider
        return _MockGmailProvider()
    
    def bigquery(self) -> "BigQueryProviderProtocol":
        """Get BigQuery provider.
        
        Returns:
            BigQuery provider instance (mock or real)
        """
        if agent_settings.PROVIDERS == "real":
            from . import bigquery_real
            return bigquery_real.BigQueryProvider(
                project=agent_settings.BQ_PROJECT,
                credentials_path=agent_settings.BQ_CREDENTIALS_PATH
            )
        
        # Mock provider
        from ..tools.bigquery import _MockBQProvider
        return _MockBQProvider()
    
    def dbt(self) -> "DbtProviderProtocol":
        """Get dbt provider.
        
        Returns:
            dbt provider instance (mock or real)
        """
        if agent_settings.PROVIDERS == "real":
            from . import dbt_real
            return dbt_real.DbtProvider(
                cmd=agent_settings.DBT_CMD,
                project_dir=agent_settings.DBT_PROJECT_DIR,
                profiles_dir=agent_settings.DBT_PROFILES_DIR
            )
        
        # Mock provider
        from ..tools.dbt import _MockDbtProvider
        return _MockDbtProvider()
    
    def es(self) -> "ESProviderProtocol":
        """Get Elasticsearch provider.
        
        Returns:
            Elasticsearch provider instance (mock or real)
        """
        if agent_settings.PROVIDERS == "real":
            from . import elasticsearch_real
            return elasticsearch_real.ESProvider(
                host=agent_settings.ES_HOST,
                index=agent_settings.ES_INDEX_EMAILS,
                timeout=agent_settings.ES_TIMEOUT
            )
        
        # Mock provider
        from ..tools.elasticsearch import _MockESProvider
        return _MockESProvider()


# Global factory instance
provider_factory = ProviderFactory()


def get_provider_factory() -> ProviderFactory:
    """Get provider factory instance.
    
    Returns:
        Provider factory
    """
    return provider_factory
