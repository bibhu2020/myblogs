"""
Meridian — System Design Document Generator
Produces myblogs.pdf with architecture overview and sequence diagrams
for every major flow in the application.
"""
import io, os, textwrap, math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, Image, HRFlowable, PageBreak, KeepTogether)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from PIL import Image as PILImage

# ── Colour palette ─────────────────────────────────────────────────────────────
DARK   = '#0d0d1a'
VIOLET = '#7c3aed'
RED    = '#dc2626'
SLATE  = '#334155'
LIGHT  = '#f8fafc'
BORDER = '#e2e8f0'
GREEN  = '#16a34a'
AMBER  = '#d97706'
BLUE   = '#2563eb'
TEAL   = '#0891b2'
ROSE   = '#e11d48'

W, H = A4  # 595.27 x 841.89 pt

# ── Sequence diagram renderer ──────────────────────────────────────────────────

def render_sequence(title, participants, steps, figsize=(14, None), colors_map=None):
    """
    participants: list of str
    steps: list of (from_idx, to_idx, label, style)
        style: 'sync' | 'async' | 'return' | 'note'
        For 'note': (None, participant_idx, text, 'note')
    Returns PNG bytes.
    """
    n = len(participants)
    line_h = 0.55   # vertical space per step
    top_pad = 1.4   # header area
    bot_pad = 0.6
    total_h = top_pad + len(steps) * line_h + bot_pad
    if figsize[1] is None:
        figsize = (figsize[0], max(4, total_h))

    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlim(-0.55, n - 0.45)
    ax.set_ylim(0, total_h)
    ax.axis('off')
    fig.patch.set_facecolor('#f8fafc')
    ax.set_facecolor('#f8fafc')

    # Default participant colours
    base_colors = [VIOLET, BLUE, TEAL, GREEN, AMBER, RED, SLATE, ROSE]
    if colors_map is None:
        colors_map = {i: base_colors[i % len(base_colors)] for i in range(n)}

    xs = list(range(n))   # x positions (0..n-1 mapped to ax coords)
    def x(i): return i

    # Title
    ax.text((n-1)/2, total_h - 0.25, title,
            ha='center', va='top', fontsize=13, fontweight='bold',
            color=DARK, fontfamily='DejaVu Sans')

    # Participant boxes
    box_y_top = total_h - 0.55
    box_h = 0.55
    for i, name in enumerate(participants):
        col = colors_map.get(i, SLATE)
        rect = mpatches.FancyBboxPatch(
            (x(i) - 0.35, box_y_top - box_h), 0.70, box_h,
            boxstyle='round,pad=0.05', linewidth=1.2,
            edgecolor=col, facecolor=col)
        ax.add_patch(rect)
        wrapped = '\n'.join(textwrap.wrap(name, 12))
        ax.text(x(i), box_y_top - box_h/2, wrapped,
                ha='center', va='center', fontsize=7.5, fontweight='bold',
                color='white', fontfamily='DejaVu Sans')

    # Lifelines
    lifeline_top = box_y_top - box_h
    lifeline_bot = bot_pad - 0.1
    for i in range(n):
        col = colors_map.get(i, SLATE)
        ax.plot([x(i), x(i)], [lifeline_bot, lifeline_top],
                color=col, linewidth=1, alpha=0.35, linestyle='--', zorder=1)

    # Steps
    y_cursor = lifeline_top - line_h * 0.5
    activation = {}   # track activation boxes per participant

    for step in steps:
        frm, to, label, style = step
        y = y_cursor

        if style == 'note':
            # frm is None, to is participant index
            note_x = x(to) + 0.05 if to < n-1 else x(to) - 0.7
            note_w = 0.75
            note_h = 0.30
            rect = mpatches.FancyBboxPatch(
                (note_x, y - note_h/2), note_w, note_h,
                boxstyle='round,pad=0.03', linewidth=0.8,
                edgecolor=AMBER, facecolor='#fef3c7', zorder=4)
            ax.add_patch(rect)
            ax.text(note_x + note_w/2, y, label,
                    ha='center', va='center', fontsize=6.5,
                    color='#92400e', fontfamily='DejaVu Sans', zorder=5,
                    style='italic')
        else:
            xi, xo = x(frm), x(to)
            going_right = xo >= xi
            arrowstyle = '->' if style in ('sync', 'async') else '<-'
            linestyle = '--' if style in ('return', 'async') else '-'
            col = colors_map.get(frm if style != 'return' else to, SLATE)
            alpha = 0.85

            offset = 0.015  # slight vertical offset per direction for clarity
            ax.annotate('',
                xy=(xo, y), xytext=(xi, y),
                arrowprops=dict(
                    arrowstyle='->', color=col,
                    lw=1.4 if style == 'sync' else 0.9,
                    linestyle=linestyle,
                    connectionstyle='arc3,rad=0.0'),
                zorder=3)

            # Label above the arrow
            mid_x = (xi + xo) / 2
            align = 'center'
            wrapped = label if len(label) <= 40 else label[:37] + '…'
            ax.text(mid_x, y + 0.085, wrapped,
                    ha=align, va='bottom', fontsize=6.8,
                    color=DARK, fontfamily='DejaVu Sans',
                    bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                              edgecolor='none', alpha=0.85),
                    zorder=5)

        y_cursor -= line_h

    # Bottom participant mirrors
    bot_box_y = lifeline_bot - box_h + 0.1
    for i, name in enumerate(participants):
        col = colors_map.get(i, SLATE)
        rect = mpatches.FancyBboxPatch(
            (x(i) - 0.35, bot_box_y), 0.70, box_h,
            boxstyle='round,pad=0.05', linewidth=1.2,
            edgecolor=col, facecolor=col)
        ax.add_patch(rect)
        wrapped = '\n'.join(textwrap.wrap(name, 12))
        ax.text(x(i), bot_box_y + box_h/2, wrapped,
                ha='center', va='center', fontsize=7.5, fontweight='bold',
                color='white', fontfamily='DejaVu Sans')

    plt.tight_layout(pad=0.3)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=160, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def png_to_rl_image(png_bytes, max_width=None, max_height=None):
    """Convert PNG bytes to a ReportLab Image flowable."""
    pil = PILImage.open(io.BytesIO(png_bytes))
    w_px, h_px = pil.size
    aspect = h_px / w_px
    if max_width is None:
        max_width = W - 2 * cm
    img_w = min(max_width, w_px * 0.7)
    img_h = img_w * aspect
    if max_height and img_h > max_height:
        img_h = max_height
        img_w = img_h / aspect
    return Image(io.BytesIO(png_bytes), width=img_w, height=img_h)


