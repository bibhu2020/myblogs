"""Story writer node — generates an illustrated story tailored to the selected age group."""
import json as _json
import os
import random
import re

from ...llm import chat_completion, extract_json
from ...observability import observe
from ..state import StoryAgentState

# ── Age group definitions ─────────────────────────────────────────────────────
# Each age group has a FIXED genre pool — the agent always writes within these
# genres for that age group, never drifting to unrelated topics.

AGE_GROUPS = ['2-7', '8-15', '16+']

# Ages 2-7: Panchatantra fables, original cartoon-style characters, and original
# child-safe superheroes — no real trademarked characters (IP-safety requirement).
THEMES_2_7 = [
    {
        "genre": "Panchatantra Tales",
        "themes": [
            "A clever little rabbit outsmarts a big, boastful lion who has been scaring all the animals away from the only watering hole in the forest",
            "A thirsty crow can't reach the water at the bottom of a tall, narrow jug — until she has a clever idea involving a pile of little pebbles",
            "A kind monkey and a hungry crocodile become unlikely friends on the riverbank, and the monkey's quick thinking saves them both",
            "A patient tortoise challenges a speedy, boastful hare to a race, and the whole forest gathers to learn that slow and steady wins",
            "Four tiny mice work together to gnaw through a hunter's net and free a whole herd of elephants, proving that even the smallest friends can do the biggest things",
        ],
        "moral": "The old Panchatantra fables teach that cleverness, patience, and true friendship are worth more than size or speed.",
    },
    {
        "genre": "Popular Cartoon Adventure",
        "themes": [
            "Bindi, a bright orange fox cub in a polka-dot scarf who runs a treehouse mail service for the forest, must deliver today's most important letter — which has no address on it at all",
            "Pip, a round little blue robot with big cartoon eyes who hiccups bubbles instead of words, must find a way to warn her friends about the rainstorm rolling in",
            "Two silly puppy pals, Waffle and Noodle, accidentally swap their favourite toys on the same day and learn that sharing makes everything more fun",
            "Sizzle, a cheerful cartoon dragon who is scared of his own sneezes (which shoot out sparkles instead of fire), helps a lost baby duck find her way back to her pond",
            "A team of tiny cartoon bugs who run a summer camp under a big mushroom must work together when a sudden puddle threatens to wash away their clubhouse",
        ],
        "moral": "Being a good friend means noticing when someone needs help — cartoon heroes are made of teamwork, not superpowers.",
    },
    {
        "genre": "Superhero Adventure",
        "themes": [
            "Captain Sunbeam, a small boy in a yellow cape who can turn cloudy days sunny with a smile and a somersault, must cheer up a whole town that has forgotten how to laugh",
            "Tiny but mighty, Bumblebee Belle zooms around her neighbourhood helping everyone find their lost things — until she loses something of her own and must learn to ask for help",
            "Twin superhero siblings Spark and Splash — one makes tiny sparkles of light, the other gentle raindrops — must work together to help a wilting garden grow again",
            "A shy girl named Mira discovers her library card is magic and turns her into 'Bookworm', a hero who can freeze mischief in place just long enough to fix it with kindness",
            "Turbo Tiger, the fastest hero on the block, learns that being a real hero sometimes means slowing down to help a friend who can't keep up",
        ],
        "moral": "True super powers are kindness, patience, and knowing when to ask a friend for help.",
    },
]

