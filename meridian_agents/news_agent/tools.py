"""Tools available to the Meridian News Agent."""
import json
import os

import requests
from agents import function_tool

from .publisher import save_news_items as _save


@function_tool
def search_news(region: str, query: str, max_results: int = 8) -> str:
    """Search for top news for a given region using DuckDuckGo news search.

    Args:
        region: One of 'world', 'usa', 'india', 'odisha'.
        query:  Search query string, e.g. 'top world news today'.
        max_results: Max articles to return (default 8).

    Returns:
        JSON array of articles with keys: title, url, body, image, date, source.
    """
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            raw = list(ddgs.news(query, max_results=max_results))
        articles = [
            {
                "title": a.get("title", ""),
                "url": a.get("url", ""),
                "body": a.get("body", ""),
                "image": a.get("image"),
                "date": a.get("date", ""),
                "source": a.get("source", ""),
            }
            for a in raw
        ]
        return json.dumps(articles)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@function_tool
def save_news(items_json: str) -> str:
    """Save the final curated list of news items to the Meridian platform.

    Args:
        items_json: JSON array of news items. Each item must have:
            - title (str): Headline
            - summary (str): ~100-word summary of the story
            - sourceUrl (str): Link to the original article
            - region (str): 'world' | 'usa' | 'india' | 'odisha'
            - imageUrl (str | null): Thumbnail image URL
            - sourceName (str): Publication name (e.g. "BBC News")
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