# ── Architecture diagram ───────────────────────────────────────────────────────

def render_arch_diagram():
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 14); ax.set_ylim(0, 8)
    ax.axis('off')
    fig.patch.set_facecolor('#f8fafc')

    def box(x, y, w, h, label, sublabel='', color=VIOLET, text_color='white', fontsize=9):
        rect = mpatches.FancyBboxPatch((x, y), w, h,
            boxstyle='round,pad=0.12', linewidth=1.5,
            edgecolor=color, facecolor=color)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2 + (0.18 if sublabel else 0), label,
                ha='center', va='center', fontsize=fontsize,
                fontweight='bold', color=text_color)
        if sublabel:
            ax.text(x + w/2, y + h/2 - 0.22, sublabel,
                    ha='center', va='center', fontsize=7,
                    color=text_color, alpha=0.85, style='italic')

    def arrow(x1, y1, x2, y2, label='', color=SLATE):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=color,
                                   lw=1.5, connectionstyle='arc3,rad=0.0'))
        if label:
            mx, my = (x1+x2)/2, (y1+y2)/2
            ax.text(mx, my + 0.12, label, ha='center', va='bottom',
                    fontsize=7, color=SLATE)

    def dashed(x1, y1, x2, y2, label='', color=SLATE):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=color, lw=1.2,
                                   linestyle='dashed',
                                   connectionstyle='arc3,rad=0.0'))
        if label:
            mx, my = (x1+x2)/2, (y1+y2)/2
            ax.text(mx, my + 0.12, label, ha='center', va='bottom',
                    fontsize=7, color=SLATE, style='italic')

    # Title
    ax.text(7, 7.7, 'Meridian — System Architecture', ha='center', va='top',
            fontsize=14, fontweight='bold', color=DARK)

    # Browser / Client
    box(0.3, 5.5, 2.4, 1.1, 'Browser', 'localhost:5173 / HF Space', color=BLUE)
    # Vite Dev / Nginx
    box(0.3, 3.7, 2.4, 1.0, 'Vite / Nginx', 'Vue 3 SPA', color='#0284c7', fontsize=8)
    arrow(1.5, 5.5, 1.5, 4.7, '')

    # API Gateway
    box(3.8, 4.4, 2.5, 1.2, 'API Gateway', ':3000 · JWT Guard', color=VIOLET)

    # Proxy arrows browser → gateway
    arrow(2.7, 5.2, 3.8, 5.1, '/api/*')
    arrow(2.7, 4.3, 3.8, 4.7, '/uploads/*')

    # Auth Service
    box(7.2, 6.0, 2.4, 1.0, 'Auth Service', ':3001 · auth.db', color=TEAL)
    arrow(6.3, 5.2, 7.2, 6.4, '/api/auth/*')

    # Blog Service
    box(7.2, 4.3, 2.4, 1.0, 'Blog Service', ':3002 · blog.db', color=GREEN)
    arrow(6.3, 4.9, 7.2, 4.8, '/api/posts/*')

    # Media Service
    box(7.2, 2.6, 2.4, 1.0, 'Media Service', ':3003 · media.db', color=AMBER)
    arrow(6.3, 4.5, 7.2, 3.1, '/api/media/*')

    # TTS Service
    box(7.2, 0.9, 2.4, 1.0, 'TTS Service', ':5500 · Kokoro AI', color=ROSE)
    arrow(6.3, 4.3, 7.2, 1.4, '/api/tts')

    # External: GitHub Media
    box(10.3, 2.6, 2.4, 1.0, 'GitHub', 'bibhu2020/media', color='#1f2937', fontsize=8)
    dashed(9.6, 3.1, 10.3, 3.1, 'PUT image')

    # External: OpenAI
    box(10.3, 5.3, 2.4, 1.0, 'OpenAI', 'GPT-4o / DALL-E', color='#065f46', fontsize=8)

    # External: HF Inference
    box(10.3, 3.9, 2.4, 1.0, 'HF Inference', 'FLUX.1-schnell', color='#f59e0b', text_color=DARK, fontsize=8)

    # External: Gemini
    box(10.3, 6.7, 2.4, 0.9, 'Gemini', 'gemini-2.5-flash', color='#1d4ed8', fontsize=8)

    # External: Unsplash
    box(10.3, 1.4, 2.4, 0.9, 'Unsplash', 'Photo fallback', color='#374151', fontsize=8)

    # AI Agent
    box(3.8, 6.5, 2.5, 1.1, 'AI Agent', 'node-cron Sat+Sun', color='#7e22ce')
    arrow(5.05, 6.5, 5.05, 5.6, 'POST /api/mcp')
    dashed(6.3, 7.0, 10.3, 6.9, 'research+image')

    # Databases
    box(0.3, 1.5, 1.5, 0.8, 'auth.db', 'SQLite', color='#6b7280', fontsize=8)
    box(0.3, 0.5, 1.5, 0.8, 'blog.db', 'SQLite', color='#6b7280', fontsize=8)
    dashed(7.2, 6.0, 1.8, 2.05, '', '#9ca3af')
    dashed(7.2, 4.3, 1.8, 0.9, '', '#9ca3af')

    # Supervisord label
    ax.text(9.25, 0.35, 'Supervisord manages all services in Docker container',
            ha='center', va='bottom', fontsize=7, color='#6b7280', style='italic')

    # Legend
    legend_items = [
        (VIOLET, 'API Gateway'), (TEAL, 'Auth'), (GREEN, 'Blog'),
        (AMBER, 'Media'), (ROSE, 'TTS'), (BLUE, 'Frontend'),
        ('#7e22ce', 'AI Agent'),
    ]
    for idx, (col, lbl) in enumerate(legend_items):
        px = 0.4 + idx * 1.9
        ax.add_patch(mpatches.FancyBboxPatch((px, 0.05), 0.25, 0.22,
            boxstyle='round,pad=0.03', facecolor=col, edgecolor='none'))
        ax.text(px + 0.32, 0.16, lbl, va='center', fontsize=6.5, color=DARK)

    plt.tight_layout(pad=0.2)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=160, bbox_inches='tight',
                facecolor='#f8fafc')
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ── ReportLab styles ───────────────────────────────────────────────────────────

