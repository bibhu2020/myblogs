import pytest

from meridian_agents.llm import extract_json, _inject_json_instruction


def test_extract_json_direct_parse():
    assert extract_json('{"title": "Hello", "content": "World"}') == {
        "title": "Hello",
        "content": "World",
    }


def test_extract_json_strips_markdown_fences():
    text = '```json\n{"title": "Hello", "content": "World"}\n```'
    assert extract_json(text) == {"title": "Hello", "content": "World"}


def test_extract_json_ignores_surrounding_prose():
    text = 'Here is the JSON you asked for: {"title": "Hi"} Hope that helps!'
    assert extract_json(text) == {"title": "Hi"}


def test_extract_json_strips_invalid_control_characters():
    text = '{"title": "A\x01B"}'
    assert extract_json(text) == {"title": "AB"}


def test_extract_json_field_by_field_fallback_for_unescaped_quotes():
    text = '{"title": "My Post", "content": "He said "hi" to me"}'
    result = extract_json(text)
    assert result["title"] == "My Post"
    assert result["content"] == 'He said "hi" to me'


def test_extract_json_field_by_field_fallback_for_truncated_response():
    text = '{"title": "Partial", "content": "Some unfinished text'
    result = extract_json(text)
    assert result["title"] == "Partial"
    assert result["content"] == "Some unfinished text"


def test_extract_json_raises_when_no_fields_recoverable():
    with pytest.raises(ValueError):
        extract_json("not json at all")


def test_inject_json_instruction_appends_to_existing_system_message():
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hi"},
    ]
    result = _inject_json_instruction(messages)
    assert result[0]["content"].startswith("You are helpful.")
    assert "valid JSON object" in result[0]["content"]
    assert result[1] == {"role": "user", "content": "Hi"}
    # original list must not be mutated
    assert messages[0]["content"] == "You are helpful."


def test_inject_json_instruction_prepends_when_no_system_message():
    messages = [{"role": "user", "content": "Hi"}]
    result = _inject_json_instruction(messages)
    assert result[0]["role"] == "system"
    assert "valid JSON object" in result[0]["content"]
    assert result[1] == {"role": "user", "content": "Hi"}
