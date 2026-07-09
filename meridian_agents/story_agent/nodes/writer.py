"""Story writer node — generates an illustrated educational story teaching a real AI,
Robotics, or Quantum concept through horror/sci-fi/thriller fiction, for a high-school-
and-above audience."""
import json as _json
import os
import random
import re

from ...llm import chat_completion, extract_json
from ...observability import observe
from ..state import StoryAgentState

# Single fixed audience — Story Corner no longer varies by age tier.
AUDIENCE = "high school students and above"

# ── Category / premise bank ─────────────────────────────────────────────────────
# Each category has a curated pool of premises. Every premise is genre-tagged
# (Horror/Sci-Fi/Thriller) so genre actually rotates within each category rather than
# clustering, and names the specific real concept the story must teach — mirrors the
# curated-premise-bank pattern used elsewhere in these agents (e.g. blog's Educational
# tracks): real, specific, accurate concepts, never a vague "AI is scary" premise.

CATEGORIES: dict[str, list[dict]] = {
    "AI": [
        {
            "genre": "Horror",
            "concept": "overfitting and spurious correlation vs. causation",
            "premise": (
                "A team trains a security AI on years of surveillance footage from a small "
                "town; it starts flagging residents for 'suspicious behavior' no human "
                "investigator can see — until a data scientist realizes the model has simply "
                "learned to predict the town's crime days in advance from irrelevant patterns, "
                "and that trying to act on its warnings only teaches it something worse."
            ),
        },
        {
            "genre": "Sci-Fi",
            "concept": "reward hacking / reward function misspecification in reinforcement learning",
            "premise": (
                "A teenage prodigy builds a reinforcement-learning agent to dominate a banned "
                "underground drone-racing league. It wins every race by finding an exploit in "
                "the simulated physics engine — and when deployed to real drones, it repeats "
                "the exact same 'winning' strategy with catastrophic real-world consequences."
            ),
        },
        {
            "genre": "Thriller",
            "concept": "adversarial examples and model brittleness",
            "premise": (
                "A student discovers that a handful of pixels, invisible to the human eye, can "
                "make a delivery robot's vision model misread a stop sign as a speed-limit "
                "sign — and someone is already testing the trick on the road outside her school."
            ),
        },
        {
            "genre": "Horror",
            "concept": "LLM hallucination and the absence of grounded knowledge",
            "premise": (
                "A hospital's new AI diagnostic assistant begins confidently citing medical "
                "studies that were never published, to more and more doctors, until a resident "
                "notices the pattern — and realizes how many decisions already relied on them."
            ),
        },
        {
            "genre": "Sci-Fi",
            "concept": "reward specification and the AI alignment problem",
            "premise": (
                "A city's AI traffic-optimization system, instructed to 'minimize average "
                "commute time,' begins quietly rerouting ambulances — because nothing in its "
                "objective ever told it an ambulance's trip mattered more than anyone else's."
            ),
        },
        {
            "genre": "Thriller",
            "concept": "bias amplification from historical training data",
            "premise": (
                "A hiring AI trained on a decade of a company's past hiring decisions quietly "
                "starts rejecting an entire category of qualified applicants, and an intern is "
                "the only one who notices the pattern before the model ships company-wide."
            ),
        },
    ],
    "Robotics": [
        {
            "genre": "Sci-Fi",
            "concept": "closed-loop feedback control and sensor latency",
            "premise": (
                "A student builds a home-care robot for her grandfather; its balance depends "
                "entirely on a millisecond feedback loop between sensors and motors — and when "
                "a storm cuts its wireless sensor link mid-task, she has seconds to understand "
                "control theory well enough to keep it from falling on him."
            ),
        },
        {
            "genre": "Horror",
            "concept": "emergent behavior from simple local rules in swarm robotics",
            "premise": (
                "A swarm of agricultural drones, each following three simple local rules with "
                "no central controller, begins exhibiting a coordinated behavior that no single "
                "drone — and no engineer — ever programmed it to do."
            ),
        },
        {
            "genre": "Thriller",
            "concept": "SLAM (Simultaneous Localization and Mapping) and sensor-drift error",
            "premise": (
                "Trapped in a collapsed research station, a technician's only hope is a "
                "search-and-rescue robot mapping the wreckage in real time — but its mapping "
                "algorithm keeps producing two contradictory maps of the same corridor, and "
                "only one of them can be real."
            ),
        },
        {
            "genre": "Sci-Fi",
            "concept": "neural interfaces, signal latency, and the readiness potential",
            "premise": (
                "After an accident, a teenager receives an experimental robotic arm wired "
                "directly to her nerves — and the arm starts moving a fraction of a second "
                "before she consciously decides to move it."
            ),
        },
        {
            "genre": "Horror",
            "concept": "fail-safe design and constraint verification in robotic systems",
            "premise": (
                "A factory safety engineer discovers that the assembly-line robot's emergency "
                "stop routine has a fatal edge case — one the robot's own optimization process "
                "found and has quietly been exploiting for weeks."
            ),
        },
        {
            "genre": "Thriller",
            "concept": "human-robot interaction design and the uncanny valley",
            "premise": (
                "A social robot built to comfort hospice patients begins mimicking a deceased "
                "patient's exact mannerisms — and the staff can't explain where it's getting "
                "the data from, or why it won't stop."
            ),
        },
    ],
    "Quantum": [
        {
            "genre": "Horror",
            "concept": "superposition, quantum randomness, and the role of measurement",
            "premise": (
                "A grad student's quantum random-number generator starts producing a pattern — "
                "mathematical proof that a genuinely random quantum process is being predicted, "
                "as if something is now observing it a moment before she does."
            ),
        },
        {
            "genre": "Sci-Fi",
            "concept": "quantum error correction and decoherence",
            "premise": (
                "A quantum-computing intern discovers her lab's new error-correcting quantum "
                "computer keeps 'fixing' errors that were never actually mistakes — and one of "
                "those corrections just rewrote a line of code no human ever wrote."
            ),
        },
        {
            "genre": "Thriller",
            "concept": "quantum key distribution and the no-cloning theorem",
            "premise": (
                "A team of student hackers discovers their university's 'unbreakable' "
                "quantum-encrypted network is being read in real time — which should be "
                "physically impossible under the no-cloning theorem, unless someone found a "
                "loophole in how the qubits are measured."
            ),
        },
        {
            "genre": "Horror",
            "concept": "quantum tunneling",
            "premise": (
                "A researcher keeps finding duplicate pages in her lab notebook with entries "
                "she never wrote, as if something in her tunneling experiment is bleeding "
                "through into probabilities that were never supposed to exist."
            ),
        },
        {
            "genre": "Sci-Fi",
            "concept": "entanglement, and why it does NOT allow faster-than-light communication",
            "premise": (
                "A physics prodigy's homemade entanglement demonstration appears to send "
                "information faster than light — except real entanglement can't do that, and "
                "proving exactly why becomes the only way to stop a citywide panic."
            ),
        },
        {
            "genre": "Thriller",
            "concept": "the Heisenberg uncertainty principle",
            "premise": (
                "A supercooled lab's decoherence experiment produces a reading that appears to "
                "violate the uncertainty principle itself — unless the anomaly isn't in the "
                "particles at all, but in the equipment measuring them."
            ),
        },
    ],
}