def make_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles['h1'] = ParagraphStyle('h1', parent=base['Heading1'],
        fontSize=26, textColor=colors.HexColor(DARK),
        spaceAfter=6, fontName='Helvetica-Bold', leading=30)

    styles['h2'] = ParagraphStyle('h2', parent=base['Heading2'],
        fontSize=16, textColor=colors.HexColor(VIOLET),
        spaceBefore=18, spaceAfter=6, fontName='Helvetica-Bold', leading=20)

    styles['h3'] = ParagraphStyle('h3', parent=base['Heading3'],
        fontSize=12, textColor=colors.HexColor(SLATE),
        spaceBefore=12, spaceAfter=4, fontName='Helvetica-Bold', leading=15)

    styles['body'] = ParagraphStyle('body', parent=base['Normal'],
        fontSize=9.5, textColor=colors.HexColor(SLATE),
        spaceAfter=6, leading=14, alignment=TA_JUSTIFY)

    styles['caption'] = ParagraphStyle('caption', parent=base['Normal'],
        fontSize=8, textColor=colors.HexColor('#64748b'),
        spaceAfter=8, leading=11, alignment=TA_CENTER, fontName='Helvetica-Oblique')

    styles['code'] = ParagraphStyle('code', parent=base['Normal'],
        fontSize=8, fontName='Courier', textColor=colors.HexColor('#1e293b'),
        backColor=colors.HexColor('#f1f5f9'),
        spaceAfter=6, spaceBefore=4, leading=12,
        leftIndent=12, rightIndent=12,
        borderPad=6, borderWidth=1, borderColor=colors.HexColor(BORDER),
        borderRadius=4)

    styles['bullet'] = ParagraphStyle('bullet', parent=base['Normal'],
        fontSize=9.5, textColor=colors.HexColor(SLATE),
        spaceAfter=3, leading=13, leftIndent=16, firstLineIndent=-10)

    return styles

S = make_styles()

def H(text): return Paragraph(text, S['h2'])
def H3(text): return Paragraph(text, S['h3'])
def P(text): return Paragraph(text, S['body'])
def Cap(text): return Paragraph(text, S['caption'])
def B(text): return Paragraph(f'• {text}', S['bullet'])
def SP(n=6): return Spacer(1, n)
def HR(): return HRFlowable(width='100%', thickness=0.5,
    color=colors.HexColor(BORDER), spaceAfter=8, spaceBefore=4)


def seq_image(png_bytes, caption_text):
    img = png_to_rl_image(png_bytes, max_width=W - 2.5*cm, max_height=19*cm)
    return [img, Cap(caption_text), SP(8)]


# ── Sequence diagram definitions ───────────────────────────────────────────────

FLOWS = []

# 1. User Registration
FLOWS.append(('User Registration', seq_image(render_sequence(
    'Flow 1 — User Registration',
    ['Browser', 'Vue SPA', 'API Gateway\n:3000', 'Auth Service\n:3001', 'auth.db'],
    [
        (0, 1, 'Navigate to /admin', 'sync'),
        (1, 1, 'router.beforeEach → not logged in', 'note'),
        (1, 0, 'Redirect → /admin/login', 'return'),
        (0, 1, 'POST /api/auth/register\n{ name, email, password }', 'sync'),
        (1, 2, 'POST /api/auth/register', 'sync'),
        (2, 3, 'POST /auth/register', 'sync'),
        (3, 3, 'bcrypt.hash(password, 10)', 'note'),
        (3, 4, 'INSERT INTO users', 'sync'),
        (4, 3, '201 { id, email }', 'return'),
        (3, 2, '201 Created', 'return'),
        (2, 1, '201 Created', 'return'),
        (1, 0, 'Account created — prompt login', 'return'),
    ]
), 'Figure 1: User registration — password is bcrypt-hashed before storage in auth.db')))

# 2. Login & JWT
FLOWS.append(('User Login / JWT Issue', seq_image(render_sequence(
    'Flow 2 — User Login & JWT Issue',
    ['Browser', 'Vue SPA\nauth.js store', 'API Gateway\n:3000', 'Auth Service\n:3001'],
    [
        (0, 1, 'POST /api/auth/login { email, password }', 'sync'),
        (1, 2, 'POST /api/auth/login', 'sync'),
        (2, 3, 'POST /auth/login', 'sync'),
        (3, 3, 'bcrypt.compare(password, hash)', 'note'),
        (3, 2, '200 { access_token, user }', 'return'),
        (2, 1, '200 { access_token, user }', 'return'),
        (1, 1, 'localStorage.setItem("token", jwt)', 'note'),
        (1, 1, 'axios.defaults.headers.Authorization = Bearer …', 'note'),
        (1, 0, 'Redirect → /admin/dashboard', 'return'),
        (0, 1, 'All subsequent API calls include Authorization header', 'async'),
        (1, 2, 'Gateway verifies JWT (JwtStrategy)', 'async'),
        (2, 3, 'GET /auth/validate (optional)', 'async'),
    ]
), 'Figure 2: JWT issued by Auth Service; stored in localStorage; auto-attached to all API requests via Axios default header')))

# 3. A/B Layout
FLOWS.append(('A/B Layout Assignment', seq_image(render_sequence(
    'Flow 3 — A/B Layout Assignment (Session-Sticky)',
    ['Browser', 'Vue SPA\nlayout.js store', 'localStorage', 'Pinia Store', 'All Page\nComponents'],
    [
        (0, 1, 'First visit — no variant in localStorage', 'sync'),
        (1, 2, 'getItem("meridian_ab_variant")', 'sync'),
        (2, 1, 'null (not set)', 'return'),
        (1, 1, 'Math.random() < 0.5 → "a" or "b"', 'note'),
        (1, 2, 'setItem("meridian_ab_variant", "a"|"b")', 'sync'),
        (1, 3, 'variant = ref("a"|"b")', 'sync'),
        (3, 4, 'layout.variant injected via useLayoutStore()', 'sync'),
        (4, 4, 'layout.variant === "b"  → dark classes applied', 'note'),
        (0, 1, 'Return visit — variant already in localStorage', 'async'),
        (1, 2, 'getItem("meridian_ab_variant")', 'async'),
        (2, 1, '"a" or "b" (sticky)', 'return'),
        (1, 3, 'Same variant re-used — no re-randomisation', 'sync'),
    ]
), 'Figure 3: A/B variant randomly assigned once per browser; persisted in localStorage so the same user always sees the same layout')))

