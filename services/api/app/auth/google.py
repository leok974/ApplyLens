"""Google OAuth integration."""
import urllib.parse
import httpx
from typing import Dict, Any

AUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def build_auth_url(client_id: str, redirect_uri: str, state: str) -> str:
    """Build Google OAuth authorization URL."""
    q = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_BASE}?{urllib.parse.urlencode(q)}"


async def exchange_code_for_tokens(
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code: str
) -> Dict[str, Any]:
    """Exchange authorization code for access and refresh tokens."""
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "code": code,
            }
        )
        response.raise_for_status()
        return response.json()


async def get_userinfo(access_token: str) -> Dict[str, Any]:
    """Get user profile information from Google."""
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        return response.json()
