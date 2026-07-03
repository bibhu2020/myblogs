# Meridian — Agentic Feature Ideas

Ideas for future agentic features. Revisit when ready to implement.

---

## Content & Editorial

1. **Comment Moderation Agent** — runs on new comments, flags spam/toxicity, auto-approves clean ones, holds borderline ones for admin review. Could also generate a thoughtful reply suggestion.

2. **SEO Agent** — after a post is published, analyzes title, excerpt, headings, and keyword density; suggests improvements; can rewrite the meta description and slug if they score poorly.

3. **Related Posts Agent** — periodically clusters existing posts by semantic similarity (embeddings) and updates a "related reading" list on each post. More useful than tag-based matching.

4. **Post Update Agent** — scans published posts older than 6 months, cross-checks facts against current news, flags outdated claims, and drafts an "Editor's note" addendum without rewriting the original.

---

## Reader Engagement

5. **Newsletter Agent** — weekly digest: picks the top 3 posts + 1 story + 3 news items, writes a cohesive email narrative around them, and sends via a transactional email API (Resend/Mailgun).

6. **Quiz/Flashcard Agent** — after a blog post publishes, generates 5 comprehension questions with answers. Surfaced as an interactive "Test your knowledge" section at the bottom of the post.

7. **Personalized Feed Agent** — tracks which categories/tags a reader engages with (reads fully, plays TTS), builds a lightweight preference profile, and reorders the home feed accordingly.

---

## Media & Presentation

8. **Podcast Episode Agent** — stitches together TTS audio for the week's top post + a story + news summary into a single polished podcast episode with intro/outro music; publishes to an RSS feed compatible with podcast apps.

9. **Social Card Agent** — generates Open Graph images for each post (headline + featured image composited as a 1200×630 card) using a headless browser or canvas API, so social shares look professional.

10. **Video Reel Agent** — turns a news summary or story excerpt into a short-form narrated slideshow (text + images + TTS audio) exported as an MP4, suitable for Instagram Reels or YouTube Shorts.

---

## Operations & Intelligence

11. **Trend Scout Agent** — runs daily, monitors Google Trends / Reddit / Hacker News for rising topics that match Meridian's categories, scores them by novelty and audience fit, and queues the top 3 as post suggestions in the admin panel.

12. **Analytics Narrative Agent** — weekly, pulls read counts, TTS play rates, and comment counts from the DB; writes a 2-paragraph plain-English "what worked this week" summary for the admin dashboard.

13. **Translation Agent** — takes a published post and produces localized versions in 2–3 target languages (using Gemini), publishing them as separate posts tagged with the locale. Enables Meridian to serve multilingual audiences.

14. **Fact-Check Agent** — before a post is approved, extracts all factual claims, queries a search API for supporting sources, and attaches a confidence score + source links to the admin review UI. Admin sees a green/amber/red badge per claim.

---

## Priority Notes

Highest-leverage to implement first:
- **Trend Scout** — fuels the content pipeline with timely topics
- **Newsletter** — distribution channel to grow readership
- **Comment Moderation** — keeps the platform clean as it grows
