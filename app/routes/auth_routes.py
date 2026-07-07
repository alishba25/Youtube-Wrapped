from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from app.auth import build_authorization_url, exchange_code_for_token
from app.config import settings

router = APIRouter()


@router.get("/auth/login/{path_type}")
async def login(path_type: str, request: Request):
    if path_type not in ("taste", "creator"):
        return RedirectResponse(f"{settings.FRONTEND_URL}/?error=invalid_path")

    url, state = build_authorization_url(path_type)
    request.session["oauth_state"] = state
    return RedirectResponse(url)


@router.get("/auth/callback")
async def callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        return RedirectResponse(f"{settings.FRONTEND_URL}/?error={error}")

    expected_state = request.session.get("oauth_state")
    if not state or not code or state != expected_state:
        return RedirectResponse(f"{settings.FRONTEND_URL}/?error=state_mismatch")

    path_type = state.split(":")[0]

    try:
        token_data = await exchange_code_for_token(code)
    except Exception:
        return RedirectResponse(f"{settings.FRONTEND_URL}/?error=token_exchange_failed")

    access_token = token_data.get("access_token")
    if not access_token:
        return RedirectResponse(f"{settings.FRONTEND_URL}/?error=token_exchange_failed")

    request.session["access_token"] = access_token
    request.session["path_type"] = path_type
    request.session.pop("oauth_state", None)

    return RedirectResponse(f"{settings.FRONTEND_URL}/?path={path_type}&ready=1")


@router.get("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(settings.FRONTEND_URL)


@router.get("/auth/status")
async def status(request: Request):
    return {
        "signed_in": bool(request.session.get("access_token")),
        "path_type": request.session.get("path_type"),
    }
