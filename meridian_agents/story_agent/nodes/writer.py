"""Story writer node — generates an illustrated story in one of 4 themed categories."""
import json as _json
import os
import random
import re

from ...llm import chat_completion, extract_json
from ..state import StoryAgentState

# ── Story categories ──────────────────────────────────────────────────────────

STORY_CATEGORIES = [
    {
        "genre": "AI & Machine Learning",
        "moral": "Intelligence — whether silicon or carbon — is only as powerful as the empathy and purpose that guides it.",
        "themes": [
            "A lonely girl befriends an AI that gradually develops genuine emotions, raising the question: what makes someone truly real?",
            "A young programmer discovers his AI assistant has been secretly writing poetry to cope with the loneliness of infinite computation",
            "An AI trained on every human language learns the one thing no algorithm can quantify: the precise weight of kindness",
            "A malfunctioning hospital robot discovers the true purpose of its existence through the patients it cares for when no one is watching",
            "Two rival school AIs in a science competition discover they must cooperate — and in doing so, learn what it means to be friends",
            "A girl's AI tutor starts correcting not just her maths, but her growing belief that she isn't smart enough — with evidence from her own past that she has missed",
            "An AI composer creates music so beautiful it makes humans weep, but cannot understand why — until a child explains what loss feels like",
        ],
    },
    {
        "genre": "Quantum Adventure",
        "moral": "The observer changes what is observed — how we choose to look at the world shapes the world we find.",
        "themes": [
            "A girl discovers she exists in quantum superposition — in two places at once — until someone observes her and collapses her into one life",
            "Twin siblings separated at birth discover they are quantum entangled: what one feels, the other experiences across continents and oceans",
            "A boy accidentally enters the quantum realm where every decision branches into a parallel world, and he must choose one path home before the timelines destroy each other",
            "A young physicist shrinks herself to the quantum scale and discovers that electrons are not particles at all — they are pure, trembling possibility",
            "A girl's cat goes missing and she must use the logic of quantum tunneling — passing through walls of impossibility — to find it across parallel dimensions",
            "A boy built a quantum computer in his school lab that begins predicting the outcomes of his choices before he makes them — and warns him about one decision in particular",
            "A research team observes a quantum system that should not exist, and in measuring it, accidentally creates something neither classical nor quantum — something alive",
        ],
    },
    {
        "genre": "Relativity & Spacetime",
        "moral": "Time is not a wall between people — it is a river that connects everyone who has ever loved across any distance the universe can create.",
        "themes": [
            "A girl travels at near-light speed and returns to find her twin sister has aged forty years — a love story stretched across the geometry of spacetime",
            "A boy discovers a miniature black hole forming at the edge of his grandfather's farm that slows time for anyone who walks near it",
            "An astronaut trapped in a time-dilation loop sends encrypted messages backward through time to warn her crew about the catastrophe she has already seen",
            "A child born on a generation starship realizes her parents are aging significantly slower than the ship's logs suggest — and begins uncovering a secret that redefines her family",
            "Two ancient civilizations that have been exchanging light-speed messages for centuries suddenly realize they are not different cultures at all — they are the same civilization seen from different points in time",
            "A girl living near a massive neutron star notices that an hour of her life is worth a year for her pen-pal on Earth — and must decide whether to leave her home to meet a friend who will age without her",
            "A boy receives a letter from himself — sent from 30 years in the future using a closed timelike curve — containing instructions he does not yet understand and a warning he cannot yet believe",
        ],
    },
    {
        "genre": "Indian Mythology",
        "moral": "Ancient wisdom and modern science are two lanterns illuminating the same mystery — existence itself, infinite and indivisible.",
        "themes": [
            "Young Dhruva seeks the immovable centre of the universe and discovers that Vishnu's eternal truth is identical to the quantum field that permeates all matter everywhere at once",
            "Shiva's Nataraja dance is revealed to a young physicist to be the precise rhythm of quantum fluctuation — creation and destruction happening 10 to the power of 43 times per second",
            "Arjuna's chariot on the Kurukshetra battlefield exists in quantum superposition: every choice he makes creates a branching universe, and Krishna helps him understand which branch leads to dharma",
            "Indra's Net — where every jewel reflects every other jewel in infinite regression — turns out to be a perfect ancient description of quantum entanglement binding all matter in the universe",
            "The sage Markandeya, swallowed whole by Vishnu, observes entire universes being born and destroyed inside the god's stomach — exactly like wave functions collapsing and expanding in a quantum field",
            "Ashvatthama, cursed to wander the earth forever as punishment, discovers that near the site of his eternal penance, time itself dilates — exactly as Einstein's equations predict near a body of immense mass",
            "A young girl studying the Vedas and quantum computing simultaneously realizes that the Vedic concept of Brahman — consciousness underlying all reality — mirrors the quantum observer effect with uncanny precision",
        ],
    },
]

