import os
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from ..state import AgentState

CATEGORIES = [
    {
        "name": "AI & Machine Learning",
        "pool": "ai",
        "research_style": "artificial intelligence and machine learning",
        "discover_prompt": lambda d: (
            f"Today is {d}. Search the web for the single most exciting or surprising AI / machine "
            "learning discovery, breakthrough, or development from the past 7 days. Consider: new model "
            "releases with surprising capabilities, landmark research papers, safety/alignment "
            "breakthroughs, or industry-shaking events. Focus on educational depth — explain WHY it "
            "matters and HOW it works. Return: the exact topic, why it's significant, 4–6 key technical "
            "facts with specific numbers/names, and 2–3 direct source URLs."
        ),
    },
    {
        "name": "Quantum Computing",
        "pool": "science",
        "research_style": "quantum computing and quantum physics",
        "discover_prompt": lambda d: (
            f"Today is {d}. Search the web for the most interesting recent development in quantum "
            "computing, quantum cryptography, or quantum physics (past 3 months). Consider: new qubit "
            "milestones, error-correction breakthroughs, quantum supremacy experiments, or real-world "
            "quantum applications. Return: the specific development, the physics behind it (superposition, "
            "entanglement, decoherence), 4–6 concrete facts, and source URLs."
        ),
    },
    {
        "name": "Relativity & Spacetime",
        "pool": "science",
        "research_style": "relativity, spacetime, and cosmology",
        "discover_prompt": lambda d: (
            f"Today is {d}. Pick a fascinating topic related to Einstein's theories of relativity, "
            "spacetime, black holes, gravitational waves, time dilation, or cosmology. This can be a "
            "recent discovery, a classic concept explained in modern context, or a surprising consequence "
            "of relativity that most people don't know. Return: the specific topic, the physics "
            "explained accessibly, 4–6 concrete facts or phenomena, and reference sources."
        ),
    },
    {
        "name": "History",
        "pool": "general",
        "research_style": "history and historical analysis",
        "discover_prompt": lambda d: (
            f"Today is {d}. Pick a fascinating, lesser-known historical event, figure, or turning point "
            "that most people don't know about — something that genuinely changed the world or reveals "
            "a surprising truth about the past. Prefer stories with scientific or technological relevance. "
            "Return: the specific topic, why it's surprising or underappreciated, 4–6 concrete historical "
            "facts, and reference sources."
        ),
    },
    {
        "name": "Travel",
        "pool": "general",
        "research_style": "travel and destinations",
        "discover_prompt": lambda d: (
            f"Today is {d}. Search the web for the most buzzworthy travel destination, hidden gem, or "
            "educational travel experience gaining attention right now. Focus on destinations with "
            "scientific, historical, or cultural depth worth learning about. Return: the specific "
            "destination or trend, why it's educational and interesting, 4–6 concrete facts, and URLs."
        ),
    },
    {
        "name": "Educational",
        "pool": "general",
        "research_style": "educational concepts, ideas, and mental models",
        "discover_prompt": lambda d: (
            f"Today is {d}. Pick one genuinely fascinating educational concept, scientific phenomenon, "
            "or 'how does that actually work' question — from psychology, economics, mathematics, "
            "philosophy, linguistics, biology, or everyday life. Choose something where the real answer "
            "surprises most people and has deep educational value. Return: the specific concept, what "
            "makes it surprising, 4–6 concrete facts or examples, and reference sources."
        ),
    },
]


def _pick_category() -> dict:
    mode = os.getenv("TOPIC_MODE", "").strip()
    if not mode:
        return random.choice(CATEGORIES)
    if mode == "ai_trending":
        return next(c for c in CATEGORIES if c["pool"] == "ai")
    if mode == "random_general":
        pool = [c for c in CATEGORIES if c["pool"] == "general"]
        return random.choice(pool)
    named = next((c for c in CATEGORIES if c["name"].lower() == mode.lower()), None)
    if named:
        return named
    return random.choice(CATEGORIES)


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
    print(f"🔍 Discovering trending topic [category: {category['name']}{mode_label}]...")

    trend = _web_search(category["discover_prompt"](today))
    print(f"📌 Trend discovered: {trend[:120]}...")

    return {
        "category_name": category["name"],
        "category_pool": category["pool"],
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
