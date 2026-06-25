"""Shared LLM client: Gemini 2.5 Flash (free) first, gpt-4o fallback."""
import html as _html
import json
import os
import re

_GEMINI_MODEL = "gemini-2.5-flash"
_OAI_MODEL = "gpt-4o"
_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# Appended to the system message when calling Gemini (no json_object response_format).
_JSON_INSTRUCTION = (
    "\n\nCRITICAL: Your entire response must be a single valid JSON object. "
    "No explanatory text, no markdown code fences (no ```json), no preamble or postamble. "
    "Begin your response immediately with { and end with }."
)


def chat_completion(
    messages: list[dict],
    *,
    max_tokens: int,
    temperature: float = 0.8,
) -> tuple[str, str]:
    """Call Gemini 2.5 Flash first; fall back to gpt-4o on any error.

    Returns (text, model_name).
    """
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=gemini_key, base_url=_GEMINI_BASE_URL)
            response = client.chat.completions.create(
                model=_GEMINI_MODEL,
                messages=_inject_json_instruction(messages),
                max_tokens=max_tokens,
                temperature=temperature,
            )
            text = (response.choices[0].message.content or "").strip()
            print(f"   [llm] model={_GEMINI_MODEL}  ~{len(text.split())} words")
            return text, _GEMINI_MODEL
        except Exception as exc:
            print(f"⚠️  Gemini Inference failed ({exc!r}) — falling back to {_OAI_MODEL}")

    from openai import OpenAI

    oai = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
    response = oai.chat.completions.create(
        model=_OAI_MODEL,
        messages=messages,
        response_format={"type": "json_object"},
        max_tokens=max_tokens,
        temperature=temperature,
    )
    text = (response.choices[0].message.content or "").strip()
    print(f"   [llm] model={_OAI_MODEL}  ~{len(text.split())} words")
    return text, _OAI_MODEL


def extract_json(text: str) -> dict:
    """Parse JSON from LLM output that may include surrounding prose or code fences."""
    text = text.strip()

    # Fast path: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned, flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Strip control characters invalid in JSON strings (not \n \r \t which are meaningful)
    sanitised = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", cleaned)
    if sanitised != cleaned:
        try:
            return json.loads(sanitised)
        except json.JSONDecodeError:
            pass
        cleaned = sanitised

    # Find outermost { ... } block
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        candidate = match.group()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    else:
        # No closing } found — response is likely truncated. Fall through to
        # field-by-field extraction on the raw cleaned text so we can salvage
        # whatever fields the LLM did produce.
        candidate = cleaned

    # Field-by-field extraction — robust against unescaped double quotes in
    # the "content" HTML (dialogue, HTML attributes, etc.).
    # Assumes "content" is the last field (true for all Meridian agent prompts).
    result = _extract_fields(candidate)
    if result and ("title" in result or "content" in result):
        return result

    raise ValueError(
        f"No valid JSON found in LLM response. First 300 chars: {text[:300]!r}"
    )


def _extract_fields(text: str) -> dict:
    """Extract individual fields from a JSON string that may have unescaped quotes.

    Handles simple string fields with a standard JSON regex, and the 'content' field
    specially: everything from '"content": "' up to the last '"' before the final '}'
    is treated as the content value, regardless of embedded double quotes.
    """
    result: dict = {}

    # Simple string fields (no HTML, no embedded quotes expected)
    for field in ("title", "excerpt", "featuredImagePrompt", "moralLesson",
                  "unsplashSearchQuery", "genre", "ageGroup"):
        m = re.search(
            rf'"{re.escape(field)}"\s*:\s*(?:"((?:[^"\\]|\\.)*)"|null)',
            text,
        )
        if m:
            val = m.group(1)  # None if matched null
            result[field] = _html.unescape(val) if val is not None else None

    # 'content' field: take everything between '"content": "' and the last '"'
    # that immediately precedes optional whitespace and the closing '}'.
    content_m = re.search(r'"content"\s*:\s*"', text)
    if content_m:
        content_start = content_m.end()
        rest = text[content_start:]
        # The JSON object closes with  "  (optional whitespace)  }
        # Find the rightmost such pattern.
        end_m = re.search(r'"\s*\}\s*$', rest)
        if end_m:
            raw = rest[: end_m.start()]
        else:
            # Fallback: strip trailing quote/brace manually
            raw = rest.rstrip()
            if raw.endswith("}"):
                raw = raw[:-1].rstrip()
            if raw.endswith('"'):
                raw = raw[:-1]
        # Unescape \" sequences the LLM may have correctly written
        result["content"] = raw.replace('\\"', '"')

    return result


def _inject_json_instruction(messages: list[dict]) -> list[dict]:
    """Append JSON-only instruction to the system message."""
    result = [dict(m) for m in messages]
    for i, msg in enumerate(result):
        if msg["role"] == "system":
            result[i]["content"] = msg["content"] + _JSON_INSTRUCTION
            return result
    # No system message — prepend one
    return [{"role": "system", "content": _JSON_INSTRUCTION.strip()}, *result]
