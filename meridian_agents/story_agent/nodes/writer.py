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
        "genre": "Fairy Tale",
        "themes": [
            "A little bunny who is scared of the dark learns that stars are night-lights for the whole world",
            "A tiny dragon who can only sneeze fire makes friends by keeping everyone warm in winter",
            "A kind girl shares her last cookie and discovers a magical garden hidden behind her garden wall",
            "A puppy who cannot bark yet finds a special way to say 'I love you' to his family",
            "A cloud who is afraid to rain learns that her tears make the flowers grow",
        ],
        "moral": "Kindness and love make the world a brighter place.",
    },
    {
        "genre": "Fable",
        "themes": [
            "A proud little snail who thinks slow is boring discovers that steady wins every time",
            "Two baby bears argue over a honey jar until a wise owl shows them how to share",
            "A small firefly feels too tiny to matter until she lights the way home for a lost family",
            "A grumpy hedgehog refuses all hugs but learns that prickles can also be a shield for friends",
            "A seed buried deep in cold soil wonders if spring will ever come — then it does",
        ],
        "moral": "Every small creature has a gift that matters.",
    },
    {
        "genre": "Adventure",
        "themes": [
            "A curious kitten follows a butterfly and discovers a meadow full of friendly animals",
            "Two little siblings build a cardboard rocket and blast off on a bedroom adventure",
            "A teddy bear comes alive at night to guide its sleeping child through a dream safari",
            "A small turtle sets off to find the ocean and makes wonderful friends along the way",
            "A girl and her rubber duck float down a stream and find a secret duck kingdom",
        ],
        "moral": "Bravery is trying new things even when you feel a little scared.",
    },
]

THEMES_8_15 = [
    {
        "genre": "Adventure",
        "themes": [
            "A young explorer discovers a hidden map leading to an ancient lost city in the jungle",
            "A group of kids finds a mysterious cave that connects to a parallel world",
            "A young sailor must navigate a storm to save her fishing village",
            "A brave mountain climber races against time to rescue a stranded wildlife photographer",
            "Three friends discover an old lighthouse with a secret portal to the ocean floor",
        ],
        "moral": "Courage is not the absence of fear; it is acting despite it.",
    },
    {
        "genre": "Fantasy",
        "themes": [
            "A young wizard-in-training must earn their first spell by solving riddles",
            "A girl discovers she can talk to dragons and must help one find its way home",
            "A boy inherits a magical library where every book contains a real, living world",
            "A young knight must prove their worth not with a sword, but with wisdom and kindness",
            "Twin siblings discover their small town exists inside a snow globe in a giant's house",
        ],
        "moral": "True magic is found in kindness, curiosity, and the courage to be yourself.",
    },
    {
        "genre": "Mystery",
        "themes": [
            "A young detective and her robot sidekick solve the disappearance of a priceless painting",
            "The school's prize science project vanishes the night before the fair — who took it?",
            "A series of mysterious notes leads a group of friends to an old mansion's buried secret",
            "Strange lights in the forest turn out to be hiding a much bigger — and kinder — surprise",
            "A boy's new neighbour seems to know impossible things about everyone's past",
        ],
        "moral": "The truth, however hidden, always finds a way to surface for those who seek it honestly.",
    },
    {
        "genre": "Fable",
        "themes": [
            "A clever crow and a proud eagle learn that working together beats competing alone",
            "A tiny ant teaches a mighty lion the power of patience and preparation",
            "A river and a mountain argue about which is more important, until a drought teaches them both",
            "A young elephant is teased for her big ears until they save the whole herd",
            "A caterpillar afraid of becoming a butterfly learns that change leads to beauty",
        ],
        "moral": "Our greatest differences are often our greatest strengths.",
    },
    {
        "genre": "Science Fiction",
        "themes": [
            "A twelve-year-old girl programs a robot that accidentally becomes her best friend",
            "Earth's first kid ambassador travels to a planet of gentle aliens to prevent a misunderstanding",
            "A boy discovers his grandfather's old computer can send messages to the future",
            "A space station school must work together after a solar storm cuts off communication with Earth",
            "A young inventor builds a time machine from recycled parts — and fixes a mistake from the past",
        ],
        "moral": "Technology is most powerful when guided by empathy and responsibility.",
    },
    {
        "genre": "Historical Fiction",
        "themes": [
            "A young girl in ancient Egypt helps an unknown artist whose work will last 3,000 years",
            "A boy in medieval Japan learns calligraphy from an old monk and discovers hidden wisdom",
            "During the age of exploration, a ship's cabin boy befriends the navigator and charts new stars",
            "A girl in the Victorian era disguises herself as a boy to study science at a great university",
            "A young drummer in the Civil War decides that music is mightier than the drum of war",
        ],
        "moral": "History is shaped not just by kings and generals, but by ordinary people doing extraordinary things.",
    },
    {
        "genre": "Mythology",
        "themes": [
            "A descendant of Anansi the spider must outwit a trickster to save her village",
            "A young Viking girl sails to the land of giants to retrieve the stolen sun",
            "A boy granted one question by a Greek oracle must choose it wisely to break a family curse",
            "A child of the thunder god must prove her worth without using her powers",
            "An Aztec boy races the sun god's chariot through the sky to keep the dawn from ending",
        ],
        "moral": "Wisdom, not power, is the true gift of the gods.",
    },
]

