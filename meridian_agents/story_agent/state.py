from typing import Optional
from typing_extensions import TypedDict


class StoryAgentState(TypedDict):
    # Config
    server_base: str
    author_name: str

    # Age group + theme selected by pick_theme step
    age_group: str              # '2-7', '8-15', or '16+'
    theme: str
    genre: str
    premise: str
    moral_lesson: str

    # Writing output
    story_title: str
    story_excerpt: str
    story_content: str          # HTML with [[IMAGE: ...]] placeholders
    featured_image_prompt: str
    word_count: int

    # Image processing output
    featured_image_url: Optional[str]
    final_content: str          # HTML with placeholders resolved

    # Saved result
    pending_story_id: Optional[int]
    pending_story_slug: Optional[str]
