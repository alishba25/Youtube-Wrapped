"""
Rule-based persona matching. Deliberately NOT using embeddings/clustering here -
YouTube's own video categories are already a clean, well-labeled taxonomy, so
scoring against them directly is more reliable than unsupervised clustering
and has zero extra ML dependencies to deploy.

(If you want to extend this later: swap category-matching for sentence-transformer
embeddings of video titles + KMeans, and use this rule-based version as your
baseline to measure improvement against. That comparison is a great thing to
write up for a portfolio README.)
"""
import random
from collections import Counter
from typing import Optional
from zoneinfo import ZoneInfo
from app.models import Signal, WrappedResult
from app.config import settings

DISPLAY_TZ = ZoneInfo(settings.DISPLAY_TIMEZONE)

# Each persona has: the YouTube category names that score toward it, an emoji
# for the reveal + card, a tagline (shown right under the persona name), and
# a separate roast_line (a punchier, funnier one-liner shown on its own slide -
# this is deliberately kept separate from tagline so the reveal has two
# distinct beats instead of dumping all the humor in one line).
PERSONAS = {
    "The 3AM Documentary Detective": {
        "categories": {"Education", "Science & Technology", "Nonprofits & Activism"},
        "emoji": "🔦",
        "tagline": "You watch to learn, not to scroll.",
        "roast": "Somewhere, a Wikipedia rabbit hole is jealous of your commitment.",
    },
    "The Comfort Rewatcher": {
        "categories": {"Comedy", "Entertainment", "Film & Animation"},
        "emoji": "🔁",
        "tagline": "Same clips, same joy, every single time.",
        "roast": "You've rewatched things you could recite from memory. You basically have.",
    },
    "The Gaming Grinder": {
        "categories": {"Gaming"},
        "emoji": "🎮",
        "tagline": "Your watch history has a K/D ratio.",
        "roast": "You watch other people play games for fun. Genuinely elite behavior.",
    },
    "The Sound Chaser": {
        "categories": {"Music"},
        "emoji": "🎧",
        "tagline": "Your algorithm is basically a playlist with extra steps.",
        "roast": "You've heard that one song 40 times and you're still not tired of it. Concerning. Iconic.",
    },
    "The News Junkie": {
        "categories": {"News & Politics"},
        "emoji": "📰",
        "tagline": "You knew before your group chat did.",
        "roast": "You've doomscrolled news longer than most people doomscroll anything else.",
    },
    "The Tutorial Hoarder": {
        "categories": {"Howto & Style"},
        "emoji": "🛠️",
        "tagline": "17 tabs open, all of them 'how to fix.'",
        "roast": "You've watched more how-to videos than things you've actually fixed. It's fine. It's a phase.",
    },
    "The Vlog Life Regular": {
        "categories": {"People & Blogs"},
        "emoji": "📹",
        "tagline": "You know their dog's name. Possibly their ex's too.",
        "roast": "At this point you're basically a background character in a stranger's life.",
    },
    "The Sports Fanatic": {
        "categories": {"Sports"},
        "emoji": "🏟️",
        "tagline": "Highlights, full games, and everything in between.",
        "roast": "You've watched the same goal from six angles. All six were necessary.",
    },
    "The Wanderer": {
        "categories": {"Travel & Events"},
        "emoji": "🧳",
        "tagline": "Living vicariously, one vlog at a time.",
        "roast": "Your passport has fewer stamps than your watch history has destinations.",
    },
    "The Gearhead": {
        "categories": {"Autos & Vehicles"},
        "emoji": "🚗",
        "tagline": "You know 0-60 times you'll never personally test.",
        "roast": "You've watched more car reviews than you've driven cars. We don't judge. Much.",
    },
    "The Softie": {
        "categories": {"Pets & Animals"},
        "emoji": "🐾",
        "tagline": "One dog video and your whole day improves.",
        "roast": "Your recommendations are basically a shelter you can't adopt from.",
    },
    "The Curious Generalist": {
        "categories": set(),  # fallback persona - matches nothing specifically
        "emoji": "🌀",
        "tagline": "You contain multitudes. Your watch history proves it.",
        "roast": "Your watch history doesn't have a personality. It has fourteen.",
    },
}

NIGHT_OWL_HOURS = set(range(0, 5))  # 12am - 4:59am

HEADLINE_TEMPLATES = [
    "{count:,} {noun}. No notes.",
    "{count:,} {noun} deep. Certified behavior.",
    "{count:,} {noun} and counting.",
    "{count:,} {noun} — a personality trait at this point.",
]


def punchy_stat(count: int, noun: str) -> str:
    """Wraps a raw number in a bit of personality. Used by the route handlers
    for the headline_stat field so it doesn't read like a database export."""
    template = random.choice(HEADLINE_TEMPLATES)
    return template.format(count=count, noun=noun)


def match_persona(signals: list[Signal]) -> tuple[str, dict]:
    """Score each persona by how many signals fall into its category set,
    weighted by the signal's own weight. Returns (persona_name, persona_info)."""
    category_weight = Counter()
    for s in signals:
        if s.category:
            category_weight[s.category] += s.weight

    if not category_weight:
        name = "The Curious Generalist"
        return name, PERSONAS[name]

    scores = Counter()
    for persona_name, info in PERSONAS.items():
        if not info["categories"]:
            continue
        scores[persona_name] = sum(
            category_weight.get(cat, 0) for cat in info["categories"]
        )

    best_persona, best_score = scores.most_common(1)[0]
    if best_score == 0:
        best_persona = "The Curious Generalist"

    return best_persona, PERSONAS[best_persona]


def compute_peak_hour_label(signals: list[Signal]) -> Optional[str]:
    # Takeout timestamps are UTC - convert to DISPLAY_TZ (IST by default)
    # before pulling out the hour, or every result is off by 5.5 hours.
    hours = [
        s.timestamp.astimezone(DISPLAY_TZ).hour
        for s in signals
        if s.timestamp is not None
    ]
    if not hours:
        return None
    peak = Counter(hours).most_common(1)[0][0]
    label = f"{peak % 12 or 12}{'am' if peak < 12 else 'pm'}"
    if peak in NIGHT_OWL_HOURS:
        return f"{label} — certified night owl"
    return label


def build_wrapped_result(
    signals: list[Signal],
    path_type: str,
    headline_stat: str,
    extra_facts: list[str] | None = None,
) -> WrappedResult:
    persona_name, info = match_persona(signals)

    cat_counter = Counter()
    chan_counter = Counter()
    for s in signals:
        if s.category:
            cat_counter[s.category] += s.weight
        if s.channel:
            chan_counter[s.channel] += s.weight

    return WrappedResult(
        path_type=path_type,
        persona_name=persona_name,
        persona_emoji=info["emoji"],
        persona_tagline=info["tagline"],
        roast_line=info["roast"],
        headline_stat=headline_stat,
        top_categories=[(k, int(v)) for k, v in cat_counter.most_common(5)],
        top_channels=[(k, int(v)) for k, v in chan_counter.most_common(5)],
        peak_hour_label=compute_peak_hour_label(signals),
        total_signals=len(signals),
        extra_facts=extra_facts or [],
    )