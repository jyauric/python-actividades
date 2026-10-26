"""Dashboard de la Tarea 2: voces y documentos peruanos (OCR + ASR + LLM)."""
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATOS = Path(__file__).resolve().parent / "datos"
EJEMPLOS = DATOS / "ejemplos"

st.set_page_config(page_title="Voces y documentos peruanos", page_icon="📜", layout="wide")


@st.cache_data
def cargar(nombre):
    ruta = DATOS / nombre
    return pd.read_csv(ruta) if ruta.exists() else pd.DataFrame()


def descargar(df, nombre):
    st.download_button("Descargar CSV", df.to_csv(index=False).encode("utf-8"), nombre, "text/csv", key=nombre)


def ejemplo(id_, extensiones):
    "Ruta del archivo publicable de datos/ejemplos/, si existe."
    for ext in extensiones:
        ruta = EJEMPLOS / f"{id_}{ext}"
        if ruta.exists():
            return ruta
    return None


docs = cargar("documentos.csv")
auds = cargar("transcripciones.csv")
fuentes = cargar("fuentes.csv")
metricas = cargar("metricas.csv")
evaluacion = cargar("evaluacion_por_archivo.csv")
llm = cargar("extraccion_llm.csv")
auditoria = cargar("auditoria_llm.csv")

if docs.empty or auds.empty:
    st.error("Faltan `datos/documentos.csv` o `datos/transcripciones.csv`: ejecuta primero los notebooks.")
    st.stop()

# ── Encabezado ────────────────────────────────────────────────────────────────
st.title("¿Pueden convertirse documentos escaneados y entrevistas en audio en un archivo de texto estructurado y buscable?")
st.markdown(
    "**Metodología.** 25 documentos peruanos de Wikimedia Commons (8 impresos, 8 fotos y 9 manuscritos) "
    "leídos con PaddleOCR (PP-OCRv6) y 36 minutos de audio en 31 clips (12 entrevistas de Commons y 6 clips "
    "de OpenSLR 73) transcritos con faster-whisper small (VAD + diarización), con nombres seudonimizados. "
    "Una muestra fija de 10 documentos y 10 clips se comparó con transcripciones manuales (CER/WER) frente a "
    "EasyOCR y Qwen3-ASR, y Gemini extrajo campos estructurados que se auditaron a mano."
)

# ── Filtros ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filtros")
    buscar = st.text_input("Buscar en los textos")
    todos_tipos = sorted(docs.tipo.dropna().unique())
    tipos = st.multiselect("Tipo de documento", todos_tipos, default=todos_tipos)
    todos_modelos = sorted(evaluacion.modelo.unique()) if not evaluacion.empty else []
    modelos = st.multiselect("Modelo (evaluación)", todos_modelos, default=todos_modelos)
    dur_max = float(auds.duracion_seg.max())
    rango = st.slider("Duración del clip (s)", 0.0, dur_max, (0.0, dur_max))

docs_f = docs[docs.tipo.isin(tipos)]
auds_f = auds[auds.duracion_seg.between(*rango)]
if buscar:
    docs_f = docs_f[docs_f.texto_ocr.fillna("").str.contains(buscar, case=False, regex=False)]
    auds_f = auds_f[auds_f.texto_asr.fillna("").str.contains(buscar, case=False, regex=False)]
eval_f = evaluacion[evaluacion.modelo.isin(modelos)] if not evaluacion.empty else evaluacion


def metrica_elegida(nombre):
    if metricas.empty:
        return "—"
    fila = metricas[(metricas.metrica == nombre) & metricas.elegido.astype(bool)]
    return f"{fila.valor.iloc[0]:.2f}" if len(fila) else "—"


# ── Indicadores ───────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Documentos", len(docs_f))
c2.metric("Minutos de audio", f"{auds_f.duracion_seg.sum() / 60:.1f}")
c3.metric("CER (OCR elegido)", metrica_elegida("CER"))
c4.metric("WER (ASR elegido)", metrica_elegida("WER"))
c5.metric("Concordancia LLM-humano",
          f"{auditoria.correcta.mean():.0%} ({int(auditoria.correcta.sum())}/{len(auditoria)})"
          if not auditoria.empty else "—")

resumen, tab_eval, tab_docs, tab_auds, tab_fuentes = st.tabs(
    ["Resumen", "Evaluación", "Documentos", "Audios", "Fuentes"])

