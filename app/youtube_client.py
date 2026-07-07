"""
All outbound calls to Google's APIs live here. Two kinds of auth are used:

1. API key (server-owned) - for public, read-only lookups like video metadata
   and the category ID -> name mapping. Used by the Takeout path.
2. OAuth access token (user-owned) - for anything scoped to a specific user's
   account: their liked videos, subscriptions, or channel analytics. Used by
   the Taste and Creator paths.

Batches video ID lookups 50 at a time (the API's max) and caches category
names for the process lifetime, since there are only ~15-30 of them and they
almost never change.
"""
import httpx
from datetime import date, timedelta
from app.config import settings

DATA_API_BASE = "https://www.googleapis.com/youtube/v3"
ANALYTICS_API_BASE = "https://youtubeanalytics.googleapis.com/v2"

_category_cache: dict[str, dict[str, str]] = {}  # region_code -> {category_id: name}


class YouTubeAPIError(Exception):
    pass


def _get(url: str, params: dict, access_token: str | None = None) -> dict:
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    else:
        params = {**params, "key": settings.YOUTUBE_API_KEY}

    resp = httpx.get(url, params=params, headers=headers, timeout=15)
    if resp.status_code == 401:
        raise YouTubeAPIError("Google session expired - please sign in again.")
    if resp.status_code == 403:
        raise YouTubeAPIError(
            "YouTube API refused the request - check your API key/quota, or "
            "that the required scopes were granted."
        )
    resp.raise_for_status()
    return resp.json()


def get_category_map(region_code: str = "US") -> dict[str, str]:
    """Returns {category_id: category_name}, e.g. {'20': 'Gaming'}."""
    if region_code in _category_cache:
        return _category_cache[region_code]

    data = _get(
        f"{DATA_API_BASE}/videoCategories",
        {"part": "snippet", "regionCode": region_code},
    )
    mapping = {item["id"]: item["snippet"]["title"] for item in data.get("items", [])}
    _category_cache[region_code] = mapping
    return mapping


def enrich_video_ids(video_ids: list[str]) -> dict[str, dict]:
    """
    Batch-fetches category and channel info for a list of video IDs.
    Returns {video_id: {"category_id": str, "channel": str}}.
    Silently skips IDs that come back deleted/private (common in old history).
    """
    category_map = get_category_map()
    results: dict[str, dict] = {}

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        data = _get(
            f"{DATA_API_BASE}/videos",
            {"part": "snippet", "id": ",".join(batch)},
        )
        for item in data.get("items", []):
            snippet = item["snippet"]
            cat_id = snippet.get("categoryId")
            results[item["id"]] = {
                "category": category_map.get(cat_id, "Other"),
                "channel": snippet.get("channelTitle"),
            }

    return results


# ---- OAuth-scoped calls (Taste + Creator paths) ----

def get_my_channel(access_token: str) -> dict:
    """Returns the signed-in user's own channel info, including the ID of
    their 'liked videos' playlist."""
    data = _get(
        f"{DATA_API_BASE}/channels",
        {"part": "snippet,contentDetails", "mine": "true"},
        access_token=access_token,
    )
    items = data.get("items", [])
    if not items:
        raise YouTubeAPIError("Couldn't find a YouTube channel on this Google account.")
    return items[0]


def get_liked_videos(access_token: str, max_results: int = 100) -> list[dict]:
    channel = get_my_channel(access_token)
    likes_playlist_id = channel["contentDetails"]["relatedPlaylists"].get("likes")
    if not likes_playlist_id:
        return []

    category_map = get_category_map()
    videos = []
    page_token = None

    while len(videos) < max_results:
        params = {
            "part": "snippet",
            "playlistId": likes_playlist_id,
            "maxResults": 50,
        }
        if page_token:
            params["pageToken"] = page_token

        data = _get(f"{DATA_API_BASE}/playlistItems", params, access_token=access_token)
        for item in data.get("items", []):
            snippet = item["snippet"]
            videos.append(
                {
                    "title": snippet.get("title"),
                    "channel": snippet.get("videoOwnerChannelTitle", "Unknown"),
                }
            )

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return videos[:max_results]


def get_subscriptions(access_token: str, max_results: int = 100) -> list[dict]:
    subs = []
    page_token = None

    while len(subs) < max_results:
        params = {"part": "snippet", "mine": "true", "maxResults": 50}
        if page_token:
            params["pageToken"] = page_token

        data = _get(f"{DATA_API_BASE}/subscriptions", params, access_token=access_token)
        for item in data.get("items", []):
            subs.append({"channel": item["snippet"]["title"]})

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return subs[:max_results]


def get_channel_analytics(access_token: str, channel_id: str) -> dict:
    """Pulls a 90-day summary report: views, watch time, top videos."""
    end = date.today()
    start = end - timedelta(days=90)

    summary = _get(
        f"{ANALYTICS_API_BASE}/reports",
        {
            "ids": f"channel=={channel_id}",
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "metrics": "views,estimatedMinutesWatched,subscribersGained",
        },
        access_token=access_token,
    )

    top_videos = _get(
        f"{ANALYTICS_API_BASE}/reports",
        {
            "ids": f"channel=={channel_id}",
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "metrics": "views",
            "dimensions": "video",
            "sort": "-views",
            "maxResults": 5,
        },
        access_token=access_token,
    )

    return {"summary": summary, "top_videos": top_videos}
