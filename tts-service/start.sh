#!/bin/sh
# Run the local TTS model everywhere (including HuggingFace Spaces).
# HF Spaces free tier has 2 vCPU / 16 GB RAM — local VITS inference is
# significantly faster than the HF Inference API which cold-starts per request.
exec /opt/tts-venv/bin/python /app/tts-service/app.py
