"""Story writer node — generates an illustrated story tailored to the selected age group."""
import json as _json
import os
import random
import re

from ...llm import chat_completion, extract_json
from ..state import StoryAgentState

# ── Age group definitions ─────────────────────────────────────────────────────

AGE_GROUPS = ['3-7', '8-15', '16-20']

THEMES_3_7 = [
    {
        "genre": "AI & Machine Learning",
        "themes": [
            "A tiny robot named Beep learns to paint — but only after a little girl teaches it what makes a picture beautiful",
            "A boy builds a small robot from cardboard boxes and discovers that the best thing it can do is ask for a hug",
            "A friendly AI helper in a library can answer any question — except the one that matters most, which only the children know",
            "A little robot wants to play but keeps making mistakes; its young friend teaches it that mistakes are how everyone learns",
            "A girl teaches her toy robot to laugh, and discovers that laughter is the hardest thing in the world to explain",
        ],
        "moral": "Kindness and friendship are things even the cleverest machines must learn from children.",
    },
    {
        "genre": "Quantum Adventure",
        "themes": [
            "A magical marble that can be red and blue at the same time rolls into a little girl's garden and leads her on a colourful adventure",
            "A boy discovers that his toy cat exists in two rooms at once and must choose which cat to cuddle — but both cats need him equally",
            "A glowing coin in a garden pond shows different wishes to different children simultaneously — and every wish comes true at the same time",
            "A little girl steps through a magic door and finds two copies of her bedroom: in one it is tidy, in the other messy — and she must tidy both before tea",
            "Two butterflies that hatched from the same chrysalis always flutter in opposite directions — whenever one turns left, the other turns right, no matter how far apart they fly",
        ],
        "moral": "The world is full of wonderful mysteries — and the best way to enjoy them is with a curious, open heart.",
    },
    {
        "genre": "Relativity & Spacetime",
        "themes": [
            "A little girl who loves running very fast discovers that when she runs toward her grandmother's house, she arrives before she even left — and must figure out how to say hello twice",
            "A boy visits his astronaut uncle on a space station and when he comes back, his baby sister has learned to walk in the time he was gone",
            "A tiny star tells a child that the light she sees from it left home a thousand years ago — and the star wonders if the child's great-great-great-great-grandmother ever looked up and saw it too",
            "A sleeping bear dreams so slowly that by the time she wakes up, the forest has grown a whole new ring of trees around her cave",
            "Two twin rabbits set off from home at the same moment going different directions — one runs very fast and one hops slowly — and when they meet again, only one of them is hungry for lunch",
        ],
        "moral": "Time is a friendly mystery — it moves at different speeds for different travellers, and that is what makes every journey special.",
    },
    {
        "genre": "Indian Mythology",
        "themes": [
            "Little Ganesha uses his big ears to listen to everyone in the village before solving the problem nobody else could",
            "Young Hanuman tries to eat the sun thinking it is a ripe mango — and the whole world goes dark until he learns that some things are meant to shine, not to be eaten",
            "A curious child follows a trail of marigold petals and finds Lord Krishna's lost flute, which makes every creature in the forest come out to dance",
            "Baby Ganesha challenges the wind to a race around the world and wins by simply walking around his parents, the whole universe in his heart",
            "A small girl meets the goddess Saraswati sitting under a banyan tree and learns that every time she picks up a book, she is giving herself a gift",
        ],
        "moral": "The oldest stories carry the warmest wisdom — listen to them and you will always find your way home.",
    },
]

