"""Real BigQuery provider implementation.

Integrates with Google BigQuery using service account or ADC.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..schemas.tools import BQQueryResult


class BigQueryProvider:
    """Real BigQuery provider.
    
    Uses google-cloud-bigquery client library.
    Requires BQ_PROJECT and optionally BQ_CREDENTIALS_PATH.
    """
    
    def __init__(
        self,
        project: str | None = None,
        credentials_path: str | None = None
    ):
        """Initialize BigQuery provider.
        
        Args:
            project: GCP project ID
            credentials_path: Path to service account JSON
        """
        self.project = project or os.getenv("BQ_PROJECT")
        self.credentials_path = credentials_path or os.getenv("BQ_CREDENTIALS_PATH")
        self._client = None
    
    def _get_client(self):
        """Lazy-load BigQuery client.
        
        Returns:
            BigQuery client instance
        """
        if self._client is None:
            try:
                from google.cloud import bigquery
                from google.oauth2 import service_account
                
                if self.credentials_path:
                    credentials = service_account.Credentials.from_service_account_file(
                        self.credentials_path
                    )
                    self._client = bigquery.Client(
                        project=self.project,
                        credentials=credentials
                    )
                else:
                    # Use Application Default Credentials
                    self._client = bigquery.Client(project=self.project)
            except Exception as e:
                raise NotImplementedError(
                    f"BigQuery integration pending: {e}. "
                    "Set APPLYLENS_PROVIDERS=mock for testing."
                )
        return self._client
    
    def query(self, sql: str) -> "BQQueryResult":
        """Execute a SQL query.
        
        Args:
            sql: SQL query to execute
            
        Returns:
            Query result with rows and statistics
        """
        from ..schemas.tools import BQQueryResult
        
        client = self._get_client()
        
        query_job = client.query(sql)
        results = query_job.result()
        
        # Convert rows to dicts
        rows = [dict(row) for row in results]
        
        # Collect stats
        stats = {
            "bytes_processed": query_job.total_bytes_processed or 0,
            "bytes_billed": query_job.total_bytes_billed or 0,
            "cached": query_job.cache_hit or False,
            "execution_time_ms": query_job.ended - query_job.started if query_job.ended else 0,
        }
        
        return BQQueryResult(rows=rows, stats=stats)
    
    def query_rows(self, sql: str) -> list[dict[str, Any]]:
        """Execute query and return only rows.
        
        Args:
            sql: SQL query
            
        Returns:
            List of row dictionaries
        """
        result = self.query(sql)
        return result.rows
    
    def query_scalar(self, sql: str) -> Any:
        """Execute query expecting single scalar value.
        
        Args:
            sql: SQL query returning single value
            
        Returns:
            First column of first row
        """
        rows = self.query_rows(sql)
        if not rows:
            return None
        first_row = rows[0]
        return next(iter(first_row.values()))
