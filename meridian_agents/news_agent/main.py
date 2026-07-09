"""Meridian News Agent — Gemini-powered daily news aggregator."""
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

from openai import AsyncOpenAI
from agents import Agent, Runner, set_default_openai_client, set_default_openai_api, set_tracing_disabled

from .tools import fetch_region_news, save_news
from .tracer import start_run, complete_run
from ..observability import flush_observability, init_observability, traced_run

init_observability("news_agent")

_TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

_REGIONS = ["ai", "quantum", "jobmarket"]

_INSTRUCTIONS = """\
You are the Meridian News Agent. You have been given a batch of freshly-fetched news
articles across three topics: artificial intelligence, quantum computing, and the job
market. Your job is to curate exactly 10 stories, write a crisp summary for each, and
save them via save_news().

SELECTION RULES:
- Target: 4 ai, 3 quantum, 3 jobmarket
- The 4 "ai" stories MUST come from the ai topic and cover the latest AI developments
  (product launches, model releases, regulation, or major research)
- The 3 "quantum" stories MUST come from the quantum topic and cover quantum computing
  or quantum technology (hardware milestones, error correction, research breakthroughs,
  real-world applications)
- The 3 "jobmarket" stories MUST come from the jobmarket topic and cover employment,
  hiring, layoffs, wages, labor policy, or workforce trends
- If a topic has fewer articles than needed, take what's available and fill the gap from
  whichever topic has the most articles
- No duplicate stories across topics
- Prefer articles with a non-null image field

BUZZ & IMPACT CRITERION (most important selection filter):
- Within each topic's quota, always pick the stories with the HIGHEST public interest
- Signals of a high-buzz story: affects many people, involves a major institution/country/company,
  has market-moving implications, represents a significant first or reversal, or is breaking news
- Avoid niche/local stories when a more impactful alternative exists within the same topic

SUMMARY RULES:
- Each summary: ~100 words, neutral journalistic tone
- Explain what happened and why it matters
- Do NOT start with "The"
- Use only facts present in the article's title/body — do not fabricate

TTS WRITING STYLE (each item's title + summary will be read aloud as its own standalone
audio clip by a news-anchor AI voice — it must make sense on its own, with no dependency
on a spoken introduction or the items around it):
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
    "region":      "<ai|quantum|jobmarket>",
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

    _GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"

    # Use the SDK's proper API for non-OpenAI providers:
    # set_default_openai_client sets the global client _get_client() returns,
    # set_default_openai_api("chat_completions") switches from Responses API
    # (which Gemini doesn't implement) to Chat Completions.
    gemini_client = AsyncOpenAI(api_key=gemini_key, base_url=_GEMINI_BASE)
    set_default_openai_client(gemini_client, use_for_tracing=False)
    set_default_openai_api("chat_completions")
    set_tracing_disabled(True)

    return Agent(
        name="MeridianNewsAgent",
        model="gemini-2.5-flash",
        instructions=_INSTRUCTIONS,
        tools=[save_news],
    )


def _gather_articles() -> list[dict]:
    """Fetch from direct RSS feeds for all 3 topics before starting the agent."""
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
        "Select 10 stories (4 ai, 3 quantum, 3 jobmarket), write summaries, and call save_news()."
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
        with traced_run("news_agent"):
            articles = _gather_articles()
            summary = asyncio.run(_run(articles))
    except Exception as exc:
        complete_run(run_id, str(exc), failed=True)
        raise
    finally:
        flush_observability()

    complete_run(run_id, summary or "News articles fetched and saved.")

    print("\n" + "=" * 44)
    print(summary)
    print("=" * 44)