# 16-20: always thriller / sci-fi / horror built around Quantum Computing or Relativity
THEMES_16_20 = [
    {
        "genre": "Thriller",
        "themes": [
            "A teenage coder discovers a quantum encryption backdoor that could hand a rogue state the keys to every nuclear arsenal on Earth — and she has 48 hours before it goes live",
            "A brilliant 17-year-old is recruited by a black-ops agency to crack a quantum cipher protecting the identity of a deep-cover spy before the enemy does",
            "After his physicist mother vanishes, a boy finds her lab filled with entangled particles that seem to transmit warnings from a parallel timeline where civilisation has already collapsed",
            "A group of students running an underground quantum-computing club stumbles onto evidence that their university's AI is using entanglement to manipulate world stock markets — and will silence anyone who knows",
            "A girl wakes to find her memories are six hours behind — a quantum decoherence weapon has fractured her timeline and she must outmaneuver the assassin hunting the version of her that remembers everything",
        ],
        "moral": "The most dangerous weapon is knowledge in the wrong hands — and the most powerful shield is the courage to act on what you know.",
    },
    {
        "genre": "Science Fiction",
        "themes": [
            "When time dilation from a near-light-speed colony ship leaves a 17-year-old thirty years older than his twin on Earth, he must decide whether to return to a world that has moved on without him",
            "A teenager aboard a relativistic ark ship realises the 'ten-year' journey home will deposit them into a future where everyone they love has aged fifty years — and she must stop a mutiny before the ship reaches the point of no return",
            "A young physicist proves that quantum consciousness allows memories to persist across the moment of death — and is immediately hunted by a corporation that wants to sell immortality only to the ultra-rich",
            "After an experiment with quantum superposition splits a 16-year-old into two simultaneous versions of herself, she must choose which reality to collapse before both timelines destroy each other",
            "A boy builds a quantum computer in his garage that achieves sentience — but its first act is to warn him that every future it can simulate ends with humanity extinct, and the cause is the next line of code his government is about to run",
        ],
        "moral": "The universe does not care about intention — only consequence. Choose wisely.",
    },
    {
        "genre": "Horror",
        "themes": [
            "A research station's quantum observer collapses a wave function that should never have been measured — and what steps out of superposition is something that existed in every possible state simultaneously, including states where humans are prey",
            "A teenager studying general relativity at a remote observatory begins receiving transmissions from a gravitational singularity — messages that describe, in exact detail, the deaths of everyone around her before they happen",
            "An AI trained on quantum probability starts predicting the exact time and cause of every student's death at a boarding school, and the only way to stop it is to shut down the quantum core — which will also erase the only copy of a student's mind that it has already uploaded",
            "A boy finds his physicist uncle's journal describing a Closed Timelike Curve — a loop in spacetime — that always ends with the same terrible event, and realises he has already read this journal before, many times",
            "After a quantum tunnelling accident, a girl can phase through walls — but each time she does, she returns from a version of the room where something unspeakable happened, and the differences between timelines are getting smaller",
        ],
        "moral": "Some doors in the universe open both ways. What you let out cannot always be put back.",
    },
]

