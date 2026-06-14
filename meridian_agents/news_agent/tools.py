"""Tools and search helpers for the Meridian News Agent."""
import json
import re
import urllib.parse
from datetime import datetime, timezone, timedelta

import feedparser
import requests
from agents import function_tool

from .publisher import save_news_items as _save

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MeridianBot/1.0)"}


def _parse_gnews_date(date_str: str) -> str | None:
    """Parse RFC 2822 date from Google News RSS into ISO format."""
    try:
        import email.utils
        ts = email.utils.parsedate_to_datetime(date_str)
        return ts.isoformat()
    except Exception:
        return date_str or None


def _is_within_hours(date_str: str | None, hours: int = 48) -> bool:
    """Return True if the date_str is within the last `hours` hours."""
    if not date_str:
        return True  # unknown date — keep it
    try:
        import email.utils
        ts = email.utils.parsedate_to_datetime(date_str)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return ts >= cutoff
    except Exception:
        return True


def _extract_og_image(url: str, timeout: int = 5) -> str | None:
    """Try to fetch og:image from the article page."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout, allow_redirects=True)
        match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](https?://[^"\']+)["\']', resp.text)
        if not match:
            match = re.search(r'<meta[^>]+content=["\'](https?://[^"\']+)["\'][^>]+property=["\']og:image["\']', resp.text)
        return match.group(1) if match else None
    except Exception:
        return None


def fetch_region_news(region: str, query: str, max_results: int = 10) -> list[dict]:
    """Search Google News RSS for a region. Articles within 48h preferred; falls back to 7d."""
    encoded = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"

    feed = feedparser.parse(url)
    entries = feed.entries[:max_results * 2]  # fetch extra, then filter

    articles = []
    for e in entries:
        pub_date = e.get("published", "")
        # Google News wraps source articles — extract the real URL from the link
        link = e.get("link", "")
        source = e.get("source", {}).get("title", "") if hasattr(e.get("source", ""), "get") else ""
        title = e.get("title", "")
        # Strip " - Source Name" suffix Google appends to titles
        if source and title.endswith(f" - {source}"):
            title = title[: -len(f" - {source}")]

        # Try media:content for thumbnail, else None (agent will handle)
        image = None
        if hasattr(e, "media_content") and e.media_content:
            image = e.media_content[0].get("url")

        articles.append({
            "title": title.strip(),
            "url": link,
            "body": e.get("summary", ""),
            "image": image,
            "date": pub_date,
            "source": source,
            "region": region,
        })

    # Prefer articles within 36h; fall back to all if fewer than 3 fresh ones
    fresh = [a for a in articles if _is_within_hours(a["date"], hours=36)]
    chosen = fresh if len(fresh) >= 3 else articles
    window = "36h" if chosen is fresh else "all"

    result = chosen[:max_results]
    print(f"   [{region:6}]  {len(result)} articles  (window={window})")
    return result


# ── Save tool (called by the agent) ──────────────────────────────────────────

@function_tool
def save_news(items_json: str) -> str:
    """Save the final curated list of news items to the Meridian platform.

    Args:
        items_json: JSON array of exactly 10 news items. Each item must have:
            - title (str): Headline
            - summary (str): ~100-word neutral journalistic summary
            - sourceUrl (str): Link to the original article
            - region (str): 'world' | 'usa' | 'india' | 'odisha'
            - imageUrl (str | null): Thumbnail image URL
            - sourceName (str): Publication name
            - publishedAt (str | null): ISO date string

    Returns:
        JSON result from the platform API.
    """
    try:
        items = json.loads(items_json)
        result = _save(items)
        return json.dumps(result)
    except Exception as exc:
        return json.dumps({"error": str(exc)})
