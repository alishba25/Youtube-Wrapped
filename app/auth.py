"""
Minimal OAuth2 authorization-code flow against Google, written by hand rather
than pulling in google-auth-oauthlib - it's ~40 lines of straightforward
HTTP calls and keeping it explicit makes it easy to see exactly what data
we're requesting and storing.

Access tokens are kept ONLY in the signed session cookie (see main.py's
SessionMiddleware) - never written to disk or a database. That's a deliberate
scope-reduction: this app doesn't need to remember users between visits.
"""
import secrets
from urllib.parse import urlencode
import httpx
from app.config import (
    settings,
    GOOGLE_AUTH_ENDPOINT,
    GOOGLE_TOKEN_ENDPOINT,
    GOOGLE_USERINFO_ENDPOINT,
    SCOPES,
)


def build_authorization_url(path_type: str) -> tuple[str, str]:
    """Returns (redirect_url, state). Caller must stash state in the session
    and verify it on callback to prevent CSRF."""
    if path_type not in SCOPES:
        raise ValueError(f"Unknown path_type: {path_type}")

    csrf_token = secrets.token_urlsafe(16)
    state = f"{path_type}:{csrf_token}"
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES[path_type]),
        "access_type": "online",  # we don't need a refresh token for a single-run wrapped
        "include_granted_scopes": "true",
        "state": state,
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(params)}", state


async def exchange_code_for_token(code: str) -> dict:
    """Returns Google's token response dict, including 'access_token'."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GOOGLE_TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def get_user_email(access_token: str) -> str | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            GOOGLE_USERINFO_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code != 200:
            return None
        return resp.json().get("email")