# 4. Fetch Blog Posts (Home Page)
FLOWS.append(('Browse Home / All Posts', seq_image(render_sequence(
    'Flow 4 — Browse Home Page (Fetch & Render Posts)',
    ['Browser', 'Vue SPA\nblog.js store', 'API Gateway\n:3000', 'Blog Service\n:3002', 'blog.db'],
    [
        (0, 1, 'Navigate to / or /blog', 'sync'),
        (1, 1, 'blog.fetchCategories() + blog.fetchPosts()', 'note'),
        (1, 2, 'GET /api/categories', 'sync'),
        (2, 3, 'GET /categories', 'sync'),
        (3, 4, 'SELECT * FROM categories', 'sync'),
        (4, 3, 'rows[]', 'return'),
        (3, 2, '200 [ { id, name, slug, icon, color } ]', 'return'),
        (2, 1, 'categories[]', 'return'),
        (1, 2, 'GET /api/posts?page=1&limit=12', 'sync'),
        (2, 3, 'GET /posts?page=1&limit=12', 'sync'),
        (3, 4, 'SELECT … ORDER BY createdAt DESC', 'sync'),
        (4, 3, 'posts[], total', 'return'),
        (3, 2, '200 { posts[], pagination }', 'return'),
        (2, 1, 'posts[], pagination', 'return'),
        (1, 0, 'Render PostCard grid (A or B layout)', 'return'),
    ]
), 'Figure 4: Posts are fetched lazily by the Pinia blog store; results are cached and re-used across components')))

# 5. Read Blog Post
FLOWS.append(('Read Blog Post', seq_image(render_sequence(
    'Flow 5 — Read Individual Blog Post',
    ['Browser', 'Vue SPA\nBlogPost.vue', 'API Gateway\n:3000', 'Blog Service\n:3002'],
    [
        (0, 1, 'Navigate to /blog/:slug', 'sync'),
        (1, 2, 'GET /api/posts/:slug', 'sync'),
        (2, 3, 'GET /posts/:slug', 'sync'),
        (3, 3, 'SELECT post; UPDATE views += 1', 'note'),
        (3, 2, '200 { post with category, tags }', 'return'),
        (2, 1, 'post object', 'return'),
        (1, 1, 'render v-html content; hljs.highlightElement()', 'note'),
        (1, 2, 'GET /api/posts?category=slug&limit=3', 'sync'),
        (2, 3, 'GET /posts?category=slug&limit=3', 'sync'),
        (3, 2, '200 related posts[]', 'return'),
        (2, 1, 'related posts', 'return'),
        (1, 2, 'GET /api/comments/post/:id', 'sync'),
        (2, 3, 'GET /comments/post/:id', 'sync'),
        (3, 2, '200 comments[]', 'return'),
        (2, 1, 'comments[]', 'return'),
        (1, 0, 'Full page rendered (article + related + comments)', 'return'),
    ]
), 'Figure 5: Each post view increments the view counter in blog.db; related posts and comments are loaded in parallel')))

# 6. TTS
FLOWS.append(('Text-to-Speech Playback', seq_image(render_sequence(
    'Flow 6 — Text-to-Speech (TTS) Playback',
    ['User', 'BlogPost.vue', 'API Gateway\n:3000', 'TTS Service\n:5500', 'Kokoro AI\nModel'],
    [
        (0, 1, 'Click "Listen to article"', 'sync'),
        (1, 1, 'splitChunks(post.content) → N chunks ≤500 chars', 'note'),
        (1, 1, 'Launch all N fetches concurrently (pre-fetch)', 'note'),
        (1, 2, 'POST /api/tts { text: chunk[0] }', 'sync'),
        (1, 2, 'POST /api/tts { text: chunk[1] }  (parallel)', 'async'),
        (2, 3, 'POST /tts { text }', 'sync'),
        (3, 4, 'kokoro.generate(text)', 'sync'),
        (4, 3, 'WAV audio bytes', 'return'),
        (3, 2, '200 audio/wav blob', 'return'),
        (2, 1, 'Blob (chunk 0 ready)', 'return'),
        (1, 1, 'new Audio(blobUrl).play()', 'note'),
        (0, 1, 'Click Pause', 'sync'),
        (1, 1, 'currentAudio.pause(); state=paused', 'note'),
        (0, 1, 'Drag seek slider', 'sync'),
        (1, 1, 'seekTo(fraction) → jump to target chunk', 'note'),
        (1, 1, 'cancelCurrentChunk(); runFrom(target)', 'note'),
        (0, 1, 'Click Stop', 'sync'),
        (1, 1, 'sessionId++ → all loops invalidated; state=idle', 'note'),
    ]
), 'Figure 6: All TTS chunks are pre-fetched concurrently; seek works with already-fetched blobs. Kokoro AI runs locally in the Docker container.')))

# 7. Search
FLOWS.append(('Search Articles', seq_image(render_sequence(
    'Flow 7 — Search Articles',
    ['User', 'Search.vue', 'API Gateway\n:3000', 'Blog Service\n:3002'],
    [
        (0, 1, 'Type query in search box', 'sync'),
        (1, 1, '350ms debounce timer', 'note'),
        (1, 2, 'GET /api/posts?search=query&limit=50', 'sync'),
        (2, 3, 'GET /posts?search=query&limit=50', 'sync'),
        (3, 3, 'WHERE title LIKE %q% OR content LIKE %q%', 'note'),
        (3, 2, '200 { posts[], total }', 'return'),
        (2, 1, 'results[]', 'return'),
        (1, 0, 'Render result cards with thumbnail + meta', 'return'),
        (0, 1, 'Click category chip in sidebar', 'sync'),
        (1, 2, 'GET /api/posts?category=slug&search=query', 'sync'),
        (2, 3, 'GET /posts?category=slug&search=query', 'sync'),
        (3, 2, 'Filtered results', 'return'),
        (2, 1, 'results[]', 'return'),
        (1, 0, 'Update results + URL (router.replace)', 'return'),
    ]
), 'Figure 7: Search is fully client-side driven with a 350ms debounce; URL query params updated so search links are shareable')))

# 8. Submit Comment
FLOWS.append(('Submit Comment', seq_image(render_sequence(
    'Flow 8 — Submit Comment',
    ['Reader', 'BlogPost.vue', 'API Gateway\n:3000', 'Blog Service\n:3002', 'blog.db'],
    [
        (0, 1, 'Fill name/email/content, click Post Comment', 'sync'),
        (1, 2, 'POST /api/comments/post/:id\n{ authorName, authorEmail, content }', 'sync'),
        (2, 3, 'POST /comments/post/:id', 'sync'),
        (3, 4, 'INSERT INTO comments (status=pending)', 'sync'),
        (4, 3, 'comment row', 'return'),
        (3, 2, '201 { id, status: "pending" }', 'return'),
        (2, 1, '201 Created', 'return'),
        (1, 0, '"Comment submitted — awaiting approval" banner', 'return'),
        (None, 2, 'Admin reviews comment in /admin panel', 'note'),
        (None, 3, 'PATCH /comments/:id { status: approved }', 'note'),
    ]
), 'Figure 8: Comments are stored with status=pending; admin approves via the admin panel before they appear publicly')))

