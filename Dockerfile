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

# api-gateway — msedge-tts has a pnpm-only preinstall script; skip all scripts
WORKDIR /app/api-gateway
COPY api-gateway/package*.json ./
RUN npm ci --ignore-scripts
COPY api-gateway/ ./
RUN npm run build && npm prune --production

# frontend — build static assets only
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Production ────────────────────────────────────────────────────────────────
FROM node:20-slim

# System packages: nginx, supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx supervisor \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/log/supervisor /run/nginx

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

# nginx: remove Debian defaults, install our config
RUN rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/meridian.conf

COPY supervisord.conf /etc/supervisord.conf

EXPOSE 7860

# Tell Docker (and HF Spaces) the container is healthy once nginx serves a 200 on port 7860.
# start-period=60s gives NestJS services time to finish TypeORM sync + seeding before checks begin.
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=3 \
    CMD node -e "require('http').get('http://localhost:7860/',(r)=>process.exit(r.statusCode===200?0:1)).on('error',()=>process.exit(1))"

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
