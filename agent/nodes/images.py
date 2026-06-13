import base64
import hashlib
import hmac
import json
import os
import re
import time
from io import BytesIO

import requests
from openai import OpenAI

from ..state import AgentState

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


def _make_agent_jwt() -> str:
    secret = os.getenv("JWT_SECRET", "myblogs-secret-key-2024").encode()
    now = int(time.time())

    def b64url(obj: dict) -> str:
        return (
            base64.urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode())
            .rstrip(b"=")
            .decode()
        )

    header = b64url({"alg": "HS256", "typ": "JWT"})
    payload = b64url({
        "sub": 0, "id": 0,
        "email": "ai-agent@meridian.internal",
        "name": "AI Agent",
        "role": "admin",
        "iat": now,
        "exp": now + 3600,
    })
    signing_input = f"{header}.{payload}".encode()
    sig = (
        base64.urlsafe_b64encode(
            hmac.new(secret, signing_input, hashlib.sha256).digest()
        )
        .rstrip(b"=")
        .decode()
    )
    return f"{header}.{payload}.{sig}"


def _upload_image(buf: bytes, mime: str, alt: str, server_base: str) -> str:
    jwt = _make_agent_jwt()
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


def _try_dalle3(prompt: str, size: str) -> tuple[bytes, str]:
    valid = {"1024x1024", "1792x1024", "1024x1792"}
    resp = client.images.generate(
        model="dall-e-3",
        prompt=prompt[:900],
        size=size if size in valid else "1024x1024",
        quality="hd",
        n=1,
    )
    url = resp.data[0].url
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.content, "image/png"


def _try_dalle2(prompt: str) -> tuple[bytes, str]:
    resp = client.images.generate(model="dall-e-2", prompt=prompt[:1000], size="1024x1024", n=1)
    url = resp.data[0].url
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.content, "image/png"


def _try_flux(prompt: str) -> tuple[bytes, str]:
    token = os.getenv("HF_TOKEN", "")
    if not token:
        raise RuntimeError("HF_TOKEN not set")
    api_url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    res = requests.post(api_url, headers=headers, json={"inputs": prompt[:500]}, timeout=120)
    if res.status_code == 503:
        wait = min(res.json().get("estimated_time", 20), 30)
        print(f"  ⏳ FLUX loading, retrying in {wait:.0f}s...")
        time.sleep(wait)
        res = requests.post(api_url, headers=headers, json={"inputs": prompt[:500]}, timeout=120)
    res.raise_for_status()
    mime = res.headers.get("content-type", "image/jpeg").split(";")[0]
    return res.content, mime


def _try_gemini(prompt: str) -> tuple[bytes, str]:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import google.generativeai as genai
    genai.configure(api_key=api_key)
    # Use Imagen 3 if available; fall back to gemini-2.0-flash-exp inline_data
    try:
        model = genai.ImageGenerationModel("imagen-3.0-generate-002")
        result = model.generate_images(prompt=prompt[:800], number_of_images=1)
        img = result.images[0]
        return img._image_bytes, "image/png"
    except Exception:
        pass
    model = genai.GenerativeModel("gemini-2.0-flash-exp")
    response = model.generate_content(
        [{"text": prompt[:800]}, {"text": "Generate an image based on this description."}],
        generation_config={"response_modalities": ["IMAGE", "TEXT"]},
    )
    for part in response.parts:
        if hasattr(part, "inline_data") and part.inline_data.mime_type.startswith("image/"):
            return base64.b64decode(part.inline_data.data), part.inline_data.mime_type
    raise RuntimeError("Gemini returned no image data")


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

    ai_prompt = f"{prompt}. Professional, high-quality illustration, no text overlays, no watermarks."
    providers: list[tuple[str, object]] = [
        ("DALL-E 3", lambda: _try_dalle3(ai_prompt, size)),
        ("DALL-E 2", lambda: _try_dalle2(ai_prompt)),
        ("FLUX.1-schnell", lambda: _try_flux(ai_prompt)),
        ("Gemini", lambda: _try_gemini(ai_prompt)),
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
            alt = re.sub(r"\s+", " ", prompt)[:120]
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
