"""Elasticsearch sync utilities for applications archive lifecycle.

Handles indexing, tombstoning, and deletion of applications in Elasticsearch.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def get_es_applications_index() -> str:
    """Get the Elasticsearch index name for applications."""
    return os.getenv("ES_APPS_INDEX", "applications_v1")


def es_available() -> bool:
    """Check if Elasticsearch is available and configured."""
    try:
        from elasticsearch import Elasticsearch
        
        url = (
            os.getenv("ELASTICSEARCH_URL")
            or f"http://{os.getenv('ES_HOST','localhost')}:{os.getenv('ES_PORT','9200')}"
        )
        if not url:
            return False
            
        es = Elasticsearch(url, request_timeout=2)
        return es.ping()
    except Exception:
        return False


def es_tombstone_application(app_id: int):
    """
    Mark an application as archived in Elasticsearch (tombstone pattern).
    
    Options:
    1. Set a `visible` field to False so default searches exclude it
    2. Delete the document entirely
    
    Current implementation: Set visible=False to allow restoration
    
    Args:
        app_id: Application ID to tombstone
    """
    if not es_available():
        logger.debug(f"[ES Sync] Elasticsearch not available, skipping tombstone for app {app_id}")
        return
    
    try:
        from elasticsearch import Elasticsearch
        
        url = (
            os.getenv("ELASTICSEARCH_URL")
            or f"http://{os.getenv('ES_HOST','localhost')}:{os.getenv('ES_PORT','9200')}"
        )
        user = os.getenv("ES_USER")
        pwd = os.getenv("ES_PASS")
        
        es = Elasticsearch(url, basic_auth=(user, pwd) if user and pwd else None)
        index = get_es_applications_index()
        
        # Update document to set visible=false
        es.update(
            index=index,
            id=str(app_id),
            body={
                "doc": {
                    "visible": False,
                    "archived": True
                }
            },
            refresh=True  # Make immediately searchable
        )
        
        logger.info(f"[ES Sync] Tombstoned application {app_id} in {index}")
        
    except Exception as e:
        logger.error(f"[ES Sync] Failed to tombstone application {app_id}: {e}")


def es_upsert_application(app):
    """
    Upsert an application document in Elasticsearch (for restore).
    
    Re-indexes the application and sets visible=True.
    
    Args:
        app: Application model instance
    """
    if not es_available():
        logger.debug(f"[ES Sync] Elasticsearch not available, skipping upsert for app {app.id}")
        return
    
    try:
        from elasticsearch import Elasticsearch
        
        url = (
            os.getenv("ELASTICSEARCH_URL")
            or f"http://{os.getenv('ES_HOST','localhost')}:{os.getenv('ES_PORT','9200')}"
        )
        user = os.getenv("ES_USER")
        pwd = os.getenv("ES_PASS")
        
        es = Elasticsearch(url, basic_auth=(user, pwd) if user and pwd else None)
        index = get_es_applications_index()
        
        # Build document
        doc = {
            "id": app.id,
            "company": app.company,
            "role": app.role,
            "status": app.status.value if app.status else None,
            "source": app.source,
            "source_confidence": app.source_confidence,
            "thread_id": app.thread_id,
            "gmail_thread_id": app.gmail_thread_id,
            "notes": app.notes,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "updated_at": app.updated_at.isoformat() if app.updated_at else None,
            "archived_at": app.archived_at.isoformat() if app.archived_at else None,
            "deleted_at": app.deleted_at.isoformat() if app.deleted_at else None,
            "visible": True,  # Set visible to true on restore
            "archived": False
        }
        
        # Upsert document
        es.index(
            index=index,
            id=str(app.id),
            document=doc,
            refresh=True  # Make immediately searchable
        )
        
        logger.info(f"[ES Sync] Upserted application {app.id} in {index}")
        
    except Exception as e:
        logger.error(f"[ES Sync] Failed to upsert application {app.id}: {e}")


def es_delete_application(app_id: int):
    """
    Permanently delete an application from Elasticsearch.
    
    Args:
        app_id: Application ID to delete
    """
    if not es_available():
        logger.debug(f"[ES Sync] Elasticsearch not available, skipping delete for app {app_id}")
        return
    
    try:
        from elasticsearch import Elasticsearch
        
        url = (
            os.getenv("ELASTICSEARCH_URL")
            or f"http://{os.getenv('ES_HOST','localhost')}:{os.getenv('ES_PORT','9200')}"
        )
        user = os.getenv("ES_USER")
        pwd = os.getenv("ES_PASS")
        
        es = Elasticsearch(url, basic_auth=(user, pwd) if user and pwd else None)
        index = get_es_applications_index()
        
        # Delete document
        es.delete(
            index=index,
            id=str(app_id),
            refresh=True,  # Make immediately searchable
            ignore=[404]  # Ignore if not found
        )
        
        logger.info(f"[ES Sync] Deleted application {app_id} from {index}")
        
    except Exception as e:
        logger.error(f"[ES Sync] Failed to delete application {app_id}: {e}")


def ensure_archived_excluded_from_search() -> str:
    """
    Get a filter clause to exclude archived applications from default searches.
    
    Returns:
        Elasticsearch query filter to exclude archived applications
    """
    return """
    Add this to your Elasticsearch queries to exclude archived applications:
    
    {
      "bool": {
        "must_not": [
          {"term": {"visible": false}},
          {"term": {"archived": true}},
          {"exists": {"field": "archived_at"}}
        ]
      }
    }
    
    Or more simply, if visible field is maintained:
    {
      "term": {"visible": true}
    }
    """