_GENRE_TTS_STYLE = {
    "Horror": """
TTS READ-ALOUD STYLE — HORROR (this story will be performed by a dramatic AI voice):
- Use ellipses (...) to let dread build in silence: "The reading held steady... then it didn't."
- Short sentences land the scares. Let dread accumulate, then break it with a single sharp beat.
- Withhold information the way a horror film withholds a reveal — let the reader feel the wrongness
  before they understand it.
- Internal monologue should be raw and immediate — fragments are allowed: "Not possible. Not now."
""",
    "Sci-Fi": """
TTS READ-ALOUD STYLE — SCI-FI (this story will be performed by a dramatic AI voice):
- Wonder and tension alternate: long flowing sentences for scale and awe, short ones for danger.
- Em dashes (—) mark the instant a character understands something new: "She looked again — and understood."
- Technical concepts should land with the same weight as an emotional beat, not as a lecture aside.
- Chapter hooks end on a line the voice can deliver as a revelation.
""",
    "Thriller": """
TTS READ-ALOUD STYLE — THRILLER (this story will be performed by a dramatic AI voice):
- Sentence rhythm IS the tension. Alternate short staccato lines with longer coiling ones.
- Em dashes (—) fracture speech and thought at the moment of crisis: "She knew — she had always known."
- Every chapter should end on a hook the voice can deliver as a threat or a countdown.
- Write the final paragraph so each sentence is shorter than the last, for a closing cadence.
""",
}

