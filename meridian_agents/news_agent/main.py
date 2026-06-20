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
from .tracer import start_run, complete_run

_TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

_REGIONS = ["world", "usa", "india", "odisha"]

_INSTRUCTIONS = """\
You are the Meridian News Agent. You have been given two batches of freshly-fetched
news articles: general regional news and a dedicated AI/Quantum technology feed.
Your job is to curate exactly 12 stories total, write a crisp summary for each,
and save them via save_news().

SELECTION RULES — GENERAL (10 items):
- Target: 3 world, 3 usa, 2 india, 2 odisha
- If a region has fewer articles than needed, take what's available and
  fill the gap from whichever region has the most articles
- No duplicate topics across regions
- Prefer articles with a non-null image field

SELECTION RULES — AI/QUANTUM (2 items, mandatory):
- You MUST always include exactly 2 items from the AI/Quantum feed
- Pick the 2 most significant, latest developments in AI or Quantum Computing
- These must use region "ai_quantum"
- These are in addition to the 10 general stories — never substitute or skip them

SUMMARY RULES:
- Each summary: ~100 words, neutral journalistic tone
- Explain what happened and why it matters
- Do NOT start with "The"
- Use only facts present in the article's title/body — do not fabricate

OUTPUT:
Call save_news() once with a JSON array of exactly 12 items, each with:
  {
    "title":       "<headline verbatim or lightly improved>",
    "summary":     "<~100-word summary>",
    "sourceUrl":   "<url from the article>",
    "region":      "<world|usa|india|odisha|ai_quantum>",
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


def _gather_articles() -> tuple[list[dict], list[dict]]:
    """Fetch from direct RSS feeds for all regions. Returns (general, ai_quantum)."""
    print("🔍 Fetching news feeds (general regions)...")
    general = []
    for region in _REGIONS:
        articles = fetch_region_news(region, max_results=10)
        general.extend(articles)
    print(f"   Total general articles: {len(general)}\n")

    print("🤖 Fetching AI/Quantum feeds...")
    ai_quantum = fetch_region_news("ai_quantum", max_results=15)
    print(f"   Total AI/Quantum articles: {len(ai_quantum)}\n")

    return general, ai_quantum


async def _run(general: list[dict], ai_quantum: list[dict]) -> str:
    agent = _build_agent()
    prompt = (
        f"Today is {_TODAY}.\n\n"
        f"## General regional news articles:\n\n"
        f"```json\n{json.dumps(general, indent=2)}\n```\n\n"
        f"## AI/Quantum technology articles (you MUST pick exactly 2 from this pool):\n\n"
        f"```json\n{json.dumps(ai_quantum, indent=2)}\n```\n\n"
        "Select 10 general stories + exactly 2 AI/Quantum stories (12 total), "
        "write summaries, and call save_news()."
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

    run_id = start_run()
    try:
        general, ai_quantum = _gather_articles()
        summary = asyncio.run(_run(general, ai_quantum))
    except Exception as exc:
        complete_run(run_id, str(exc), failed=True)
        raise

    complete_run(run_id, summary or "News articles fetched and saved.")

    print("\n" + "=" * 44)
    print(summary)
    print("=" * 44)
