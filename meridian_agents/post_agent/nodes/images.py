import os
import re
import time
from io import BytesIO

import requests

from ...auth import make_agent_jwt
from ..state import AgentState


def _upload_image(buf: bytes, mime: str, alt: str, server_base: str) -> str:
    jwt = make_agent_jwt()
    ext = "jpg" if "jpeg" in mime else "webp" if "webp" in mime else "png"
    files = {"file": (f"ai-{int(time.time())}.{ext}", BytesIO(buf), mime)}
    res = requests.post(
        f"{server_base}/api/media/upload",
        headers={"Authorization": f"Bearer {jwt}"},
        files=files,
        data={"alt": alt[:200]},
        timeout=120,
    )
    if not res.ok:
        raise RuntimeError(f"Upload failed ({res.status_code}): {res.text[:300]}")
    url = res.json().get("url")
    if not url:
        raise RuntimeError(f"Upload response missing url: {res.text[:300]}")
    return url


_HF_BASE = "https://router.huggingface.co/hf-inference/models"


def _hf_infer(model: str, payload: dict, timeout: int = 180) -> requests.Response:
    """POST to HuggingFace Inference API (new router endpoint) with one 503 retry."""
    token = os.getenv("HF_TOKEN", "")
    if not token:
        raise RuntimeError("HF_TOKEN not set")
    url = f"{_HF_BASE}/{model}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    res = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if res.status_code == 503:
        wait = min(res.json().get("estimated_time", 30), 60)
        print(f"  ⏳ {model.split('/')[-1]} loading, retrying in {wait:.0f}s...")
        time.sleep(wait)
        res = requests.post(url, headers=headers, json=payload, timeout=timeout)
    res.raise_for_status()
    return res


def _try_flux_dev(prompt: str) -> tuple[bytes, str]:
    """FLUX.1-dev — photorealistic DSLR-quality images via HF Inference API.
    Attempts FLUX.1-dev (higher-quality, 30-step); if the model is unavailable
    on the free inference tier (410 Gone / not-supported), retries with
    FLUX.1-schnell using a DSLR-optimised prompt prefix for the best realism
    available without a paid HF subscription."""
    dslr_prompt = (
        "DSLR photography, photorealistic, sharp focus, natural lighting, "
        f"8K ultra-detailed, {prompt[:440]}"
    )
    # Try the full FLUX.1-dev model first
    try:
        res = _hf_infer(
            "black-forest-labs/FLUX.1-dev",
            {"inputs": dslr_prompt, "parameters": {"num_inference_steps": 30}},
            timeout=180,
        )
        mime = res.headers.get("content-type", "image/jpeg").split(";")[0]
        return res.content, mime
    except requests.HTTPError as exc:
        # 410 = removed from free tier; 400 = not supported by provider
        if exc.response is not None and exc.response.status_code in (400, 410):
            print("  ℹ️  FLUX.1-dev unavailable on free tier — using schnell + DSLR prompt")
        else:
            raise
    # Fallback: FLUX.1-schnell with DSLR prompt prefix
    res = _hf_infer(
        "black-forest-labs/FLUX.1-schnell",
        {"inputs": dslr_prompt},
        timeout=120,
    )
    mime = res.headers.get("content-type", "image/jpeg").split(";")[0]
    return res.content, mime


def _try_flux(prompt: str) -> tuple[bytes, str]:
    res = _hf_infer(
        "black-forest-labs/FLUX.1-schnell",
        {"inputs": prompt[:500]},
        timeout=120,
    )
    mime = res.headers.get("content-type", "image/jpeg").split(";")[0]
    return res.content, mime


_IMAGEN_ASPECT = {
    "1792x1024": "16:9",
    "1024x1792": "9:16",
    "1024x1024": "1:1",
}