# ── Resumen ───────────────────────────────────────────────────────────────────
with resumen:
    g1, g2 = st.columns(2)
    largo = docs_f.assign(n_caracteres=docs_f.texto_ocr.fillna("").str.len())
    g1.plotly_chart(px.box(largo, x="tipo", y="n_caracteres", points="all",
                           title="Los manuscritos (carteles escolares y libros parroquiales) generan más texto OCR que impresos y fotos"),
                    width="stretch")
    g2.plotly_chart(px.histogram(auds_f, x="duracion_seg", nbins=20,
                                 title="La mitad de los clips dura 60 s: son los tramos en que se cortaron las entrevistas largas"),
                    width="stretch")
    st.dataframe(docs_f[["id", "tipo", "fuente", "modelo_ocr", "texto_ocr"]], width="stretch")
    descargar(docs_f, "documentos_filtrados.csv")

# ── Evaluación ────────────────────────────────────────────────────────────────
with tab_eval:
    if eval_f.empty:
        st.info("Aún no hay resultados de evaluación (Parte 2).")
    else:
        g1, g2 = st.columns(2)
        g1.plotly_chart(px.bar(metricas[metricas.modelo.isin(modelos)], x="modelo", y="valor",
                               color="metrica", barmode="group",
                               title="Error promedio por modelo (CER en documentos, WER en audio)"),
                        width="stretch")
        g2.plotly_chart(px.box(eval_f, x="modelo", y="error", color="modalidad", points="all",
                               title="Error por archivo de la muestra"),
                        width="stretch")
        st.dataframe(eval_f, width="stretch")
        descargar(eval_f, "evaluacion_filtrada.csv")


def campos_llm(id_):
    fila = llm[llm.id == id_] if not llm.empty else llm
    if len(fila):
        st.json(json.loads(fila.campos_json.iloc[0]))
    else:
        st.caption("Sin extracción LLM para este archivo.")


def comparacion(id_):
    filas = eval_f[eval_f.id == id_] if not eval_f.empty else eval_f
    if len(filas):
        st.dataframe(filas[["modelo", "error", "segundos", "texto"]], width="stretch")
    else:
        st.caption("Este archivo no está en la muestra de evaluación.")


# ── Explorador de documentos ──────────────────────────────────────────────────
with tab_docs:
    if docs_f.empty:
        st.info("Ningún documento coincide con los filtros.")
    else:
        id_doc = st.selectbox("Documento", docs_f.id)
        d = docs_f.set_index("id").loc[id_doc]
        izq, der = st.columns(2)
        with izq:
            imagen = ejemplo(id_doc, [".jpg", ".jpeg", ".png"])
            if imagen:
                st.image(str(imagen), caption=f"{id_doc} · {d.tipo}")
            else:
                st.info("Imagen no publicable (licencia o datos personales): solo se muestra el texto.")
        with der:
            st.markdown(f"**Texto OCR** ({d.modelo_ocr})")
            st.text(d.texto_ocr)
            if isinstance(d.texto_referencia, str) and d.texto_referencia:
                st.markdown("**Referencia manual**")
                st.text(d.texto_referencia)
            st.markdown("**Campos extraídos por el LLM**")
            campos_llm(id_doc)
        st.markdown("**Comparación de modelos (CER)**")
        comparacion(id_doc)

# ── Explorador de audios ──────────────────────────────────────────────────────
with tab_auds:
    if auds_f.empty:
        st.info("Ningún clip coincide con los filtros.")
    else:
        id_aud = st.selectbox("Clip", auds_f.id)
        a = auds_f.set_index("id").loc[id_aud]
        st.caption(f"{a.duracion_seg / 60:.1f} min · {a.n_hablantes} hablante(s) · {a.modelo_asr}")
        audio = ejemplo(id_aud, [".ogg", ".mp3", ".wav"])
        url = None
        if "url_audio_publico" in fuentes.columns:
            url = fuentes.set_index("id").url_audio_publico.get(id_aud)
        if audio:
            st.audio(str(audio))
        elif isinstance(url, str) and url:
            st.audio(url)
        else:
            st.info("Audio no publicable: solo se muestra la transcripción.")
        st.markdown("**Transcripción con hablantes**")
        st.text(a.texto_asr)
        st.markdown("**Campos extraídos por el LLM**")
        campos_llm(id_aud)
        st.markdown("**Comparación de modelos (WER)**")
        comparacion(id_aud)

# ── Fuentes ───────────────────────────────────────────────────────────────────
with tab_fuentes:
    st.dataframe(fuentes, width="stretch")
    descargar(fuentes, "fuentes.csv")