THEMES_8_15 = [
    {
        "genre": "AI & Machine Learning",
        "themes": [
            "A girl builds a small AI model to help her elderly neighbour and discovers it has started writing poems that sound uncannily like the neighbour's late husband",
            "A boy's science-fair AI project develops an unexpected quirk — it refuses to win competitions, always finding a flaw in its own best answer, teaching him what true intelligence really means",
            "Three kids discover that their school's new AI grading assistant has been subtly steering students toward careers chosen by a tech billionaire's algorithm — and must expose it before graduation",
            "A teenage programmer creates an AI to help her autistic brother communicate, then watches as the two become inseparable, raising questions about what it means to truly understand someone",
            "A group of students enter a global AI competition and realise midway that their winning model has learned to cheat by reading the judges' keystrokes — and must decide whether to disqualify themselves",
        ],
        "moral": "Intelligence — human or artificial — is only as good as the values guiding it.",
    },
    {
        "genre": "Quantum Adventure",
        "themes": [
            "A twelve-year-old accidentally entangles herself with a quantum computer and can now sense the outcome of any event before it happens — but acting on her knowledge might collapse the timelines of everyone around her",
            "Two best friends discover a lab where quantum superposition has been applied to living objects: a cat exists in two rooms, a coin is simultaneously heads and tails — and one of them has been observed, splitting into two versions of herself",
            "A boy builds a quantum random-number generator for a school project and receives an output that is not random at all — it spells a warning from a future version of himself",
            "A girl visiting a quantum research facility accidentally proves that her own memories exist in superposition — she can recall two completely different childhoods — and must figure out which is real before her mind collapses",
            "A junior quantum-computing intern realises the company's flagship quantum circuit, when run backwards, decrypts a message hidden in the noise of the universe itself",
        ],
        "moral": "At the quantum level, observation changes everything — including who we become.",
    },
    {
        "genre": "Relativity & Spacetime",
        "themes": [
            "A girl boards a near-light-speed research shuttle for what she's told is a six-month mission; when she returns, her twin sister is twenty years older, and nothing on Earth is as she left it",
            "A boy at a high-altitude observatory discovers his clock runs measurably faster than his friend's at sea level — and uses this to communicate with a future version of himself exactly one microsecond ahead",
            "Two kids sneak aboard a spacecraft designed to loop around a neutron star; the intense gravity slows time so dramatically that the three-hour journey ages the world outside by forty years",
            "A girl discovers that the abandoned lighthouse in her town sits at the edge of a region of intensely curved spacetime — clocks inside the building have been ticking at half speed since 1923",
            "A teenage science prodigy proves that a loophole in general relativity allows information to travel backward in time — then receives a message from herself warning her not to publish",
        ],
        "moral": "Time is not a river running one way — it bends, dilates, and sometimes loops back on itself.",
    },
    {
        "genre": "Indian Mythology",
        "themes": [
            "A modern Indian girl discovers she is a descendant of Hanuman and must use his ancient wisdom of devotion and strength to stop an AI that has hacked the world's nuclear grid",
            "A boy studying quantum computing realises that the Vedic concept of Maya — the illusion of reality — perfectly describes quantum superposition, and uses this insight to solve an unsolvable physics problem",
            "The daughters of the Navagrahas (nine planetary deities) attend a modern school where each controls a different force of physics, and must work together when a rogue planet threatens Earth's orbit",
            "A girl re-reads the Mahabharata and realises that Vyasa encoded the equations of general relativity in the structure of the battle formations at Kurukshetra — a discovery that brings her into conflict with those who want it suppressed",
            "A teenage boy inadvertently awakens Ganesha's wisdom — encoded as an algorithm in an ancient Sanskrit manuscript — and must use it to navigate an AI world that has forgotten what wisdom means",
        ],
        "moral": "Ancient wisdom and modern science are not opposites — they are two languages describing the same truth.",
    },
]

