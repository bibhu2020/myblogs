import io
import os
import threading
from functools import lru_cache

import numpy as np
import soundfile as sf
from flask import Flask, jsonify, request, send_file
from kokoro import KPipeline

VOICE = os.getenv('TTS_VOICE', 'af_heart')  # warm, emotional storytelling voice
SPEED = float(os.getenv('TTS_SPEED', '1.0'))

app = Flask(__name__)

print(f'Loading Kokoro-82M (voice: {VOICE})...', flush=True)
_pipeline = KPipeline(lang_code='a')  # American English
_lock = threading.Lock()
print('TTS model ready.', flush=True)


@lru_cache(maxsize=256)
def _synthesize(text: str) -> bytes:
    """Synthesize text → 24kHz WAV via Kokoro-82M. Cached for instant replays."""
    with _lock:
        audio_chunks = []
        for _, _, audio in _pipeline(text, voice=VOICE, speed=SPEED):
            audio_chunks.append(audio)
    if not audio_chunks:
        return b''
    full_audio = np.concatenate(audio_chunks)
    buf = io.BytesIO()
    sf.write(buf, full_audio, 24000, format='WAV')
    return buf.getvalue()


@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'model': 'Kokoro-82M', 'voice': VOICE})


@app.route('/tts', methods=['POST'])
def synthesize():
    body = request.get_json(silent=True) or {}
    text = body.get('text', '').strip()
    if not text:
        return jsonify({'error': 'text required'}), 400
    try:
        audio_bytes = _synthesize(text)
        return send_file(io.BytesIO(audio_bytes), mimetype='audio/wav')
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, threaded=True)
