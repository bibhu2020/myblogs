import io
import threading
from functools import lru_cache
import numpy as np
import scipy.io.wavfile as wavfile
import torch
from flask import Flask, jsonify, request, send_file
from transformers import AutoTokenizer, VitsModel

MODEL = 'facebook/mms-tts-eng'
app = Flask(__name__)

_tokenizer = None
_model = None
_lock = threading.Lock()
_load_lock = threading.Lock()


def _ensure_loaded():
    global _tokenizer, _model
    if _model is not None:
        return
    with _load_lock:
        if _model is not None:
            return
        print(f'Loading {MODEL}...', flush=True)
        _tokenizer = AutoTokenizer.from_pretrained(MODEL)
        _model = VitsModel.from_pretrained(MODEL)
        _model.eval()
        print('TTS model ready.', flush=True)


@lru_cache(maxsize=128)
def _synthesize(text: str) -> bytes:
    _ensure_loaded()
    with _lock:
        inputs = _tokenizer(text, return_tensors='pt')
        with torch.no_grad():
            waveform = _model(**inputs).waveform.squeeze().numpy()
    rate = _model.config.sampling_rate
    buf = io.BytesIO()
    wavfile.write(buf, rate, (waveform * 32767).astype(np.int16))
    return buf.getvalue()


@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'model_loaded': _model is not None})


@app.route('/tts', methods=['POST'])
def synthesize():
    text = (request.get_json(silent=True) or {}).get('text', '').strip()
    if not text:
        return jsonify({'error': 'text required'}), 400
    try:
        audio_bytes = _synthesize(text)
        return send_file(io.BytesIO(audio_bytes), mimetype='audio/wav')
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, threaded=True)