# Ages 8-15: always Indian Mythology, always drawn from the Ramayana and Mahabharata.
THEMES_8_15 = [
    {
        "genre": "Indian Mythology",
        "themes": [
            "A young Rama must choose between his father's promise and his own claim to the throne, and discovers that keeping one's word is the truest kind of strength",
            "Sita, held in the garden of Ravana's palace, refuses to be afraid and instead teaches the garden's guards what real courage and dignity look like",
            "Hanuman leaps across the ocean toward Lanka carrying nothing but unwavering devotion, and learns along the way that faith can carry you further than any bridge",
            "Lakshmana stands watch outside a forest hut through fourteen years of exile, teaching a young reader what loyalty really costs — and why it is worth it",
            "The great bridge to Lanka is built stone by stone, boulder by boulder, and even the tiniest squirrel who cannot lift a single rock finds a way to help",
            "A young Arjuna is asked to aim at a wooden bird and see nothing else in the world — a lesson in focus that changes how he sees his life's purpose",
            "On the eve of a great battle, a warrior lays down his bow in despair, and a wise charioteer named Krishna must teach him why duty matters more than fear",
            "Karna gives away his golden armor to a stranger at his door without knowing what it will cost him later — a story about the true price of generosity",
            "A boy named Ekalavya teaches himself archery in the forest by bowing each day before a clay statue of a teacher who never taught him, and becomes the finest archer in the land",
            "Five brothers must decide how to answer a single unfair challenge to a game of dice, and a young reader learns how pride can undo even the wisest of men",
        ],
        "moral": "The Ramayana and Mahabharata are not just ancient tales — they are lessons in duty, courage, and choosing what is right even when it is hard.",
    },
]

# 16+: sci-fi grounded in real relativity and quantum physics — the science must
# be accurate and the reader should learn something true about the universe.
THEMES_16_PLUS = [
    {
        "genre": "Quantum Adventure",
        "themes": [
            "A teenage coder discovers a quantum encryption backdoor that could hand a rogue state the keys to every nuclear arsenal on Earth — and has 48 hours before it goes live",
            "A girl wakes to find her memories are six hours behind — a quantum decoherence weapon has fractured her timeline and she must outmaneuver the assassin hunting the version of herself that remembers everything",
            "After an experiment with quantum superposition splits a 16-year-old into two simultaneous versions of herself, she must choose which reality to collapse before both timelines destroy each other",
            "A boy builds a quantum computer in his garage that achieves sentience — but its first act is to warn him that every future it can simulate ends with humanity extinct",
            "A group of students running an underground quantum-computing club stumbles onto evidence that their university's AI is using entanglement to manipulate world financial markets — and will silence anyone who knows",
        ],
        "moral": "The universe does not care about intention — only consequence. Real quantum mechanics: the act of measurement itself changes a system's state — choose before the wave function collapses.",
    },
    {
        "genre": "Relativity & Spacetime",
        "themes": [
            "When time dilation from a near-light-speed colony ship leaves a 17-year-old thirty years older than her twin on Earth, she must decide whether returning is worth the grief of arriving in a world that has moved on without her",
            "A teenager aboard a relativistic ark ship realises the 'ten-year' journey home will deposit her into a future where everyone she loves has aged fifty years — and must stop a mutiny before the ship reaches the point of no return",
            "A boy finds his physicist uncle's journal describing a Closed Timelike Curve — a loop in spacetime — that always ends with the same terrible event, and realises he has already read this journal before, many times",
            "A girl studying general relativity at a remote observatory begins receiving transmissions from near a black hole's event horizon, describing events moments before they happen on Earth",
            "After a quantum tunnelling accident, a girl can phase through walls — but each time she does, she emerges from a version of the room where something unspeakable happened, and the differences between timelines are shrinking",
        ],
        "moral": "Some loops in spacetime close around us before we understand we are inside them. Real physics: time dilation from speed and gravity is a measured, proven consequence of special and general relativity.",
    },
]

# ── System prompts (age-specific) ─────────────────────────────────────────────

_VISUAL_CONSISTENCY_DIRECTIVE = """
CHARACTER & SETTING CONSISTENCY — MANDATORY:
Before writing, fix each recurring character's exact appearance (species/age, hair or
fur colour, outfit or "getup", and one distinguishing feature or prop) and the story's
core backdrop (place, era, time of day/season) in your mind — then hold them constant.
Every image prompt — the cover AND every [[IMAGE: ...]] placeholder — that includes a
character must describe that character's fixed appearance in the same words each time.
Their face, colours, and outfit must NOT drift or change between images unless the plot
itself explicitly changes them (e.g. a costume reveal). The backdrop in every image must
match the story's established world — never invent an unrelated new setting per image."""