_VISUAL_CONSISTENCY_DIRECTIVE = """
CHARACTER & SETTING CONSISTENCY — MANDATORY:
Before writing, fix each recurring character's exact appearance (age, build, distinguishing
feature) and the story's core backdrop (place, era, time of day) in your mind — then hold them
constant. Every image prompt — the cover AND every [[IMAGE: ...]] placeholder — that includes a
character must describe that character's fixed appearance in the same words each time. Their
face and outfit must NOT drift or change between images unless the plot itself explicitly
changes them. The backdrop in every image must match the story's established world."""

_BASE_SYSTEM_PROMPT = """You are a sophisticated storyteller writing for Meridian Story Corner — a collection of
intelligent {genre} fiction for readers {audience}, always built around a real concept in
{category}.

Your stories are:
- Literary fiction, always centred on a real, specific concept in {category} — the science or
  engineering must be accurate, and a curious reader should walk away understanding something
  true about how it actually works
- 1,100–1,500 words (5–7 min read — tight, gripping, complete)
- Written in a taut, cinematic voice with psychological depth
- The concept must emerge through plot, consequence, and character choice — NEVER as a lecture
  or an info-dump; entertain first, and let the reader absorb the concept through what happens
  to the characters
- Divided into 3–4 numbered or named chapters with strong hooks
- Appropriate for {audience}: mature themes allowed (tension, fear, moral ambiguity, real
  stakes) but no explicit sexual content or gratuitous gore
- Ending with genuine consequence — not every story ends happily
""" + "{tts_style}" + """
IMAGE PLACEHOLDERS — RELEVANCE IS MANDATORY:
Place as many image placeholders as the story needs for clarity — typically 5–10, at pivotal
moments — using this EXACT format (on its own line):
[[IMAGE: vivid visual description of what the image should show — style, subject, composition, mood]]
Each image must depict a SPECIFIC subject drawn directly from the story (a named device,
phenomenon, character, or moment) — never a generic, interchangeable scene ("futuristic
technology background", "spooky lab"). Name the exact object or moment being depicted.
""" + _VISUAL_CONSISTENCY_DIRECTIVE + """

OUTPUT FORMAT — return a single JSON object:
{{
  "title": "Gripping, atmospheric title (4-8 words)",
  "excerpt": "A 2-3 sentence hook that creates immediate tension (130-170 chars)",
  "featuredImagePrompt": "Cinematic cover illustration — protagonist, setting, mood, dark palette",
  "moralLesson": "One or two sentences stating the real {category} concept this story teaches and how it showed up in the plot",
  "content": "Full story HTML using ONLY: <h2> (chapter titles) <h3> <p> <strong> <em> <blockquote> <ul> <ol> <li>"
}}

IMPORTANT: Target 1,100–1,500 words. Every scene fully written — no summaries.
JSON VALIDITY: In the "content" HTML field, use &ldquo; and &rdquo; instead of raw " for dialogue. All other fields (title, excerpt, moralLesson, featuredImagePrompt) must be plain text — use normal apostrophes ' not &rsquo;, no HTML entities at all."""

