"""Tools and search helpers for the Meridian News Agent."""
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from io import BytesIO

import feedparser
import requests
from agents import function_tool

from ..auth import make_agent_jwt
from .publisher import save_news_items as _save

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Per-region list of direct RSS feeds (real URLs, no Google wrappers)
_REGION_FEEDS: dict[str, list[tuple[str, str]]] = {
    "world": [
        ("BBC World",   "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("CNN",         "http://rss.cnn.com/rss/edition.rss"),
        ("The Guardian","https://www.theguardian.com/world/rss"),
        ("Al Jazeera",  "https://www.aljazeera.com/xml/rss/all.xml"),
    ],
    "usa": [
        ("BBC US & Canada", "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml"),
        ("CNN",             "http://rss.cnn.com/rss/edition_us.rss"),
        ("NPR",             "https://feeds.npr.org/1001/rss.xml"),
    ],
    "india": [
        ("NDTV",       "https://feeds.feedburner.com/ndtvnews-india-news"),
        ("Times of India", "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"),
        ("The Hindu",  "https://www.thehindu.com/news/national/feeder/default.rss"),
    ],
    "odisha": [
        ("OTV",        "https://odishatv.in/feed"),
        ("Pragativadi","https://pragativadi.com/feed"),
        ("The Hindu Odisha", "https://www.thehindu.com/news/national/other-states/feeder/default.rss"),
    ],
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_within_hours(date_str: str | None, hours: int = 36) -> bool:
    if not date_str:
        return True
    try:
        import email.utils
        ts = email.utils.parsedate_to_datetime(date_str)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return ts >= cutoff
    except Exception:
        return True


def _rss_image(entry) -> str | None:
    """Extract image URL from feedparser entry (media:content / enclosure / media:thumbnail)."""
    mc = getattr(entry, "media_content", None) or []
    if mc:
        return mc[0].get("url")
    enc = getattr(entry, "enclosures", None) or []
    for e in enc:
        if e.get("type", "").startswith("image"):
            return e.get("href") or e.get("url")
    mt = getattr(entry, "media_thumbnail", None) or []
    if mt:
        return mt[0].get("url")
    return None


def _fetch_og_image(url: str, timeout: int = 8) -> str | None:
    """Fetch og:image / twitter:image from an article page."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout,
                            allow_redirects=True)
        if resp.status_code != 200:
            return None
        html = resp.text
        for pattern in [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](https?://[^"\'> ]+)',
            r'<meta[^>]+content=["\'](https?://[^"\'> ]+)[^>]+property=["\']og:image["\']',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\'](https?://[^"\'> ]+)',
            r'<meta[^>]+content=["\'](https?://[^"\'> ]+)[^>]+name=["\']twitter:image["\']',
        ]:
            m = re.search(pattern, html, re.IGNORECASE)
            if m:
                return m.group(1)
        return None
    except Exception:
        return None


def _parse_feed(source_name: str, feed_url: str, region: str) -> list[dict]:
    """Parse one RSS feed and return normalised article dicts."""
    try:
        feed = feedparser.parse(feed_url)
        articles = []
        for e in feed.entries:
            title = e.get("title", "").strip()
            url = e.get("link", "")
            if not title or not url:
                continue
            articles.append({
                "title": title,
                "url": url,
                "body": re.sub(r"<[^>]+>", " ", e.get("summary", "")).strip(),
                "image": _rss_image(e),
                "date": e.get("published", ""),
                "source": source_name,
                "region": region,
            })
        return articles
    except Exception:
        return []


# ── Public search function (called from main.py) ─────────────────────────────

def fetch_region_news(region: str, _query: str = "", max_results: int = 10) -> list[dict]:
    """Aggregate articles from multiple direct RSS feeds for a region."""
    feeds = _REGION_FEEDS.get(region, [])
    all_articles: list[dict] = []

    # Fetch all feeds in parallel
    with ThreadPoolExecutor(max_workers=len(feeds)) as pool:
        futures = {pool.submit(_parse_feed, name, url, region): name
                   for name, url in feeds}
        for future in as_completed(futures):
            all_articles.extend(future.result())

    # Deduplicate by title similarity (keep first seen)
    seen: set[str] = set()
    unique = []
    for a in all_articles:
        key = re.sub(r"[^a-z0-9]", "", a["title"].lower())[:60]
        if key not in seen:
            seen.add(key)
            unique.append(a)

    # Sort newest-first by parsed date
    def _sort_key(a):
        try:
            import email.utils
            return email.utils.parsedate_to_datetime(a["date"])
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)

    unique.sort(key=_sort_key, reverse=True)

    # Prefer fresh (36h); fall back to all
    fresh = [a for a in unique if _is_within_hours(a["date"], hours=36)]
    chosen = fresh if len(fresh) >= 3 else unique
    window = "36h" if chosen is fresh else "all"

    result = chosen[:max_results]
    with_img = sum(1 for a in result if a["image"])
    print(f"   [{region:6}]  {len(result)} articles  "
          f"(window={window}, {with_img} with RSS image)")
    return result


# ── Image enhancement via Gemini ─────────────────────────────────────────────

def _download_image(url: str, timeout: int = 15) -> tuple[bytes, str] | None:
    """Download an image and return (bytes, mime_type), or None on failure."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code != 200:
            return None
        ct = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
        if not ct.startswith("image/"):
            return None
        return resp.content, ct
    except Exception:
        return None


def _upload_to_media(buf: bytes, mime: str, alt: str) -> str | None:
    """Upload image bytes to the Meridian media service and return the URL."""
    server_base = os.getenv("SERVER_BASE", "http://localhost:3000")
    try:
        jwt = make_agent_jwt(name="News Agent", email="news-agent@meridian.internal")
        ext = "jpg" if "jpeg" in mime else "webp" if "webp" in mime else "png"
        files = {"file": (f"news-{int(time.time())}.{ext}", BytesIO(buf), mime)}
        res = requests.post(
            f"{server_base}/api/media/upload",
            headers={"Authorization": f"Bearer {jwt}"},
            files=files,
            data={"alt": alt[:200]},
            timeout=60,
        )
        if not res.ok:
            return None
        return res.json().get("url")
    except Exception:
        return None


_ENHANCE_MODELS = [
    "gemini-3.1-flash-image",
    "gemini-2.5-flash-image",
    "gemini-3-pro-image",
]

_ENHANCE_PROMPT = (
    "Enhance this news thumbnail: sharpen focus, remove blur and noise, "
    "improve brightness and contrast. Keep the same subject and composition. "
    "Return a crisp, professional image suitable for a news website."
)


def _gemini_enhance(image_bytes: bytes, mime: str) -> tuple[bytes, str] | None:
    """Send an image to Gemini for enhancement and return (enhanced_bytes, mime)."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        parts = [
            types.Part.from_bytes(data=image_bytes, mime_type=mime),
            types.Part.from_text(text=_ENHANCE_PROMPT),
        ]
        cfg = types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"])

        for model_name in _ENHANCE_MODELS:
            try:
                response = client.models.generate_content(
                    model=model_name, contents=parts, config=cfg
                )
                for part in response.candidates[0].content.parts:
                    if getattr(part, "inline_data", None):
                        return part.inline_data.data, part.inline_data.mime_type
            except Exception:
                continue
        return None
    except Exception as exc:
        print(f"      ⚠️  Gemini enhance: {exc}")
        return None


def _enhance_item_image(idx_item: tuple[int, dict]) -> tuple[int, str | None]:
    """Download, enhance via Gemini, upload, and return (idx, new_url or None)."""
    idx, item = idx_item
    url = item.get("imageUrl")
    if not url:
        return idx, None

    downloaded = _download_image(url)
    if not downloaded:
        return idx, None
    raw_bytes, mime = downloaded

    enhanced = _gemini_enhance(raw_bytes, mime)
    if not enhanced:
        return idx, None
    enh_bytes, enh_mime = enhanced

    new_url = _upload_to_media(enh_bytes, enh_mime, item.get("title", "news thumbnail")[:120])
    return idx, new_url


def _enhance_all_images(items: list[dict]) -> list[dict]:
    """Enhance every item that has an imageUrl using Gemini, upload to media service."""
    candidates = [(i, it) for i, it in enumerate(items) if it.get("imageUrl")]
    if not candidates:
        return items

    print(f"   ✨ Enhancing {len(candidates)} thumbnail(s) with Gemini…")
    enhanced = [dict(it) for it in items]

    with ThreadPoolExecutor(max_workers=min(len(candidates), 5)) as pool:
        futures = {pool.submit(_enhance_item_image, pair): pair[0] for pair in candidates}
        for f in as_completed(futures):
            idx, new_url = f.result()
            title = items[idx].get("title", "")[:55]
            if new_url:
                enhanced[idx]["imageUrl"] = new_url
                print(f"      ✓ {title}")
            else:
                print(f"      ✗ {title} (kept original)")

    return enhanced


# ── Image enrichment (run after agent selects articles) ──────────────────────

def _enrich_images(items: list[dict]) -> list[dict]:
    """Fetch og:image for items that have no imageUrl yet."""
    need = [(i, it) for i, it in enumerate(items) if not it.get("imageUrl")]
    if not need:
        return items

    print(f"   🖼  Fetching og:image for {len(need)} articles…")
    results: dict[int, str | None] = {}

    with ThreadPoolExecutor(max_workers=len(need)) as pool:
        futures = {pool.submit(_fetch_og_image, it["sourceUrl"]): i
                   for i, it in need}
        for f in as_completed(futures):
            results[futures[f]] = f.result()

    enriched = [dict(it) for it in items]
    for i, _ in need:
        enriched[i]["imageUrl"] = results.get(i)
        status = "✓" if results.get(i) else "✗"
        print(f"      {status} {enriched[i]['title'][:55]}")

    return enriched


# ── Save tool (called by the agent) ──────────────────────────────────────────

@function_tool
def save_news(items_json: str) -> str:
    """Save the final curated list of news items to the Meridian platform.

    Images missing from RSS feeds are fetched automatically from each
    article's source page before saving.

    Args:
        items_json: JSON array of exactly 10 news items. Each item must have:
            - title (str): Headline
            - summary (str): ~100-word neutral journalistic summary
            - sourceUrl (str): Direct article URL (from the search results)
            - region (str): 'world' | 'usa' | 'india' | 'odisha'
            - imageUrl (str | null): Image URL from the search result, or null
            - sourceName (str): Publication name
            - publishedAt (str | null): date field from the search result

    Returns:
        JSON result from the platform API.
    """
    try:
        items = json.loads(items_json)
        items = _enrich_images(items)
        items = _enhance_all_images(items)
        result = _save(items)
        got = sum(1 for it in items if it.get("imageUrl"))
        print(f"   💾  Saved {len(items)} items ({got} with thumbnail)")
        return json.dumps(result)
    except Exception as exc:
        return json.dumps({"error": str(exc)})
