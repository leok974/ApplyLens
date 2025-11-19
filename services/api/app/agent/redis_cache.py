"""
Agent v2 - Redis caching for domain risk and session state.

Phase 2 implementation:
- Domain risk cache (avoid recomputing security signals)
- Chat session cache (maintain context across queries)
"""

from typing import Optional, Dict, Any
import json
import logging
import os
from datetime import datetime

import redis.asyncio as redis
from app.schemas_agent import DomainRiskCache, ChatSessionCache
from app.agent.metrics import (
    agent_redis_hits_total,
    agent_redis_errors_total,
    agent_redis_latency_seconds,
)

logger = logging.getLogger(__name__)

# Global Redis client (initialized on first use)
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """Get async Redis client with connection pooling."""
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    url = os.getenv("REDIS_URL")
    if not url:
        logger.warning("REDIS_URL not set; Redis caching disabled for agent")
        return None

    # Optional separate DB for agent if you want: redis://host:port/2
    agent_url = os.getenv("REDIS_AGENT_URL", url)

    try:
        _redis_client = redis.from_url(agent_url, decode_responses=True)
        logger.info("Redis client initialized for agent")
        return _redis_client
    except Exception as e:
        logger.error(f"Failed to initialize Redis client: {e}")
        return None


async def _get_json(key: str) -> Optional[dict]:
    """Internal helper to get JSON from Redis with metrics."""
    client = get_redis_client()
    if client is None:
        return None

    with agent_redis_latency_seconds.labels(kind="get").time():
        try:
            raw = await client.get(key)
        except Exception as exc:
            logger.exception("Redis GET failed for %s: %s", key, exc)
            agent_redis_errors_total.labels(kind="get").inc()
            return None

    if raw is None:
        agent_redis_hits_total.labels(kind="get", result="miss").inc()
        return None

    agent_redis_hits_total.labels(kind="get", result="hit").inc()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in Redis for key %s; deleting", key)
        await client.delete(key)
        return None


async def _set_json(key: str, value: dict, ttl_seconds: int) -> None:
    """Internal helper to set JSON in Redis with metrics."""
    client = get_redis_client()
    if client is None:
        return

    with agent_redis_latency_seconds.labels(kind="set").time():
        try:
            await client.set(key, json.dumps(value), ex=ttl_seconds)
        except Exception as exc:
            logger.exception("Redis SET failed for %s: %s", key, exc)
            agent_redis_errors_total.labels(kind="set").inc()


# ============================================================================
# Domain Risk Cache
# ============================================================================

DOMAIN_RISK_TTL_SECONDS = int(
    os.getenv("AGENT_DOMAIN_RISK_TTL_SECONDS", "2592000")
)  # 30d


async def get_domain_risk(domain: str) -> Optional[DomainRiskCache]:
    """
    Get cached domain risk intelligence.

    Returns None if not cached or Redis unavailable.
    """
    key = f"agent:domain_risk:{domain.lower()}"
    data = await _get_json(key)
    if not data:
        return None
    try:
        return DomainRiskCache(**data)
    except Exception:
        logger.exception("Failed to parse DomainRiskCache from Redis for %s", domain)
        return None


async def set_domain_risk(domain: str, cache: DomainRiskCache) -> None:
    """
    Cache domain risk intelligence.

    TTL: 30 days (default, configurable via AGENT_DOMAIN_RISK_TTL_SECONDS).
    """
    key = f"agent:domain_risk:{domain.lower()}"
    await _set_json(key, cache.dict(), ttl_seconds=DOMAIN_RISK_TTL_SECONDS)


async def update_domain_stats(domain: str, email_count_delta: int = 1) -> bool:
    """
    Increment email count for a domain (without overwriting full cache).

    Useful when processing new emails.
    """
    try:
        # Get existing cache
        cached = await get_domain_risk(domain)
        if not cached:
            return False

        # Update count
        cached.email_count += email_count_delta
        cached.last_seen_at = datetime.utcnow()

        # Save back
        return await set_domain_risk(domain, cached)

    except Exception as e:
        logger.error(f"Redis update_domain_stats failed for {domain}: {e}")
        return False


# ============================================================================
# Chat Session Cache
# ============================================================================

SESSION_TTL_SECONDS = int(os.getenv("AGENT_SESSION_TTL_SECONDS", "3600"))  # 1h


async def get_session_context(user_id: str) -> Optional[ChatSessionCache]:
    """
    Get cached chat session context.

    Helps interpret follow-up queries without frontend re-sending full context.
    """
    key = f"agent:session:{user_id}"
    data = await _get_json(key)
    if not data:
        return None
    try:
        return ChatSessionCache(**data)
    except Exception:
        logger.exception("Failed to parse ChatSessionCache from Redis for %s", user_id)
        return None


async def set_session_context(user_id: str, cache: ChatSessionCache) -> None:
    """
    Cache chat session context.

    TTL: 1 hour (default, configurable via AGENT_SESSION_TTL_SECONDS).
    """
    key = f"agent:session:{user_id}"
    await _set_json(key, cache.dict(), ttl_seconds=SESSION_TTL_SECONDS)


async def clear_session_context(user_id: str) -> bool:
    """Clear chat session cache (e.g., on explicit user reset)."""
    try:
        client = await get_redis_client()
        if not client:
            return False

        key = f"chat:session:{user_id}"
        await client.delete(key)
        logger.debug(f"Cleared session for {user_id}")
        return True

    except Exception as e:
        logger.error(f"Redis clear_session_context failed for {user_id}: {e}")
        return False


# ============================================================================
# Health Check
# ============================================================================


async def redis_health_check() -> Dict[str, Any]:
    """
    Check Redis connectivity.

    Returns: {"status": "ok" | "error", "latency_ms": int, "error": str}
    """
    try:
        client = await get_redis_client()
        if not client:
            return {"status": "error", "error": "Redis client not initialized"}

        start = datetime.utcnow()
        await client.ping()
        latency_ms = int((datetime.utcnow() - start).total_seconds() * 1000)

        return {"status": "ok", "latency_ms": latency_ms}

    except Exception as e:
        return {"status": "error", "error": str(e)}
