"""Rate limiting middleware for API endpoints.

Provides in-memory token bucket rate limiting for /auth/* endpoints.
Protects against brute force attacks and abuse during high traffic.
"""
import time
import hashlib
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import agent_settings
from app.core.metrics import rate_limit_exceeded_total, rate_limit_allowed_total

logger = logging.getLogger(__name__)


class MemoryBucket:
    """In-memory token bucket rate limiter.
    
    Uses a simple token bucket algorithm with per-IP, per-path tracking.
    For multi-instance deployments, use Redis-backed implementation.
    """
    
    def __init__(self, capacity: int, window: int):
        """Initialize bucket limiter.
        
        Args:
            capacity: Maximum requests allowed per window
            window: Time window in seconds
        """
        self.capacity = capacity
        self.window = window
        self.tokens = {}  # {key: {"ts": timestamp, "count": count}}
        logger.info(f"Rate limiter initialized: {capacity} req/{window}sec")
    
    def _key(self, ip: str, path: str) -> str:
        """Generate unique key for IP + path combination.
        
        Args:
            ip: Client IP address
            path: Request path
            
        Returns:
            SHA256 hash of IP:path
        """
        return hashlib.sha256(f"{ip}:{path}".encode()).hexdigest()
    
    def allow(self, ip: str, path: str) -> bool:
        """Check if request is allowed under rate limit.
        
        Args:
            ip: Client IP address
            path: Request path
            
        Returns:
            True if request allowed, False if rate limited
        """
        now = int(time.time())
        key = self._key(ip, path)
        bucket = self.tokens.get(key)
        
        # New window or expired bucket
        if not bucket or now - bucket["ts"] >= self.window:
            self.tokens[key] = {"ts": now, "count": 1}
            return True
        
        # Within window, check capacity
        if bucket["count"] < self.capacity:
            bucket["count"] += 1
            return True
        
        # Rate limited
        logger.warning(f"Rate limit exceeded: {ip} on {path} ({bucket['count']}/{self.capacity})")
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting auth endpoints.
    
    Limits requests to /auth/* paths based on IP address.
    Returns 429 Too Many Requests when limit exceeded.
    """
    
    def __init__(self, app, capacity: int, window: int):
        """Initialize middleware.
        
        Args:
            app: FastAPI application
            capacity: Max requests per window
            window: Time window in seconds
        """
        super().__init__(app)
        self.mem = MemoryBucket(capacity, window)
        logger.info("Rate limit middleware registered")
    
    async def dispatch(self, request: Request, call_next):
        """Process request and apply rate limiting.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler
            
        Returns:
            HTTP response (200 or 429)
        """
        if not agent_settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        path = request.url.path
        
        # Only limit auth and demo endpoints
        if path.startswith("/auth/"):
            # Extract real client IP from X-Forwarded-For header (first IP in chain)
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                # Take first IP (actual client), not last (proxy)
                ip = forwarded_for.split(",")[0].strip()
            else:
                ip = request.client.host if request.client else "0.0.0.0"
            
            if not self.mem.allow(ip, path):
                logger.warning(f"Rate limit exceeded: {ip} on {path}")
                # Track metric with IP prefix for privacy (first 2 octets only)
                ip_prefix = ".".join(ip.split(".")[:2]) + ".*.*" if "." in ip else "unknown"
                rate_limit_exceeded_total.labels(path=path, ip_prefix=ip_prefix).inc()
                return Response(
                    "Too Many Requests - Please slow down",
                    status_code=429,
                    headers={"Retry-After": str(agent_settings.RATE_LIMIT_WINDOW_SEC)}
                )
            
            # Request allowed
            rate_limit_allowed_total.labels(path=path).inc()
        
        return await call_next(request)
