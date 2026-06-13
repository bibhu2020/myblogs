import json
import os
import re

from openai import OpenAI

from ..state import AgentState

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

_BASE_SYSTEM = """You are a senior technology journalist writing for Meridian, a premium AI and technology blog.
Your posts are detailed, authoritative, and read like long-form magazine features — not listicles.

CONTENT RULES:
- Minimum 3,000 words of body content (aim for 3,500–4,500 for a 12-15 min read)
- Write flowing narrative prose, not bullet-point summaries
- Explain the WHY and HOW, not just the WHAT
- Include concrete examples, analogies, and real technical depth
- Use pull quotes from real people (from the research) inside <blockquote> tags
- Add code snippets with <pre><code class="language-X"> where illustrative

IMAGE PLACEHOLDERS:
Place 4–6 image placeholders throughout using this EXACT format (on its own line):
[[IMAGE: detailed DALL-E 3 prompt — be specific about style, content, composition, colors]]

OUTPUT FORMAT — return a single JSON object with these exact keys:
{
  "title": "55–70 character headline, specific and compelling, no clickbait",
  "excerpt": "140–160 character teaser for blog listing cards — hook the reader",
  "suggestedCategoryKeywords": ["ai", "machine-learning", "research"],
  "suggestedTagKeywords": ["openai", "llm", "transformer", "neural-network", "gpt"],
  "featuredImagePrompt": "Detailed DALL-E 3 prompt for a 16:9 hero image. Photorealistic or artistic render. No text/logos.",
  "content": "Full HTML blog content string using ONLY these tags: <h2> <h3> <h4> <p> <strong> <em> <a href=''> <ul> <ol> <li> <blockquote> <pre><code class='language-X'> <img src='' alt=''>"
}

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
    return _BASE_SYSTEM + (_TRAVEL_ADDENDUM if category == "Travel" else "")


def _word_count(html: str) -> int:
    return len(re.sub(r"<[^>]+>", " ", html).split())


def _user_prompt(state: AgentState) -> str:
    return f"""Write a comprehensive, deeply researched blog post based on the research below.
The post must be AT LEAST 3,000 words — do not cut corners. This is long-form editorial journalism.

## TOPIC & KEY FACTS
{state['trend']}

## TECHNICAL DEPTH
{state['technical']}

## EXPERT OPINIONS & COMMUNITY REACTION
{state['reactions']}

## REAL-WORLD IMPLICATIONS
{state['implications']}

Structure suggestion (adapt as needed):
1. Hook — Open with the most surprising or dramatic element
2. Background — What was the state of the art before this?
3. The Breakthrough — What exactly happened / was built / was discovered?
4. Under the Hood — Technical deep-dive (architecture, methodology, results)
5. Expert Voices — Reactions from the community (use real quotes from the research)
6. Implications — Who benefits? Who's disrupted? What changes?
7. The Bigger Picture — Where does this fit in the arc of progress?
8. Key Takeaways — 4–6 bullet points in a <ul>
9. Conclusion — Forward-looking synthesis"""


# ── LangGraph nodes ──────────────────────────────────────────────────────────

def write_post_node(state: AgentState) -> dict:
    print("✍️  Writing blog post (this takes ~60s)...")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _system_prompt(state["category_name"])},
            {"role": "user", "content": _user_prompt(state)},
        ],
        response_format={"type": "json_object"},
        max_tokens=10000,
        temperature=0.8,
    )
    post = json.loads(response.choices[0].message.content)
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
    current_json = json.dumps({
        "title": state["post_title"],
        "excerpt": state["post_excerpt"],
        "featuredImagePrompt": state["post_featured_image_prompt"],
        "suggestedCategoryKeywords": state["post_category_keywords"],
        "suggestedTagKeywords": state["post_tag_keywords"],
        "content": state["post_content"],
    })
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _system_prompt(state["category_name"])},
            {"role": "user", "content": _user_prompt(state)},
            {"role": "assistant", "content": current_json},
            {
                "role": "user",
                "content": (
                    "The content is too short. Expand the HTML content to at least 3,000 words by: "
                    "adding more paragraphs to each section, deepening the technical explanation, "
                    "adding more expert quotes and context, and expanding the implications section. "
                    "Return the complete updated JSON with the same structure."
                ),
            },
        ],
        response_format={"type": "json_object"},
        max_tokens=10000,
        temperature=0.7,
    )
    post = json.loads(response.choices[0].message.content)
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
