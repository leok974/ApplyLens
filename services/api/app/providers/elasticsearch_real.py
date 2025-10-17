"""Real Elasticsearch provider implementation.

Integrates with Elasticsearch cluster for document operations.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..schemas.tools import ESSearchResponse


class ESProvider:
    """Real Elasticsearch provider.
    
    Uses elasticsearch-py client library.
    Requires ES_HOST configuration.
    """
    
    def __init__(
        self,
        host: str | None = None,
        index: str | None = None,
        timeout: int = 30
    ):
        """Initialize Elasticsearch provider.
        
        Args:
            host: Elasticsearch host URL
            index: Default index name
            timeout: Request timeout in seconds
        """
        self.host = host or os.getenv("ES_HOST", "http://elasticsearch:9200")
        self.index = index or os.getenv("ES_INDEX_EMAILS", "emails")
        self.timeout = timeout
        self._client = None
    
    def _get_client(self):
        """Lazy-load Elasticsearch client.
        
        Returns:
            Elasticsearch client instance
        """
        if self._client is None:
            try:
                from elasticsearch import Elasticsearch
                
                self._client = Elasticsearch(
                    hosts=[self.host],
                    timeout=self.timeout
                )
                
                # Verify connection
                if not self._client.ping():
                    raise ConnectionError(f"Cannot connect to Elasticsearch at {self.host}")
                    
            except Exception as e:
                raise NotImplementedError(
                    f"Elasticsearch integration pending: {e}. "
                    "Set APPLYLENS_PROVIDERS=mock for testing."
                )
        return self._client
    
    def search(self, query: dict[str, Any], index: str | None = None) -> "ESSearchResponse":
        """Search documents.
        
        Args:
            query: Elasticsearch query DSL
            index: Index to search (uses default if not specified)
            
        Returns:
            Search response with hits
        """
        from ..schemas.tools import ESSearchHit, ESSearchResponse
        
        client = self._get_client()
        idx = index or self.index
        
        # Execute search
        response = client.search(
            index=idx,
            body={"query": query, "size": 100}
        )
        
        # Parse hits
        hits = []
        for hit in response["hits"]["hits"]:
            hits.append(ESSearchHit(
                id=hit["_id"],
                score=hit.get("_score", 0.0),
                source=hit["_source"]
            ))
        
        return ESSearchResponse(hits=hits)
    
    def aggregate_daily(self, index: str | None = None, days: int = 7) -> list[dict[str, Any]]:
        """Aggregate document counts by day.
        
        Args:
            index: Index to query
            days: Number of days to aggregate
            
        Returns:
            List of {day: str, count: int} dicts
        """
        client = self._get_client()
        idx = index or self.index
        
        # Date histogram aggregation
        response = client.search(
            index=idx,
            body={
                "size": 0,
                "query": {
                    "range": {
                        "received_at": {"gte": f"now-{days}d/d"}
                    }
                },
                "aggs": {
                    "daily": {
                        "date_histogram": {
                            "field": "received_at",
                            "calendar_interval": "1d"
                        }
                    }
                }
            }
        )
        
        buckets = response["aggregations"]["daily"]["buckets"]
        return [
            {"day": bucket["key_as_string"][:10], "emails": bucket["doc_count"]}
            for bucket in buckets
        ]
    
    def latest_event_ts(self, index: str | None = None) -> str | None:
        """Get timestamp of most recent document.
        
        Args:
            index: Index to query
            
        Returns:
            ISO timestamp string or None
        """
        client = self._get_client()
        idx = index or self.index
        
        response = client.search(
            index=idx,
            body={
                "size": 1,
                "sort": [{"received_at": {"order": "desc"}}],
                "_source": ["received_at"]
            }
        )
        
        hits = response["hits"]["hits"]
        if not hits:
            return None
        
        return hits[0]["_source"].get("received_at")
