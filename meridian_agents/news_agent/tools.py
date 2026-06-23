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
    "ai": [
        ("TechCrunch AI",        "https://techcrunch.com/category/artificial-intelligence/feed/"),
        ("The Verge AI",         "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"),
        ("MIT Technology Review","https://www.technologyreview.com/feed/"),
        ("VentureBeat AI",       "https://venturebeat.com/category/ai/feed/"),
    ],
    "finance": [
        ("Reuters Business",  "https://feeds.reuters.com/reuters/businessNews"),
        ("CNBC Finance",      "https://www.cnbc.com/id/10001147/device/rss/rss.html"),
        ("MarketWatch",       "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines"),
        ("Financial Times",   "https://www.ft.com/rss/home"),
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

_MIN_DIMENSION = 100   # pixels — filters tracking pixels / tiny icons
_MIN_BYTES     = 4096  # bytes  — filters empty or near-empty responses


def _validate_image(data: bytes) -> tuple[bool, str]:
    """Return (ok, mime) after verifying data is a real image with acceptable dimensions."""
    if len(data) < _MIN_BYTES:
        return False, ""
    try:
        from PIL import Image
        img = Image.open(BytesIO(data))
        img.verify()                       # raises on corrupt files
        img = Image.open(BytesIO(data))    # re-open after verify (PIL limitation)
        w, h = img.size
        if w < _MIN_DIMENSION or h < _MIN_DIMENSION:
            return False, ""
        fmt = (img.format or "JPEG").lower()
        mime = f"image/{fmt}" if fmt != "jpg" else "image/jpeg"
        return True, mime
    except Exception:
        return False, ""


def _download_image(url: str, timeout: int = 15) -> tuple[bytes, str] | None:
    """Download an image, validate it is a real image, and return (bytes, mime_type)."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code != 200:
            return None
        ct = resp.headers.get("content-type", "").split(";")[0].strip()
        if not ct.startswith("image/"):
            return None
        ok, mime = _validate_image(resp.content)
        if not ok:
            return None
        return resp.content, mime
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


def _fetch_item_image(idx_item: tuple[int, dict]) -> tuple[int, str | None]:
    """Download and upload the real thumbnail for a news item.

    Tries the RSS-provided imageUrl first; falls back to scraping og:image from
    the source article page. The image is uploaded as-is — no AI generation is
    applied so the thumbnail always matches the actual news story.
    """
    idx, item = idx_item
    url = item.get("imageUrl")

    # Try RSS/provided URL first
    downloaded = _download_image(url) if url else None

    # Fall back to og:image scraped from the article source page
    if not downloaded:
        og_url = _fetch_og_image(item.get("sourceUrl", ""))
        if og_url:
            downloaded = _download_image(og_url)

    if not downloaded:
        return idx, None

    raw_bytes, mime = downloaded
    new_url = _upload_to_media(raw_bytes, mime, item.get("title", "news thumbnail")[:120])
    return idx, new_url


def _enhance_all_images(items: list[dict]) -> list[dict]:
    """Fetch and upload real thumbnails for every news item (RSS or og:image fallback)."""
    candidates = list(enumerate(items))
    if not candidates:
        return items

    with_url = sum(1 for _, it in candidates if it.get("imageUrl"))
    print(f"   🖼  Fetching {len(candidates)} thumbnail(s) ({with_url} with RSS image)…")
    result = [dict(it) for it in items]

    with ThreadPoolExecutor(max_workers=min(len(candidates), 5)) as pool:
        futures = {pool.submit(_fetch_item_image, pair): pair[0] for pair in candidates}
        for f in as_completed(futures):
            idx, new_url = f.result()
            title = items[idx].get("title", "")[:55]
            if new_url:
                result[idx]["imageUrl"] = new_url
                print(f"      ✓ {title}")
            else:
                result[idx]["imageUrl"] = None
                print(f"      ✗ {title} (no image found)")

    return result


# ── Save tool (called by the agent) ──────────────────────────────────────────

@function_tool
def save_news(items_json: str) -> str:
    """Save the final curated list of news items to the Meridian platform.

    Images missing from RSS feeds are fetched automatically from each
    article's source page before saving.

    Args:
        items_json: JSON array of exactly 14 news items. Each item must have:
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
        items = _enhance_all_images(items)
        result = _save(items)
        got = sum(1 for it in items if it.get("imageUrl"))
        print(f"   💾  Saved {len(items)} items ({got} with thumbnail)")
        return json.dumps(result)
    except Exception as exc:
        return json.dumps({"error": str(exc)})
