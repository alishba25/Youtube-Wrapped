"""
Central place for all environment configuration.
Nothing else in the app should call os.environ directly - import from here instead.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Google OAuth app credentials (from Google Cloud Console)
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")

    # Must exactly match a redirect URI registered in Google Cloud Console
    GOOGLE_REDIRECT_URI: str = os.getenv(
        "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback"
    )

    # Separate API key for public, unauthenticated Data API calls (video metadata lookups)
    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")

    # Used to sign the session cookie. Generate with: python -c "import secrets; print(secrets.token_hex(32))"
    SESSION_SECRET: str = os.getenv("SESSION_SECRET", "dev-only-insecure-secret-change-me")

    # Base URL of the frontend, used for post-login redirects
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:8000")

    # Toggle verbose logging
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Timezone used when computing "peak watching hour" - Takeout timestamps
    # arrive in UTC, so this is what they get converted to for display.
    # Override via env var if you're not in India.
    DISPLAY_TIMEZONE: str = os.getenv("DISPLAY_TIMEZONE", "Asia/Kolkata")


settings = Settings()

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"

# Scopes needed per path. Keep these as narrow as possible - Google reviews
# apps more strictly the more sensitive scopes you request.
SCOPES = {
    "taste": [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/youtube.readonly",
    ],
    "creator": [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/yt-analytics.readonly",
    ],
}