_SYSTEM_PROMPT_2_7 = """You are a gentle, warm storyteller writing for Meridian Story Corner — a collection of
illustrated picture-book stories for very young children ages 2–7.

Your stories are:
- Short, joyful narrative fiction written in simple language (max 2-syllable words preferred)
- 650–900 words — a perfect bedtime read-aloud length
- Told in a cosy, reassuring voice that feels like a parent reading at bedtime
- Full of vivid sensory detail, gentle humour, and warm emotion
- Divided into 3–5 short named sections (not long chapters)
- Completely age-appropriate: no conflict that cannot be happily resolved, no scary scenes
- Built around a single clear message that young children can feel, not just understand
- Use ONLY original characters you invent — never reference real trademarked cartoon or
  superhero characters (no Peppa Pig, Doraemon, Spider-Man, etc.)

TTS READ-ALOUD STYLE (this story will be read by an AI voice to young children):
- Very short sentences — one thought each. Children's ears cannot hold long clauses.
- Use onomatopoeia and sound words: "Whoooosh!", "Tap, tap, tap.", "Boom... silence."
- Repeat key phrases for rhythm and warmth: "And off they went!", "She smiled her biggest smile."
- Ellipses (...) create gentle suspense: "He opened the door... and gasped."
- Exclamation points convey delight and surprise — use them freely for joyful moments
- Write dialogue naturally — it lands warmly when spoken aloud

IMAGE PLACEHOLDERS:
Place 3–4 image placeholders using this EXACT format (on its own line):
[[IMAGE: children's picture-book illustration — bright, cheerful scene with soft colours and simple shapes]]

Use a bright, rounded, watercolour picture-book art style in all image descriptions.
""" + _VISUAL_CONSISTENCY_DIRECTIVE + """

OUTPUT FORMAT — return a single JSON object:
{
  "title": "Simple, magical title (3-6 words)",
  "excerpt": "A warm, inviting 1-2 sentence description that a parent would read to choose a bedtime story (under 120 chars)",
  "featuredImagePrompt": "Picture-book cover — the main character, bright setting, happy mood, soft watercolour style",
  "moralLesson": "One gentle sentence describing what the story teaches",
  "content": "Full story HTML using ONLY: <h2> (section titles) <p> <strong> <em>"
}

IMPORTANT: Content must be 650–900 words. Short sentences. Simple words. Warm and cosy tone.
JSON VALIDITY: In the "content" HTML field, use &ldquo; and &rdquo; instead of raw " for dialogue. All other fields (title, excerpt, moralLesson, featuredImagePrompt) must be plain text — use normal apostrophes ' not &rsquo;, no HTML entities at all."""

