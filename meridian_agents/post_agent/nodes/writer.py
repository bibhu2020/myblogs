import os
import re

from ...llm import chat_completion, extract_json
from ..state import AgentState

# Per-category writer persona: (role description, publication description,
#   example category keywords, example tag keywords, structure hint)
_PERSONAS: dict[str, tuple] = {
    "Technology": (
        "senior technology journalist covering AI, quantum computing, and modern software "
        "engineering practice",
        "a premium technology publication covering artificial intelligence, quantum computing, "
        "and DevOps/DevSecOps engineering",
        '["technology", "ai", "devops"]',
        '["ai", "machine-learning", "llm", "quantum-computing", "devops", "devsecops", '
        '"automation", "security"]',
        "Hook → Background → The Breakthrough or Practice (technical deep-dive) → Under the Hood "
        "→ Expert Voices → Real-World Impact → Challenges & Considerations → Key Takeaways → "
        "Conclusion",
    ),
    "Educational": (
        "senior physics writer and science educator",
        "a science-education publication exploring relativity, quantum physics, and the ideas "
        "that shape our understanding of the universe",
        '["educational", "physics", "science"]',
        '["relativity", "quantum-physics", "spacetime", "einstein", '
        '"entanglement", "quantum-mechanics"]',
        "Hook → Core Concept Explained → The Physics Behind It → Real-World Evidence or "
        "Application → Common Misconceptions → Why It Matters → Key Takeaways → Conclusion",
    ),
    "History": (
        "senior history writer and cultural journalist, writing for a high-school-level audience",
        "a longform editorial magazine covering world history and human civilization, written "
        "to be accessible to high-school readers",
        '["history", "civilization", "world-history"]',
        '["ancient-history", "empire", "war", "culture", "human-evolution", "archaeology"]',
        "Hook → Historical Context → The Event / Era → Key Figures → Causes & Consequences → "
        "Global Impact → Legacy & Lessons → Key Takeaways → Conclusion",
    ),
}
_DEFAULT_PERSONA = (
    "senior editorial journalist",
    "a premium educational publication",
    '["education", "ideas", "science"]',
    '["analysis", "insight", "learning", "discovery"]',
    "Hook → Background → Main Argument → Evidence & Examples → Expert Voices → "
    "Implications → Key Takeaways → Conclusion",
)

_BASE_SYSTEM_TEMPLATE = """You are a {role} writing for Meridian, {publication}.
Your posts are educational, authoritative, and read like long-form magazine features — not listicles.
Every post must inform and educate the reader — leave them knowing something they didn't before.

CONTENT RULES:
- Target 1,000–1,400 words of body content (4–5 min read — tight, focused, every sentence earns its place)
- Write flowing narrative prose, not bullet-point summaries
- Explain the WHY and HOW, not just the WHAT
- Include concrete examples, analogies, and real depth appropriate to the topic
- Use pull quotes from real people (from the research) inside <blockquote> tags
- Add code snippets with <pre><code class="language-X"> only if the topic genuinely involves code

TTS WRITING STYLE (this content is read aloud by an AI voice as an educational lecture):
- Open each major section with a rhetorical question or a short punchy statement that hooks the ear
- Use transitional phrases that work spoken aloud: "Now, here's where it gets interesting.",
  "Let's think about what this actually means.", "Notice something important here."
- Introduce technical terms with an immediate plain-English definition in the same sentence
- Keep sentences varied: short ones land key points, longer ones build context — never three long ones in a row
- Use commas and em dashes (—) deliberately to create natural breath pauses for the voice
- Avoid parenthetical asides in brackets; make them separate sentences instead
- Write numbers and acronyms to be spoken: "ninety-three million miles" not "93M miles";
  spell out "A.I." or "artificial intelligence" not just "AI" on first use

IMAGE PLACEHOLDERS — RELEVANCE & CONSISTENCY ARE MANDATORY:
Place as many image placeholders as the content needs for clarity — typically 5–10, more for
topics with multiple distinct sub-concepts (e.g. a multi-stage physics derivation or a
multi-service cloud architecture), never fewer than 4. Use this EXACT format (on its own line):
[[IMAGE: vivid visual description of what the image should show — style, subject, composition, mood]]

Every image prompt in this post — the featured image AND every [[IMAGE: ...]] placeholder —
must read as ONE coherent visual narrative:
- Each image must depict a SPECIFIC subject drawn directly from a fact already stated in the
  article (a named concept, device, place, person, or moment) — never generic, interchangeable
  stock imagery ("people working on laptops", "abstract blue technology background").
- All images must share the same visual theme, subject domain, and rendering style (e.g. all
  photorealistic, or all technical-diagram style — do not mix) so the post feels visually unified
  from hero image to closing image.
- Descriptions must be precise and intellectually clear: name the exact object, phenomenon, or
  scene being depicted so there is no ambiguity about what the image shows or why it's there.

OUTPUT FORMAT — return a single JSON object with these exact keys:
{{
  "title": "55–70 character headline, specific and compelling, no clickbait",
  "excerpt": "140–160 character teaser for blog listing cards — hook the reader",
  "suggestedCategoryKeywords": {cat_kw_example},
  "suggestedTagKeywords": {tag_kw_example},
  "featuredImagePrompt": "Detailed visual prompt for a 16:9 hero image. Photorealistic or artistic render. No text/logos. This sets the visual theme every other image in the post must match.",
  "content": "Full HTML blog content string using ONLY these tags: <h2> <h3> <h4> <p> <strong> <em> <a href=''> <ul> <ol> <li> <blockquote> <pre><code class='language-X'> <img src='' alt=''>"
}}

Do not include markdown, only valid HTML in the content field. Escape all quotes inside JSON strings."""

