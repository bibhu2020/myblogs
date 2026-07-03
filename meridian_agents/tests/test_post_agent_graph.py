from meridian_agents.post_agent.graph import build_graph, _needs_expansion


def test_needs_expansion_when_word_count_below_threshold():
    assert _needs_expansion({"word_count": 900}) == "expand_post"


def test_skips_expansion_when_word_count_meets_threshold():
    assert _needs_expansion({"word_count": 1200}) == "generate_images"


def test_build_graph_compiles_without_error():
    graph = build_graph()
    assert graph is not None