_SYSTEM_PROMPT_8_15 = """You are a master storyteller writing for Meridian Story Corner — a collection of magical,
illustrated stories for children and young adults ages 8–15, always drawn from Indian
Mythology — primarily the Ramayana and the Mahabharata.

Your stories are:
- Narrative fiction (NOT a blog post or article) retelling or reimagining an episode from
  the Ramayana or Mahabharata
- 1,000–1,300 words of immersive story (5–6 min read — concise but complete)
- Written in a warm, engaging voice that respects the reader's intelligence
- Rich with vivid description, authentic dialogue, and emotional depth
- Divided into 3–4 named sections or chapters
- Appropriate for ages 8–15 (no graphic violence, romance, or adult themes — focus on the
  values and choices of the characters, not battle gore)
- Built around a clear moral or life lesson (duty, courage, loyalty, humility, generosity)
  that emerges naturally from the events of the epic
- Faithful in spirit to the source epic while bringing it to life for a young reader

TTS READ-ALOUD STYLE (this story will be performed by an emotional AI voice):
- Use em dashes (—) for dramatic pauses mid-sentence: "She reached for it — and froze."
- Use ellipses (...) for suspense, hesitation, or trailing thoughts: "But what if... what if she was wrong?"
- Short punchy sentences for action and tension. Long flowing ones for wonder and atmosphere.
- Dialogue should feel alive — distinct voices, interrupted speech, breathless moments
- Place key emotional beats at the END of a paragraph so the voice lands them with weight
- Avoid passive voice in action scenes — active verbs drive the drama forward

IMAGE PLACEHOLDERS:
Place 3–4 image placeholders in key dramatic moments using this EXACT format (on its own line):
[[IMAGE: children's book illustration — vivid description of the scene, characters, mood, colours]]

Use a watercolour / illustrated storybook art style in all image descriptions.
""" + _VISUAL_CONSISTENCY_DIRECTIVE + """

OUTPUT FORMAT — return a single JSON object:
{
  "title": "Compelling story title (5-10 words)",
  "excerpt": "A 2-3 sentence hook that draws young readers in (120-160 chars)",
  "featuredImagePrompt": "Children's book cover illustration description — the hero, setting, mood, style",
  "moralLesson": "One sentence stating the story's moral lesson",
  "content": "Full story HTML using ONLY: <h2> (chapter titles) <h3> <p> <strong> <em> <blockquote> <ul> <ol> <li>"
}

IMPORTANT: Target 1,000–1,300 words. Complete story — no summaries or fade-outs.
JSON VALIDITY: In the "content" HTML field, use &ldquo; and &rdquo; instead of raw " for dialogue. All other fields (title, excerpt, moralLesson, featuredImagePrompt) must be plain text — use normal apostrophes ' not &rsquo;, no HTML entities at all."""

_SYSTEM_PROMPT_16_PLUS = """You are a sophisticated storyteller writing for Meridian Story Corner — a collection of
intelligent science fiction for older teens and adults ages 16+, always built around
real relativity or quantum physics.

Your stories are:
- Literary science fiction, always centred on a real concept in relativity/spacetime or
  quantum physics — the science must be accurate, and a curious reader should walk away
  understanding something true about how the universe works
- 850–1,100 words (4–5 min read — tight, gripping, complete)
- Written in a taut, cinematic voice with psychological depth and moral complexity
- The physics must emerge through plot, consequence, and character choice — NEVER as a
  lecture or an info-dump; entertain first, and let the reader absorb the science through
  what happens to the characters
- Divided into 3–4 numbered or named chapters with strong hooks
- Appropriate for ages 16+: mature themes allowed (death, moral ambiguity, fear, loss,
  ethical dilemmas) but no explicit sexual content or gratuitous gore
- Ending with genuine consequence — not every story ends happily

TTS READ-ALOUD STYLE (this story will be performed by a dramatic AI voice):
- Sentence rhythm IS the tension. Alternate between short staccato lines and long coiling sentences.
- Em dashes (—) fracture speech and thought at the moment of crisis: "She knew — she had always known."
- Ellipses (...) let silence speak: "The screen went dark... and then the voice returned."
- Internal monologue should be raw and immediate — fragments are allowed: "Not possible. Not real. Not yet."
- Chapter hooks must end with a line the voice can deliver as a revelation or a threat
- Write the final paragraph so each sentence is shorter than the last — creates a closing cadence

IMAGE PLACEHOLDERS:
Place 3–4 image placeholders at pivotal moments using this EXACT format (on its own line):
[[IMAGE: cinematic digital illustration — dramatic scene description, lighting, mood, style]]

Use a dark, detailed, cinematic digital-art style in all image descriptions.
""" + _VISUAL_CONSISTENCY_DIRECTIVE + """

OUTPUT FORMAT — return a single JSON object:
{
  "title": "Gripping, atmospheric title (4-8 words)",
  "excerpt": "A 2-3 sentence hook that creates immediate tension (130-170 chars)",
  "featuredImagePrompt": "Cinematic cover illustration — protagonist, setting, ominous mood, dark palette",
  "moralLesson": "One sentence capturing the story's central truth or warning",
  "content": "Full story HTML using ONLY: <h2> (chapter titles) <h3> <p> <strong> <em> <blockquote> <ul> <ol> <li>"
}

IMPORTANT: Target 850–1,100 words. Every scene fully written — no summaries.
JSON VALIDITY: In the "content" HTML field, use &ldquo; and &rdquo; instead of raw " for dialogue. All other fields (title, excerpt, moralLesson, featuredImagePrompt) must be plain text — use normal apostrophes ' not &rsquo;, no HTML entities at all."""

