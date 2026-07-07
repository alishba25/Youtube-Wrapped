"""
Parses the watch-history.json file from a Google Takeout YouTube export.

Real Takeout exports are messy:
- Some entries are ads ("From Google Ads") - we skip these
- Some entries are for deleted videos and have no titleUrl - we skip these
- Video ID has to be pulled out of a full watch URL
- Timestamps are ISO8601 strings, sometimes with fractional seconds

This module only extracts and cleans the raw data. It does NOT hit the
YouTube API - that enrichment step happens separately in youtube_client.py
so this stays fast and testable offline.
"""
import json
import re
from datetime import datetime
from dataclasses import dataclass

VIDEO_ID_RE = re.compile(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})")


@dataclass
class RawWatchEntry:
    video_id: str
    title: str
    channel: str | None
    timestamp: datetime | None


def _extract_video_id(url: str) -> str | None:
    match = VIDEO_ID_RE.search(url)
    return match.group(1) if match else None


def _parse_timestamp(raw: str) -> datetime | None:
    try:
        # Takeout uses formats like "2025-06-01T12:34:56.789Z"
        cleaned = raw.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except (ValueError, AttributeError):
        return None


def parse_takeout_file(file_bytes: bytes) -> list[RawWatchEntry]:
    """Main entry point. Raises ValueError with a friendly message on bad input."""
    try:
        raw_entries = json.loads(file_bytes)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "That doesn't look like a valid watch-history.json file. "
            "Make sure you selected the JSON export (not HTML) from Takeout."
        ) from exc

    if not isinstance(raw_entries, list):
        raise ValueError("Unexpected file format - expected a JSON array of watch entries.")

    parsed: list[RawWatchEntry] = []
    for entry in raw_entries:
        # Skip ads and other non-video entries
        if entry.get("header") != "YouTube":
            continue
        title_url = entry.get("titleUrl")
        if not title_url:
            continue  # deleted video, no way to recover which one it was

        video_id = _extract_video_id(title_url)
        if not video_id:
            continue

        raw_title = entry.get("title", "")
        # Takeout prefixes titles with "Watched " - strip that for display
        title = re.sub(r"^Watched\s+", "", raw_title).strip()

        subtitles = entry.get("subtitles") or []
        channel = subtitles[0].get("name") if subtitles else None

        timestamp = _parse_timestamp(entry.get("time", ""))

        parsed.append(
            RawWatchEntry(video_id=video_id, title=title, channel=channel, timestamp=timestamp)
        )

    if not parsed:
        raise ValueError(
            "No watchable video entries found in this file. "
            "Double check you exported 'YouTube and YouTube Music' > 'history' as JSON."
        )

    return parsed