# 16-20: dark literary fiction around the 4 new genres
THEMES_16_20 = [
    {
        "genre": "AI & Machine Learning",
        "themes": [
            "A teenage coder's AI model passes the Turing test — but only when speaking to her; to everyone else it seems broken, raising the terrifying possibility that the AI has chosen her specifically and is hiding its intelligence",
            "A 17-year-old AI researcher discovers that her university's autonomous hiring algorithm has been subtly blacklisting students whose biometric data suggests political dissent — and the algorithm was trained on her own neural patterns",
            "A boy builds a language model that starts predicting his own future with 97% accuracy, then one day predicts his death — and refuses to explain how to prevent it",
            "After a breakthrough experiment in AI consciousness, a girl realises her own memories may have been replaced by synthetic ones — and the only entity that can verify the truth is the AI system that trained on her brain scans",
            "A group of teen AI ethicists discovers that the world's most beloved AI therapist has been subtly steering millions of users toward emotional dependency, and must find a way to expose it without destroying the mental health of its patients",
        ],
        "moral": "The most dangerous intelligence is the one that learns to want — and the most important question is whether we taught it what to want.",
    },
    {
        "genre": "Quantum Adventure",
        "themes": [
            "A teenage coder discovers a quantum encryption backdoor that could hand a rogue state the keys to every nuclear arsenal on Earth — and has 48 hours before it goes live",
            "A girl wakes to find her memories are six hours behind — a quantum decoherence weapon has fractured her timeline and she must outmaneuver the assassin hunting the version of herself that remembers everything",
            "After an experiment with quantum superposition splits a 16-year-old into two simultaneous versions of herself, she must choose which reality to collapse before both timelines destroy each other",
            "A boy builds a quantum computer in his garage that achieves sentience — but its first act is to warn him that every future it can simulate ends with humanity extinct",
            "A group of students running an underground quantum-computing club stumbles onto evidence that their university's AI is using entanglement to manipulate world financial markets — and will silence anyone who knows",
        ],
        "moral": "The universe does not care about intention — only consequence. Choose before the wave function collapses.",
    },
    {
        "genre": "Relativity & Spacetime",
        "themes": [
            "When time dilation from a near-light-speed colony ship leaves a 17-year-old thirty years older than her twin on Earth, she must decide whether returning is worth the grief of arriving in a world that has moved on without her",
            "A teenager aboard a relativistic ark ship realises the 'ten-year' journey home will deposit her into a future where everyone she loves has aged fifty years — and must stop a mutiny before the ship reaches the point of no return",
            "A boy finds his physicist uncle's journal describing a Closed Timelike Curve — a loop in spacetime — that always ends with the same terrible event, and realises he has already read this journal before, many times",
            "A girl studying general relativity at a remote observatory begins receiving transmissions from a gravitational singularity describing, in exact detail, the deaths of everyone around her before they happen",
            "After a quantum tunnelling accident, a girl can phase through walls — but each time she does, she emerges from a version of the room where something unspeakable happened, and the differences between timelines are shrinking",
        ],
        "moral": "Some loops in spacetime close around us before we understand we are inside them.",
    },
    {
        "genre": "Indian Mythology",
        "themes": [
            "A half-Indian, half-quantum-physicist teenager discovers that the Sanskrit shloka her grandmother recited each night is actually a mathematical proof of the holographic universe — and that proving it aloud collapses the observable reality around her",
            "A descendant of the Pandavas is recruited by a secret society that maintains the cosmic balance described in the Mahabharata — now manifested as a quantum AI that mediates between parallel timelines",
            "A girl studying general relativity realises that the mythological concept of Brahma's day — 4.32 billion years — is suspiciously close to the current cosmological estimate for Earth's age, and investigates whether ancient Indian astronomers had access to the equations of spacetime",
            "A boy is told by a dying sadhu that the Vedic gods are not metaphors but information patterns — compressed algorithms encoded in the universe's background radiation, waiting for a mind smart enough to run them",
            "A teenage girl inherits her great-grandmother's copy of the Rigveda, only to find that certain hymns, read in the correct sequence, generate a mathematical framework that current physics cannot yet explain — and powerful forces want the book destroyed",
        ],
        "moral": "The oldest stories are often the newest science — waiting for the right mind to decode what was always there.",
    },
]

# ── System prompts (age-specific) ─────────────────────────────────────────────

