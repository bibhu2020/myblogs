"""LangGraph pipeline for the rebranding agent."""
from langgraph.graph import END, StateGraph

from .state import RebrandState
from .nodes.guard import check_first_sunday_node
from .nodes.research import research_mood_node
from .nodes.planner import generate_plan_node
from .nodes.patcher import apply_changes_node
from .nodes.publisher import verify_build_node, revert_changes_node, commit_push_node


def _route_after_guard(state: RebrandState) -> str:
    return "research" if state.get("is_first_sunday") else END


def _route_after_build(state: RebrandState) -> str:
    return "publish" if state.get("build_passed") else "revert"


def build_graph():
    g = StateGraph(RebrandState)

    g.add_node("guard",    check_first_sunday_node)
    g.add_node("research", research_mood_node)
    g.add_node("plan",     generate_plan_node)
    g.add_node("patch",    apply_changes_node)
    g.add_node("build",    verify_build_node)
    g.add_node("revert",   revert_changes_node)
    g.add_node("publish",  commit_push_node)

    g.set_entry_point("guard")
    g.add_conditional_edges("guard",   _route_after_guard)
    g.add_edge("research", "plan")
    g.add_edge("plan",     "patch")
    g.add_edge("patch",    "build")
    g.add_conditional_edges("build",   _route_after_build)
    g.add_edge("revert",   END)
    g.add_edge("publish",  END)

    return g.compile()
