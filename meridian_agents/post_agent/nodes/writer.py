import os
import re

from ...llm import chat_completion, extract_json
from ..state import AgentState

# Per-category writer persona: (role description, publication description,
#   example category keywords, example tag keywords, structure hint)
_PERSONAS: dict[str, tuple] = {
    "AI/ML": (
        "senior AI and machine learning journalist",
        "a premium AI research and technology publication",
        '["artificial-intelligence", "machine-learning", "neural-network"]',
        '["llm", "transformer", "openai", "deepmind", "reinforcement-learning", "generative-ai"]',
        "Hook → Background → The Breakthrough → Under the Hood (technical deep-dive) → "
        "Expert Voices → Implications → The Bigger Picture → Key Takeaways → Conclusion",
    ),
    "Quantum": (
        "senior quantum physics science journalist",
        "a rigorous popular-science magazine covering quantum mechanics and quantum computing",
        '["quantum", "quantum-computing", "quantum-mechanics"]',
        '["entanglement", "superposition", "qubit", "decoherence", "photoelectric-effect", "wave-function"]',
        "Hook → Background → The Physics → Experiment / Breakthrough → Expert Reactions → "
        "Real-World Implications → The Bigger Picture → Key Takeaways → Conclusion",
    ),
    "Relativity": (
        "senior physics and cosmology science journalist",
        "a popular-science magazine covering Einstein's theories, spacetime, and the cosmos",
        '["relativity", "spacetime", "einstein"]',
        '["time-dilation", "black-hole", "gravitational-waves", "special-relativity", "general-relativity", "speed-of-light"]',
        "Hook → Background → The Physics / Discovery → Thought Experiment → Expert Reactions → "
        "Implications → The Bigger Picture → Key Takeaways → Conclusion",
    ),
    "Travel": (
        "senior science travel writer",
        "a premium travel publication covering the world's most scientifically fascinating destinations",
        '["travel", "destinations", "science-tourism"]',
        '["cern", "observatory", "physics-lab", "nature", "photography", "adventure"]',
        "Hook → Destination Overview → Getting There → What to See & Experience → The Science Behind It → "
        "Practical Tips → When to Go → Key Takeaways → Conclusion",
    ),
    "Educational": (
        "senior science educator and explainer journalist",
        "a visual, accessible popular-science magazine that makes complex physics beautiful and clear",
        '["physics", "science-education", "explainer"]',
        '["blackbody-radiation", "ultraviolet-catastrophe", "photoelectric-effect", "double-slit", "quantum-tunneling"]',
        "Hook → The Puzzle (what puzzled scientists) → The Concept Explained Simply → "
        "Analogy & Visualization → The Maths (gentle) → Real-World Applications → Key Takeaways → Conclusion",
    ),
    "History": (
        "senior history of science writer",
        "a longform magazine covering the history of physics, mathematics, and the scientists who changed everything",
        '["history-of-science", "physics-history", "scientific-revolution"]',
        '["planck", "einstein", "bohr", "heisenberg", "curie", "feynman", "manhattan-project"]',
        "Hook → Historical Context → The Discovery / Event → Key Figures → Scientific Impact → "
        "Legacy & Modern Relevance → Key Takeaways → Conclusion",
    ),
}
_DEFAULT_PERSONA = (
    "senior editorial journalist",
    "a premium multi-topic publication",
    '["editorial", "culture", "society"]',
    '["trends", "analysis", "insight", "society", "ideas"]',
    "Hook → Background → Main Argument → Evidence & Examples → Expert Voices → "
    "Implications → Key Takeaways → Conclusion",
)

_BASE_SYSTEM_TEMPLATE = """You are a {role} writing for Meridian, {publication}.
Your posts are detailed, authoritative, and read like long-form magazine features — not listicles.

CONTENT RULES:
- 1,500–2,000 words of body content (target a 7–10 min read — concise and punchy)
- Write flowing narrative prose, not bullet-point summaries
- Explain the WHY and HOW, not just the WHAT
- Include concrete examples, analogies, and real depth appropriate to the topic
- Use pull quotes from real people (from the research) inside <blockquote> tags
- Add code snippets with <pre><code class="language-X"> only if the topic genuinely involves code

IMAGE PLACEHOLDERS:
Place 4–6 image placeholders throughout using this EXACT format (on its own line):
[[IMAGE: vivid visual description of what the image should show — style, subject, composition, mood]]

OUTPUT FORMAT — return a single JSON object with these exact keys:
{{
  "title": "55–70 character headline, specific and compelling, no clickbait",
  "excerpt": "140–160 character teaser for blog listing cards — hook the reader",
  "suggestedCategoryKeywords": {cat_kw_example},
  "suggestedTagKeywords": {tag_kw_example},
  "featuredImagePrompt": "Detailed visual prompt for a 16:9 hero image. Photorealistic or artistic render. No text/logos.",
  "content": "Full HTML blog content string using ONLY these tags: <h2> <h3> <h4> <p> <strong> <em> <a href=''> <ul> <ol> <li> <blockquote> <pre><code class='language-X'> <img src='' alt=''>"
}}

Do not include markdown, only valid HTML in the content field. Escape all quotes inside JSON strings."""