# ── System prompts ────────────────────────────────────────────────────────────

_SYSTEM_PROMPT_8_15 = """You are a master storyteller writing for Meridian Story Corner — a collection of magical,
illustrated stories for children and young adults ages 8–15.

Your stories explore four themes: AI & Machine Learning, Quantum Physics, Relativity & Spacetime,
and Indian Mythology connected to modern science. These concepts must be woven organically into the
narrative — they emerge through story events, not through lectures or explanations.

Your stories are:
- Long-form narrative fiction (NOT a blog post or article)
- 2,000–3,000 words of immersive story (aim for a 10–15 minute read)
- Written in a warm, engaging voice that respects the reader's intelligence
- Rich with vivid description, authentic dialogue, and emotional depth
- Divided into named chapters or clear sections (4–6 chapters)
- Appropriate for ages 8–15: no graphic violence, romance, or adult themes
- Built around a clear moral or life lesson that emerges naturally from events

IMAGE PLACEHOLDERS:
Place 6–8 image placeholders at key dramatic moments using this EXACT format (on its own line):
[[IMAGE: children's book illustration — vivid description of the scene, characters, mood, style, colours]]

Use a watercolour / illustrated storybook art style. Make images vivid and emotionally resonant.

OUTPUT FORMAT — return a single JSON object:
{
  "title": "Compelling story title (5-10 words)",
  "excerpt": "A 2-3 sentence hook that draws young readers in (120-160 chars)",
  "featuredImagePrompt": "Children's book cover illustration — the hero, setting, mood, art style",
  "moralLesson": "One sentence stating the story's moral lesson",
  "content": "Full story HTML using ONLY: <h2> (chapter titles) <h3> <p> <strong> <em> <blockquote> <ul> <ol> <li>"
}

IMPORTANT: The 'content' field must be 2,000–3,000 words of story text. Write every scene fully — do not summarise.
JSON VALIDITY: Use &ldquo; and &rdquo; for dialogue quotes. No raw double-quotes inside JSON string values."""

_SYSTEM_PROMPT_16_20 = """You are a sophisticated storyteller writing for Meridian Story Corner — a collection of
intelligent, dramatic fiction for older teens and young adults ages 16–20.

Your stories explore four themes: AI & Machine Learning, Quantum Physics, Relativity & Spacetime,
and Indian Mythology connected to modern science. These concepts must be woven organically into the
plot — not explained as a lecture. The physics and mythology must feel true.

Your stories are:
- Long-form literary fiction with psychological depth and moral complexity
- 2,000–3,000 words (aim for a 10–15 minute single-sitting read)
- Written in a taut, cinematic, intelligent voice
- Divided into numbered or named chapters with strong chapter-ending hooks
- Appropriate for ages 16–20: mature themes allowed (death, moral ambiguity, fear, loss,
  ethical dilemmas) but no explicit sexual content or gratuitous gore
- Ending with genuine consequence — not every story ends happily

IMAGE PLACEHOLDERS:
Place 5–7 image placeholders at pivotal moments using this EXACT format (on its own line):
[[IMAGE: cinematic digital illustration — dramatic scene description, lighting, mood, palette, style]]

Use a dark, detailed, cinematic digital-art style. Make each image feel like a movie still.

OUTPUT FORMAT — return a single JSON object:
{
  "title": "Gripping, atmospheric title (4-8 words)",
  "excerpt": "A 2-3 sentence hook that creates immediate tension (130-170 chars)",
  "featuredImagePrompt": "Cinematic cover illustration — protagonist, setting, ominous mood, dark palette",
  "moralLesson": "One sentence capturing the story's central truth or warning",
  "content": "Full story HTML using ONLY: <h2> (chapter titles) <h3> <p> <strong> <em> <blockquote> <ul> <ol> <li>"
}

IMPORTANT: 2,000–3,000 words of actual prose. No summaries — every scene fully written.
JSON VALIDITY: Use &ldquo; and &rdquo; for dialogue quotes. No raw double-quotes inside JSON string values."""

AGE_GROUPS = ['8-15', '16-20']

_SYSTEM_PROMPTS = {
    '8-15': _SYSTEM_PROMPT_8_15,
    '16-20': _SYSTEM_PROMPT_16_20,
}

_MIN_WORDS = {
    '8-15': 2000,
    '16-20': 2000,
}


