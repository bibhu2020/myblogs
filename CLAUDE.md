# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install all dependencies (first time setup)
npm run install:all

# Run all 5 services concurrently (recommended)
npm start

# Backend only (no frontend)
npm run start:backend

# Individual services
npm run start:auth-service     # port 3001
npm run start:blog-service     # port 3002
npm run start:media-service    # port 3003
npm run start:api-gateway      # port 3000
npm run dev:frontend           # port 5173

# Build frontend
npm run build:frontend

# Build everything (all 4 services + frontend)
npm run build:all

# Re-seed blog database (only works on empty DB — wipes and re-seeds)
npm run seed
```

Test suites exist per service (`npm run test:<service>` / `test:cov:<service>`, plus
`npm run coverage:python` for the agents) — see `npm run coverage:all`. There are no
lint scripts defined.

## Architecture

**Meridian** is a multi-topic blogging platform with a microservice backend and Vue 3 frontend.

```
Browser → Vite dev server (5173)
            ├── /api/*   → proxy → API Gateway (3000)
            └── /uploads/* → proxy → Media Service (3003)

API Gateway (3000)
  ├── forwards /api/auth/*   → Auth Service (3001)
  ├── forwards /api/posts/*  → Blog Service (3002)
  ├── forwards /api/categories/tags/comments/* → Blog Service (3002)
  └── forwards /api/media/*  → Media Service (3003)
```

### Service responsibilities

| Service | Port | DB file | Purpose |
|---|---|---|---|
| `api-gateway` | 3000 | — | Single entry point; JWT guard; proxies via axios |
| `auth-service` | 3001 | `auth.db` | Users, JWT issue/validate, bcrypt passwords |
| `blog-service` | 3002 | `blog.db` | Posts, categories, tags, comments; seeds on first boot |
| `media-service` | 3003 | `media.db` | File uploads (Multer → `media-service/uploads/`), media records |
| `frontend` | 5173 | — | Vue 3 SPA |

All four NestJS services share the same JWT secret: `myblogs-secret-key-2024`. Each service runs its own `JwtStrategy` and `PassportModule` — there is no shared auth library.

### Single root package.json (no per-service manifests)

There is exactly one `package.json`/`package-lock.json` for the whole repo (root) — no
service has its own. The 4 NestJS services are wired together via one root
`nest-cli.json` in [monorepo mode](https://docs.nestjs.com/cli/monorepo) (`"projects"`
map, each pointing at that service's existing `src/`); the frontend is built via `vite
--config frontend/vite.config.js` (its `root` is set to an absolute path derived from
`import.meta.url` inside the config file itself — a *relative* `root` resolves against
`process.cwd()`, not the config file's location, despite older Vite docs). Each service
still has its own `tsconfig.json` (with `rootDir`/`outDir` pointing at itself) and
`jest.config.js` (not a `package.json`, so it's allowed) — only the installable-package
manifests were consolidated. Run any service with `npm run start:<service>` /
`build:<service>` / `test:<service>` from the repo root; `npm run build:all` builds
everything. The production `Dockerfile` does one `npm ci` + `npm run build:all`, then
copies a single shared `node_modules` into the final image — Node's `require()`
resolution walks up from each service's `dist/main.js` to find it.

### API Gateway pattern

`api-gateway/src/proxy.service.ts` — `ProxyService.forward(service, path, method, data?, headers?)` makes direct HTTP calls to internal service URLs. File uploads use `forwardWithFile()` which streams a `form-data` multipart body. The gateway holds JWT guards; internal services trust the forwarded `Authorization` header.

### Database

Each service uses **better-sqlite3** via TypeORM with `synchronize: true` (schema auto-migrates on startup). DB files live at the service root:
- `auth-service/auth.db`
- `blog-service/blog.db`
- `media-service/media.db`

DB files and `media-service/uploads/` are **committed to git** (`.gitignore` explicitly excludes `*/dist/` only).

### Blog service seeding

`blog-service/src/seed.service.ts` (implements `OnModuleInit`) seeds categories, tags, and sample posts **only when the categories table is empty**. To force a re-seed, delete `blog.db` and restart. To add seed data without a fresh DB, insert directly via Python's `sqlite3` module (the preferred approach used throughout this project).

### Frontend structure

- **`src/stores/`** — Pinia stores: `blog.js` (posts/categories/tags, fetched lazily), `auth.js` (JWT in localStorage, axios default header set on login)
- **`src/api.js`** — Axios instance with `baseURL: '/api'`; token injected from localStorage on load
- **`src/views/admin/`** — Protected by `router.beforeEach` checking `auth.isLoggedIn`; admin login credentials are `admin@myblogs.com` / `admin123`
- **`src/components/LogoMark.vue`** — Reusable SVG logo mark (Meridian globe icon); imported wherever the brand logo appears

### Tailwind CSS v4 (critical)

The project uses **Tailwind CSS v4** via `@tailwindcss/vite`. Configuration is **CSS-first** in `frontend/src/style.css`:
- Use `@plugin` (not `@import`) for plugins: `@plugin "@tailwindcss/typography"`
- Theme tokens live in `@theme {}` blocks
- The `@tailwindcss/typography` plugin provides `prose` classes used in blog post content

### Rich text editor

The admin post editor (`PostEditor.vue`) uses **TipTap** with:
- `StarterKit.configure({ codeBlock: false })` — built-in code block disabled
- `CodeBlockLowlight` with `createLowlight(common)` — syntax-highlighted code blocks
- `Image` and `Link` extensions

Blog post rendering (`BlogPost.vue`) applies `hljs.highlightElement()` after `v-html` renders, targeting `.post-content pre code`.

### Media files

Uploaded files land in `media-service/uploads/` with UUID filenames. The frontend accesses them at `/uploads/<filename>` (proxied by Vite to port 3003). Post `featuredImage` fields store either a full URL (Unsplash) or a `/uploads/` path.

### Adding data to a running system

Since `SeedService` only runs on empty DB, use Python to insert directly:

```python
import sqlite3, json
conn = sqlite3.connect('blog-service/blog.db')
conn.execute("INSERT INTO categories (name, slug, description, color, icon) VALUES (?,?,?,?,?)", (...))
conn.commit()
conn.close()
```

Tag-post relationships use the junction table `posts_tags_tags` with columns `"postsId"` and `"tagsId"`.
