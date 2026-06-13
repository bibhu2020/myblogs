import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from .graph import build_graph  # noqa: E402 — must load .env before importing graph

SERVER_BASE       = os.getenv("SERVER_BASE", "https://mishrabP-myblogs.hf.space")
AUTHOR_NAME       = os.getenv("AGENT_AUTHOR_NAME", "Meridian AI Researcher")
AUTHOR_EMAIL      = os.getenv("AGENT_AUTHOR_EMAIL", "ai.researcher@meridian.blog")
AUTHOR_PASSWORD   = os.getenv("AGENT_AUTHOR_PASSWORD", f"MeridianAI{time.strftime('%Y')}!rsch")


def run_agent() -> dict:
    print("\n╔══════════════════════════════════════════╗")
    print("║        Meridian AI Blog Agent v2         ║")
    print("║           LangGraph Edition              ║")
    print("╚══════════════════════════════════════════╝\n")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required. Add it to .env or export it first.")

    graph = build_graph()
    t0 = time.time()

    initial: dict = {
        "server_base": SERVER_BASE,
        "author_name": AUTHOR_NAME,
        "author_email": AUTHOR_EMAIL,
        "author_password": AUTHOR_PASSWORD,
        # Research
        "category_name": "",
        "category_pool": "",
        "category_research_style": "",
        "trend": "",
        "technical": "",
        "reactions": "",
        "implications": "",
        # Writing
        "post_title": "",
        "post_excerpt": "",
        "post_content": "",
        "post_featured_image_prompt": "",
        "post_category_keywords": [],
        "post_tag_keywords": [],
        "post_unsplash_query": None,
        "word_count": 0,
        # Images
        "featured_image_url": None,
        "final_content": "",
        # Taxonomy
        "category_id": None,
        "tag_ids": [],
        # Result
        "published_slug": None,
        "published_id": None,
    }

    final = graph.invoke(initial)
    elapsed = round(time.time() - t0)

    slug = final.get("published_slug") or final.get("published_id") or "(see site)"
    print("\n╔══════════════════════════════════════════╗")
    print("║  ✅  Post published successfully!        ║")
    print("╚══════════════════════════════════════════╝")
    print(f"  Title:  {final['post_title']}")
    print(f"  Slug:   {slug}")
    print(f"  Author: {AUTHOR_NAME}")
    if final.get("featured_image_url"):
        print(f"  Image:  {final['featured_image_url']}")
    print(f"  Time:   {elapsed}s\n")

    return final
