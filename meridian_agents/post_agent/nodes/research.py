import os
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from openai import OpenAI

from ..state import AgentState

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

CATEGORIES = [
    {
        "name": "AI",
        "pool": "ai",
        "research_style": "AI and machine learning",
        "discover_prompt": lambda d: (
            f"Today is {d}. Search the web for the single most exciting or surprising AI / machine "
            "learning discovery, breakthrough, or development from the past 7 days. Consider: new model "
            "releases with surprising capabilities, landmark research papers, safety/alignment "
            "breakthroughs, or industry-shaking events. Pick ONE topic — the one with the most "
            "discussion, surprise value, or significance. Return: the exact topic name, why it's buzzing "
            "right now, 3–5 key facts with specific numbers/names, and 2–3 direct source URLs if available."
        ),
    },
    {
        "name": "Technology",
        "pool": "general",
        "research_style": "technology and engineering",
        "discover_prompt": lambda d: (
            f"Today is {d}. Search the web for the single most interesting technology development from "
            "the past 7 days — outside of pure AI/ML. Consider: major software releases, hardware "
            "breakthroughs, cybersecurity events, space tech, quantum computing, biotech, or big tech "
            "news. Pick ONE topic with the most buzz or real-world impact. Return: the exact topic, why "
            "it matters, 3–5 concrete facts, and 2–3 source URLs."
        ),
    },
    {
        "name": "Science",
        "pool": "general",
        "research_style": "science and research",
        "discover_prompt": lambda d: (
            f"Today is {d}. Search the web for the most fascinating scientific discovery or research "
            "finding published in the past 2 weeks. Consider: physics, astronomy, biology, climate "
            "science, medicine, or any field where researchers found something genuinely surprising. "
            "Pick ONE discovery. Return: the finding, the research team/institution, 3–5 key facts "
            "with numbers, and source URLs."
        ),
    },
    {
        "name": "History",
        "pool": "general",
        "research_style": "history and historical analysis",
        "discover_prompt": lambda d: (
            f"Today is {d}. Pick a fascinating, lesser-known historical event, figure, or turning point "
            "that most people don't know about — something that genuinely changed the world or reveals "
            "a surprising truth about the past. Return: the specific topic, why it's surprising or "
            "underappreciated, 3–5 concrete historical facts, and reference sources."
        ),
    },
    {
        "name": "Travel",
        "pool": "general",
        "research_style": "travel and destinations",
        "discover_prompt": lambda d: (
            f"Today is {d}. Search the web for the most buzzworthy travel destination, hidden gem, or "
            "travel experience gaining attention right now. Return: the specific destination or trend, "
            "why it's getting buzz, 3–5 concrete facts, and source URLs."
        ),
    },
    {
        "name": "Knowledge",
        "pool": "general",
        "research_style": "knowledge and ideas",
        "discover_prompt": lambda d: (
            f"Today is {d}. Pick one genuinely fascinating concept, phenomenon, or 'how does that "
            "actually work' question from any field — psychology, economics, mathematics, philosophy, "
            "linguistics, or everyday life. Choose something where the real answer surprises most "
            "people. Return: the specific concept, what makes it surprising, 3–5 concrete facts or "
            "examples, and reference sources."
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


def _web_search(prompt: str) -> str:
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
