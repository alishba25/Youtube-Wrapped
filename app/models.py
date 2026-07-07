"""
The whole point of this file: no matter which of the 3 paths a user takes
(Takeout upload / Taste / Creator), we convert their raw data into a list
of Signal objects. Everything downstream (insights engine, persona matching,
card generation) only ever deals with Signal objects and never needs to know
where the data originally came from.
"""
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel


class Signal(BaseModel):
    """One unit of 'this user engaged with this content'."""
    source: Literal["takeout", "taste", "creator"]
    category: Optional[str] = None      # e.g. "Gaming", "Music", "Education"
    channel: Optional[str] = None       # channel name
    title: Optional[str] = None         # video title, if known
    weight: float = 1.0                 # how strongly this counts (watches > likes > subs)
    timestamp: Optional[datetime] = None


class WrappedResult(BaseModel):
    """Final computed output shown on the results page and drawn onto the card."""
    path_type: Literal["takeout", "taste", "creator"]
    persona_name: str
    persona_emoji: str = "🌀"
    persona_tagline: str
    roast_line: str = ""
    headline_stat: str                  # the single biggest "wow" number, e.g. "312 hours watched"
    top_categories: list[tuple[str, int]]
    top_channels: list[tuple[str, int]]
    peak_hour_label: Optional[str] = None
    total_signals: int = 0
    extra_facts: list[str] = []
