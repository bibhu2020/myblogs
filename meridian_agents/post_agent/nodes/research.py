import os
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from ..state import AgentState

# Priority order: Technology > Education > Travel == History.
# Weighted daily pick so Technology dominates, Education is second most common,
# and Travel/History share the remaining, lowest share.
_CATEGORY_WEIGHTS = [50, 30, 10, 10]

CATEGORIES = [
    {
        "name": "Technology",
        "research_style": (
            "artificial intelligence, quantum computing, and modern DevOps/DevSecOps engineering"
        ),
        # One of these is chosen at random each run — every Technology post is
        # always anchored to one of these specific angles.
        "subtopics": [
            "the single most exciting or surprising recent AI / machine learning development from "
            "the past 7 days — a new model release, landmark research paper, or safety/alignment "
            "breakthrough",
            "the most interesting recent development in quantum computing or quantum technology "
            "(past 3 months) — a new qubit milestone, error-correction breakthrough, or real-world "
            "quantum application",
            "how artificial intelligence is being used in DevOps today — AI-driven CI/CD, incident "
            "response, infrastructure automation, or observability",
            "how artificial intelligence is being used in DevSecOps today — AI-driven vulnerability "
            "detection, software supply-chain security, or automated security review in the delivery "
            "pipeline",
            "a genuinely useful modern DevOps practice, tool, or cultural shift worth understanding "
            "deeply",
            "a genuinely useful modern DevSecOps practice, tool, or cultural shift worth understanding "
            "deeply",
        ],
        "discover_prompt": lambda d, subtopic: (
            f"Today is {d}. Search the web and report on {subtopic}. Focus on educational depth — "
            "explain WHY it matters and HOW it works. Return: the exact topic, why it's significant, "
            "4–6 key technical facts with specific numbers/names, and 2–3 direct source URLs."
        ),
    },
    {
        "name": "Education",
        "research_style": (
            "physics education — relativity, quantum physics, and quantum effects in semiconductors"
        ),
        "subtopics": [
            "a fascinating aspect of Einstein's theories of relativity, spacetime, black holes, "
            "gravitational waves, or time dilation — a recent discovery, a classic concept explained "
            "in modern context, or a surprising consequence most people don't know",
            "a fascinating concept in quantum physics — superposition, entanglement, decoherence, "
            "quantum tunneling, or a recent experiment that reveals something counter-intuitive about "
            "the quantum world",
            "how quantum physics governs modern semiconductor technology — quantum tunneling in "
            "transistors, band theory, quantum dots, or the physical limits chipmakers are now running "
            "into",
        ],
        "discover_prompt": lambda d, subtopic: (
            f"Today is {d}. Pick a fascinating educational angle on {subtopic}. Return: the specific "
            "topic, the physics explained accessibly, 4–6 concrete facts or phenomena, and reference "
            "sources."
        ),
    },
    {
        "name": "Travel",
        "research_style": "travel and destinations",
        "discover_prompt": lambda d: (
            f"Today is {d}. Search the web for the most buzzworthy travel destination, hidden gem, or "
            "educational travel experience gaining attention right now. Focus on destinations with "
            "scientific, historical, or cultural depth worth learning about. Return: the specific "
            "destination or trend, why it's educational and interesting, 4–6 concrete facts, and URLs."
        ),
    },
    {
        "name": "History",
        "research_style": "history and historical analysis",
        "discover_prompt": lambda d: (
            f"Today is {d}. Pick a fascinating, lesser-known historical event, figure, or turning point "
            "that most people don't know about — something that genuinely changed the world or reveals "
            "a surprising truth about the past. Prefer stories with scientific or technological relevance. "
            "Return: the specific topic, why it's surprising or underappreciated, 4–6 concrete historical "
            "facts, and reference sources."
        ),
    },
]