def _try_gemini(prompt: str, size: str = "1024x1024") -> tuple[bytes, str]:
    """Two-step Gemini pipeline: Gemini Flash enhances the prompt, Imagen 3 renders it.

    Step 1 is best-effort — if Flash is unavailable the original prompt is used.
    Step 2 tries imagen-3.0-generate-002 then imagen-3.0-fast-generate-001.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    from google import genai  # google-genai package
    client = genai.Client(api_key=api_key)

    # ── Step 1: enhance prompt with Gemini Flash ───────────────────────────
    imagen_prompt = prompt
    try:
        text_resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=(
                "Rewrite the following as a vivid, specific image generation prompt for Imagen 3. "
                "Focus on visual details: lighting, composition, colour palette, style, mood. "
                "Return ONLY the improved prompt — no explanation, no preamble.\n\n"
                f"{prompt[:600]}"
            ),
        )
        if text_resp.text and text_resp.text.strip():
            imagen_prompt = text_resp.text.strip()
            print(f"  ✦ Gemini enhanced prompt: {imagen_prompt[:80]}…")
    except Exception as e:
        print(f"  ℹ️  Gemini prompt enhancement skipped ({e}) — using original")

    # ── Step 2: generate image with Imagen 3 ──────────────────────────────
    aspect_ratio = _IMAGEN_ASPECT.get(size, "1:1")
    last_exc: Exception = RuntimeError("No Imagen model succeeded")
    for model_name in ("imagen-4.0-generate-001", "imagen-4.0-fast-generate-001"):
        try:
            result = client.models.generate_images(
                model=model_name,
                prompt=imagen_prompt[:1000],
                config=dict(
                    number_of_images=1,
                    aspect_ratio=aspect_ratio,
                    output_mime_type="image/jpeg",
                ),
            )
            if result.generated_images:
                return result.generated_images[0].image.image_bytes, "image/jpeg"
            last_exc = RuntimeError("Imagen returned 0 images")
        except Exception as exc:
            last_exc = exc
    raise RuntimeError(f"Gemini Imagen: {last_exc}")


def _try_unsplash(topic: str) -> tuple[bytes, str, str | None]:
    key = os.getenv("UNSPLASH_ACCESS_KEY", "")
    if not key:
        raise RuntimeError("UNSPLASH_ACCESS_KEY not set")
    query = " ".join(re.sub(r"[^\w\s]", " ", topic).split()[:5])
    res = requests.get(
        "https://api.unsplash.com/photos/random",
        params={"query": query, "orientation": "landscape", "content_filter": "high"},
        headers={"Authorization": f"Client-ID {key}"},
        timeout=30,
    )
    res.raise_for_status()
    data = res.json()
    img_url = data["urls"]["regular"]
    img_res = requests.get(img_url, timeout=60)
    img_res.raise_for_status()
    mime = img_res.headers.get("content-type", "image/jpeg").split(";")[0]
    credit = data.get("user", {}).get("name")
    return img_res.content, mime, credit


def _generate_image(
    prompt: str,
    size: str = "1024x1024",
    category: str = "",
    unsplash_query: str = "",
) -> tuple[bytes, str] | None:
    if category == "Travel":
        try:
            buf, mime, credit = _try_unsplash(unsplash_query or prompt)
            note = f" (photo by {credit} on Unsplash)" if credit else " (Unsplash)"
            print(f"  ✓ Real travel photo{note}")
            return buf, mime
        except Exception as e:
            print(f"  ⚠️  Unsplash (travel): {e} — falling back to AI generation")

    ai_prompt = f"{prompt}. Professional, high-quality, no text overlays, no watermarks."
    providers: list[tuple[str, object]] = [
        ("Gemini",         lambda: _try_gemini(ai_prompt, size)),  # Imagen 3 via Gemini Flash
        ("FLUX.1-dev",     lambda: _try_flux_dev(ai_prompt)),      # DSLR HF fallback
        ("FLUX.1-schnell", lambda: _try_flux(ai_prompt)),          # fast HF fallback
    ]
    for name, fn in providers:
        try:
            buf, mime = fn()  # type: ignore[misc]
            print(f"  ✓ {name}")
            return buf, mime
        except Exception as e:
            print(f"  ⚠️  {name}: {e}")

    try:
        buf, mime, credit = _try_unsplash(prompt)
        note = f" (photo by {credit})" if credit else ""
        print(f"  ✓ Unsplash stock{note}")
        return buf, mime
    except Exception as e:
        print(f"  ⚠️  Unsplash stock: {e}")

    return None


# ── LangGraph node ────────────────────────────────────────────────────────────

def generate_images_node(state: AgentState) -> dict:
    category = state["category_name"]
    server_base = os.getenv("SERVER_BASE", "https://mishrabP-myblogs.hf.space")

    # Featured image
    is_travel = category == "Travel"
    label = "📸 Fetching real travel photo..." if is_travel else "🎨 Generating featured image (1792×1024)..."
    print(label)

    featured_url = None
    result = _generate_image(
        state["post_featured_image_prompt"],
        size="1792x1024",
        category=category,
        unsplash_query=state.get("post_unsplash_query") or "",
    )
    if result:
        buf, mime = result
        featured_url = _upload_image(buf, mime, state["post_featured_image_prompt"][:120], server_base)
        print(f"  ✅ Featured: {featured_url}")
    else:
        print("  ⚠️  No image source available — post will publish without a featured image")

    # Inline images
    content = state["post_content"]
    placeholders = list(re.finditer(r"\[\[IMAGE:\s*([\s\S]*?)\]\]", content))
    if placeholders:
        icon = "📸" if is_travel else "🖼️"
        print(f"{icon}  Processing {len(placeholders)} inline image(s)...")
        for match in placeholders:
            full_match = match.group(0)
            prompt = match.group(1).strip()
            # Strip any LLM-generated label prefix ("detailed DALL-E 3 prompt — ", etc.)
            clean = re.sub(r"^[\w\s\-]+(?:prompt|image)\s*[—–\-:]+\s*", "", prompt, flags=re.IGNORECASE).strip()
            alt = re.sub(r"\s+", " ", clean or prompt)[:120]
            try:
                print(f'  → "{alt[:65]}"')
                img_result = _generate_image(prompt, size="1024x1024", category=category)
                if not img_result:
                    print("  ⚠️  All image sources failed — removing placeholder")
                    content = content.replace(full_match, "", 1)
                    continue
                buf, mime = img_result
                url = _upload_image(buf, mime, alt, server_base)
                escaped_alt = alt.replace('"', "&quot;")
                figure = (
                    f'<figure class="my-8 text-center">'
                    f'<img src="{url}" alt="{escaped_alt}" '
                    f'class="w-full rounded-xl shadow-lg mx-auto" />'
                    f'<figcaption class="mt-3 text-sm text-gray-500 italic">{alt}</figcaption>'
                    f"</figure>"
                )
                content = content.replace(full_match, figure, 1)
                print(f"  ✅ {url}")
            except Exception as e:
                print(f"  ❌ Image failed: {e}")
                content = content.replace(full_match, "", 1)
            time.sleep(2)

    return {"featured_image_url": featured_url, "final_content": content}