# 9. Admin Create Post
FLOWS.append(('Admin Create Blog Post', seq_image(render_sequence(
    'Flow 9 — Admin Create Blog Post',
    ['Admin', 'PostEditor.vue', 'API Gateway\n:3000', 'Blog Service\n:3002', 'blog.db'],
    [
        (0, 1, 'Navigate to /admin/posts/new', 'sync'),
        (1, 1, 'JWT guard validates token in localStorage', 'note'),
        (0, 1, 'Write content in TipTap rich-text editor', 'sync'),
        (1, 1, 'TipTap → HTML with code highlighting', 'note'),
        (0, 1, 'Click Publish', 'sync'),
        (1, 2, 'POST /api/posts { title, content, categoryId,\n  tags[], featuredImage, excerpt, readTime }', 'sync'),
        (2, 2, 'JwtAuthGuard validates Bearer token', 'note'),
        (2, 3, 'POST /posts { ...body, authorId, authorName }', 'sync'),
        (3, 4, 'INSERT INTO posts; link tags in posts_tags_tags', 'sync'),
        (4, 3, 'post row', 'return'),
        (3, 2, '201 { post }', 'return'),
        (2, 1, '201 Created', 'return'),
        (1, 0, 'Redirect → /admin/posts (success toast)', 'return'),
    ]
), 'Figure 9: Admin JWT is validated at the API Gateway before forwarding; tags use a junction table posts_tags_tags')))

# 10. Media Upload
FLOWS.append(('Media File Upload', seq_image(render_sequence(
    'Flow 10 — Media Upload (Image Attach)',
    ['Admin', 'Vue SPA', 'API Gateway\n:3000', 'Media Service\n:3003', 'GitHub\nbibhu2020/media', 'media.db'],
    [
        (0, 1, 'Select image in post editor', 'sync'),
        (1, 2, 'POST /api/media/upload\nmultipart/form-data (binary file)', 'sync'),
        (2, 2, 'JwtAuthGuard validates token', 'note'),
        (2, 3, 'forwardWithFile() — streams multipart body', 'sync'),
        (3, 3, 'Multer saves to uploads/ with UUID filename', 'note'),
        (3, 4, 'PUT /repos/bibhu2020/media/contents/:filename\n(base64 encoded)', 'sync'),
        (4, 3, '200 OK — raw CDN URL returned', 'return'),
        (3, 5, 'INSERT INTO media { url: github_raw_url }', 'sync'),
        (5, 3, 'media row', 'return'),
        (3, 2, '201 { url: "https://raw.githubusercontent.com/…" }', 'return'),
        (2, 1, 'media URL', 'return'),
        (1, 1, 'Embed URL as featuredImage or in TipTap content', 'note'),
        (None, 3, 'If GitHub write fails → fallback to /uploads/ local URL', 'note'),
    ]
), 'Figure 10: Media Service uploads to GitHub CDN first; if GitHub returns 403 it falls back gracefully to local /uploads/ path')))

# 11. AI Agent Saturday
FLOWS.append(('AI Agent — Saturday Run (AI Trending)', seq_image(render_sequence(
    'Flow 11 — AI Agent Saturday Run (AI Trending)',
    ['node-cron\nSat 3am', 'Agent\nindex.js', 'OpenAI\nResearch', 'Image\nFallback Chain', 'MCP API\n:3000/mcp', 'Blog Service\n:3002'],
    [
        (0, 1, 'CRON_SCHEDULE "0 3 * * 6" fires', 'sync'),
        (1, 1, 'TOPIC_MODE=ai_trending → pick AI category', 'note'),
        (1, 2, 'discoverTrend() — GPT-4o web_search_preview\nDiscover top AI story this week', 'sync'),
        (2, 1, 'trend summary + source URLs', 'return'),
        (1, 2, 'deepResearch() — 3 parallel GPT-4o searches\ntechnical + reactions + implications', 'sync'),
        (2, 1, '{ topicSummary, technical, reactions, implications }', 'return'),
        (1, 2, 'generatePost() — GPT-4o writes full article\nHTML with h2/h3/blockquote/code', 'sync'),
        (2, 1, '{ title, content, excerpt, tags[] }', 'return'),
        (1, 3, 'generateImage(prompt) — try DALL-E 3', 'sync'),
        (3, 3, 'DALL-E 3 → DALL-E 2 → FLUX.1 → Gemini → Unsplash', 'note'),
        (3, 1, '{ buffer, mimeType, credit? }', 'return'),
        (1, 4, 'uploadMedia(imageBuffer) → POST /mcp { action:"upload_media" }', 'sync'),
        (4, 5, 'Media Service → GitHub / local', 'sync'),
        (5, 4, 'media URL', 'return'),
        (4, 1, '{ url }', 'return'),
        (1, 4, 'publishPost() → POST /mcp { action:"create_post", ...post }', 'sync'),
        (4, 5, 'POST /posts (agent JWT)', 'sync'),
        (5, 4, '201 post created', 'return'),
        (4, 1, '✅ post published', 'return'),
    ]
), 'Figure 11: Saturday agent always picks the AI category. 3 parallel research queries deepen the content before GPT-4o writes the final article.')))

# 12. AI Agent Sunday
FLOWS.append(('AI Agent — Sunday Run (Random Topic)', seq_image(render_sequence(
    'Flow 12 — AI Agent Sunday Run (Random General Topic)',
    ['node-cron\nSun 3am', 'Agent', 'OpenAI', 'Image Chain', 'MCP / Blog'],
    [
        (0, 1, 'CRON_SCHEDULE "0 3 * * 0" fires', 'sync'),
        (1, 1, 'TOPIC_MODE=random_general', 'note'),
        (1, 1, 'pickCategory() — random from:\nTechnology, Science, History, Travel, Knowledge', 'note'),
        (1, 2, 'discoverTrend() with selected category prompt', 'sync'),
        (2, 1, 'trend + category context', 'return'),
        (1, 2, 'deepResearch() — 3 parallel searches', 'sync'),
        (2, 1, 'research object', 'return'),
        (1, 2, 'generatePost() — GPT-4o writes article', 'sync'),
        (2, 1, 'post content', 'return'),
        (1, 3, 'generateImage(prompt)', 'sync'),
        (3, 1, 'image buffer', 'return'),
        (1, 4, 'uploadMedia() then publishPost() via MCP', 'sync'),
        (4, 1, '✅ post published in chosen category', 'return'),
    ]
), 'Figure 12: Sunday run picks a random non-AI category each week — ensuring content diversity across Technology, Science, History, Travel, and Knowledge')))

