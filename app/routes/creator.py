from fastapi import APIRouter, Request, HTTPException
from app.youtube_client import get_my_channel, get_channel_analytics, YouTubeAPIError
from app.insights_engine import signals_from_creator
from app.personas import build_wrapped_result, punchy_stat

router = APIRouter()


@router.post("/api/creator/wrapped")
async def creator_wrapped(request: Request):
    access_token = request.session.get("access_token")
    if not access_token or request.session.get("path_type") != "creator":
        raise HTTPException(401, "Please sign in with Google first.")

    try:
        channel = get_my_channel(access_token)
        channel_id = channel["id"]
        channel_title = channel["snippet"]["title"]
        analytics = get_channel_analytics(access_token, channel_id)
    except YouTubeAPIError as e:
        raise HTTPException(502, str(e))

    summary_rows = analytics["summary"].get("rows") or [[0, 0, 0]]
    views, minutes_watched, subs_gained = summary_rows[0]

    signals = signals_from_creator(analytics, channel_title)
    headline = punchy_stat(int(views), "views in the last 90 days")
    extra_facts = [
        f"{int(minutes_watched):,} minutes watched by your audience",
        f"{int(subs_gained):,} new subscribers",
    ]

    result = build_wrapped_result(signals, "creator", headline, extra_facts)
    return result