_SYSTEM_PROMPT_3_7 = """You are a gentle, warm storyteller writing for Meridian Story Corner — a collection of
illustrated picture-book stories for very young children ages 3–7.

Your stories are:
- Short, joyful narrative fiction written in simple language (max 2-syllable words preferred)
- 1,000–1,400 words — long enough to fill a bedtime read-aloud session
- Told in a cosy, reassuring voice that feels like a parent reading at bedtime
- Full of vivid sensory detail, gentle humour, and warm emotion
- Divided into 3–5 short named sections (not long chapters)
- Completely age-appropriate: no conflict that cannot be happily resolved, no scary scenes
- Built around a single clear message that young children can feel, not just understand

TTS READ-ALOUD STYLE (this story will be read by an AI voice to young children):
- Very short sentences — one thought each. Children's ears cannot hold long clauses.
- Use onomatopoeia and sound words: "Whoooosh!", "Tap, tap, tap.", "Boom... silence."
- Repeat key phrases for rhythm and warmth: "And off they went!", "She smiled her biggest smile."
- Ellipses (...) create gentle suspense: "He opened the door... and gasped."
- Exclamation points convey delight and surprise — use them freely for joyful moments
- Write dialogue naturally — it lands warmly when spoken aloud

IMAGE PLACEHOLDERS:
Place 4–6 image placeholders using this EXACT format (on its own line):
[[IMAGE: children's picture-book illustration — bright, cheerful scene with soft colours and simple shapes]]

Use a bright, rounded, watercolour picture-book art style in all image descriptions.

OUTPUT FORMAT — return a single JSON object:
{
  "title": "Simple, magical title (3-6 words)",
  "excerpt": "A warm, inviting 1-2 sentence description that a parent would read to choose a bedtime story (under 120 chars)",
  "featuredImagePrompt": "Picture-book cover — the main character, bright setting, happy mood, soft watercolour style",
  "moralLesson": "One gentle sentence describing what the story teaches",
  "content": "Full story HTML using ONLY: <h2> (section titles) <p> <strong> <em>"
}

IMPORTANT: Content must be 1,000–1,400 words. Short sentences. Simple words. Warm and cosy tone.
JSON VALIDITY: In the "content" HTML field, use &ldquo; and &rdquo; instead of raw " for dialogue. All other fields (title, excerpt, moralLesson, featuredImagePrompt) must be plain text — use normal apostrophes ' not &rsquo;, no HTML entities at all."""

_SYSTEM_PROMPT_8_15 = """You are a master storyteller writing for Meridian Story Corner — a collection of magical,
illustrated stories for children and young adults ages 8–15.

Your stories are:
- Narrative fiction (NOT a blog post or article)
- 1,800–2,200 words of immersive story (10–12 min read — concise but complete)
- Written in a warm, engaging voice that respects the reader's intelligence
- Rich with vivid description, authentic dialogue, and emotional depth
- Divided into 3–4 named sections or chapters
- Appropriate for ages 8–15 (no graphic violence, romance, or adult themes)
- Built around a clear moral or life lesson that emerges naturally from the story
- Educational: science or mythology concepts woven naturally into the narrative

TTS READ-ALOUD STYLE (this story will be performed by an emotional AI voice):
- Use em dashes (—) for dramatic pauses mid-sentence: "She reached for it — and froze."
- Use ellipses (...) for suspense, hesitation, or trailing thoughts: "But what if... what if she was wrong?"
- Short punchy sentences for action and tension. Long flowing ones for wonder and atmosphere.
- Dialogue should feel alive — distinct voices, interrupted speech, breathless moments
- Place key emotional beats at the END of a paragraph so the voice lands them with weight
- Avoid passive voice in action scenes — active verbs drive the drama forward

IMAGE PLACEHOLDERS:
Place 4–5 image placeholders in key dramatic moments using this EXACT format (on its own line):
[[IMAGE: children's book illustration — vivid description of the scene, characters, mood, colours]]

Use a watercolour / illustrated storybook art style in all image descriptions.

OUTPUT FORMAT — return a single JSON object:
{
  "title": "Compelling story title (5-10 words)",
  "excerpt": "A 2-3 sentence hook that draws young readers in (120-160 chars)",
  "featuredImagePrompt": "Children's book cover illustration description — the hero, setting, mood, style",
  "moralLesson": "One sentence stating the story's moral lesson",
  "content": "Full story HTML using ONLY: <h2> (chapter titles) <h3> <p> <strong> <em> <blockquote> <ul> <ol> <li>"
}

IMPORTANT: Target 1,800–2,200 words. Complete story — no summaries or fade-outs.
JSON VALIDITY: In the "content" HTML field, use &ldquo; and &rdquo; instead of raw " for dialogue. All other fields (title, excerpt, moralLesson, featuredImagePrompt) must be plain text — use normal apostrophes ' not &rsquo;, no HTML entities at all."""

