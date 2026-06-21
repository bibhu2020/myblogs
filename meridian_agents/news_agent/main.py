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

TTS WRITING STYLE (summaries will be read aloud by a news-anchor AI voice):
- Short, declarative sentences — maximum 20 words each
- Active voice always: "The court ruled..." not "It was ruled by the court..."
- One idea per sentence — no compound clauses joined by semicolons
- Strong opening verb: "Scientists confirmed...", "Authorities arrested...", "Voters approved..."
- Specific nouns: "The US Senate" not "lawmakers"; "Mount Fuji" not "the volcano"
- No em dashes or ellipses — clean periods only for crisp delivery
- Each sentence should be a complete broadcast-ready thought

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
    """Fetch from direct RSS feeds for all 4 regions before starting the agent."""
    print("🔍 Fetching news feeds (all regions)...")
    all_articles = []
    for region in _REGIONS:
        articles = fetch_region_news(region, max_results=10)
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

    run_id = start_run()
    try:
        articles = _gather_articles()
        summary = asyncio.run(_run(articles))
    except Exception as exc:
        complete_run(run_id, str(exc), failed=True)
        raise

    complete_run(run_id, summary or "News articles fetched and saved.")

    print("\n" + "=" * 44)
    print(summary)
    print("=" * 44)
