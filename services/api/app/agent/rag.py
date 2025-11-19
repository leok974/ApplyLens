"""
Agent v2 - RAG (Retrieval-Augmented Generation)

Phase 3 implementation:
- Email-based RAG (use ES to retrieve relevant emails)
- Knowledge base RAG (curated phishing/job search docs)
- LLM synthesis with retrieved contexts
"""

from typing import List, Optional
import logging
from datetime import datetime, timedelta

from elasticsearch import AsyncElasticsearch

from app.schemas_agent import RAGContext, KnowledgeBaseEntry
from app.agent.metrics import mailbox_agent_rag_context_count

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================


def _build_time_filter(time_window_days: Optional[int]) -> Optional[dict]:
    """Build ES time range filter."""
    if not time_window_days:
        return None
    now = datetime.utcnow()
    gte = (now - timedelta(days=time_window_days)).isoformat()
    return {"range": {"received_at": {"gte": gte}}}


# ============================================================================
# Email Context Retrieval
# ============================================================================


async def retrieve_email_contexts(
    es: AsyncElasticsearch,
    user_id: str,
    query_text: str,
    time_window_days: Optional[int] = None,
    max_results: int = 20,
) -> List[RAGContext]:
    """
    Retrieve relevant email snippets for RAG from ES.

    Phase 3.1: Use BM25 (no vectors yet)
    Phase 3.2: Add vector search for semantic matching
    """
    must = [{"match": {"body": query_text}}]
    filter_clauses = [{"term": {"user_id": user_id}}]

    time_filter = _build_time_filter(time_window_days)
    if time_filter:
        filter_clauses.append(time_filter)

    body = {
        "query": {
            "bool": {
                "must": must,
                "filter": filter_clauses,
            }
        },
        "_source": ["id", "thread_id", "subject", "body", "from", "received_at"],
    }

    try:
        res = await es.search(
            index="gmail_emails",  # adapt to your index name
            body=body,
            size=max_results,
        )
    except Exception as exc:
        logger.exception("RAG email search failed: %s", exc)
        return []

    contexts: List[RAGContext] = []
    for hit in res["hits"]["hits"]:
        src = hit["_source"]
        contexts.append(
            RAGContext(
                source_type="email",
                source_id=str(src.get("id") or hit["_id"]),
                content=f"Subject: {src.get('subject', '(no subject)')}\n\n{src.get('body', '')[:800]}",
                score=hit.get("_score", 0) / 10.0,  # Normalize to 0-1 range
                metadata={
                    "thread_id": src.get("thread_id"),
                    "from": src.get("from"),
                    "received_at": src.get("received_at"),
                    "subject": src.get("subject"),
                },
            )
        )

    mailbox_agent_rag_context_count.labels("emails").inc(len(contexts))
    return contexts


# ============================================================================
# Knowledge Base Context Retrieval
# ============================================================================


async def retrieve_kb_contexts(
    es: AsyncElasticsearch,
    query_text: str,
    max_results: int = 5,
) -> List[RAGContext]:
    """
    Retrieve KB docs (phishing tips, job advice, etc.) from a dedicated index.

    Phase 3.1: Simple text search in Postgres/ES
    Phase 3.2: Add pgvector for semantic search
    """
    body = {
        "query": {
            "multi_match": {
                "query": query_text,
                "fields": ["title^3", "content"],
            }
        },
        "_source": ["id", "title", "content", "tags", "category"],
    }

    try:
        res = await es.search(
            index="agent_kb",  # create this ES index with your KB docs
            body=body,
            size=max_results,
        )
    except Exception as exc:
        logger.exception("RAG KB search failed: %s", exc)
        return []

    contexts: List[RAGContext] = []
    for hit in res["hits"]["hits"]:
        src = hit["_source"]
        contexts.append(
            RAGContext(
                source_type="knowledge_base",
                source_id=str(src.get("id") or hit["_id"]),
                content=src.get("content", "")[:800],
                score=hit.get("_score", 0) / 10.0,  # Normalize to 0-1 range
                metadata={
                    "title": src.get("title"),
                    "tags": src.get("tags", []),
                    "category": src.get("category"),
                },
            )
        )

    mailbox_agent_rag_context_count.labels("kb").inc(len(contexts))
    return contexts


# ============================================================================
# Knowledge Base Management
# ============================================================================


async def add_kb_entry(entry: KnowledgeBaseEntry) -> bool:
    """
    Add entry to knowledge base.

    Stores in:
    - Postgres (source of truth)
    - Elasticsearch (for text search)
    - TODO Phase 3.2: pgvector (for semantic search)
    """
    try:
        # TODO: Implement KB storage
        return False

    except Exception as e:
        logger.error(f"Failed to add KB entry: {e}", exc_info=True)
        return False


async def list_kb_entries(
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 100,
) -> List[KnowledgeBaseEntry]:
    """List knowledge base entries with optional filters."""
    try:
        # TODO: Implement KB listing
        return []

    except Exception as e:
        logger.error(f"Failed to list KB entries: {e}", exc_info=True)
        return []


async def delete_kb_entry(entry_id: str) -> bool:
    """Delete knowledge base entry."""
    try:
        # TODO: Implement KB deletion
        return False

    except Exception as e:
        logger.error(f"Failed to delete KB entry: {e}", exc_info=True)
        return False


# ============================================================================
# Fallback Strategies
# ============================================================================


async def get_fallback_answer(query: str, intent: str) -> str:
    """
    Get safe fallback answer when RAG fails.

    Returns generic but helpful responses based on intent.
    """
    fallback_templates = {
        "suspicious": (
            "I'm having trouble accessing your emails right now. "
            "In general, watch for: emails from unknown senders, urgent requests for personal info, "
            "mismatched sender addresses, and suspicious links. "
            "Check the sender's email address carefully."
        ),
        "bills": (
            "I can't retrieve your emails at the moment. "
            "To manage bills, check your inbox for keywords like 'invoice', 'payment due', "
            "or 'statement'. You can also search by sender (e.g., 'from:utility-company')."
        ),
        "follow_ups": (
            "I'm unable to access your inbox right now. "
            "For follow-ups, look for emails where you were the last to respond, "
            "or search for keywords like 'waiting', 'pending', or 'following up'."
        ),
        "interviews": (
            "I can't check your emails at the moment. "
            "For interview tracking, search for keywords like 'interview', 'schedule', "
            "or sender domains from recruiting companies."
        ),
        "generic": (
            "I'm having trouble accessing your emails right now. "
            "Please try again in a moment, or use the search bar to find specific emails."
        ),
    }

    return fallback_templates.get(intent, fallback_templates["generic"])
