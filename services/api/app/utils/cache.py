"""
Lightweight Redis cache utility for API responses.

Provides simple key-value caching with TTL support. Falls back gracefully
if Redis is not available (returns None for gets, no-ops for sets).
"""

import json
import os
from typing import Optional

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore

_redis: Optional["redis.Redis"] = None  # type: ignore


def get_redis() -> Optional["redis.Redis"]:  # type: ignore
    """
    Get Redis client singleton.
    
    Returns None if Redis is not available or configured.
    """
    global _redis
    if not REDIS_AVAILABLE:
        return None
    
    if _redis is not None:
        return _redis
    
    url = os.getenv("REDIS_URL")
    if not url:
        return None
    
    try:
        _redis = redis.from_url(url, decode_responses=True)  # type: ignore
        # Test connection
        _redis.ping()
        return _redis
    except Exception:
        return None


def cache_get(key: str) -> Optional[dict]:
    """
    Get cached value by key.
    
    Args:
        key: Cache key
        
    Returns:
        Cached dict or None if not found/expired/unavailable
    """
    r = get_redis()
    if not r:
        return None
    
    try:
        raw = r.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def cache_set(key: str, value: dict, ttl: int = 60) -> None:
    """
    Set cached value with TTL.
    
    Args:
        key: Cache key
        value: Dict to cache (will be JSON serialized)
        ttl: Time-to-live in seconds (default 60s)
    """
    r = get_redis()
    if not r:
        return
    
    try:
        r.setex(key, ttl, json.dumps(value))
    except Exception:
        # Fail gracefully - caching is optional
        pass


def cache_delete(key: str) -> None:
    """
    Delete cached value.
    
    Args:
        key: Cache key to delete
    """
    r = get_redis()
    if not r:
        return
    
    try:
        r.delete(key)
    except Exception:
        pass