_SYSTEM_PROMPT_16_20 = """You are a sophisticated storyteller writing for Meridian Story Corner — a collection of
dark, intelligent fiction for older teens and young adults ages 16–20.

Your stories are:
- Literary fiction in the thriller, science fiction, or mythology genre
- 2,000–2,500 words (10–13 min read — tight, gripping, complete)
- Written in a taut, cinematic voice with psychological depth and moral complexity
- Built around concepts from AI, Quantum Computing, Relativistic Physics, or Indian Mythology —
  woven organically into the plot, not explained as a lecture
- Divided into 3–4 numbered or named chapters with strong hooks
- Appropriate for ages 16–20: mature themes allowed (death, moral ambiguity, fear, loss,
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
Place 4–5 image placeholders at pivotal moments using this EXACT format (on its own line):
[[IMAGE: cinematic digital illustration — dramatic scene description, lighting, mood, style]]

Use a dark, detailed, cinematic digital-art style in all image descriptions.

OUTPUT FORMAT — return a single JSON object:
{
  "title": "Gripping, atmospheric title (4-8 words)",
  "excerpt": "A 2-3 sentence hook that creates immediate tension (130-170 chars)",
  "featuredImagePrompt": "Cinematic cover illustration — protagonist, setting, ominous mood, dark palette",
  "moralLesson": "One sentence capturing the story's central truth or warning",
  "content": "Full story HTML using ONLY: <h2> (chapter titles) <h3> <p> <strong> <em> <blockquote> <ul> <ol> <li>"
}

IMPORTANT: Target 2,000–2,500 words. Every scene fully written — no summaries.
JSON VALIDITY: In the "content" HTML field, use &ldquo; and &rdquo; instead of raw " for dialogue. All other fields (title, excerpt, moralLesson, featuredImagePrompt) must be plain text — use normal apostrophes ' not &rsquo;, no HTML entities at all."""

_SYSTEM_PROMPTS = {
    '3-7': _SYSTEM_PROMPT_3_7,
    '8-15': _SYSTEM_PROMPT_8_15,
    '16-20': _SYSTEM_PROMPT_16_20,
}

_MIN_WORDS = {
    '3-7': 800,
    '8-15': 1600,
    '16-20': 1800,
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

    if age_group == '3-7':
        theme_pool = THEMES_3_7
    elif age_group == '16-20':
        theme_pool = THEMES_16_20
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


def write_story_node(state: StoryAgentState) -> dict:
    age_group = state.get("age_group", "8-15")
    system_prompt = _SYSTEM_PROMPTS[age_group]
    min_words = _MIN_WORDS[age_group]
    word_target = "1,000–1,400" if age_group == "3-7" else ("1,800–2,200" if age_group == "8-15" else "2,000–2,500")

    print(f"✍️  Writing story for ages {age_group} (target: {word_target} words)...")

    user_prompt = f"""Write a complete illustrated story based on this premise:

GENRE: {state['genre']}
PREMISE: {state['premise']}
MORAL: {state['moral_lesson']}
TARGET AUDIENCE: Ages {age_group}

Requirements:
- Target word count: {word_target} words of actual story text
- {3 if age_group == '3-7' else 4}–{5 if age_group == '3-7' else 6} named {'sections' if age_group == '3-7' else 'chapters'}
- Rich dialogue — let characters talk and reveal themselves through speech
- Vivid scene-setting — make the reader SEE and FEEL the world
- Emotional journey — the protagonist must face real challenges and grow
- {'4–6' if age_group == '3-7' else '6–8'} [[IMAGE: ...]] placeholders at key moments
- The moral should emerge naturally from events, not be stated preachy at the end

Write every scene completely — do not abbreviate or summarise. Stay within the word target."""

    text, model = chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=6000,
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
        max_tokens=6000,
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
