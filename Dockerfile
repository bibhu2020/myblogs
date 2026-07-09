# ── Builder (Debian slim — same base as production so native modules match) ───
FROM node:20-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 make g++ && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# One shared install for every service + the frontend — single package.json/
# package-lock.json/nest-cli.json at the repo root, no per-service manifests.
COPY package.json package-lock.json nest-cli.json ./
RUN npm ci --legacy-peer-deps

COPY auth-service/  ./auth-service/
COPY blog-service/  ./blog-service/
COPY media-service/ ./media-service/
COPY api-gateway/   ./api-gateway/
COPY frontend/      ./frontend/

RUN npm run build:all
RUN npm prune --production --legacy-peer-deps

# ── Production ────────────────────────────────────────────────────────────────
FROM node:20-slim

# System packages: nginx, supervisor, Python for local TTS service.
# ffmpeg: encodes pre-rendered blog-post narration to mp3 for the media library.
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx supervisor python3 python3-venv espeak-ng ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/log/supervisor /run/nginx

# Python virtual environment — isolates TTS deps from system Python
RUN python3 -m venv /opt/tts-venv

# PyTorch CPU-only (much smaller than CUDA build; sufficient for inference)
RUN /opt/tts-venv/bin/pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cpu

# TTS service dependencies (kokoro + soundfile on top of the pre-installed torch)
COPY tts-service/requirements.txt /app/tts-service/requirements.txt
RUN /opt/tts-venv/bin/pip install --no-cache-dir -r /app/tts-service/requirements.txt

# Download Kokoro-82M into the image at build time.
# Pre-warm both lang_code='a' (American) and 'b' (British) pipelines so
# story/blog/news voices are all ready at first request with no cold-start.
ENV HF_HOME=/app/models
RUN /opt/tts-venv/bin/python -c "\
from kokoro import KPipeline; \
print('Downloading Kokoro-82M (American English)...', flush=True); \
KPipeline(lang_code='a'); \
print('Downloading Kokoro-82M (British English)...', flush=True); \
KPipeline(lang_code='b'); \
print('Kokoro models ready.', flush=True)"

COPY tts-service/app.py   /app/tts-service/app.py
COPY tts-service/start.sh /app/tts-service/start.sh
RUN chmod +x /app/tts-service/start.sh

# One shared, production-pruned node_modules — every service's `node dist/main.js`
# resolves into this via Node's normal upward node_modules lookup.
COPY --from=builder /app/node_modules /app/node_modules

# auth-service
COPY --from=builder /app/auth-service/dist /app/auth-service/dist

# blog-service
COPY --from=builder /app/blog-service/dist /app/blog-service/dist

# media-service
COPY --from=builder /app/media-service/dist /app/media-service/dist
RUN mkdir -p /app/media-service/uploads

# api-gateway
COPY --from=builder /app/api-gateway/dist /app/api-gateway/dist

# Frontend static files (already compiled)
COPY --from=builder /app/frontend/dist /app/frontend/dist

# nginx: remove Debian defaults, install our config
RUN rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/meridian.conf

COPY supervisord.conf /etc/supervisord.conf

# Tell the api-gateway TTS endpoint to call the local Python service
ENV TTS_SERVICE_URL=http://localhost:5050

EXPOSE 7860

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