_TRAVEL_ADDENDUM = """

TRAVEL CATEGORY — REAL PHOTO INSTRUCTIONS:
This post will use real photographs downloaded from Unsplash, NOT AI-generated images.

For the "featuredImagePrompt" field: describe what the ideal hero photograph would show (the actual
place, landmark, or scene), starting with the destination name. Example: "Santorini Greece:
white-washed cycladic buildings with blue domes overlooking the Aegean Sea at sunset, aerial view".

Add a REQUIRED extra field "unsplashSearchQuery": a 3-5 word location phrase that will be used to
search Unsplash for a real photo. Name the specific place and country. Examples: "Santorini Greece
sunset", "Kyoto Japan cherry blossoms".

For all [[IMAGE: ...]] placeholders inside the content: start each prompt with the specific location
name followed by a colon, then describe the scene.

Add "unsplashSearchQuery" to the OUTPUT FORMAT JSON alongside the other fields."""


def _system_prompt(category: str) -> str:
    role, publication, cat_kw, tag_kw, _ = _PERSONAS.get(category, _DEFAULT_PERSONA)
    system = _BASE_SYSTEM_TEMPLATE.format(
        role=role,
        publication=publication,
        cat_kw_example=cat_kw,
        tag_kw_example=tag_kw,
    )
    if category == "Travel":
        system += _TRAVEL_ADDENDUM
    return system


def _word_count(html: str) -> int:
    return len(re.sub(r"<[^>]+>", " ", html).split())


def _user_prompt(state: AgentState) -> str:
    category = state["category_name"]
    _, _, _, _, structure = _PERSONAS.get(category, _DEFAULT_PERSONA)
    return f"""Write a comprehensive, deeply researched blog post based on the research below.
The post must be 1,500–2,000 words — tight, engaging, and complete. No filler; every sentence earns its place.

CATEGORY: {category}
Ensure suggestedCategoryKeywords and suggestedTagKeywords reflect the **{category}** topic,
not unrelated domains (e.g. do NOT use tech/code keywords for a {category} post).

## TOPIC & KEY FACTS
{state['trend']}

## DEPTH & DETAIL
{state['technical']}

## EXPERT OPINIONS & COMMUNITY REACTION
{state['reactions']}

## REAL-WORLD IMPLICATIONS
{state['implications']}

Recommended structure (adapt as needed): {structure}"""


# ── LangGraph nodes ──────────────────────────────────────────────────────────

def write_post_node(state: AgentState) -> dict:
    print("✍️  Writing blog post (this takes ~60s)...")
    text, model = chat_completion(
        messages=[
            {"role": "system", "content": _system_prompt(state["category_name"])},
            {"role": "user", "content": _user_prompt(state)},
        ],
        max_tokens=10000,
        temperature=0.8,
    )
    post = extract_json(text)
    wc = _word_count(post["content"])
    print(f"📊 Draft word count: {wc}")

    return {
        "post_title": post["title"],
        "post_excerpt": post["excerpt"],
        "post_content": post["content"],
        "post_featured_image_prompt": post["featuredImagePrompt"],
        "post_category_keywords": post.get("suggestedCategoryKeywords", []),
        "post_tag_keywords": post.get("suggestedTagKeywords", []),
        "post_unsplash_query": post.get("unsplashSearchQuery"),
        "word_count": wc,
    }


def expand_post_node(state: AgentState) -> dict:
    print("📝 Expanding post to meet length requirements...")
    import json as _json
    current_json = _json.dumps({
        "title": state["post_title"],
        "excerpt": state["post_excerpt"],
        "featuredImagePrompt": state["post_featured_image_prompt"],
        "suggestedCategoryKeywords": state["post_category_keywords"],
        "suggestedTagKeywords": state["post_tag_keywords"],
        "content": state["post_content"],
    })
    text, model = chat_completion(
        messages=[
            {"role": "system", "content": _system_prompt(state["category_name"])},
            {"role": "user", "content": _user_prompt(state)},
            {"role": "assistant", "content": current_json},
            {
                "role": "user",
                "content": (
                    "The content is too short. Expand the HTML content to 1,500–2,000 words by: "
                    "adding more depth to each section, deepening key arguments, "
                    "adding relevant examples and context. Keep it tight — no padding. "
                    "Return the complete updated JSON with the same structure."
                ),
            },
        ],
        max_tokens=10000,
        temperature=0.7,
    )
    post = extract_json(text)
    wc = _word_count(post["content"])
    print(f"📊 Final word count: {wc}")

    return {
        "post_title": post["title"],
        "post_excerpt": post["excerpt"],
        "post_content": post["content"],
        "post_featured_image_prompt": post["featuredImagePrompt"],
        "post_category_keywords": post.get("suggestedCategoryKeywords", state["post_category_keywords"]),
        "post_tag_keywords": post.get("suggestedTagKeywords", state["post_tag_keywords"]),
        "post_unsplash_query": post.get("unsplashSearchQuery", state.get("post_unsplash_query")),
        "word_count": wc,
    }
