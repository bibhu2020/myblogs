import io
import threading
import numpy as np
import scipy.io.wavfile as wavfile
import torch
from flask import Flask, jsonify, request, send_file
from transformers import AutoTokenizer, VitsModel

MODEL = 'facebook/mms-tts-eng'
app = Flask(__name__)

print(f'Loading {MODEL}...', flush=True)
_tokenizer = AutoTokenizer.from_pretrained(MODEL)
_model = VitsModel.from_pretrained(MODEL)
_model.eval()
# PyTorch VITS inference is not thread-safe — one inference at a time.
# Gunicorn handles concurrent HTTP connections; this lock serialises the GPU/CPU work.
_lock = threading.Lock()
print('TTS model ready.', flush=True)


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/tts', methods=['POST'])
def synthesize():
    text = (request.get_json(silent=True) or {}).get('text', '').strip()
    if not text:
        return jsonify({'error': 'text required'}), 400
    try:
        with _lock:
            inputs = _tokenizer(text, return_tensors='pt')
            with torch.no_grad():
                waveform = _model(**inputs).waveform.squeeze().numpy()
        rate = _model.config.sampling_rate
        buf = io.BytesIO()
        wavfile.write(buf, rate, (waveform * 32767).astype(np.int16))
        buf.seek(0)
        return send_file(buf, mimetype='audio/wav')
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


if __name__ == '__main__':
    # Dev only — production uses gunicorn via start.sh
    app.run(host='0.0.0.0', port=5050, threaded=True)
