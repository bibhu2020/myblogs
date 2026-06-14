"""Meridian News Agent — Gemini-powered daily news aggregator."""
import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

from openai import AsyncOpenAI
from agents import Agent, Runner
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

from .tools import search_news, save_news

_INSTRUCTIONS = """\
You are the Meridian News Agent. Your job is to curate 10 top news stories of the day
across four regions and save them to the platform. You MUST call search_news() four
separate times — once per region — before choosing any stories.

MANDATORY STEPS (follow in order, do not skip any):

STEP 1 — Search world news:
  search_news(region="world", query="top world news today international breaking", max_results=6)

STEP 2 — Search USA news:
  search_news(region="usa", query="top USA news today America breaking", max_results=6)

STEP 3 — Search India news:
  search_news(region="india", query="top India news today breaking", max_results=6)

STEP 4 — Search Odisha news:
  search_news(region="odisha", query="Odisha news today Bhubaneswar state breaking", max_results=6)

STEP 5 — Select exactly 10 stories with this STRICT distribution:
  - 3 stories with region="world"
  - 3 stories with region="usa"
  - 2 stories with region="india"
  - 2 stories with region="odisha"
  Pick the most significant and recent from each batch. No duplicate topics.

STEP 6 — For each selected story write a ~100-word neutral journalistic summary:
  - Explain what happened and why it matters
  - Do NOT start with "The"
  - Use only facts from the search result (do not fabricate)

STEP 7 — Call save_news() with a JSON array of exactly 10 items.
Each item MUST have:
  {
    "title": "Headline verbatim or lightly improved",
    "summary": "~100-word neutral summary",
    "sourceUrl": "https://...",
    "region": "world" | "usa" | "india" | "odisha",
    "imageUrl": "https://... or null",
    "sourceName": "Publication name",
    "publishedAt": "ISO date string or null"
  }

STEP 8 — Report how many items were saved and stop.

RULES:
- You MUST call search_news() four times before selecting stories.
- Do NOT call save_news() before completing all four searches.
- Do NOT fabricate URLs, titles, or facts.
"""

_TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


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
        tools=[search_news, save_news],
    )


async def _run() -> str:
    agent = _build_agent()
    result = await Runner.run(
        agent,
        input=f"Today is {_TODAY}. Fetch and publish the top 10 news stories now.",
        max_turns=20,
    )
    return result.final_output or "(no output)"


def run_news_agent() -> None:
    print("\n╔══════════════════════════════════════╗")
    print("║  Meridian News Agent                 ║")
    print("║  Gemini 2.5 Flash · DuckDuckGo News  ║")
    print("╚══════════════════════════════════════╝\n")
    print(f"Date (UTC): {_TODAY}")
    print(f"Target:     {os.getenv('SERVER_BASE', 'http://localhost:3000')}\n")

    summary = asyncio.run(_run())

    print("\n" + "=" * 44)
    print(summary)
    print("=" * 44)