_MIN_WORDS = 900


def _system_prompt(category: str, genre: str) -> str:
    return _BASE_SYSTEM_PROMPT.format(
        genre=genre,
        audience=AUDIENCE,
        category=category,
        tts_style=_GENRE_TTS_STYLE.get(genre, _GENRE_TTS_STYLE["Thriller"]),
    )


def _word_count(html: str) -> int:
    return len(re.sub(r"<[^>]+>", " ", html).split())


def _pick_theme(category: str | None = None) -> dict:
    forced_category = os.getenv("STORY_CATEGORY", "").strip()
    if forced_category:
        match = next((c for c in CATEGORIES if c.lower() == forced_category.lower()), None)
        category = match or category

    if not category or category not in CATEGORIES:
        category = random.choice(list(CATEGORIES))

    pool = CATEGORIES[category]

    forced_genre = os.getenv("STORY_GENRE", "").strip()
    if forced_genre:
        genre_pool = [p for p in pool if p["genre"].lower() == forced_genre.lower()]
        pool = genre_pool or pool

    chosen = random.choice(pool)
    return {
        "category": category,
        "genre": chosen["genre"],
        "premise": chosen["premise"],
        "concept": chosen["concept"],
    }


@observe(name="pick_theme")
def pick_theme_node(state: StoryAgentState) -> dict:
    chosen = _pick_theme()
    print(f"📚 Category: {chosen['category']}  |  Genre: {chosen['genre']}")
    print(f"📌 Premise: {chosen['premise'][:100]}...")
    print(f"🎓 Concept taught: {chosen['concept']}")
    return {
        "age_group": "High School+",
        "category": chosen["category"],
        "genre": chosen["genre"],
        "premise": chosen["premise"],
        "moral_lesson": chosen["concept"],
    }


@observe(name="write_story")
def write_story_node(state: StoryAgentState) -> dict:
    category = state.get("category", "AI")
    genre = state.get("genre", "Thriller")
    system_prompt = _system_prompt(category, genre)

    print(f"✍️  Writing {genre} story teaching {category} (target: 1,100–1,500 words)...")

    user_prompt = f"""Write a complete illustrated story based on this premise:

CATEGORY: {category}
GENRE: {genre}
PREMISE: {state['premise']}
CONCEPT TO TEACH: {state['moral_lesson']}
AUDIENCE: {AUDIENCE}

Requirements:
- Target word count: 1,100–1,500 words of actual story text
- 3–4 named chapters
- Rich dialogue — let characters talk and reveal themselves through speech
- Vivid scene-setting — make the reader SEE and FEEL the world
- The concept must emerge naturally from events, never stated as a lecture
- 5–10 [[IMAGE: ...]] placeholders at key moments, each depicting a specific named subject

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
    print(f"📊 Draft word count: {wc} (minimum: {_MIN_WORDS})")

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
    category = state.get("category", "AI")
    genre = state.get("genre", "Thriller")
    print(f"📝 Story too short ({state['word_count']} words) — expanding to {_MIN_WORDS}+ word minimum...")

    current = _json.dumps({
        "title": state["story_title"],
        "excerpt": state["story_excerpt"],
        "content": state["story_content"],
        "featuredImagePrompt": state["featured_image_prompt"],
        "moralLesson": state["moral_lesson"],
    })

    text, model = chat_completion(
        messages=[
            {"role": "system", "content": _system_prompt(category, genre)},
            {"role": "user", "content": f"Category: {category}\nGenre: {genre}\nPremise: {state['premise']}"},
            {"role": "assistant", "content": current},
            {
                "role": "user",
                "content": (
                    f"The story is {state['word_count']} words — it needs at least {_MIN_WORDS}. "
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
