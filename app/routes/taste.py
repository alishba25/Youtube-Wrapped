from fastapi import APIRouter, Request, HTTPException
from app.insights_engine import signals_from_taste
from app.personas import build_wrapped_result
from app.youtube_client import YouTubeAPIError

router = APIRouter()


@router.post("/api/taste/wrapped")
async def taste_wrapped(request: Request):
    access_token = request.session.get("access_token")
    if not access_token or request.session.get("path_type") != "taste":
        raise HTTPException(401, "Please sign in with Google first.")

    try:
        signals = signals_from_taste(access_token)
    except YouTubeAPIError as e:
        raise HTTPException(502, str(e))

    if not signals:
        raise HTTPException(
            400,
            "No liked videos or subscriptions found on this account - "
            "taste wrapped needs at least a few likes or subs to work with.",
        )

    liked_count = sum(1 for s in signals if s.weight == 2.0)
    sub_count = sum(1 for s in signals if s.weight == 1.0)
    headline = f"{liked_count:,} likes, {sub_count:,} subs — a whole taste profile"

    result = build_wrapped_result(signals, "taste", headline)
    return result