# 13. Image Fallback Chain
FLOWS.append(('Image Generation Fallback Chain', seq_image(render_sequence(
    'Flow 13 — Image Generation Fallback Chain',
    ['Agent\nimages.js', 'DALL-E 3\nOpenAI', 'DALL-E 2\nOpenAI', 'FLUX.1\nHF Inference', 'Gemini\nGoogle AI', 'Unsplash\nAPI'],
    [
        (0, 1, 'tryDalle3(prompt, "1792x1024")', 'sync'),
        (1, 0, 'Image buffer ✅ — done', 'return'),
        (None, 1, 'If error/no access:', 'note'),
        (0, 2, 'tryDalle2(prompt, "1024x1024")', 'sync'),
        (2, 0, 'Image buffer ✅ — done', 'return'),
        (None, 2, 'If error:', 'note'),
        (0, 3, 'tryFlux(aiPrompt) — POST HF Inference API', 'sync'),
        (3, 3, 'If 503: wait estimated_time seconds, retry once', 'note'),
        (3, 0, 'Image buffer ✅ — done', 'return'),
        (None, 3, 'If error/timeout:', 'note'),
        (0, 4, 'tryGemini(aiPrompt) — gemini-2.5-flash-image', 'sync'),
        (4, 4, 'responseModalities: ["image","text"]', 'note'),
        (4, 0, 'Image buffer ✅ — done', 'return'),
        (None, 4, 'If no image in response:', 'note'),
        (0, 5, 'tryUnsplash(originalPrompt) — keyword search', 'sync'),
        (5, 0, 'Photo URL + credit attribution ✅', 'return'),
        (None, 5, 'If all fail → null (post without image)', 'note'),
    ]
), 'Figure 13: Five-provider fallback ensures a high-quality image is almost always found. Unsplash uses the original prompt for natural keyword extraction.')))

# 14. CI/CD Deploy
FLOWS.append(('CI/CD — GitHub to HF Space Deploy', seq_image(render_sequence(
    'Flow 14 — CI/CD: GitHub Push → HF Space Deploy',
    ['Developer', 'GitHub\nmain branch', 'GitHub\nActions', 'HF Space\ngit repo', 'Docker\nBuild', 'Running\nContainer'],
    [
        (0, 1, 'git push origin main', 'sync'),
        (1, 2, 'Trigger: push to main', 'sync'),
        (2, 2, 'Sync secrets to HF Space\n(OPENAI, GEMINI, HF_TOKEN, UNSPLASH)', 'note'),
        (2, 3, 'git push hf main (force)', 'sync'),
        (3, 4, 'Dockerfile detected — build triggered', 'sync'),
        (4, 4, 'npm ci → nest build (4 services)', 'note'),
        (4, 4, 'npm ci → vite build (frontend)', 'note'),
        (4, 4, 'pip install (TTS deps)', 'note'),
        (4, 5, 'supervisord starts all programs', 'sync'),
        (5, 5, 'auth, blog, media, gateway, nginx, tts,\nagent-saturday, agent-sunday', 'note'),
        (3, 2, 'Build complete ✅', 'return'),
        (2, 1, 'Workflow completed (success)', 'return'),
        (1, 0, 'Live at mishrabp-meridian.hf.space', 'return'),
    ]
), 'Figure 14: The deploy workflow runs in ~20s (git push only). HF Space then rebuilds the Docker image autonomously — total cold-start ~5min.')))


# ── Build PDF ──────────────────────────────────────────────────────────────────

OUTPUT = '/home/azure/myblogs/myblogs.pdf'

doc = SimpleDocTemplate(OUTPUT, pagesize=A4,
    leftMargin=2*cm, rightMargin=2*cm,
    topMargin=2*cm, bottomMargin=2*cm)

story = []

# ─── Cover page ───────────────────────────────────────────────────────────────
cover_style = ParagraphStyle('cover', fontSize=36, fontName='Helvetica-Bold',
    textColor=colors.HexColor(DARK), alignment=TA_CENTER, leading=42)
sub_style = ParagraphStyle('sub', fontSize=14, fontName='Helvetica',
    textColor=colors.HexColor(VIOLET), alignment=TA_CENTER, leading=20)
meta_style = ParagraphStyle('meta', fontSize=10, fontName='Helvetica',
    textColor=colors.HexColor(SLATE), alignment=TA_CENTER, leading=15)

story.append(Spacer(1, 3*cm))
story.append(Paragraph('Meridian', cover_style))
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph('System Design Document', sub_style))
story.append(Spacer(1, 1*cm))
story.append(HRFlowable(width='60%', thickness=2,
    color=colors.HexColor(VIOLET), spaceAfter=16, spaceBefore=8))
story.append(Paragraph('Multi-topic AI-powered blogging platform', meta_style))
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph('Microservices Architecture · Vue 3 Frontend · AI Agent · TTS', meta_style))
story.append(Spacer(1, 2*cm))

# cover summary box
cover_data = [
    ['Stack', 'NestJS (×4 services) · Vue 3 · SQLite · Tailwind CSS v4'],
    ['AI Features', 'GPT-4o research · DALL-E / FLUX / Gemini / Unsplash images · Kokoro TTS'],
    ['Deployment', 'HuggingFace Spaces · Docker · Supervisord · GitHub Actions CI/CD'],
    ['Agent', 'Publishes 2 blog posts/week via automated cron (Sat + Sun 3am)'],
    ['A/B Testing', 'Two brand layouts — Editorial Light (A) & Dark Magazine (B)'],
    ['Date', 'June 2026'],
]
cover_table = Table(cover_data, colWidths=[4.5*cm, 10.5*cm])
cover_table.setStyle(TableStyle([
    ('BACKGROUND',  (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
    ('BACKGROUND',  (1, 0), (1, -1), colors.white),
    ('TEXTCOLOR',   (0, 0), (0, -1), colors.HexColor(VIOLET)),
    ('TEXTCOLOR',   (1, 0), (1, -1), colors.HexColor(SLATE)),
    ('FONTNAME',    (0, 0), (0, -1), 'Helvetica-Bold'),
    ('FONTNAME',    (1, 0), (1, -1), 'Helvetica'),
    ('FONTSIZE',    (0, 0), (-1, -1), 9.5),
    ('GRID',        (0, 0), (-1, -1), 0.5, colors.HexColor(BORDER)),
    ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.HexColor('#f8fafc'), colors.white]),
    ('TOPPADDING',  (0, 0), (-1, -1), 7),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
]))
story.append(cover_table)
story.append(PageBreak())

