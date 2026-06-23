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


# ── Thumbnail pipeline ───────────────────────────────────────────────────────

_MIN_DIMENSION  = 100    # pixels — rejects tracking pixels / tiny icons
_MIN_BYTES      = 4096   # bytes  — rejects empty / near-empty responses
_THUMB_W        = 800    # target thumbnail width
_THUMB_H        = 450    # target thumbnail height (16:9)


def _validate_image(data: bytes) -> tuple[bool, str]:
    """Return (ok, mime) after checking the bytes are a real image of acceptable size."""
    if len(data) < _MIN_BYTES:
        return False, ""
    try:
        from PIL import Image
        img = Image.open(BytesIO(data))
        img.verify()
        img = Image.open(BytesIO(data))   # re-open after verify (PIL limitation)
        w, h = img.size
        if w < _MIN_DIMENSION or h < _MIN_DIMENSION:
            return False, ""
        fmt = (img.format or "JPEG").lower()
        return True, "image/jpeg" if fmt == "jpg" else f"image/{fmt}"
    except Exception:
        return False, ""


def _download_image(url: str, timeout: int = 15) -> tuple[bytes, str] | None:
    """Download a URL and return (bytes, mime) if it is a valid image, else None."""
    if not url:
        return None
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code != 200:
            return None
        if not resp.headers.get("content-type", "").startswith("image/"):
            return None
        ok, mime = _validate_image(resp.content)
        return (resp.content, mime) if ok else None
    except Exception:
        return None


def _enhance_thumbnail(data: bytes) -> bytes:
    """Center-crop to 16:9 and resize to 800×450 JPEG.

    Produces a consistent thumbnail regardless of the source image's dimensions
    or aspect ratio. Returns the original bytes unchanged on any error.
    """
    try:
        from PIL import Image, ImageOps
        img = Image.open(BytesIO(data))
        # Normalise colour mode
        if img.mode == "RGBA":
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Auto-rotate based on EXIF orientation
        img = ImageOps.exif_transpose(img)

        # Center-crop to 16:9
        src_w, src_h = img.size
        if src_w / src_h > _THUMB_W / _THUMB_H:
            # Too wide — trim sides
            new_w = int(src_h * _THUMB_W / _THUMB_H)
            left = (src_w - new_w) // 2
            img = img.crop((left, 0, left + new_w, src_h))
        else:
            # Too tall — trim top & bottom
            new_h = int(src_w * _THUMB_H / _THUMB_W)
            top = (src_h - new_h) // 2
            img = img.crop((0, top, src_w, top + new_h))

        img = img.resize((_THUMB_W, _THUMB_H), Image.LANCZOS)

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        return buf.getvalue()
    except Exception:
        return data   # fall through with original bytes on any error


def _upload_to_media(buf: bytes, mime: str, alt: str) -> str | None:
    """Upload image bytes to the Meridian media service and return the hosted URL."""
    server_base = os.getenv("SERVER_BASE", "http://localhost:3000")
    try:
        jwt = make_agent_jwt(name="News Agent", email="news-agent@meridian.internal")
        files = {"file": (f"news-{int(time.time())}.jpg", BytesIO(buf), "image/jpeg")}
        res = requests.post(
            f"{server_base}/api/media/upload",
            headers={"Authorization": f"Bearer {jwt}"},
            files=files,
            data={"alt": alt[:200]},
            timeout=60,
        )
        return res.json().get("url") if res.ok else None
    except Exception:
        return None


def _fetch_item_image(idx_item: tuple[int, dict]) -> tuple[int, str | None]:
    """Best-effort thumbnail pipeline for one news item.

    Attempt order:
      1. RSS/LLM-provided imageUrl
      2. og:image / twitter:image scraped from the source article page
    Each candidate is downloaded, validated, enhanced (center-crop → 800×450 JPEG),
    and uploaded to the media service. Returns (idx, url) or (idx, None) on total failure.
    """
    idx, item = idx_item
    source_url = item.get("sourceUrl", "")

    # Build candidate list: RSS image first, then og:image scrape
    candidates: list[str] = []
    rss_url = item.get("imageUrl")
    if rss_url:
        candidates.append(rss_url)
    og_url = _fetch_og_image(source_url) if source_url else None
    if og_url and og_url != rss_url:
        candidates.append(og_url)

    for url in candidates:
        downloaded = _download_image(url)
        if not downloaded:
            continue
        raw_bytes, _ = downloaded
        enhanced = _enhance_thumbnail(raw_bytes)
        hosted_url = _upload_to_media(enhanced, "image/jpeg",
                                      item.get("title", "news thumbnail")[:120])
        if hosted_url:
            return idx, hosted_url

    return idx, None


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
