"""
OAuth 2.0 flow for Gmail (multi-user support).

Endpoints:
- GET /oauth/google/init?user_email=xxx - Start OAuth flow
- GET /oauth/google/callback?code=xxx&state=xxx - Handle OAuth callback
"""

import json
import urllib.parse

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from .db import SessionLocal
from .models import GmailToken
from .settings import settings

router = APIRouter(prefix="/oauth/google", tags=["oauth"])

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "openid",
    "email",
    "profile",
]


def _create_flow():
    """Create OAuth flow from settings."""
    if not (
        settings.GMAIL_CLIENT_ID
        and settings.GMAIL_CLIENT_SECRET
        and settings.OAUTH_REDIRECT_URI
    ):
        raise HTTPException(
            status_code=400,
            detail="oauth_not_configured: missing client credentials or redirect URI",
        )

    return Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GMAIL_CLIENT_ID,
                "client_secret": settings.GMAIL_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.OAUTH_REDIRECT_URI],
            }
        },
        scopes=SCOPES,
    )


@router.get("/init")
def init_oauth(
    user_email: str = Query(..., description="User email address for OAuth"),
):
    """
    Initialize OAuth flow for a user.

    Returns:
        {"authUrl": "https://accounts.google.com/o/oauth2/auth?..."}

    Frontend should redirect user to authUrl.
    """
    try:
        flow = _create_flow()
        flow.redirect_uri = settings.OAUTH_REDIRECT_URI

        # Encode user_email in state parameter
        state_data = {"user_email": user_email}
        state = urllib.parse.quote(json.dumps(state_data))

        # Generate authorization URL
        auth_url, _ = flow.authorization_url(
            access_type="offline",  # Get refresh token
            prompt="consent",  # Force consent to get refresh token
            include_granted_scopes="true",
            state=state,
        )

        return {"authUrl": auth_url}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initialize OAuth: {str(e)}"
        )


@router.get("/callback")
def oauth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State parameter with user_email"),
):
    """
    Handle OAuth callback from Google.

    Exchanges authorization code for tokens and stores in database.

    Returns:
        HTML page with success message
    """
    try:
        # Decode state parameter
        try:
            decoded_state = json.loads(urllib.parse.unquote(state))
            user_email = decoded_state.get("user_email")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        if not user_email:
            raise HTTPException(status_code=400, detail="missing_user_email in state")

        # Exchange code for tokens
        flow = _create_flow()
        flow.redirect_uri = settings.OAUTH_REDIRECT_URI
        flow.fetch_token(code=code)

        creds: Credentials = flow.credentials

        # Calculate expiry_date in milliseconds
        expiry_ms = None
        if hasattr(creds, "expiry") and creds.expiry:
            expiry_ms = int(creds.expiry.timestamp() * 1000)

        # Store or update token in database
        db = SessionLocal()
        try:
            # Check if token exists
            existing = (
                db.query(GmailToken).filter(GmailToken.user_email == user_email).first()
            )

            if existing:
                # Update existing token
                existing.access_token = creds.token
                # Only update refresh_token if we got a new one (first time or re-consent)
                if hasattr(creds, "refresh_token") and creds.refresh_token:
                    existing.refresh_token = creds.refresh_token
                existing.expiry_date = expiry_ms
                existing.scope = " ".join(SCOPES)
            else:
                # Create new token
                new_token = GmailToken(
                    user_email=user_email,
                    access_token=creds.token,
                    refresh_token=getattr(creds, "refresh_token", None),
                    expiry_date=expiry_ms,
                    scope=" ".join(SCOPES),
                )
                db.add(new_token)

            db.commit()
        finally:
            db.close()

        # Return success page
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Gmail Connected</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }
                .container {
                    background: white;
                    padding: 3rem;
                    border-radius: 12px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    text-align: center;
                    max-width: 400px;
                }
                h1 {
                    color: #2d3748;
                    margin: 0 0 1rem;
                    font-size: 2rem;
                }
                .success-icon {
                    font-size: 4rem;
                    margin-bottom: 1rem;
                }
                p {
                    color: #718096;
                    margin: 1rem 0;
                    line-height: 1.6;
                }
                .email {
                    background: #f7fafc;
                    padding: 0.75rem;
                    border-radius: 6px;
                    font-family: monospace;
                    color: #2d3748;
                    margin: 1rem 0;
                }
                .button {
                    display: inline-block;
                    margin-top: 1.5rem;
                    padding: 0.75rem 1.5rem;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: 500;
                    transition: background 0.2s;
                }
                .button:hover {
                    background: #5568d3;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">✅</div>
                <h1>Gmail Connected!</h1>
                <p>Successfully connected your Gmail account:</p>
                <div class="email">{{USER_EMAIL}}</div>
                <p>You can now close this window and return to ApplyLens.</p>
                <a href="/" class="button">Return to App</a>
            </div>
            <script>
                // Auto-close window after 5 seconds if opened in popup
                if (window.opener) {
                    setTimeout(() => {
                        window.close();
                    }, 5000);
                }
            </script>
        </body>
        </html>
        """.replace("{{USER_EMAIL}}", user_email)

        return HTMLResponse(content=html_content)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")


@router.get("/status")
def check_oauth_status(user_email: str = Query(..., description="User email to check")):
    """
    Check if user has connected their Gmail account.

    Returns:
        {"connected": bool, "user_email": str, "expires_at": int|null}
    """
    db = SessionLocal()
    try:
        token = db.query(GmailToken).filter(GmailToken.user_email == user_email).first()

        if not token:
            return {"connected": False, "user_email": user_email, "expires_at": None}

        return {
            "connected": True,
            "user_email": user_email,
            "expires_at": token.expiry_date,
            "has_refresh_token": bool(token.refresh_token),
        }
    finally:
        db.close()


@router.delete("/disconnect")
def disconnect_gmail(
    user_email: str = Query(..., description="User email to disconnect"),
):
    """
    Disconnect user's Gmail account (delete stored tokens).

    Returns:
        {"success": bool}
    """
    db = SessionLocal()
    try:
        token = db.query(GmailToken).filter(GmailToken.user_email == user_email).first()

        if token:
            db.delete(token)
            db.commit()
            return {"success": True, "message": f"Disconnected Gmail for {user_email}"}
        else:
            return {"success": False, "message": "No connected account found"}
    finally:
        db.close()
