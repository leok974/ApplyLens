import os

# Allow HTTP for local development (MUST be set before importing oauthlib!)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

import base64
import datetime as dt
import json
import secrets

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow

from .core.csrf import issue_csrf_cookie
from .core.crypto import Crypto
from .db import SessionLocal
from .models import OAuthToken
from .settings import settings

# LEGACY ROUTER - Disabled to prevent conflict with routers/auth.py
# Changed prefix to /auth2/google to avoid shadowing modern auth router
# Only keeping /csrf endpoint active. Use routers/auth.py for OAuth login.
router = APIRouter(prefix="/auth2/google", tags=["auth-legacy"])

# Initialize crypto for token encryption
crypto = Crypto()

# Load OAuth configuration from centralized settings
GOOGLE_CREDENTIALS = settings.GOOGLE_CREDENTIALS
SCOPES = settings.GOOGLE_OAUTH_SCOPES.split() if settings.GOOGLE_OAUTH_SCOPES else []
REDIRECT_URI = settings.effective_redirect_uri
STATE_SECRET = settings.OAUTH_STATE_SECRET or "dev_secret"


def _load_client_config():
    with open(GOOGLE_CREDENTIALS, "r") as f:
        return json.load(f)


def _encode_state(payload: dict) -> str:
    blob = json.dumps(payload).encode("utf-8")
    return base64.urlsafe_b64encode(blob + STATE_SECRET.encode()).decode()


def _decode_state(token: str) -> dict:
    raw = base64.urlsafe_b64decode(token.encode())
    raw_bytes = raw[: -len(STATE_SECRET)]
    return json.loads(raw_bytes.decode())


# Copilot: add GET /api/auth/csrf that issues the csrf_token cookie for JS to read.
@router.get("/csrf")
def get_csrf_token(response: Response):
    """Issue CSRF token cookie for frontend JavaScript to read"""
    issue_csrf_cookie(response)
    return {"ok": True}


@router.get("/login")
def login():
    """Initiate OAuth flow with Google"""
    if not GOOGLE_CREDENTIALS:
        raise HTTPException(status_code=500, detail="GOOGLE_CREDENTIALS not configured")
    if not REDIRECT_URI:
        raise HTTPException(
            status_code=500, detail="GOOGLE_REDIRECT_URI not configured"
        )

    config = _load_client_config()
    flow = Flow.from_client_config(config, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    state = _encode_state(
        {"nonce": secrets.token_hex(16), "t": int(dt.datetime.utcnow().timestamp())}
    )
    # Always request fresh refresh token by forcing consent screen
    auth_url, _ = flow.authorization_url(
        access_type="offline",  # Request offline access (refresh token)
        prompt="consent",  # Always show consent screen to get new refresh token
        include_granted_scopes="true",  # Include previously granted scopes
        state=state,
    )

    # Log the redirect_uri being used (for debugging)
    print(f"[OAuth] Initiating login flow with redirect_uri: {REDIRECT_URI}")

    return RedirectResponse(auth_url)


@router.get("/callback")
def callback(request: Request, state: str, code: str):
    """Handle OAuth callback from Google"""
    print(f"[OAuth] Callback received with redirect_uri: {REDIRECT_URI}")

    try:
        _ = _decode_state(state)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid state")

    config = _load_client_config()
    flow = Flow.from_client_config(config, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    # Build the full authorization response URL
    authorization_response = str(request.url)
    flow.fetch_token(authorization_response=authorization_response)
    creds = flow.credentials  # google.oauth2.credentials.Credentials

    # Decode the id_token to get user email
    user_email = None
    if creds.id_token:
        try:
            # id_token is a JWT string, decode it
            client_id = config.get("web", {}).get("client_id") or config.get(
                "installed", {}
            ).get("client_id")
            idinfo = id_token.verify_oauth2_token(
                creds.id_token, google_requests.Request(), client_id
            )
            user_email = idinfo.get("email")
        except Exception as e:
            print(f"Error decoding id_token: {e}")

    if not user_email:
        raise HTTPException(
            status_code=400, detail="Email not present; ensure userinfo.email scope"
        )

    db = SessionLocal()
    try:
        existing = (
            db.query(OAuthToken)
            .filter_by(provider="google", user_email=user_email)
            .first()
        )
        if not existing:
            existing = OAuthToken(
                provider="google",
                user_email=user_email,
                token_uri=creds.token_uri,
                client_id=creds.client_id,
                client_secret=creds.client_secret,
                scopes=" ".join(SCOPES),
            )
            db.add(existing)

        # Encrypt tokens before storing (AES-GCM encryption)
        existing.access_token = (
            crypto.enc(creds.token.encode()) if creds.token else existing.access_token
        )
        if creds.refresh_token:
            existing.refresh_token = crypto.enc(creds.refresh_token.encode())
        # expiry is naive datetime in UTC for google creds; ensure aware
        expiry = creds.expiry
        existing.expiry = expiry
        db.commit()
    finally:
        db.close()

    # redirect to frontend (direct to web app port with query param for success message)
    ui_url = "http://localhost:5175/?connected=google"
    return RedirectResponse(ui_url)
