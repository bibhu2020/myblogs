"""Image generation for story illustrations — children's book watercolour style."""
import os
import re
import time

from ...post_agent.nodes.images import _generate_image, _upload_image

# Prefix injected before every illustration prompt to enforce child-friendly art style
_STYLE_PREFIX = (
    "Children's book watercolour illustration, warm and vibrant colours, "
    "friendly and whimsical style, safe for all ages, detailed storybook art: "
)


def generate_story_images_node(state: dict) -> dict:
    server_base = os.getenv("SERVER_BASE", "https://mishrabp-meridian.hf.space")
    content = state["story_content"]

    # Featured cover image
    print("🎨 Generating story cover image...")
    cover_url = None
    cover_prompt = _STYLE_PREFIX + state["featured_image_prompt"]
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
            styled_prompt = _STYLE_PREFIX + raw_prompt[:450]
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
