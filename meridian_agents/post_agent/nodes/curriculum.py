"""Curriculum continuity for the Educational category — tracks which fundamental→advanced
physics topics have already been published so the next Educational post continues the
series instead of repeating or randomizing.

Runs unconditionally on every post_agent run (cheap, one REST call) and stashes the next
topic in state regardless of which category the weighted pick in discover_trend_node ends
up choosing — this avoids an ordering dependency between category selection and curriculum
lookup, at the cost of one extra REST call on non-Educational runs.
"""
import httpx

from ...auth import make_agent_jwt
from ..state import AgentState
from .research import EDUCATIONAL_TRACKS, TRACK_LABELS

# Fixed tie-break order when multiple tracks are equally behind.
_TRACK_ORDER = ["general-relativity", "special-relativity", "quantum-physics"]
_TIMEOUT = 20


def _fetch_educational_posts(server_base: str) -> list[dict]:
    jwt = make_agent_jwt()
    with httpx.Client(timeout=_TIMEOUT) as client:
        res = client.get(
            f"{server_base}/api/posts/admin",
            params={"category": "educational", "status": "published", "limit": 200},
            headers={"Authorization": f"Bearer {jwt}"},
        )
        res.raise_for_status()
        data = res.json()
        return data.get("posts", data) if isinstance(data, dict) else data


def _next_topic(posts: list[dict]) -> tuple[str, int, str]:
    """Return (series_key, series_index, topic_text) for the next post to publish.

    Round-robins across the 3 tracks (picks whichever has progressed least, ties broken
    by _TRACK_ORDER) so no single subject dominates for weeks while the others go stale.
    """
    max_index = {key: -1 for key in _TRACK_ORDER}
    for post in posts:
        key = post.get("seriesKey")
        idx = post.get("seriesIndex")
        if key in max_index and isinstance(idx, int) and idx > max_index[key]:
            max_index[key] = idx

    series_key = min(_TRACK_ORDER, key=lambda k: (max_index[k], _TRACK_ORDER.index(k)))
    series_index = max_index[series_key] + 1

    topics = EDUCATIONAL_TRACKS[series_key]
    if series_index < len(topics):
        topic = topics[series_index]
    else:
        # Track exhausted — wrap and frame as a revisit/consolidation post rather than
        # crashing or silently repeating a "first pass" topic verbatim.
        topic = f"Revisiting and synthesizing: {topics[series_index % len(topics)]}"

    return series_key, series_index, topic


# ── LangGraph node ────────────────────────────────────────────────────────────

def resolve_curriculum_node(state: AgentState) -> dict:
    server_base = state.get("server_base", "")
    try:
        posts = _fetch_educational_posts(server_base)
        series_key, series_index, topic = _next_topic(posts)
        print(
            f"📖 Curriculum: next Educational topic → {TRACK_LABELS[series_key]} "
            f"#{series_index}: {topic[:70]}"
        )
    except Exception as exc:
        # Never fail the whole run over a curriculum lookup — fall back to the start of
        # General Relativity, the same default discover_trend_node uses if this state is
        # missing entirely.
        print(f"⚠️  Curriculum lookup failed ({exc}) — defaulting to track start")
        series_key, series_index = "general-relativity", 0
        topic = EDUCATIONAL_TRACKS[series_key][0]

    return {"series_key": series_key, "series_index": series_index, "series_topic": topic}
