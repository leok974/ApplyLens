"""CSRF protection middleware and utilities.

Protects against Cross-Site Request Forgery attacks by requiring
a CSRF token for all state-changing requests (POST, PUT, PATCH, DELETE).
"""

import secrets
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import agent_settings
from app.core.metrics import csrf_fail_total, csrf_success_total

logger = logging.getLogger(__name__)

# HTTP methods that are considered safe and don't require CSRF protection
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

# Paths that are exempt from CSRF protection (e.g., non-sensitive UX metrics)
CSRF_EXEMPT_PATHS = {
    "/ux/heartbeat",  # Via nginx proxy (strips /api prefix)
    "/api/ux/heartbeat",  # Direct API access (for testing/monitoring)
    "/ux/chat/opened",  # Chat engagement metric (via nginx)
    "/api/ux/chat/opened",  # Direct API access
    "/chat",  # Chat endpoint (without /api prefix)
    "/chat/stream",  # EventSource (SSE) - can't send custom headers
    "/api/chat",  # Chat endpoint (with /api prefix, for nginx)
    "/api/chat/stream",  # EventSource via nginx
    "/assistant/query",  # Assistant query endpoint
    "/api/assistant/query",  # Assistant via nginx
}


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware for FastAPI.

    Validates CSRF tokens on all non-safe HTTP methods.
    Issues and rotates CSRF tokens automatically via cookies.
    """

    async def dispatch(self, request: Request, call_next):
        """Process request and validate CSRF token if needed.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response with CSRF cookie set
        """
        if not agent_settings.CSRF_ENABLED:
            # CSRF protection disabled - pass through
            return await call_next(request)

        # Get or generate CSRF token from cookie
        token = request.cookies.get(agent_settings.CSRF_COOKIE_NAME)
        if not token:
            token = secrets.token_urlsafe(32)
            logger.debug("Generated new CSRF token")

        # Check if path is exempt from CSRF protection
        if request.url.path in CSRF_EXEMPT_PATHS:
            logger.debug(f"CSRF exempt path: {request.method} {request.url.path}")
            response = await call_next(request)
            # Still set cookie for future requests
            response.set_cookie(
                key=agent_settings.CSRF_COOKIE_NAME,
                value=token,
                httponly=False,
                secure=agent_settings.COOKIE_SECURE == "1",
                samesite="lax",
                path="/",
            )
            return response

        # Validate token for unsafe methods
        if request.method not in SAFE_METHODS:
            header_token = request.headers.get(agent_settings.CSRF_HEADER_NAME)

            if not header_token:
                logger.warning(
                    f"CSRF failure: Missing {agent_settings.CSRF_HEADER_NAME} header for {request.method} {request.url.path}"
                )
                csrf_fail_total.labels(
                    path=request.url.path, method=request.method
                ).inc()
                return Response("CSRF token missing", status_code=403)

            if header_token != token:
                logger.warning(
                    f"CSRF failure: Token mismatch for {request.method} {request.url.path}"
                )
                csrf_fail_total.labels(
                    path=request.url.path, method=request.method
                ).inc()
                return Response("CSRF token invalid", status_code=403)

            logger.debug(f"CSRF validated for {request.method} {request.url.path}")
            csrf_success_total.labels(
                path=request.url.path, method=request.method
            ).inc()

        # Process request
        response = await call_next(request)

        # Set/update CSRF cookie on every response
        # httponly=False allows JavaScript to read the token
        response.set_cookie(
            key=agent_settings.CSRF_COOKIE_NAME,
            value=token,
            httponly=False,  # JS needs to read this for AJAX requests
            secure=agent_settings.COOKIE_SECURE == "1",
            samesite="lax",
            path="/",
        )

        return response


def issue_csrf_cookie(response: Response):
    """Helper to issue a CSRF cookie during login redirects.

    Args:
        response: FastAPI Response object to add cookie to
    """
    token = secrets.token_urlsafe(32)
    response.set_cookie(
        key=agent_settings.CSRF_COOKIE_NAME,
        value=token,
        httponly=False,  # JS needs to read this
        secure=agent_settings.COOKIE_SECURE == "1",
        samesite="lax",
        path="/",
    )
    logger.debug("Issued CSRF cookie")


# Force rebuild
# Force rebuild 2
