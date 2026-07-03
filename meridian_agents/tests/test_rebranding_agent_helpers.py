"""Tests for rebranding_agent/tools/_helpers.py: process/string utilities and
the WCAG colour-contrast math. subprocess.run is mocked in the process-helper
test since `run()` is a thin wrapper with no logic of its own to verify beyond
argument passthrough.
"""
from unittest.mock import patch, MagicMock

from meridian_agents.rebranding_agent.tools._helpers import (
    run,
    mask_token,
    norm_hex,
    replace_markers,
    relative_luminance,
    contrast_ratio,
    web_search,
)


class TestRun:
    def test_passes_args_through_to_subprocess(self):
        with patch(
            "meridian_agents.rebranding_agent.tools._helpers.subprocess.run",
            return_value=MagicMock(returncode=0),
        ) as mock_run:
            run(["git", "status"], cwd="/repo", timeout=30)
        mock_run.assert_called_once_with(
            ["git", "status"], cwd="/repo", capture_output=True, text=True, timeout=30
        )


class TestMaskToken:
    def test_masks_a_github_pat(self):
        text = "auth failed for github_pat_11ABCDEFG_somesecret"
        assert mask_token(text) == "auth failed for ***TOKEN***"

    def test_leaves_text_without_a_token_unchanged(self):
        assert mask_token("no secrets here") == "no secrets here"


class TestNormHex:
    def test_adds_a_leading_hash_when_missing(self):
        assert norm_hex("ff0000") == "#ff0000"

    def test_leaves_a_hash_prefixed_value_unchanged(self):
        assert norm_hex("#00ff00") == "#00ff00"

    def test_strips_surrounding_whitespace(self):
        assert norm_hex("  ff0000  ") == "#ff0000"


class TestReplaceMarkers:
    def test_replaces_content_between_markers(self):
        content = "before\nSTART\nold\nEND\nafter"
        result, ok = replace_markers(content, "START", "END", "new")
        assert ok is True
        assert result == "before\nSTART\nnew\nEND\nafter"

    def test_returns_unchanged_and_false_when_markers_absent(self):
        content = "no markers here"
        result, ok = replace_markers(content, "START", "END", "new")
        assert ok is False
        assert result == content


class TestRelativeLuminance:
    def test_white_has_luminance_one(self):
        assert relative_luminance("#ffffff") == 1.0

    def test_black_has_luminance_zero(self):
        assert relative_luminance("#000000") == 0.0

    def test_accepts_hex_without_leading_hash(self):
        assert relative_luminance("ffffff") == relative_luminance("#ffffff")


class TestContrastRatio:
    def test_black_on_white_is_maximum_contrast(self):
        assert round(contrast_ratio("#000000", "#ffffff"), 2) == 21.0

    def test_identical_colours_have_ratio_one(self):
        assert contrast_ratio("#336699", "#336699") == 1.0

    def test_is_order_independent(self):
        assert contrast_ratio("#123456", "#ffffff") == contrast_ratio("#ffffff", "#123456")


class TestWebSearch:
    def test_uses_responses_api_when_available(self):
        client = MagicMock()
        client.responses.create.return_value = MagicMock(output_text="search results")
        result = web_search(client, "what happened this month")
        assert result == "search results"
        client.chat.completions.create.assert_not_called()

    def test_falls_back_to_search_preview_chat_model(self):
        client = MagicMock()
        client.responses.create.side_effect = Exception("responses api unavailable")
        client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="fallback results"))]
        )
        result = web_search(client, "prompt")
        assert result == "fallback results"
        client.chat.completions.create.assert_called_once()
        assert client.chat.completions.create.call_args.kwargs["model"] == "gpt-4o-search-preview"

    def test_falls_back_to_plain_knowledge_when_both_search_paths_fail(self):
        client = MagicMock()
        client.responses.create.side_effect = Exception("unavailable")
        call_count = 0

        def chat_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("search-preview unavailable")
            return MagicMock(choices=[MagicMock(message=MagicMock(content="knowledge-based answer"))])

        client.chat.completions.create.side_effect = chat_side_effect
        result = web_search(client, "prompt")
        assert result == "knowledge-based answer"
        assert client.chat.completions.create.call_count == 2
        final_call_kwargs = client.chat.completions.create.call_args.kwargs
        assert final_call_kwargs["model"] == "gpt-4o"

    def test_returns_empty_string_when_responses_output_text_is_none(self):
        client = MagicMock()
        client.responses.create.return_value = MagicMock(output_text=None)
        result = web_search(client, "prompt")
        assert result == ""
