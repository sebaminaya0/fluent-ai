# Auditoría Interna - Proyecto Fluent AI

## Versión de Python
- **Versión efectiva**: Python 3.13.5

## Dependencias Instaldas
- El comando `uv pip list` confirma que todas las dependencias listadas en `pyproject.toml` están correctamente instaladas.

## Detalles de Instalación de Dependencias
```
Package            Version
------------------ -----------
audioop-lts        0.2.1
audioread          3.0.1
certifi            2025.7.14
cffi               1.17.1
charset-normalizer 3.4.2
click              8.1.8
decorator          5.2.1
filelock           3.18.0
fsspec             2025.7.0
gtts               2.5.4
hf-xet             1.1.5
huggingface-hub    0.33.4
idna               3.10
jinja2             3.1.6
joblib             1.5.1
lazy-loader        0.4
librosa            0.11.0
llvmlite           0.44.0
markupsafe         3.0.2
more-itertools     10.7.0
mpmath             1.3.0
msgpack            1.1.1
networkx           3.5
numba              0.61.2
numpy              2.2.6
openai-whisper     20250625
packaging          25.0
platformdirs       4.3.8
pooch              1.8.2
pyaudio            0.2.14
pycparser          2.22
pydub              0.25.1
pygame             2.6.1
pyyaml             6.0.2
regex              2024.11.6
requests           2.32.4
safetensors        0.5.3
scikit-learn       1.7.0
scipy              1.16.0
sentencepiece      0.2.0
setuptools         80.9.0
sounddevice        0.5.2
soundfile          0.13.1
soxr               0.5.0.post1
speechrecognition  3.14.3
standard-aifc      3.13.0
standard-chunk     3.13.0
standard-sunau     3.13.0
sympy              1.14.0
threadpoolctl      3.6.0
tiktoken           0.9.0
tokenizers         0.21.2
torch              2.7.1
tqdm               4.67.1
transformers       4.53.2
typing-extensions  4.14.1
urllib3            2.5.0
webrtcvad          2.0.10
webrtcvad-wheels   2.0.14
```

## Dispositivos de Audio
```
0 Sebas’s Iphone Microphone, Core Audio (1 in, 0 out)
1 BlackHole 2ch, Core Audio (2 in, 2 out)
2 MacBook Pro Microphone, Core Audio (1 in, 0 out)
3 MacBook Pro Speakers, Core Audio (0 in, 2 out)
```

---

## Código Relacionado a Captura, ASR y TTS
- **Captura de Audio**:
  - `main.py` y `gui_app.py` utilizan `speech_recognition` y `whisper` para capturar y procesar audio.
- **ASR (Automatic Speech Recognition)**:
  - Librerías y frameworks como `speech_recognition` y `whisper` son implementados en `gui_app.py`.
- **TTS (Text-to-Speech)**:
  - Implementación de `gTTS` se encuentra en `main.py` y `gui_app.py`.
