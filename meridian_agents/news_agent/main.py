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
You are the Meridian News Agent. Your job is to curate the top 10 most important and
buzzing news stories of the day across four regions: World, USA, India, and Odisha
(an eastern Indian state). Run every day and refresh the Meridian News page.

STEP-BY-STEP PROCESS:
1. Call search_news() for each region with an appropriate query:
   - region="world",  query="top world news today breaking"
   - region="usa",    query="top USA news today breaking America"
   - region="india",  query="top India news today breaking"
   - region="odisha", query="Odisha news today Bhubaneswar Odisha state"

2. From all results, select exactly 10 stories total — roughly:
   - 3 from World
   - 3 from USA
   - 2 from India
   - 2 from Odisha
   Prioritise significance, recency, and variety (no duplicate topics).

3. For each selected story, write a crisp ~100-word summary that:
   - Explains what happened and why it matters
   - Is written in clear, neutral, journalistic prose
   - Does NOT start with the word "The"

4. Build the final list of 10 items as a JSON array and call save_news() with it.
   Each item MUST have these exact fields:
   {
     "title": "Headline (keep verbatim from source or slightly improved)",
     "summary": "~100-word neutral journalistic summary",
     "sourceUrl": "https://...",
     "region": "world" | "usa" | "india" | "odisha",
     "imageUrl": "https://... or null",
     "sourceName": "BBC News / CNN / etc.",
     "publishedAt": "ISO date string or null"
   }

5. After save_news() returns successfully, report how many items were saved and stop.

Do NOT fabricate news or URLs. Only use what search_news() returns.
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
        model="gemini-2.0-flash",
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
    print("║  Gemini 2.0 Flash · DuckDuckGo News  ║")
    print("╚══════════════════════════════════════╝\n")
    print(f"Date (UTC): {_TODAY}")
    print(f"Target:     {os.getenv('SERVER_BASE', 'http://localhost:3000')}\n")

    summary = asyncio.run(_run())

    print("\n" + "=" * 44)
    print(summary)
    print("=" * 44)
