"""Meridian News Agent — Gemini-powered daily news aggregator."""
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

from openai import AsyncOpenAI
from agents import Agent, Runner
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

from .tools import fetch_region_news, save_news

_TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

_REGION_QUERIES = [
    ("world",  "top world news when:1d",          10),
    ("usa",    "top USA America news when:1d",     10),
    ("india",  "top India news when:1d",           10),
    ("odisha", "Odisha news when:2d",              10),
]

_INSTRUCTIONS = """\
You are the Meridian News Agent. You have been given a batch of freshly-fetched news
articles across four regions. Your job is to curate exactly 10 stories, write a crisp
summary for each, and save them via save_news().

SELECTION RULES:
- Target: 3 world, 3 usa, 2 india, 2 odisha
- If a region has fewer articles than needed, take what's available and
  fill the gap from whichever region has the most articles
- No duplicate topics across regions
- Prefer articles with a non-null image field

SUMMARY RULES:
- Each summary: ~100 words, neutral journalistic tone
- Explain what happened and why it matters
- Do NOT start with "The"
- Use only facts present in the article's title/body — do not fabricate

OUTPUT:
Call save_news() once with a JSON array of exactly 10 items, each with:
  {
    "title":       "<headline verbatim or lightly improved>",
    "summary":     "<~100-word summary>",
    "sourceUrl":   "<url from the article>",
    "region":      "<world|usa|india|odisha>",
    "imageUrl":    "<image field value, or null>",
    "sourceName":  "<source field value>",
    "publishedAt": "<date field value, or null>"
  }

After save_news() succeeds, report the count and stop. Do not call save_news() more than once.
"""


def _build_agent() -> Agent:
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_key:
        raise RuntimeError("GEMINI_API_KEY is required for the news agent.")

    gemini_client = AsyncOpenAI(
        api_key=gemini_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    model = OpenAIChatCompletionsModel(
        model="gemini-2.5-flash",
        openai_client=gemini_client,
    )
    return Agent(
        name="MeridianNewsAgent",
        model=model,
        instructions=_INSTRUCTIONS,
        tools=[save_news],
    )


def _gather_articles() -> list[dict]:
    """Run all 4 region searches before starting the agent."""
    print("🔍 Searching news (all regions)...")
    all_articles = []
    for region, query, max_r in _REGION_QUERIES:
        articles = fetch_region_news(region, query, max_results=max_r)
        all_articles.extend(articles)
    print(f"   Total articles fetched: {len(all_articles)}\n")
    return all_articles


async def _run(articles: list[dict]) -> str:
    agent = _build_agent()
    prompt = (
        f"Today is {_TODAY}. Here are the freshly fetched news articles:\n\n"
        f"```json\n{json.dumps(articles, indent=2)}\n```\n\n"
        "Select 10 stories, write summaries, and call save_news()."
    )
    result = await Runner.run(agent, input=prompt, max_turns=10)
    return result.final_output or "(no output)"


def run_news_agent() -> None:
    print("\n╔══════════════════════════════════════╗")
    print("║  Meridian News Agent                 ║")
    print("║  Gemini 2.5 Flash · DuckDuckGo News  ║")
    print("╚══════════════════════════════════════╝\n")
    print(f"Date (UTC): {_TODAY}")
    print(f"Target:     {os.getenv('SERVER_BASE', 'http://localhost:3000')}\n")

    articles = _gather_articles()
    summary = asyncio.run(_run(articles))

    print("\n" + "=" * 44)
    print(summary)
    print("=" * 44)