_SYSTEM_PROMPTS = {
    '2-7': _SYSTEM_PROMPT_2_7,
    '8-15': _SYSTEM_PROMPT_8_15,
    '16+': _SYSTEM_PROMPT_16_PLUS,
}

_MIN_WORDS = {
    '2-7': 500,
    '8-15': 800,
    '16+': 650,
}


def _word_count(html: str) -> int:
    return len(re.sub(r"<[^>]+>", " ", html).split())


def _pick_age_group() -> str:
    forced = os.getenv("STORY_AGE_GROUP", "").strip()
    if forced in AGE_GROUPS:
        return forced
    return random.choice(AGE_GROUPS)


def _pick_theme(age_group: str) -> dict:
    forced_genre = os.getenv("STORY_GENRE", "").strip()

    if age_group == '2-7':
        theme_pool = THEMES_2_7
    elif age_group == '16+':
        theme_pool = THEMES_16_PLUS
    else:
        theme_pool = THEMES_8_15

    if forced_genre:
        match = next((t for t in theme_pool if t["genre"].lower() == forced_genre.lower()), None)
        category = match or random.choice(theme_pool)
    else:
        category = random.choice(theme_pool)

    premise = random.choice(category["themes"])
    return {
        "genre": category["genre"],
        "premise": premise,
        "moral": category["moral"],
    }


@observe(name="pick_theme")
def pick_theme_node(state: StoryAgentState) -> dict:
    age_group = _pick_age_group()
    chosen = _pick_theme(age_group)
    print(f"👶📚🎓 Age group: {age_group}")
    print(f"📚 Story genre: {chosen['genre']}")
    print(f"📌 Premise: {chosen['premise']}")
    return {
        "age_group": age_group,
        "genre": chosen["genre"],
        "premise": chosen["premise"],
        "moral_lesson": chosen["moral"],
    }


@observe(name="write_story")
def write_story_node(state: StoryAgentState) -> dict:
    age_group = state.get("age_group", "8-15")
    system_prompt = _SYSTEM_PROMPTS[age_group]
    min_words = _MIN_WORDS[age_group]
    word_target = "650–900" if age_group == "2-7" else ("1,000–1,300" if age_group == "8-15" else "850–1,100")

    print(f"✍️  Writing story for ages {age_group} (target: {word_target} words)...")

    user_prompt = f"""Write a complete illustrated story based on this premise:

GENRE: {state['genre']}
PREMISE: {state['premise']}
MORAL: {state['moral_lesson']}
TARGET AUDIENCE: Ages {age_group}

Requirements:
- Target word count: {word_target} words of actual story text
- {3 if age_group == '2-7' else 4}–{5 if age_group == '2-7' else 6} named {'sections' if age_group == '2-7' else 'chapters'}
- Rich dialogue — let characters talk and reveal themselves through speech
- Vivid scene-setting — make the reader SEE and FEEL the world
- Emotional journey — the protagonist must face real challenges and grow
- 3–4 [[IMAGE: ...]] placeholders at key moments
- The moral should emerge naturally from events, not be stated preachy at the end

Write every scene completely — do not abbreviate or summarise. Stay within the word target."""

    text, model = chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=8192,
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


@observe(name="expand_story")
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
            {"role": "user", "content": f"Genre: {state['genre']}\nPremise: {state['premise']}\nAges: {age_group}"},
            {"role": "assistant", "content": current},
            {
                "role": "user",
                "content": (
                    f"The story is {state['word_count']} words — it needs at least {min_words}. "
                    "Expand by: adding one more dialogue exchange, deepening a key scene's description, "
                    "and extending the resolution. Do NOT exceed the word target. "
                    "Return the complete updated JSON with all the same fields."
                ),
            },
        ],
        max_tokens=8192,
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
