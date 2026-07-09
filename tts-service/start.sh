#!/bin/sh
# Production TTS server — gunicorn with 1 worker + 8 threads.
# 1 worker: keeps a single model copy in memory (avoids duplicating ~500MB weights).
# 8 threads: accepts concurrent HTTP connections while the inference lock serialises GPU/CPU work.
# 300s timeout: CPU inference on a short chunk takes 5-15s, but a full ~1200-word blog post
# synthesized in one call (for pre-rendered mp3 generation) takes much longer — give headroom.
exec /opt/tts-venv/bin/gunicorn \
    --bind 0.0.0.0:5050 \
    --workers 1 \
    --threads 8 \
    --timeout 300 \
    --keep-alive 5 \
    --log-level info \
    app:app
