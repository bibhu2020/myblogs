#!/bin/sh
# On HuggingFace Spaces the SPACE_ID env var is always set.
# Skip loading the local model there — the gateway will use HF Inference API instead.
if [ -n "$SPACE_ID" ]; then
    echo "HuggingFace Spaces detected — local TTS model disabled, using HF Inference API"
    exit 0
fi
exec /opt/tts-venv/bin/python /app/tts-service/app.py