def _pick_category() -> dict:
    """Weighted daily pick honoring priority order, unless TOPIC_MODE forces one."""
    mode = os.getenv("TOPIC_MODE", "").strip()
    if mode:
        named = next((c for c in CATEGORIES if c["name"].lower() == mode.lower()), None)
        if named:
            return named
    return random.choices(CATEGORIES, weights=_CATEGORY_WEIGHTS, k=1)[0]


def _web_search_gemini(prompt: str) -> str:
    """Gemini 2.5 Flash with Google Search grounding."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        ),
    )
    return response.text or ""


def _web_search_openai(prompt: str) -> str:
    """OpenAI web search — Responses API → search-preview → gpt-4o fallback."""
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
    try:
        response = client.responses.create(
            model="gpt-4o",
            tools=[{"type": "web_search_preview"}],
            input=prompt,
        )
        return response.output_text
    except Exception:
        pass
    try:
        response = client.chat.completions.create(
            model="gpt-4o-search-preview",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000,
        )
        return response.choices[0].message.content
    except Exception:
        print("⚠️  Live web search unavailable — using GPT-4o training knowledge")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert researcher with deep knowledge across technology, "
                        "science, history, and ideas."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=3000,
        )
        return response.choices[0].message.content


def _web_search(prompt: str) -> str:
    """Try Gemini Search grounding first; fall back to OpenAI web search."""
    if os.getenv("GEMINI_API_KEY"):
        try:
            result = _web_search_gemini(prompt)
            if result.strip():
                return result
        except Exception as exc:
            print(f"⚠️  Gemini search failed ({exc!r}) — falling back to OpenAI")
    return _web_search_openai(prompt)


# ── LangGraph nodes ──────────────────────────────────────────────────────────

def discover_trend_node(state: AgentState) -> dict:
    category = _pick_category()
    today = date.today().isoformat()
    mode_label = f" | mode: {os.getenv('TOPIC_MODE')}" if os.getenv("TOPIC_MODE") else ""

    subtopics = category.get("subtopics")
    if subtopics:
        subtopic = random.choice(subtopics)
        prompt = category["discover_prompt"](today, subtopic)
        print(f"🔍 Discovering trending topic [category: {category['name']}{mode_label}]")
        print(f"   ↳ angle: {subtopic[:90]}...")
    else:
        prompt = category["discover_prompt"](today)
        print(f"🔍 Discovering trending topic [category: {category['name']}{mode_label}]...")

    trend = _web_search(prompt)
    print(f"📌 Trend discovered: {trend[:120]}...")

    return {
        "category_name": category["name"],
        "category_pool": category["name"].lower(),
        "category_research_style": category["research_style"],
        "trend": trend,
    }


def deep_research_node(state: AgentState) -> dict:
    style = state["category_research_style"]
    snippet = state["trend"][:600]
    print(f"📚 Conducting deep research (3 parallel queries) [{state['category_name']}]...")

    prompts = {
        "technical": (
            f'Deep research on this {style} topic: "{snippet}"\n'
            "Search for: the underlying details, methodology, key findings, data, or engineering "
            "decisions. What makes this technically or factually novel? Include specific numbers, "
            "names, dates, and direct comparisons to prior work. What do primary sources say?"
        ),
        "reactions": (
            f'Community and expert reactions to: "{snippet}"\n'
            "Search for: what are researchers, practitioners, journalists, and the broader public "
            "saying? Look at Twitter/X, Reddit, Hacker News, news outlets, and expert blogs. "
            "What controversies or debates has it sparked? Include specific quoted opinions."
        ),
        "implications": (
            f'Real-world implications of: "{snippet}"\n'
            "Search for: which industries, communities, or fields are most impacted? How does this "
            "affect everyday people, professionals, or future development? What ethical, safety, or "
            "societal concerns does it raise? What are the next steps and the likely 6–12 month impact?"
        ),
    }

    results: dict = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(_web_search, prompt): key for key, prompt in prompts.items()}
        for future in futures:
            results[futures[future]] = future.result()

    print("✅ Research complete")
    return results
