import os

# Allow HTTP for local development (MUST be set before importing oauthlib!)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

import json
import base64
import secrets
import datetime as dt
from urllib.parse import urlencode
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GRequest
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from .db import SessionLocal
from .models import OAuthToken

router = APIRouter(prefix="/auth/google", tags=["auth"])

GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")
SCOPES = os.getenv("GOOGLE_OAUTH_SCOPES", "").split()
REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI")
STATE_SECRET = os.getenv("OAUTH_STATE_SECRET", "dev_secret")

def _load_client_config():
    with open(GOOGLE_CREDENTIALS, "r") as f:
        return json.load(f)

def _encode_state(payload: dict) -> str:
    blob = json.dumps(payload).encode("utf-8")
    return base64.urlsafe_b64encode(blob + STATE_SECRET.encode()).decode()

def _decode_state(token: str) -> dict:
    raw = base64.urlsafe_b64decode(token.encode())
    raw_bytes = raw[:-len(STATE_SECRET)]
    return json.loads(raw_bytes.decode())

@router.get("/login")
def login():
    """Initiate OAuth flow with Google"""
    config = _load_client_config()
    flow = Flow.from_client_config(config, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    state = _encode_state({"nonce": secrets.token_hex(16), "t": int(dt.datetime.utcnow().timestamp())})
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state
    )
    return RedirectResponse(auth_url)

@router.get("/callback")
def callback(request: Request, state: str, code: str):
    """Handle OAuth callback from Google"""
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
            client_id = config.get("web", {}).get("client_id") or config.get("installed", {}).get("client_id")
            idinfo = id_token.verify_oauth2_token(creds.id_token, google_requests.Request(), client_id)
            user_email = idinfo.get("email")
        except Exception as e:
            print(f"Error decoding id_token: {e}")
    
    if not user_email:
        raise HTTPException(status_code=400, detail="Email not present; ensure userinfo.email scope")

    db = SessionLocal()
    try:
        existing = db.query(OAuthToken).filter_by(provider="google", user_email=user_email).first()
        if not existing:
            existing = OAuthToken(provider="google", user_email=user_email, token_uri=creds.token_uri,
                                  client_id=creds.client_id, client_secret=creds.client_secret,
                                  scopes=" ".join(SCOPES))
            db.add(existing)

        existing.access_token = creds.token
        existing.refresh_token = creds.refresh_token or existing.refresh_token
        # expiry is naive datetime in UTC for google creds; ensure aware
        expiry = creds.expiry
        existing.expiry = expiry
        db.commit()
    finally:
        db.close()

    # redirect to UI success page
    ui_url = "/inbox?connected=google"
    return RedirectResponse(ui_url)
