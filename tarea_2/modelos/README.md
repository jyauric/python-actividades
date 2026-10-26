# Modelos usados

Los pesos **no se versionan** (están en `.gitignore`): se descargan solos en la primera ejecución de los notebooks, en la caché de Hugging Face o de PaddleX.

| Uso | Modelo | Licencia | Dónde se usa |
|---|---|---|---|
| OCR (base) | PaddleOCR 3.7.0 · PP-OCRv6 (detector + reconocedor), `engine="transformers"`, GPU MPS | Apache 2.0 | `01_extraccion.ipynb`, `02_evaluacion.ipynb` |
| OCR alternativo | EasyOCR (`es`, CPU) | Apache 2.0 | `02_evaluacion.ipynb` |
| ASR (base) | faster-whisper 1.2.1 · `small` (int8, CPU, VAD) | MIT | `01_extraccion.ipynb`, `02_evaluacion.ipynb` |
| ASR alternativo | Qwen3-ASR 0.6B (GPU MPS) | Apache 2.0 | `02_evaluacion.ipynb` |
| Diarización | WeSpeaker ResNet34 (pyannote) + clustering jerárquico (`voz.diarizar`) | CC BY 4.0 | `01_extraccion.ipynb` |
| Extracción estructurada | Gemini (API, `temperature=0`, salida JSON) | Términos de Google AI | `02_evaluacion.ipynb` |