# ─── 1. System Overview ────────────────────────────────────────────────────────
story.append(H('1. System Overview'))
story.append(P(
    'Meridian is a multi-topic blogging platform built on a microservices backend and a Vue 3 '
    'single-page application frontend. It features an autonomous AI agent that publishes two '
    'research-backed articles per week, a text-to-speech reader powered by a local Kokoro AI model, '
    'an A/B layout testing system that randomly assigns one of two brand identities per browser '
    'session, and a full-featured admin panel for manual content management.'
))
story.append(P(
    'All services run inside a single Docker container orchestrated by Supervisord, '
    'hosted on HuggingFace Spaces and deployed automatically via GitHub Actions on every push to main.'
))
story.append(HR())

# ─── 2. Architecture Diagram ──────────────────────────────────────────────────
story.append(H('2. System Architecture'))
arch_png = render_arch_diagram()
story.append(png_to_rl_image(arch_png, max_width=W - 2*cm))
story.append(Cap('Figure 0: Full system architecture — browser through microservices to external AI APIs'))
story.append(SP(10))

# ─── 3. Component Details ─────────────────────────────────────────────────────
story.append(H('3. Component Descriptions'))

comp_data = [
    ['Component', 'Port', 'DB', 'Responsibility'],
    ['API Gateway',   '3000', '—',        'Single entry point for all browser requests. Validates JWTs (JwtStrategy + PassportModule). Proxies to internal services via ProxyService.forward().'],
    ['Auth Service',  '3001', 'auth.db',  'User accounts, bcrypt password hashing, JWT signing and validation. Issues 24h access tokens signed with shared secret myblogs-secret-key-2024.'],
    ['Blog Service',  '3002', 'blog.db',  'Posts, categories, tags, comments, view counters. Seeds sample data on empty DB. Tag-post junction via posts_tags_tags table. Full-text search via LIKE.'],
    ['Media Service', '3003', 'media.db', 'Multer file upload handler. Uploads to GitHub CDN repo; falls back to local /uploads/ path on failure. Serves files at /uploads/:filename.'],
    ['TTS Service',   '5500', '—',        'Kokoro AI local inference model. Accepts POST /tts { text } and returns WAV audio blob. Runs as a Python subprocess under Supervisord.'],
    ['AI Agent',      '—',    '—',        'node-cron scheduled jobs. Researches topics via GPT-4o web search, writes articles, generates images (5-provider chain), publishes via MCP REST API. Two runs/week.'],
    ['Vue 3 Frontend','5173', '—',        'SPA with Vue Router, Pinia stores (auth, blog, layout), TipTap editor, TTS player, A/B layout variants, Tailwind CSS v4.'],
    ['Nginx',         '80',   '—',        'Reverse proxy inside Docker. Routes /api/* to API Gateway and /uploads/* to Media Service. Serves built frontend assets.'],
]

comp_table = Table(comp_data, colWidths=[3.2*cm, 1.4*cm, 2.0*cm, 9.4*cm])
comp_table.setStyle(TableStyle([
    ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor(DARK)),
    ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
    ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
    ('FONTSIZE',      (0, 0), (-1, -1), 8.5),
    ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.white]),
    ('GRID',          (0, 0), (-1, -1), 0.4, colors.HexColor(BORDER)),
    ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ('TOPPADDING',    (0, 0), (-1, -1), 6),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ('LEFTPADDING',   (0, 0), (-1, -1), 6),
    ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
    ('TEXTCOLOR',     (0, 1), (0, -1),  colors.HexColor(VIOLET)),
    ('FONTNAME',      (0, 1), (0, -1),  'Helvetica-Bold'),
    ('TEXTCOLOR',     (1, 1), (1, -1),  colors.HexColor(TEAL)),
    ('FONTNAME',      (1, 1), (1, -1),  'Courier'),
]))
story.append(comp_table)
story.append(SP(8))

# ─── 4. Data Model ────────────────────────────────────────────────────────────
story.append(H('4. Data Model'))
story.append(P(
    'Each NestJS service owns its own SQLite database with TypeORM synchronize:true '
    '(auto-migrates on startup). Key entities:'
))

dm_data = [
    ['Table', 'Service', 'Key Columns'],
    ['users',             'auth.db',  'id, name, email, password (bcrypt), role, createdAt'],
    ['posts',             'blog.db',  'id, title, slug, content (HTML), excerpt, featuredImage, categoryId, authorId, authorName, readTime, views, status, createdAt'],
    ['categories',        'blog.db',  'id, name, slug, description, color (#hex), icon (emoji)'],
    ['tags',              'blog.db',  'id, name, slug'],
    ['posts_tags_tags',   'blog.db',  'postsId (FK posts), tagsId (FK tags)  — junction table'],
    ['comments',          'blog.db',  'id, postId, authorName, authorEmail, content, status (pending/approved)'],
    ['media',             'media.db', 'id, filename, originalName, mimeType, url, userId, alt, createdAt'],
]

dm_table = Table(dm_data, colWidths=[4.0*cm, 2.2*cm, 9.8*cm])
dm_table.setStyle(TableStyle([
    ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor(SLATE)),
    ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
    ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
    ('FONTSIZE',      (0, 0), (-1, -1), 8.5),
    ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.white]),
    ('GRID',          (0, 0), (-1, -1), 0.4, colors.HexColor(BORDER)),
    ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ('TOPPADDING',    (0, 0), (-1, -1), 6),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ('LEFTPADDING',   (0, 0), (-1, -1), 6),
    ('FONTNAME',      (0, 1), (0, -1),  'Courier-Bold'),
    ('TEXTCOLOR',     (0, 1), (0, -1),  colors.HexColor(DARK)),
    ('FONTNAME',      (2, 1), (2, -1),  'Courier'),
    ('FONTSIZE',      (2, 1), (2, -1),  7.5),
]))
story.append(dm_table)
story.append(SP(8))

