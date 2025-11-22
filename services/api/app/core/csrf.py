"""CSRF protection middleware and utilities.

Protects against Cross-Site Request Forgery attacks by requiring
a CSRF token for all state-changing requests (POST, PUT, PATCH, DELETE).
"""

import secrets
import logging
import os
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import agent_settings
from app.core.metrics import csrf_fail_total, csrf_success_total

logger = logging.getLogger(__name__)

# HTTP methods that are considered safe and don't require CSRF protection
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

# Machine-to-machine and automation endpoints - exempt from CSRF
# These paths are designed for non-browser clients (automation, backfill, etc.)
EXEMPT_PREFIXES = (
    "/api/extension/",  # Browser extension (dev-only)
    "/extension/",  # Without /api prefix (nginx strips)
    "/api/ops/diag",  # DevDiag diagnostics proxy
    "/api/gmail/",  # Gmail backfill/ingest automation
    "/gmail/",  # Without /api prefix
    "/api/agent/",  # Agent v1 endpoints (legacy)
    "/agent/",  # Without /api prefix
    "/api/v2/agent/",  # Agent v2 endpoints (AI assistant)
    "/v2/agent/",  # Without /api prefix
)

EXEMPT_EXACT = {
    "/api/profile/me",  # Profile brain (dev-only)
    "/profile/me",  # Without /api prefix
    "/api/ops/diag/health",  # DevDiag health check
    "/api/auth/e2e/login",  # E2E test authentication (test-only, guarded by E2E_PROD)
    "/auth/e2e/login",  # Without /api prefix
}

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


def _has_auth_header(request: Request) -> bool:
    """Check if request has machine-to-machine authentication.

    Skip CSRF validation if Authorization (Bearer token) or X-API-Key header is present.
    This allows automation scripts, CI/CD, and other non-browser clients to bypass CSRF.

    Args:
        request: Incoming HTTP request

    Returns:
        True if M2M auth header is present
    """
    auth = request.headers.get("authorization", "").strip()
    api_key = request.headers.get("x-api-key", "").strip()
    return bool(auth or api_key)


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

        path = request.url.path

        # 1) Global exemptions by path (non-browser automations)
        if path.startswith(EXEMPT_PREFIXES) or path in EXEMPT_EXACT:
            logger.debug(f"CSRF exempt M2M path: {request.method} {path}")
            response = await call_next(request)
            # Still set cookie for future browser requests
            response.set_cookie(
                key=agent_settings.CSRF_COOKIE_NAME,
                value=token,
                httponly=False,
                secure=agent_settings.COOKIE_SECURE == "1",
                samesite="lax",
                path="/",
            )
            return response

        # 2) M2M: if an Authorization or X-API-Key header is present, skip CSRF
        if _has_auth_header(request):
            logger.debug(f"CSRF exempt M2M auth: {request.method} {path}")
            response = await call_next(request)
            # No cookie needed for M2M clients
            return response

        # Check if path is exempt from CSRF protection
        if path in CSRF_EXEMPT_PATHS:
            logger.debug(f"CSRF exempt path: {request.method} {path}")
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

            # Normalize metric label path to ensure consistency
            # (nginx may strip /api prefix, so normalize for metrics)
            label_path = (
                path
                if path.startswith("/api/")
                else f"/api{path}"
                if path.startswith("/extension/") or path.startswith("/profile/")
                else path
            )

            # Dev mode: Allow cookie-only validation for dev routes
            # This makes Playwright tests and dev ergonomics easier
            is_dev_mode = os.getenv("ALLOW_DEV_ROUTES") == "1"
            is_dev_route = (
                path.startswith("/api/dev/")
                or path.startswith("/dev/")  # Without /api prefix (nginx strips it)
                or path.startswith("/api/security/")
                or path.startswith("/security/")  # Without /api prefix
                or path.startswith("/api/gmail/backfill/")
                or path.startswith("/gmail/backfill/")  # Without /api prefix
                or "/risk-feedback" in path  # Email risk feedback endpoint
                or "/risk-advice" in path  # Email risk advice endpoint
            )

            if is_dev_mode and is_dev_route and not header_token:
                # In dev mode, dev routes can proceed with cookie-only validation
                logger.debug(
                    f"CSRF dev mode: Cookie-only validation for {request.method} {path}"
                )
                csrf_success_total.labels(path=label_path, method=request.method).inc()
                # Continue to process request - cookie already validated by presence
            elif not header_token:
                logger.warning(
                    f"CSRF failure: Missing {agent_settings.CSRF_HEADER_NAME} header for {request.method} {path}"
                )
                csrf_fail_total.labels(path=label_path, method=request.method).inc()
                return Response("CSRF token missing", status_code=403)
            elif header_token != token:
                logger.warning(
                    f"CSRF failure: Token mismatch for {request.method} {path}"
                )
                csrf_fail_total.labels(path=label_path, method=request.method).inc()
                return Response("CSRF token invalid", status_code=403)
            else:
                logger.debug(f"CSRF validated for {request.method} {path}")
                csrf_success_total.labels(path=label_path, method=request.method).inc()

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
