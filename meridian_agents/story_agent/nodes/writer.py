"""Story writer node — generates a 4000+ word illustrated children's story."""
import json
import os
import random
import re

from openai import OpenAI

from ..state import StoryAgentState

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

THEMES = [
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

_SYSTEM_PROMPT = """You are a master storyteller writing for Meridian Story Corner — a collection of magical,
illustrated stories for children and young adults ages 8–15.

Your stories are:
- Long-form narrative fiction (NOT a blog post or article)
- At least 4,000 words of immersive story (aim for 4,500–5,500 for a 20-minute read)
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
  "content": "Full story HTML using ONLY: <h2> (chapter titles) <h3> <p> <strong> <em> <blockquote> (for inner thoughts or speech) <ul> <ol> <li>"
}

IMPORTANT: The 'content' field must be at least 4,000 words of story text. Do not summarise — write the full story with complete scenes, dialogue, and description. No markdown, only valid HTML."""


def _word_count(html: str) -> int:
    return len(re.sub(r"<[^>]+>", " ", html).split())


def _pick_theme() -> dict:
    forced_genre = os.getenv("STORY_GENRE", "").strip()
    if forced_genre:
        match = next((t for t in THEMES if t["genre"].lower() == forced_genre.lower()), None)
        category = match or random.choice(THEMES)
    else:
        category = random.choice(THEMES)
    premise = random.choice(category["themes"])
    return {
        "genre": category["genre"],
        "premise": premise,
        "moral": category["moral"],
    }


def pick_theme_node(state: StoryAgentState) -> dict:
    chosen = _pick_theme()
    print(f"📚 Story genre: {chosen['genre']}")
    print(f"📌 Premise: {chosen['premise']}")
    return {
        "genre": chosen["genre"],
        "premise": chosen["premise"],
        "moral_lesson": chosen["moral"],
    }


def write_story_node(state: StoryAgentState) -> dict:
    print("✍️  Writing story (this takes ~90s for 4000+ words)...")
    user_prompt = f"""Write a complete illustrated story based on this premise:

GENRE: {state['genre']}
PREMISE: {state['premise']}
MORAL: {state['moral_lesson']}

Requirements:
- MINIMUM 4,000 words of actual story text (aim for 4,500–5,500)
- 3–6 named chapters or clear sections
- Rich dialogue — let characters talk and reveal themselves through speech
- Vivid scene-setting — make the reader SEE and FEEL the world
- Emotional journey — the protagonist must face real challenges and grow
- 6–8 [[IMAGE: ...]] placeholders at key dramatic moments (watercolour illustration style)
- The moral should emerge naturally from events, not be stated preachy at the end

This is the FULL story — do not abbreviate, do not summarise, write every scene completely."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        max_tokens=12000,
        temperature=0.85,
    )
    data = json.loads(response.choices[0].message.content)
    wc = _word_count(data["content"])
    print(f"📊 Draft word count: {wc}")

    return {
        "story_title": data["title"],
        "story_excerpt": data["excerpt"],
        "story_content": data["content"],
        "featured_image_prompt": data["featuredImagePrompt"],
        "moral_lesson": data.get("moralLesson", state["moral_lesson"]),
        "word_count": wc,
    }


def expand_story_node(state: StoryAgentState) -> dict:
    print("📝 Story too short — expanding to meet 4,000-word minimum...")
    current = json.dumps({
        "title": state["story_title"],
        "excerpt": state["story_excerpt"],
        "content": state["story_content"],
        "featuredImagePrompt": state["featured_image_prompt"],
        "moralLesson": state["moral_lesson"],
    })

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Genre: {state['genre']}\nPremise: {state['premise']}"},
            {"role": "assistant", "content": current},
            {
                "role": "user",
                "content": (
                    f"The story is currently {state['word_count']} words — it needs at least 4,000. "
                    "Expand it by: adding more dialogue scenes between characters, deepening the "
                    "description of key locations, extending the climax with more tension and detail, "
                    "and adding a richer resolution. Maintain the same tone and characters. "
                    "Return the complete updated JSON with all the same fields."
                ),
            },
        ],
        response_format={"type": "json_object"},
        max_tokens=14000,
        temperature=0.75,
    )
    data = json.loads(response.choices[0].message.content)
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
