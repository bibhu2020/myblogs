# ── Builder (Debian slim — same base as production so native modules match) ───
FROM node:20-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 make g++ && rm -rf /var/lib/apt/lists/*

# auth-service
WORKDIR /app/auth-service
COPY auth-service/package*.json ./
RUN npm ci
COPY auth-service/ ./
RUN npm run build && npm prune --production

# blog-service
WORKDIR /app/blog-service
COPY blog-service/package*.json ./
RUN npm ci
COPY blog-service/ ./
RUN npm run build && npm prune --production

# media-service
WORKDIR /app/media-service
COPY media-service/package*.json ./
RUN npm ci
COPY media-service/ ./
RUN npm run build && npm prune --production

# api-gateway
WORKDIR /app/api-gateway
COPY api-gateway/package*.json ./
RUN npm ci
COPY api-gateway/ ./
RUN npm run build && npm prune --production

# frontend — build static assets only
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# agent — no compile step, just install deps
WORKDIR /app/agent
COPY agent/package*.json ./
RUN npm ci --omit=dev

# ── Production ────────────────────────────────────────────────────────────────
FROM node:20-slim

# System packages: nginx, supervisor, Python for local TTS service
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx supervisor python3 python3-venv \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/log/supervisor /run/nginx

# Python virtual environment — isolates TTS deps from system Python
RUN python3 -m venv /opt/tts-venv

# PyTorch CPU-only (much smaller than CUDA build; sufficient for TTS inference)
RUN /opt/tts-venv/bin/pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cpu

# TTS service dependencies
COPY tts-service/requirements.txt /app/tts-service/requirements.txt
RUN /opt/tts-venv/bin/pip install --no-cache-dir -r /app/tts-service/requirements.txt

# Download facebook/mms-tts-eng into the image at build time.
# HF_HOME points the cache into /app/models so the layer is predictable.
ENV HF_HOME=/app/models
RUN /opt/tts-venv/bin/python -c "\
from transformers import AutoTokenizer, VitsModel; \
print('Downloading mms-tts-eng tokenizer...', flush=True); \
AutoTokenizer.from_pretrained('facebook/mms-tts-eng'); \
print('Downloading mms-tts-eng model weights...', flush=True); \
VitsModel.from_pretrained('facebook/mms-tts-eng'); \
print('Model download complete.', flush=True)"

COPY tts-service/app.py   /app/tts-service/app.py
COPY tts-service/start.sh /app/tts-service/start.sh
RUN chmod +x /app/tts-service/start.sh

# auth-service
COPY --from=builder /app/auth-service/dist         /app/auth-service/dist
COPY --from=builder /app/auth-service/node_modules /app/auth-service/node_modules
COPY auth-service/package.json                     /app/auth-service/

# blog-service
COPY --from=builder /app/blog-service/dist         /app/blog-service/dist
COPY --from=builder /app/blog-service/node_modules /app/blog-service/node_modules
COPY blog-service/package.json                     /app/blog-service/

# media-service
COPY --from=builder /app/media-service/dist         /app/media-service/dist
COPY --from=builder /app/media-service/node_modules /app/media-service/node_modules
COPY media-service/package.json                     /app/media-service/
RUN mkdir -p /app/media-service/uploads

# api-gateway
COPY --from=builder /app/api-gateway/dist         /app/api-gateway/dist
COPY --from=builder /app/api-gateway/node_modules /app/api-gateway/node_modules
COPY api-gateway/package.json                     /app/api-gateway/

# Frontend static files
COPY --from=builder /app/frontend/dist /app/frontend/dist

# agent
COPY --from=builder /app/agent/node_modules /app/agent/node_modules
COPY agent/package.json  /app/agent/
COPY agent/index.js      /app/agent/
COPY agent/schedule.js   /app/agent/
COPY agent/src/          /app/agent/src/

# nginx: remove Debian defaults, install our config
RUN rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/meridian.conf

COPY supervisord.conf /etc/supervisord.conf

# Tell the api-gateway TTS endpoint to call the local Python service
ENV TTS_SERVICE_URL=http://localhost:5050

EXPOSE 7860

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
