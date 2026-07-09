import os
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from ..state import AgentState

# Priority order: Technology > Educational > History.
# Weighted daily pick so Technology dominates, Educational stays close behind (the
# curriculum needs regular posts or the series goes stale), and History is the lightest share.
_CATEGORY_WEIGHTS = [40, 35, 25]

# Fundamental → advanced topic ladders for the Educational category's 3 physics tracks.
# resolve_curriculum_node (nodes/curriculum.py) walks each list in order — topic 0 must be
# published before topic 1 becomes eligible — round-robining across tracks so no single
# subject dominates for weeks. Never edit list ORDER without considering already-published
# seriesIndex values; only append to the end is safe once posts exist.
EDUCATIONAL_TRACKS: dict[str, list[str]] = {
    "general-relativity": [
        "The equivalence principle — why gravity and acceleration are indistinguishable",
        "Curved spacetime and the metric — how mass tells spacetime how to bend",
        "Geodesics — why orbits are just objects going 'straight' through curved spacetime",
        "Gravitational time dilation — why clocks run slower near massive objects",
        "Black holes and event horizons — the point of no return",
        "Gravitational waves — ripples in spacetime and how we detected them",
        "Cosmological implications — the FLRW metric and the expanding universe",
    ],
    "special-relativity": [
        "The postulates of special relativity and the speed-of-light limit",
        "The relativity of simultaneity — why 'at the same time' depends on your frame",
        "Time dilation and length contraction — moving clocks run slow, moving rods shrink",
        "The Lorentz transformations — the mathematics tying space and time together",
        "Mass-energy equivalence — deriving and understanding E = mc²",
        "Spacetime diagrams and the light cone — visualizing cause and effect",
        "Relativistic momentum and energy in particle physics",
    ],
    "quantum-physics": [
        "Wave-particle duality — light and matter behaving as both",
        "The wavefunction and the Schrödinger equation",
        "Superposition — what it really means for a system to be in two states at once",
        "Quantum tunneling — how particles pass through barriers they 'shouldn't'",
        "Entanglement — spooky action at a distance, explained rigorously",
        "The uncertainty principle — the fundamental limit on what we can know",
        "Decoherence and measurement — why the quantum world looks classical to us",
        "Quantum computing basics — qubits, gates, and why superposition matters for computing",
    ],
}
TRACK_LABELS = {
    "general-relativity": "General Relativity",
    "special-relativity": "Special Relativity",
    "quantum-physics": "Quantum Physics",
}

CATEGORIES = [
    {
        "name": "Technology",
        "research_style": (
            "Azure cloud engineering, DevOps/DevSecOps practice, generative AI, and LLM "
            "fine-tuning"
        ),
        # One of these is chosen at random each run — every Technology post is always
        # anchored to one of the 4 required areas below (2 angles each for variety).
        "subtopics": [
            "a specific Azure cloud capability worth understanding deeply — Azure Kubernetes "
            "Service (AKS), Azure AI Foundry, Azure networking/security, or a recent Azure "
            "platform announcement",
            "how modern teams design and operate on Azure — landing zones, the Well-Architected "
            "Framework, or cost/performance tradeoffs in real deployments",
            "a genuinely useful modern DevOps practice, tool, or cultural shift worth "
            "understanding deeply — CI/CD design, infrastructure as code, observability, or "
            "platform engineering",
            "a genuinely useful modern DevSecOps practice — supply-chain security, shift-left "
            "vulnerability detection, or automated security review in the delivery pipeline",
            "the single most exciting or surprising recent generative AI development from the "
            "past 7 days — a new model release, landmark research paper, or capability "
            "breakthrough",
            "how generative AI is actually being used in production today — agentic workflows, "
            "retrieval-augmented generation, or multimodal applications",
            "a core LLM fine-tuning technique explained clearly — LoRA/QLoRA, RLHF/DPO, or "
            "instruction tuning, with the tradeoffs that matter in practice",
            "how to think about dataset curation and evaluation when fine-tuning an LLM for a "
            "specific task or domain",
        ],
        "discover_prompt": lambda d, subtopic: (
            f"Today is {d}. Search the web and report on {subtopic}. Focus on educational depth — "
            "explain WHY it matters and HOW it works. Return: the exact topic, why it's "
            "significant, 4–6 key technical facts with specific numbers/names, and 2–3 direct "
            "source URLs."
        ),
    },
    {
        "name": "Educational",
        "research_style": (
            "physics education — general relativity, special relativity, and quantum physics"
        ),
        # No "subtopics" here — Educational posts follow the ordered EDUCATIONAL_TRACKS
        # curriculum instead of a random pick. See resolve_curriculum_node in nodes/curriculum.py.
        "tracks": EDUCATIONAL_TRACKS,
        "discover_prompt": lambda d, track_label, topic: (
            f"Today is {d}. Research this specific {track_label} concept for a physics-education "
            f'article: "{topic}". Explain it accessibly but rigorously — the intuition, the '
            "mathematics or mechanism behind it, and a concrete real-world example or experiment "
            "that demonstrates it. Return: the specific topic, 4–6 concrete facts or phenomena, "
            "and reference sources."
        ),
    },
    {
        "name": "History",
        "research_style": "world history at a high-school-accessible level",
        "subtopics": [
            "a pivotal ancient or classical civilization (Rome, Egypt, the Indus Valley, the "
            "Maya, Mesopotamia, ancient China) — a specific institution, achievement, or turning "
            "point in its rise or fall",
            "a war or conflict with lasting world-historical consequences — its causes, a key "
            "turning point, and its long-term impact",
            "an aspect of human culture across history — religion, art, trade routes, "
            "philosophy, or how ideas spread between civilizations",
            "human evolution and prehistory — hominin species, migration out of Africa, the "
            "agricultural revolution, or the origins of early civilization",
        ],
        "discover_prompt": lambda d, subtopic: (
            f"Today is {d}. Pick a fascinating, high-school-level angle on {subtopic}. Keep it "
            "accessible and jargon-free while staying factually rigorous. Return: the specific "
            "topic, why it's significant or underappreciated, 4–6 concrete historical facts, and "
            "reference sources."
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

    if category.get("tracks"):
        # Educational — follow the curriculum. resolve_curriculum_node runs earlier in the
        # graph and always stashes the next topic in state, regardless of which category the
        # weighted pick above lands on; fall back to track 0 / topic 0 only if that lookup
        # failed (e.g. API unreachable) so a run never crashes for lack of curriculum state.
        series_key = state.get("series_key") or "general-relativity"
        series_topic = state.get("series_topic") or EDUCATIONAL_TRACKS[series_key][0]
        track_label = TRACK_LABELS.get(series_key, series_key)
        prompt = category["discover_prompt"](today, track_label, series_topic)
        print(f"🔍 Discovering trending topic [category: {category['name']}{mode_label}]")
        print(f"   ↳ curriculum: {track_label} — {series_topic}")
    else:
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
