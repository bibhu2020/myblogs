from typing import Optional
from typing_extensions import TypedDict


class AgentState(TypedDict):
    # Runtime context
    server_base: str
    author_name: str
    author_email: str
    author_password: str

    # Curriculum lookup — resolved by resolve_curriculum_node, before category is picked.
    # Only consumed by discover_trend_node when the weighted pick lands on Educational.
    series_key: Optional[str]
    series_index: Optional[int]
    series_topic: Optional[str]

    # Category selected by discover_trend_node
    category_name: str
    category_pool: str
    category_research_style: str

    # Research outputs
    trend: str
    technical: str
    reactions: str
    implications: str

    # Writing outputs
    post_title: str
    post_excerpt: str
    post_content: str              # HTML with [[IMAGE: ...]] placeholders
    post_featured_image_prompt: str
    post_category_keywords: list
    post_tag_keywords: list
    post_unsplash_query: Optional[str]
    word_count: int

    # Image processing outputs
    featured_image_url: Optional[str]
    final_content: str             # HTML with placeholders resolved to <figure> tags

    # Taxonomy resolved via MCP
    category_id: Optional[int]
    tag_ids: list

    # Pending-approval result (set by save_pending_node)
    pending_post_id: Optional[int]
    pending_post_slug: Optional[str]

    # Set to True by resume when admin approves; False if rejected
    approved: Optional[bool]

    # Final published result (set after approval)
    published_slug: Optional[str]
    published_id: Optional[int]
