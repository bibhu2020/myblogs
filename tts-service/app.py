import io
import os
import re
import threading
from functools import lru_cache

import numpy as np
import soundfile as sf
from flask import Flask, jsonify, request, send_file
from kokoro import KPipeline

app = Flask(__name__)

# ── Voice / style configuration ───────────────────────────────────────────────
# Each style maps to (lang_code, voice, speed).
# af_* = American Female,  am_* = American Male
# bf_* = British Female,   bm_* = British Male
#
#  story → af_heart  : warm, emotional — ideal for dramatic/children's narratives
#  blog  → bf_emma   : clear, articulate British female — educational lecture feel
#  news  → bm_george : crisp British male — classic news-anchor delivery
_STYLE_MAP: dict[str, tuple[str, str, float]] = {
    'story': (
        'a',
        os.getenv('TTS_VOICE_STORY', 'af_heart'),
        float(os.getenv('TTS_SPEED_STORY', '0.92')),
    ),
    'blog': (
        'b',
        os.getenv('TTS_VOICE_BLOG', 'bf_emma'),
        float(os.getenv('TTS_SPEED_BLOG', '0.88')),
    ),
    'news': (
        'b',
        os.getenv('TTS_VOICE_NEWS', 'bm_george'),
        float(os.getenv('TTS_SPEED_NEWS', '1.02')),
    ),
}
_DEFAULT: tuple[str, str, float] = (
    'a',
    os.getenv('TTS_VOICE', 'af_heart'),
    float(os.getenv('TTS_SPEED', '1.0')),
)

# ── Pipeline pool (one per lang_code, shared across styles) ───────────────────
_pipelines: dict[str, KPipeline] = {}
_locks: dict[str, threading.Lock] = {}


def _get_pipeline(lang_code: str) -> tuple[KPipeline, threading.Lock]:
    if lang_code not in _pipelines:
        print(f'Loading Kokoro pipeline: lang_code={lang_code}', flush=True)
        _pipelines[lang_code] = KPipeline(lang_code=lang_code)
        _locks[lang_code] = threading.Lock()
        print(f'Pipeline ready: lang_code={lang_code}', flush=True)
    return _pipelines[lang_code], _locks[lang_code]


# ── Text normalisation (runs before synthesis) ────────────────────────────────
_RE_ALLCAPS = re.compile(r'\b[A-Z]{4,}\b')   # 4+ letter ALL-CAPS words


def _normalize_text(text: str) -> str:
    """Prepare text for Kokoro so onomatopoeia sounds natural rather than being spelled out.

    - 4+ letter ALL-CAPS words → lowercase, keeping repeated letters intact
      WHOOOOSH → whoooosh  (espeak-ng elongates the vowel)
      ZOOOOOM  → zooooom
      BOOM     → boom
    - Short ALL-CAPS (≤3 letters) untouched so they ARE spelled out: AI, US, DNA
    """
    return _RE_ALLCAPS.sub(lambda m: m.group(0).lower(), text)


# ── Core synthesis (cached for instant replays of identical requests) ─────────
@lru_cache(maxsize=512)
def _synthesize(text: str, lang_code: str, voice: str, speed_str: str) -> bytes:
    """Return 24 kHz WAV bytes. speed_str is a string so the lru_cache key is hashable."""
    speed = float(speed_str)
    pipeline, lock = _get_pipeline(lang_code)
    with lock:
        chunks = [audio for _, _, audio in pipeline(text, voice=voice, speed=speed)]
    if not chunks:
        return b''
    buf = io.BytesIO()
    sf.write(buf, np.concatenate(chunks), 24000, format='WAV')
    return buf.getvalue()


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'model': 'Kokoro-82M', 'styles': list(_STYLE_MAP)})


@app.route('/tts', methods=['POST'])
def synthesize():
    body = request.get_json(silent=True) or {}
    text = (body.get('text') or '').strip()
    style = (body.get('style') or '').strip()

    if not text:
        return jsonify({'error': 'text required'}), 400

    lang_code, voice, speed = _STYLE_MAP.get(style, _DEFAULT)
    text = _normalize_text(text)

    try:
        wav = _synthesize(text, lang_code, voice, str(speed))
        if not wav:
            return jsonify({'error': 'synthesis produced no audio'}), 500
        return send_file(io.BytesIO(wav), mimetype='audio/wav',
                         as_attachment=False, download_name='speech.wav')
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


# ── Pre-warm all pipelines on startup ─────────────────────────────────────────
_needed = {cfg[0] for cfg in _STYLE_MAP.values()} | {_DEFAULT[0]}
for _lc in sorted(_needed):
    _get_pipeline(_lc)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, threaded=True)
