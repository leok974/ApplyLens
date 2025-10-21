"""Authentication routes for Google OAuth and demo mode."""
import secrets
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User, OAuthToken
from app.config import agent_settings
from app.auth.google import build_auth_url, exchange_code_for_tokens, get_userinfo
from app.auth.session import new_session, set_cookie, clear_cookie, verify_session
from app.auth.schema import UserSchema, SessionResponse
from app.auth.deps import current_user, optional_current_user
from app.core.crypto import crypto
from app.core.csrf import issue_csrf_cookie
from app.core.captcha import verify_captcha
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/google/login")
async def google_login(request: Request):
    """Redirect to Google OAuth login page."""
    if not agent_settings.GOOGLE_CLIENT_ID:
        raise HTTPException(400, "Google OAuth not configured")
    
    state = secrets.token_urlsafe(16)
    # Store state in session for CSRF protection
    # Note: For production, use Starlette SessionMiddleware or signed cookies
    request.session["oauth_state"] = state
    
    url = build_auth_url(
        agent_settings.GOOGLE_CLIENT_ID,
        agent_settings.OAUTH_REDIRECT_URI,
        state
    )
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback."""
    # Verify state for CSRF protection
    stored_state = request.session.get("oauth_state")
    if state != stored_state:
        raise HTTPException(400, "Invalid state parameter")
    
    # Exchange code for tokens
    try:
        token_data = await exchange_code_for_tokens(
            agent_settings.GOOGLE_CLIENT_ID,
            agent_settings.GOOGLE_CLIENT_SECRET,
            agent_settings.OAUTH_REDIRECT_URI,
            code
        )
    except Exception as e:
        logger.error(f"Token exchange failed: {e}")
        raise HTTPException(400, "Failed to exchange authorization code")
    
    # Get user profile
    try:
        profile = await get_userinfo(token_data["access_token"])
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        raise HTTPException(400, "Failed to get user profile")
    
    # Find or create user
    user = db.query(User).filter(User.email == profile["email"]).first()
    if not user:
        user = User(
            id=str(uuid.uuid4()),
            email=profile["email"],
            name=profile.get("name"),
            picture_url=profile.get("picture"),
            is_demo=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update user profile
        user.name = profile.get("name", user.name)
        user.picture_url = profile.get("picture", user.picture_url)
        db.commit()
    
    # Store or update OAuth tokens (encrypted)
    oauth = db.query(OAuthToken).filter(
        OAuthToken.user_id == user.id,
        OAuthToken.provider == "google"
    ).first()
    
    # Encrypt tokens before storing
    enc_access = crypto.enc(token_data.get("access_token", "").encode())
    enc_refresh = crypto.enc((token_data.get("refresh_token") or "").encode()) if token_data.get("refresh_token") else None
    
    if not oauth:
        oauth = OAuthToken(
            user_id=user.id,
            provider="google",
            user_email=user.email,
            access_token=enc_access,
            refresh_token=enc_refresh,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=agent_settings.GOOGLE_CLIENT_ID,
            client_secret=agent_settings.GOOGLE_CLIENT_SECRET,
            scopes=" ".join(["openid", "email", "profile", "https://www.googleapis.com/auth/gmail.readonly"])
        )
        db.add(oauth)
    else:
        oauth.access_token = enc_access
        if enc_refresh:
            oauth.refresh_token = enc_refresh
    
    db.commit()
    
    # Create session
    sess = new_session(db, user.id)
    
    # Redirect to main app with session cookie and CSRF token
    resp = RedirectResponse(url="/", status_code=302)
    set_cookie(
        resp,
        sess.id,
        domain=agent_settings.COOKIE_DOMAIN,
        secure=agent_settings.COOKIE_SECURE,
        samesite=agent_settings.COOKIE_SAMESITE
    )
    issue_csrf_cookie(resp)  # Add CSRF protection
    
    return resp


@router.post("/logout", response_model=SessionResponse)
async def logout(response: Response, request: Request, db: Session = Depends(get_db)):
    """Logout current user by clearing session."""
    # Optionally delete session from database
    sid = request.cookies.get("session_id")
    if sid:
        sess = db.query(Session).filter(Session.id == sid).first()
        if sess:
            db.delete(sess)
            db.commit()
    
    clear_cookie(response, domain=agent_settings.COOKIE_DOMAIN)
    return SessionResponse(ok=True, user=None)


@router.post("/demo/start", response_model=SessionResponse)
async def demo_start(request: Request, response: Response, db: Session = Depends(get_db)):
    """Start a demo session with read-only access."""
    if not agent_settings.ALLOW_DEMO:
        raise HTTPException(403, "Demo mode is disabled")
    
    # Verify reCAPTCHA if enabled
    captcha_token = None
    content_type = request.headers.get("content-type", "")
    
    if content_type.startswith("application/json"):
        try:
            body = await request.json()
            captcha_token = body.get("captcha")
        except Exception:
            pass
    
    # Get client IP for reCAPTCHA verification
    client_ip = request.client.host if request.client else None
    
    # Verify captcha
    if not await verify_captcha(captcha_token, client_ip):
        logger.warning(f"Demo start failed: Invalid captcha from {client_ip}")
        raise HTTPException(400, "Captcha verification failed")
    
    # Find or create demo user
    demo_email = "demo@applylens.app"
    demo = db.query(User).filter(User.email == demo_email).first()
    
    if not demo:
        demo = User(
            id=str(uuid.uuid4()),
            email=demo_email,
            name="Demo User",
            is_demo=True
        )
        db.add(demo)
        db.commit()
        db.refresh(demo)
    
    # Create session
    sess = new_session(db, demo.id)
    
    # Set session cookie
    set_cookie(
        response,
        sess.id,
        domain=agent_settings.COOKIE_DOMAIN,
        secure=agent_settings.COOKIE_SECURE,
        samesite=agent_settings.COOKIE_SAMESITE
    )
    issue_csrf_cookie(response)  # Add CSRF protection
    
    return SessionResponse(ok=True, user=UserSchema.from_orm(demo))


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(user: User = Depends(current_user)):
    """Get current authenticated user information."""
    return UserSchema.from_orm(user)


@router.get("/status")
async def auth_status(user: User = Depends(optional_current_user)):
    """Check authentication status."""
    if user:
        return {"authenticated": True, "user": UserSchema.from_orm(user)}
    return {"authenticated": False, "user": None}
