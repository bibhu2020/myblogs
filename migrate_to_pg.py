import sqlite3
import psycopg2
from psycopg2.extras import execute_values

PG_URL = "postgresql://neondb_owner:npg_96zZibhKwEcG@ep-delicate-fire-atgeeiwh-pooler.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

pg = psycopg2.connect(PG_URL)
pg.autocommit = False
cur = pg.cursor()

# ── Schema ────────────────────────────────────────────────────────────────────

cur.execute("""
CREATE TABLE IF NOT EXISTS auth_users (
  id                SERIAL PRIMARY KEY,
  email             VARCHAR(255) NOT NULL UNIQUE,
  password          VARCHAR(255) NOT NULL,
  name              VARCHAR(255) NOT NULL,
  bio               VARCHAR(255),
  avatar            VARCHAR(255),
  role              VARCHAR(255) NOT NULL DEFAULT 'guest',
  "isActive"        BOOLEAN NOT NULL DEFAULT true,
  "createdAt"       TIMESTAMPTZ NOT NULL DEFAULT now(),
  "updatedAt"       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS blog_categories (
  id            SERIAL PRIMARY KEY,
  name          VARCHAR(255) NOT NULL UNIQUE,
  slug          VARCHAR(255) NOT NULL UNIQUE,
  description   VARCHAR(255),
  color         VARCHAR(255),
  icon          VARCHAR(255),
  "createdAt"   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS blog_tags (
  id    SERIAL PRIMARY KEY,
  name  VARCHAR(255) NOT NULL UNIQUE,
  slug  VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS blog_posts (
  id              SERIAL PRIMARY KEY,
  title           VARCHAR(255) NOT NULL,
  slug            VARCHAR(255) NOT NULL UNIQUE,
  content         TEXT NOT NULL,
  excerpt         TEXT,
  "featuredImage" VARCHAR(255),
  gallery         TEXT,
  status          VARCHAR(255) NOT NULL DEFAULT 'draft',
  "authorId"      INTEGER NOT NULL,
  "authorName"    VARCHAR(255),
  "readTime"      INTEGER,
  views           INTEGER NOT NULL DEFAULT 0,
  "categoryId"    INTEGER REFERENCES blog_categories(id),
  "createdAt"     TIMESTAMPTZ NOT NULL DEFAULT now(),
  "updatedAt"     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS blog_posts_tags_tags (
  "postsId"  INTEGER NOT NULL REFERENCES blog_posts(id) ON DELETE CASCADE,
  "tagsId"   INTEGER NOT NULL REFERENCES blog_tags(id) ON DELETE CASCADE,
  PRIMARY KEY ("postsId", "tagsId")
);

CREATE TABLE IF NOT EXISTS blog_comments (
  id            SERIAL PRIMARY KEY,
  content       TEXT NOT NULL,
  "authorName"  VARCHAR(255) NOT NULL,
  "authorEmail" VARCHAR(255),
  "authorId"    INTEGER,
  approved      BOOLEAN NOT NULL DEFAULT false,
  "postId"      INTEGER REFERENCES blog_posts(id) ON DELETE CASCADE,
  "createdAt"   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS media_media (
  id               SERIAL PRIMARY KEY,
  filename         VARCHAR(255) NOT NULL,
  "originalName"   VARCHAR(255) NOT NULL,
  mimetype         VARCHAR(255) NOT NULL,
  size             INTEGER NOT NULL,
  url              VARCHAR(255) NOT NULL,
  alt              VARCHAR(255),
  "uploadedBy"     INTEGER,
  "createdAt"      TIMESTAMPTZ NOT NULL DEFAULT now()
);
""")

# ── Data migration ─────────────────────────────────────────────────────────────

def migrate(sqlite_path, table_src, table_dst, columns, skip_if_exists=False):
    if skip_if_exists:
        cur.execute(f'SELECT COUNT(*) FROM {table_dst}')
        if cur.fetchone()[0] > 0:
            print(f"  {table_dst}: already has data, skipping")
            return
    conn = sqlite3.connect(sqlite_path)
    cols_quoted = ", ".join('"' + c + '"' for c in columns)
    rows = conn.execute(f'SELECT {cols_quoted} FROM "{table_src}"').fetchall()
    conn.close()
    if not rows:
        print(f"  {table_dst}: 0 rows")
        return
    execute_values(cur, f'INSERT INTO {table_dst} ({cols_quoted}) VALUES %s ON CONFLICT DO NOTHING', rows)
    print(f"  {table_dst}: {len(rows)} rows migrated")

print("Migrating auth_users...")
migrate('auth-service/auth.db', 'users', 'auth_users',
        ['id','email','password','name','bio','avatar','role','isActive','createdAt','updatedAt'],
        skip_if_exists=True)

# Wipe blog/media tables so IDs from SQLite are inserted cleanly
print("Clearing existing blog/media tables...")
cur.execute("""
  TRUNCATE blog_posts_tags_tags, blog_comments, blog_posts,
           blog_categories, blog_tags, media_media RESTART IDENTITY CASCADE
""")

print("Migrating blog_categories...")
migrate('blog-service/blog.db', 'categories', 'blog_categories',
        ['id','name','slug','description','color','icon','createdAt'])

print("Migrating blog_tags...")
migrate('blog-service/blog.db', 'tags', 'blog_tags',
        ['id','name','slug'])

print("Migrating blog_posts...")
migrate('blog-service/blog.db', 'posts', 'blog_posts',
        ['id','title','slug','content','excerpt','featuredImage','gallery','status',
         'authorId','authorName','readTime','views','categoryId','createdAt','updatedAt'])

print("Migrating blog_posts_tags_tags...")
migrate('blog-service/blog.db', 'posts_tags_tags', 'blog_posts_tags_tags',
        ['postsId','tagsId'])

print("Migrating blog_comments...")
migrate('blog-service/blog.db', 'comments', 'blog_comments',
        ['id','content','authorName','authorEmail','authorId','approved','postId','createdAt'])

print("Migrating media_media...")
migrate('media-service/media.db', 'media', 'media_media',
        ['id','filename','originalName','mimetype','size','url','alt','uploadedBy','createdAt'])

# Reset sequences so next INSERT gets the right id
for table, col in [
    ('auth_users', 'id'), ('blog_categories', 'id'), ('blog_tags', 'id'),
    ('blog_posts', 'id'), ('blog_comments', 'id'), ('media_media', 'id'),
]:
    cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}', '{col}'), COALESCE(MAX({col}), 1)) FROM {table}")

pg.commit()
cur.close()
pg.close()
print("\nDone.")