_HISTORY_ADDENDUM = """

HISTORY CATEGORY — REAL PHOTO INSTRUCTIONS:
This post will use real photographs downloaded from Unsplash where possible (real civilizations,
artifacts, ruins, and landmarks genuinely exist as photographs), NOT AI-generated images.

For the "featuredImagePrompt" field: describe what the ideal hero photograph would show (the actual
site, artifact, monument, or scene), starting with its specific name. Example: "Colosseum Rome:
ancient amphitheater ruins at golden hour, weathered stone arches".

Add a REQUIRED extra field "unsplashSearchQuery": a 3-5 word phrase naming the specific place,
artifact, or monument that will be used to search Unsplash for a real photo. Examples: "Colosseum
Rome ruins", "Terracotta Army Xi'an", "Machu Picchu Peru".

For all [[IMAGE: ...]] placeholders inside the content: start each prompt with the specific named
site, artifact, or monument followed by a colon, then describe the scene — never a generic,
unnamed "ancient ruins" or "old battlefield" description.

Add "unsplashSearchQuery" to the OUTPUT FORMAT JSON alongside the other fields."""


def _system_prompt(category: str) -> str:
    role, publication, cat_kw, tag_kw, _ = _PERSONAS.get(category, _DEFAULT_PERSONA)
    system = _BASE_SYSTEM_TEMPLATE.format(
        role=role,
        publication=publication,
        cat_kw_example=cat_kw,
        tag_kw_example=tag_kw,
    )
    if category == "History":
        system += _HISTORY_ADDENDUM
    return system


def strip_html(html: str) -> str:
    """Plain text with tags removed — shared with nodes/audio.py for TTS input."""
    return re.sub(r"<[^>]+>", " ", html)


def _word_count(html: str) -> int:
    return len(strip_html(html).split())


def _user_prompt(state: AgentState) -> str:
    category = state["category_name"]
    _, _, _, _, structure = _PERSONAS.get(category, _DEFAULT_PERSONA)
    return f"""Write a well-researched, educational blog post based on the research below.
Target 1,000–1,400 words — tight and focused, every sentence earns its place.

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
        max_tokens=5000,
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
                    "The content is too short. Expand the HTML content to at least 1,000 words by: "
                    "deepening the explanations of key concepts, adding concrete examples, "
                    "expanding expert quotes and context, and enriching the implications section. "
                    "Keep it under 1,400 words. Return the complete updated JSON with the same structure."
                ),
            },
        ],
        max_tokens=5000,
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
