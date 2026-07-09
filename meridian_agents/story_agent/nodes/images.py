"""Image generation for story illustrations — genre-matched mature digital art style."""
import os
import re
import time

from ...observability import observe
from ...post_agent.nodes.images import _generate_image, _upload_image

# Prefix injected before every illustration prompt — matches the story's genre so the
# art style reinforces the mood (dark/ominous for Horror, clean/futuristic for Sci-Fi,
# high-contrast/moody for Thriller).
_STYLE_PREFIXES = {
    "Horror": (
        "Dark, atmospheric digital illustration, ominous lighting, unsettling mood, "
        "high detail, cinematic horror art style: "
    ),
    "Sci-Fi": (
        "Clean, cinematic science-fiction digital illustration, futuristic technology, "
        "dramatic lighting, high detail, photorealistic sci-fi concept art style: "
    ),
    "Thriller": (
        "High-contrast, tense cinematic digital illustration, dramatic shadows, moody "
        "colour grading, high detail, psychological-thriller film-still style: "
    ),
}
_DEFAULT_STYLE_PREFIX = _STYLE_PREFIXES["Thriller"]


@observe(name="generate_story_images")
def generate_story_images_node(state: dict) -> dict:
    server_base = os.getenv("SERVER_BASE", "https://mishrabp-meridian.hf.space")
    content = state["story_content"]
    style_prefix = _STYLE_PREFIXES.get(state.get("genre", ""), _DEFAULT_STYLE_PREFIX)

    # Featured cover image
    print(f"🎨 Generating story cover image ({state.get('genre', 'Thriller')} style)...")
    cover_url = None
    cover_prompt = style_prefix + state["featured_image_prompt"]
    result = _generate_image(cover_prompt, size="1792x1024")
    if result:
        buf, mime = result
        cover_url = _upload_image(buf, mime, state["featured_image_prompt"][:120], server_base)
        print(f"  ✅ Cover: {cover_url}")
    else:
        print("  ⚠️  Cover image generation failed — story will publish without cover")

    # Inline illustration placeholders
    placeholders = list(re.finditer(r"\[\[IMAGE:\s*([\s\S]*?)\]\]", content))
    if placeholders:
        print(f"🖼️  Generating {len(placeholders)} story illustration(s)...")
        for match in placeholders:
            full_match = match.group(0)
            raw_prompt = match.group(1).strip()
            alt = re.sub(r"\s+", " ", raw_prompt)[:120]
            styled_prompt = style_prefix + raw_prompt[:450]
            try:
                print(f'  → "{alt[:65]}"')
                img_result = _generate_image(styled_prompt, size="1024x1024")
                if not img_result:
                    content = content.replace(full_match, "", 1)
                    continue
                buf, mime = img_result
                url = _upload_image(buf, mime, alt, server_base)
                escaped_alt = alt.replace('"', "&quot;")
                figure = (
                    f'<figure class="my-8 text-center">'
                    f'<img src="{url}" alt="{escaped_alt}" '
                    f'class="w-full rounded-2xl shadow-lg mx-auto max-h-96 object-cover" />'
                    f'<figcaption class="mt-3 text-sm text-indigo-400 italic">{alt}</figcaption>'
                    f"</figure>"
                )
                content = content.replace(full_match, figure, 1)
                print(f"  ✅ {url}")
            except Exception as exc:
                print(f"  ❌ Illustration failed: {exc}")
                content = content.replace(full_match, "", 1)
            time.sleep(2)

    return {"featured_image_url": cover_url, "final_content": content}