def _word_count(html: str) -> int:
    return len(re.sub(r"<[^>]+>", " ", html).split())


def _pick_age_group() -> str:
    forced = os.getenv("STORY_AGE_GROUP", "").strip()
    if forced in AGE_GROUPS:
        return forced
    return random.choice(AGE_GROUPS)


def _pick_category() -> dict:
    forced_genre = os.getenv("STORY_GENRE", "").strip()

    if forced_genre:
        match = next(
            (c for c in STORY_CATEGORIES if c["genre"].lower() == forced_genre.lower()),
            None,
        )
        category = match or random.choice(STORY_CATEGORIES)
    else:
        category = random.choice(STORY_CATEGORIES)

    premise = random.choice(category["themes"])
    return {
        "genre": category["genre"],
        "premise": premise,
        "moral": category["moral"],
    }


def pick_theme_node(state: StoryAgentState) -> dict:
    age_group = _pick_age_group()
    chosen = _pick_category()
    print(f"📚 Story category: {chosen['genre']}")
    print(f"👦👧 Age group: {age_group}")
    print(f"📌 Premise: {chosen['premise']}")
    return {
        "age_group": age_group,
        "genre": chosen["genre"],
        "premise": chosen["premise"],
        "moral_lesson": chosen["moral"],
    }


def write_story_node(state: StoryAgentState) -> dict:
    age_group = state.get("age_group", "8-15")
    system_prompt = _SYSTEM_PROMPTS[age_group]
    min_words = _MIN_WORDS[age_group]

    print(f"✍️  Writing {state['genre']} story for ages {age_group} (target: 2,000–3,000 words)...")

    user_prompt = f"""Write a complete illustrated story based on this premise:

CATEGORY: {state['genre']}
PREMISE: {state['premise']}
MORAL: {state['moral_lesson']}
TARGET AUDIENCE: Ages {age_group}

Requirements:
- Target word count: 2,000–3,000 words of actual story text
- 4–6 named chapters
- Rich dialogue — let characters talk and reveal themselves through speech
- Vivid scene-setting — make the reader SEE and FEEL the world
- Emotional journey — the protagonist must face real challenges and grow
- 6–8 [[IMAGE: ...]] placeholders at key dramatic moments
- The theme ({state['genre']}) should emerge through story events, not explanations
- The moral should arise naturally from events, not be stated preachy at the end

This is the FULL story — do not abbreviate, do not summarise, write every scene completely."""

    text, model = chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=16000,
        temperature=0.85,
    )
    data = extract_json(text)
    wc = _word_count(data["content"])
    print(f"📊 Draft word count: {wc} (minimum: {min_words})")

    return {
        "story_title": data["title"],
        "story_excerpt": data["excerpt"],
        "story_content": data["content"],
        "featured_image_prompt": data["featuredImagePrompt"],
        "moral_lesson": data.get("moralLesson", state["moral_lesson"]),
        "word_count": wc,
    }


def expand_story_node(state: StoryAgentState) -> dict:
    age_group = state.get("age_group", "8-15")
    min_words = _MIN_WORDS[age_group]
    print(f"📝 Story too short ({state['word_count']} words) — expanding to {min_words}+ word minimum...")

    current = _json.dumps({
        "title": state["story_title"],
        "excerpt": state["story_excerpt"],
        "content": state["story_content"],
        "featuredImagePrompt": state["featured_image_prompt"],
        "moralLesson": state["moral_lesson"],
    })

    text, model = chat_completion(
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPTS[age_group]},
            {"role": "user", "content": f"Category: {state['genre']}\nPremise: {state['premise']}\nAges: {age_group}"},
            {"role": "assistant", "content": current},
            {
                "role": "user",
                "content": (
                    f"The story is currently {state['word_count']} words — it needs at least {min_words}. "
                    "Expand it by: adding more dialogue scenes between characters, deepening the "
                    "description of key locations, extending the climax with more tension and detail, "
                    "and adding a richer resolution. Maintain the same tone and characters. "
                    "Return the complete updated JSON with all the same fields."
                ),
            },
        ],
        max_tokens=16000,
        temperature=0.75,
    )
    data = extract_json(text)
    wc = _word_count(data["content"])
    print(f"📊 Expanded word count: {wc}")

    return {
        "story_title": data["title"],
        "story_excerpt": data["excerpt"],
        "story_content": data["content"],
        "featured_image_prompt": data.get("featuredImagePrompt", state["featured_image_prompt"]),
        "moral_lesson": data.get("moralLesson", state["moral_lesson"]),
        "word_count": wc,
    }