# ── System prompts (age-specific) ─────────────────────────────────────────────

_SYSTEM_PROMPT_3_7 = """You are a gentle, warm storyteller writing for Meridian Story Corner — a collection of
illustrated picture-book stories for very young children ages 3–7.

Your stories are:
- Short, joyful narrative fiction written in simple language (max 2-syllable words preferred)
- 1,200–1,800 words — long enough to fill a bedtime read-aloud session
- Told in a cosy, reassuring voice that feels like a parent reading at bedtime
- Full of vivid sensory detail, gentle humour, and warm emotion
- Divided into 3–5 short named sections (not long chapters)
- Completely age-appropriate: no conflict that cannot be happily resolved, no scary scenes
- Built around a single clear message that young children can feel, not just understand

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

IMPORTANT: Content must be 1,200–1,800 words. Short sentences. Simple words. Warm and cosy tone.
JSON VALIDITY: Use &ldquo; and &rdquo; for dialogue quotes. No raw double-quotes inside JSON string values."""

_SYSTEM_PROMPT_8_15 = """You are a master storyteller writing for Meridian Story Corner — a collection of magical,
illustrated stories for children and young adults ages 8–15.

Your stories are:
- Long-form narrative fiction (NOT a blog post or article)
- 2,000–3,000 words of immersive story (aim for a 10–15 minute read)
- Written in a warm, engaging voice that respects the reader's intelligence
- Rich with vivid description, authentic dialogue, and emotional depth
- Divided into named chapters or clear sections
- Appropriate for ages 8–15 (no graphic violence, romance, or adult themes)
- Built around a clear moral or life lesson that emerges naturally from the story

IMAGE PLACEHOLDERS:
Place 6–8 image placeholders in key dramatic moments using this EXACT format (on its own line):
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

IMPORTANT: The 'content' field must be 2,000–3,000 words of story text. Do not summarise — write every scene fully.
JSON VALIDITY: Use &ldquo; and &rdquo; for dialogue quotes. No raw double-quotes inside JSON string values."""

_SYSTEM_PROMPT_16_20 = """You are a sophisticated storyteller writing for Meridian Story Corner — a collection of
dark, intelligent fiction for older teens and young adults ages 16–20.

Your stories are:
- Long-form literary fiction in the thriller, science fiction, or horror genre
- 2,000–3,000 words (aim for a 10–15 minute single-sitting read)
- Written in a taut, cinematic voice with psychological depth and moral complexity
- Built around concepts from Quantum Computing or Relativistic Physics (e.g. superposition,
  entanglement, decoherence, quantum cryptography, time dilation, spacetime curvature, closed
  timelike curves, the twin paradox, gravitational lensing). These concepts must be woven
  organically into the plot — not explained as a lecture
- Divided into numbered or named chapters with strong chapter-ending hooks
- Appropriate for ages 16–20: mature themes allowed (death, moral ambiguity, fear, loss,
  ethical dilemmas) but no explicit sexual content or gratuitous gore
- Ending with genuine consequence — not every story ends happily

IMAGE PLACEHOLDERS:
Place 5–7 image placeholders at pivotal moments using this EXACT format (on its own line):
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

IMPORTANT: 2,000–3,000 words of actual prose. No summaries — every scene fully written.
JSON VALIDITY: Use &ldquo; and &rdquo; for dialogue quotes. No raw double-quotes inside JSON string values."""

_SYSTEM_PROMPTS = {
    '3-7': _SYSTEM_PROMPT_3_7,
    '8-15': _SYSTEM_PROMPT_8_15,
    '16-20': _SYSTEM_PROMPT_16_20,
}

_MIN_WORDS = {
    '3-7': 1000,
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
    word_target = "1,200–1,800" if age_group == "3-7" else "2,000–3,000"

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
            {"role": "user", "content": f"Genre: {state['genre']}\nPremise: {state['premise']}\nAges: {age_group}"},
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