# ─── 5. API Gateway pattern ───────────────────────────────────────────────────
story.append(H('5. API Gateway Pattern'))
story.append(P(
    'The API Gateway is the <b>sole public entry point</b>. It validates the JWT '
    'before forwarding any authenticated request. Internal services trust the forwarded '
    '<font face="Courier">Authorization: Bearer &lt;token&gt;</font> header and run their '
    'own JwtStrategy independently — there is no shared auth library.'
))

gw_data = [
    ['Route Pattern', 'Forwarded To', 'Auth Required'],
    ['POST /api/auth/*',                 'Auth Service :3001',  'No'],
    ['GET  /api/posts/*',                'Blog Service :3002',  'No'],
    ['POST /api/posts/*',                'Blog Service :3002',  'Yes (admin)'],
    ['GET  /api/categories, /api/tags',  'Blog Service :3002',  'No'],
    ['POST /api/comments/*',             'Blog Service :3002',  'No'],
    ['POST /api/media/upload',           'Media Service :3003', 'Yes (admin)'],
    ['POST /api/mcp',                    'MCP Controller',       'Yes (agent JWT)'],
    ['POST /api/tts',                    'TTS Service :5500',   'No'],
]

gw_table = Table(gw_data, colWidths=[6.5*cm, 5.5*cm, 4*cm])
gw_table.setStyle(TableStyle([
    ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor(VIOLET)),
    ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
    ('FONTNAME',      (0, 0), (-1, -1), 'Helvetica-Bold'),
    ('FONTNAME',      (0, 1), (1, -1),  'Courier'),
    ('FONTSIZE',      (0, 0), (-1, -1), 8.5),
    ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.white]),
    ('GRID',          (0, 0), (-1, -1), 0.4, colors.HexColor(BORDER)),
    ('TOPPADDING',    (0, 0), (-1, -1), 6),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ('LEFTPADDING',   (0, 0), (-1, -1), 6),
    ('TEXTCOLOR',     (2, 1), (2, -1),  colors.HexColor(GREEN)),
    ('TEXTCOLOR',     (2, 3), (2, 5),   colors.HexColor(RED)),
]))
story.append(gw_table)
story.append(SP(8))

# ─── 6. Sequence Diagrams ─────────────────────────────────────────────────────
story.append(H('6. Application Flow Sequence Diagrams'))
story.append(P(
    'The following sequence diagrams document every significant user-facing and system-level '
    'flow in Meridian. Solid arrows indicate synchronous calls; dashed arrows indicate '
    'asynchronous or return flows. Yellow sticky notes show internal decisions or side-effects.'
))

for flow_title, flow_items in FLOWS:
    story.append(SP(4))
    story.append(H3(f'6.{FLOWS.index((flow_title, flow_items))+1}  {flow_title}'))
    for item in flow_items:
        story.append(item)

# ─── 7. Technology Stack ──────────────────────────────────────────────────────
story.append(H('7. Technology Stack'))

tech_data = [
    ['Layer', 'Technology', 'Version / Notes'],
    ['Backend Framework', 'NestJS', 'v10 — 4 independent microservices'],
    ['Language', 'TypeScript', 'Strict mode; compiled to JS via tsc'],
    ['Database', 'SQLite (better-sqlite3)', 'Per-service DB files; TypeORM synchronize:true'],
    ['Auth', 'Passport JWT + bcrypt', 'HS256 tokens; 24h expiry; bcrypt rounds=10'],
    ['Frontend', 'Vue 3 + Vite', 'Composition API; <script setup>; Vue Router; Pinia'],
    ['CSS', 'Tailwind CSS v4', 'CSS-first config in style.css; @theme {} tokens'],
    ['Rich Text', 'TipTap', 'StarterKit + CodeBlockLowlight + Image + Link'],
    ['Syntax Highlight', 'highlight.js', 'Applied post-render on .post-content pre code'],
    ['File Upload', 'Multer', 'UUID filenames; stored in media-service/uploads/'],
    ['HTTP Proxy', 'Axios (server-side)', 'ProxyService.forward(); forwardWithFile() for uploads'],
    ['TTS AI', 'Kokoro (local model)', 'Python subprocess; WAV output; runs on CPU'],
    ['Image AI', 'DALL-E 3/2 → FLUX.1 → Gemini → Unsplash', '5-provider fallback chain'],
    ['Research AI', 'GPT-4o + web_search_preview', 'OpenAI Responses API; 3 parallel queries'],
    ['Article AI', 'GPT-4o', 'Writes full HTML article from research context'],
    ['Scheduling', 'node-cron', 'CRON_SCHEDULE env var; two separate agent processes'],
    ['Containerisation', 'Docker + Supervisord', 'Single container; multi-process managed by supervisord'],
    ['Reverse Proxy', 'Nginx', 'Inside container; routes /api and /uploads'],
    ['CI/CD', 'GitHub Actions', 'Push to main → sync secrets → git push to HF Space'],
    ['Hosting', 'HuggingFace Spaces', 'Docker runtime; public URL: mishrabp-meridian.hf.space'],
    ['A/B Testing', 'localStorage + Pinia', 'Random variant on first visit; session-sticky'],
]

tech_table = Table(tech_data, colWidths=[4*cm, 4.5*cm, 7.5*cm])
tech_table.setStyle(TableStyle([
    ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor(DARK)),
    ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
    ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
    ('FONTSIZE',      (0, 0), (-1, -1), 8.5),
    ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.white]),
    ('GRID',          (0, 0), (-1, -1), 0.4, colors.HexColor(BORDER)),
    ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ('TOPPADDING',    (0, 0), (-1, -1), 5),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ('LEFTPADDING',   (0, 0), (-1, -1), 6),
    ('TEXTCOLOR',     (0, 1), (0, -1),  colors.HexColor(SLATE)),
    ('FONTNAME',      (0, 1), (0, -1),  'Helvetica-Bold'),
    ('TEXTCOLOR',     (1, 1), (1, -1),  colors.HexColor(VIOLET)),
]))
story.append(tech_table)
story.append(SP(10))
story.append(HR())
story.append(SP(6))
story.append(Paragraph(
    'Meridian System Design Document · Bibhu Mishra · June 2026 · '
    'mishrabp-meridian.hf.space',
    ParagraphStyle('footer', fontSize=8, textColor=colors.HexColor('#94a3b8'),
                   alignment=TA_CENTER, fontName='Helvetica-Oblique')
))

doc.build(story)
print(f'✅  PDF written to {OUTPUT}')
