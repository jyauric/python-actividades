# Tarea 2 – Voces y documentos peruanos
**Dashboard:** https://<tu-app>.streamlit.app

## Pregunta
¿Pueden convertirse documentos escaneados y entrevistas en audio en texto estructurado y buscable?

## Corpus, fuentes y licencias
- Fecha de extracción: 25/10/2026
- Documentos (25): Wikimedia Commons (dominio público, CC0, CC BY, CC BY-SA), ninguno de los usados en clase
- Audio (36 min, 31 clips): 12 entrevistas de Wikimedia Commons (CC BY-SA 4.0; las de más de 2 min cortadas en tramos de 60 s) y 6 clips de español peruano leído de OpenSLR 73 (CC BY-SA 4.0), ninguno de los usados en clase
- Archivos de Commons citados por número de página (`https://commons.wikimedia.org/?curid=…`), porque varios títulos contienen nombres de personas; 75 entidades seudonimizadas en los textos (`PERSONA_N`)
- Detalle por archivo: `datos/fuentes.csv`. `voz.py` y `datos.py` provienen de la Sesión 13 del curso; de `datos.py` solo se usan `ZipRemoto` y `OPENSLR73` (se quitaron las entrevistas de Commons de la clase, que no se usan).

## Pipeline
Búsqueda en la API de Commons → descarga → OCR con PaddleOCR PP-OCRv6 (GPU MPS) → ASR con faster-whisper small (CPU, VAD) + diarización (WeSpeaker + clustering, `voz.diarizar`) → seudonimización (`voz.seudonimizar`) → extracción con Gemini → evaluación CER/WER sobre 10 documentos y 10 clips frente a EasyOCR y Qwen3-ASR

## Resultados
| Modalidad | Modelo | Métrica | Valor | RTF |
...

## Hallazgos
1. …
2. …

## Limitaciones
1. La diarización sobrestima el número de hablantes en las entrevistas de calle (hasta 7 en un clip de 95 s) por el ruido y los turnos cortos; en los clips de OpenSLR se fijó 1 hablante porque se sabe de antemano.
2. … (por ejemplo: el OCR de los manuscritos antiguos, como el Libro de Bautismos de Lampa, tiene confianza baja y produce texto poco útil; o el corte en tramos de 60 s parte frases a la mitad)

## Cómo ejecutar en local
    # con uv (recomendado)
    uv sync                                               # solo la app
    uv run streamlit run app.py
    # notebooks: uv sync --group docai --group audio --group notebooks

## Cómo reproducir todo desde cero
1. `git clone https://github.com/jyauric/python-actividades && cd python-actividades/tarea_2`
2. Instala uv (<https://docs.astral.sh/uv/>) y ejecuta `uv sync --group docai --group audio --group notebooks` (Python 3.12, versiones exactas en `uv.lock`).
3. Opcional, solo para volver a llamar al LLM: copia `.env.example` a `.env` y pon tu `GEMINI_API_KEY`. Sin clave, el notebook usa `datos/extraccion_llm.csv`.
4. Abre `01_extraccion.ipynb` y luego `02_evaluacion.ipynb` (VS Code con kernel `.venv`, o `uv run jupyter lab`) y ejecuta **Restart & Run All**. Las imágenes y entrevistas de Commons y los clips de OpenSLR 73 se descargan solos.
5. La primera ejecución descarga modelos: PaddleOCR PP-OCRv6, faster-whisper `small`, EasyOCR, Qwen3-ASR 0.6B y WeSpeaker (unos 3–4 GB en total, en la caché de Hugging Face).
6. Lo manual no se recalcula: la muestra (`muestra_evaluacion.csv`), las referencias (`texto_referencia`), la extracción LLM y la auditoría (`auditoria_llm.csv`) se leen de los CSV publicados. Los nombres reales (`datos/raw/reemplazos.json`) no se publican por privacidad; sin ese archivo los textos se dejan como están en los CSV, que ya están seudonimizados.

    # o con pip
    pip install -r requirements.txt && streamlit run app.py

## Uso de IA
Capturas de la conversación en `evidencias_ia/`.