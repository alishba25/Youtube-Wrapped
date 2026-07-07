"""
This is the piece that makes 3 different data sources behave like one.
Each function here takes that path's raw API response and returns a plain
list[Signal] - after this point, personas.py and card_generator.py don't
care whether the data came from a file upload or an API call.
"""
from app.models import Signal
from app.takeout_parser import RawWatchEntry
from app import youtube_client


def signals_from_takeout(entries: list[RawWatchEntry]) -> list[Signal]:
    """Enriches parsed Takeout entries with category data via the Data API,
    then converts everything into Signals. Watches are weighted 1.0 each."""
    video_ids = [e.video_id for e in entries]
    enrichment = youtube_client.enrich_video_ids(video_ids)

    signals = []
    for entry in entries:
        info = enrichment.get(entry.video_id)
        signals.append(
            Signal(
                source="takeout",
                category=info["category"] if info else None,
                channel=info["channel"] if info else entry.channel,
                title=entry.title,
                weight=1.0,
                timestamp=entry.timestamp,
            )
        )
    return signals


def signals_from_taste(access_token: str) -> list[Signal]:
    """Liked videos count more heavily than subscriptions - liking a specific
    video is a stronger signal of taste than subscribing once and forgetting."""
    liked = youtube_client.get_liked_videos(access_token)
    subs = youtube_client.get_subscriptions(access_token)

    # Enrich liked videos with category via a second lookup pass isn't possible
    # without video IDs from playlistItems (we'd need part=contentDetails + a
    # second videos.list call) - kept simple here by categorizing on channel
    # only. See README for how to extend this with full category enrichment.
    signals = []
    for video in liked:
        signals.append(
            Signal(source="taste", channel=video["channel"], title=video["title"], weight=2.0)
        )
    for sub in subs:
        signals.append(Signal(source="taste", channel=sub["channel"], weight=1.0))

    return signals


def signals_from_creator(analytics_data: dict, channel_title: str) -> list[Signal]:
    """Creator path doesn't have per-category breakdown from Analytics API
    directly - we build signals from top videos so persona matching still
    has something to chew on, weighted by view count."""
    signals = []
    top_videos = analytics_data.get("top_videos", {})
    headers = [h["name"] for h in top_videos.get("columnHeaders", [])]
    rows = top_videos.get("rows", [])

    for row in rows:
        row_dict = dict(zip(headers, row))
        views = row_dict.get("views", 0)
        signals.append(
            Signal(
                source="creator",
                channel=channel_title,
                title=row_dict.get("video"),
                weight=float(views),
            )
        )

    return signals
