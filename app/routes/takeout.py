from fastapi import APIRouter, UploadFile, File, HTTPException
from app.takeout_parser import parse_takeout_file
from app.insights_engine import signals_from_takeout
from app.personas import build_wrapped_result, punchy_stat
from app.youtube_client import YouTubeAPIError

router = APIRouter()

# Caps how many videos we send to the Data API for category enrichment per
# request. Each request costs 1 quota unit per 50 IDs, and the default daily
# quota is 10,000 units - 3000 videos = 60 batches = 60 units per request,
# so this comfortably supports plenty of requests per day even on the free
# quota. Users with fewer than this many videos in their history automatically
# get all of them enriched (the slice below just no-ops if the list is shorter).
MAX_VIDEOS_TO_ENRICH = 3000


@router.post("/api/takeout/wrapped")
async def takeout_wrapped(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(400, "Please upload the watch-history.json file from Takeout (JSON format, not HTML).")

    content = await file.read()
    try:
        entries = parse_takeout_file(content)
    except ValueError as e:
        raise HTTPException(400, str(e))

    total_watched = len(entries)
    sample = entries[:MAX_VIDEOS_TO_ENRICH]

    try:
        signals = signals_from_takeout(sample)
    except YouTubeAPIError as e:
        raise HTTPException(502, str(e))

    extra_facts = []
    if total_watched > MAX_VIDEOS_TO_ENRICH:
        extra_facts.append(
            f"Categorized your {MAX_VIDEOS_TO_ENRICH:,} most recent watches out of {total_watched:,} total"
        )

    headline = punchy_stat(total_watched, "videos watched")
    result = build_wrapped_result(signals, "takeout", headline, extra_facts)
    return result