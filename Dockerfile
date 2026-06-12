# ── Builder ───────────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

# Native module compilation (better-sqlite3 is in prod deps)
RUN apk add --no-cache python3 make g++

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

# ── Production ────────────────────────────────────────────────────────────────
FROM node:20-alpine

RUN apk add --no-cache nginx supervisor && \
    mkdir -p /var/log/supervisor /run/nginx

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

# nginx + supervisor config
COPY nginx.conf       /etc/nginx/http.d/default.conf
COPY supervisord.conf /etc/supervisord.conf

EXPOSE 7860

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
