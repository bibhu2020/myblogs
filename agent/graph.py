from langgraph.graph import END, START, StateGraph

from .nodes.images import generate_images_node
from .nodes.mcp import (
    ensure_author_node,
    init_mcp_node,
    pick_taxonomy_node,
    publish_post_node,
)
from .nodes.research import deep_research_node, discover_trend_node
from .nodes.writer import expand_post_node, write_post_node
from .state import AgentState


def _needs_expansion(state: AgentState) -> str:
    return "expand_post" if state["word_count"] < 2200 else "generate_images"


def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("init_mcp",        init_mcp_node)
    builder.add_node("ensure_author",   ensure_author_node)
    builder.add_node("discover_trend",  discover_trend_node)
    builder.add_node("deep_research",   deep_research_node)
    builder.add_node("write_post",      write_post_node)
    builder.add_node("expand_post",     expand_post_node)
    builder.add_node("generate_images", generate_images_node)
    builder.add_node("pick_taxonomy",   pick_taxonomy_node)
    builder.add_node("publish_post",    publish_post_node)

    builder.add_edge(START,              "init_mcp")
    builder.add_edge("init_mcp",         "ensure_author")
    builder.add_edge("ensure_author",    "discover_trend")
    builder.add_edge("discover_trend",   "deep_research")
    builder.add_edge("deep_research",    "write_post")
    builder.add_conditional_edges("write_post", _needs_expansion)
    builder.add_edge("expand_post",      "generate_images")
    builder.add_edge("generate_images",  "pick_taxonomy")
    builder.add_edge("pick_taxonomy",    "publish_post")
    builder.add_edge("publish_post",     END)

    return builder.compile()
