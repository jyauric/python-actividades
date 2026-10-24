# ¿Cuántas personas viven cerca de los incendios del Perú? · Reel con mi voz

Tarea sesión 15 · Ciencia de Datos con Python · 24 de octubre de 2026

Un reel vertical de 59 segundos, narrado con mi voz clonada por Qwen3-TTS, a partir del README
de la tarea anterior ([`../tarea_clase/README.md`](../tarea_clase/README.md), copiado aquí como
[`informe.md`](informe.md)).

- **Reel:** [`salidas/reel.mp4`](salidas/reel.mp4) (subtítulos aparte en [`salidas/reel.srt`](salidas/reel.srt))
- **Posts:** [`salidas/posts.md`](salidas/posts.md) (LinkedIn, Instagram y X)
- **Diapositivas de la arquitectura:** [claude.ai/artifact/UnoQysVvBRBbC5XbrdJjDX](https://claude.ai/artifact/UnoQysVvBRBbC5XbrdJjDX)

> Voz generada con IA. La grabación de referencia no está en el repositorio.

## Flujo

| Paso | Quién | Herramienta | Sale |
|---|---|---|---|
| 1. Texto largo | Fuente | README de la tarea anterior | `informe.md` |
| 2. Guion | Modelo | `guion.py` arma el prompt; Qwen (chat.qwen.ai) lo escribe | `salidas/guion.json` |
| 3. Revisión | Yo | Frase por frase contra `informe.md` | este README |
| 4. Voz | Modelo | Qwen3-TTS-12Hz-0.6B-Base clona 15 s de mi voz | `salidas/tmp/voz.wav` |
| 5. Video | Modelos y código | Whisper, Pillow y ffmpeg | `reel.mp4`, `reel.srt`, `portada.png`, `posts.md` |

## Qué corregí del guion

`guion.py` no marcó ninguna cifra con `¡¡`: todos los números estaban en el texto. Los errores
estaban en las frases, como en la demo de la clase. La respuesta original de Qwen está en
[`respuesta.txt`](respuesta.txt); la versión corregida, en [`salidas/guion.json`](salidas/guion.json).

### Escenas

| Escena | Frase original (Qwen) | Frase corregida | Por qué (dato del README) |
|---|---|---|---|
| 1 | «~696 000 personas viven expuestas a cinco kilómetros de los incendios **activos** en el Perú» | «~696 000 personas viven a 5 km o menos de algún incendio del Perú de esta semana» | Las ~696 000 son para los 255 incendios del 14 al 21 oct. Los activos en las últimas 24 h fueron 21, con ~17 000 personas. Además es «≤ 5 km», no «a 5 km». |
| 5 | «El incendio de Río Tambo que analicé **quemó ~1 085 hectáreas**» | «En Río Tambo se quemaron **al menos** ~1 085 hectáreas, pero solo ~1 060 personas viven a 5 km o menos» | Las hectáreas son un mínimo: las nubes tapan el 44 % de los focos y la imagen es anterior a los focos. |
| 6 | «**este modelo** probablemente subestima a las comunidades asháninkas» | «**WorldPop** probablemente no ve bien a las comunidades asháninkas dispersas» | «Este modelo» suena a que hablo del modelo de IA; el README se refiere a WorldPop. |
| Título | «¿A quién **afectan** los incendios del Perú?» | «¿Cuántas personas **viven cerca** de los incendios del Perú?» | El análisis mide exposición (vivir a ≤ 5 km), no afectación; el título contradecía la escena 4. Venía de mi propio README. |

Sin cambios: escenas 2, 3, 4 y 7 coinciden con el README (255 incendios con ≥ 3 focos; Ucayali
~150 000 y 26 % de su población; exposición no es afectación; el hallazgo de Río Tambo).

Agregué a mano en la escena 2 una nota al pie que define «incendio» (3 o más focos de calor del
satélite VIIRS a ≤ 1 km y ≤ 48 h entre sí), y una figura de la tarea anterior en las escenas 1,
2, 3, 5 y 6.

### Posts

| Post | Qué decía | Qué quedó | Por qué |
|---|---|---|---|
| LinkedIn | «Analizamos la exposición poblacional a los incendios **activos**» | «Analicé la exposición de la población a los incendios» | Mismo error de la escena 1; el trabajo es individual. |
| LinkedIn | «identifiqué 255 incendios» | «255 incendios con al menos tres focos» | La definición de incendio es una decisión del método. |
| Instagram | «~696 000 personas viven expuestas a ≤ 5 km de incendios **activos**» | «…de alguno de los 255 incendios del Perú entre el 14 y el 21 de octubre» | Mismo error de la escena 1. |
| Instagram | «Ucayali concentra el 26 % de su población en esta condición» | «En Ucayali es el 26 % de su población» | Evita leerlo como 26 % del país. |
| X | «a ≤ 5 km de incendios **activos**» | «a ≤ 5 km de alguno de los 255 incendios» | Mismo error de la escena 1. |

### Subtítulos

En la primera versión, los subtítulos salían de lo que Whisper escuchó y tenían errores:
«Ukayali» (Ucayali), «hayan incas» (asháninkas), «World Pop» (WorldPop) y «696 .000».
Ahora el texto de los subtítulos sale del guion revisado; de Whisper solo se toma cuándo
empieza y termina cada escena.

## Voz clonada

- Referencia: nota de voz del celular, ~15 s, en un cuarto en silencio. No se sube (`.gitignore`).
- Modelo: Qwen3-TTS-12Hz-0.6B-Base en el chip de una Mac mini M4 (`--device mps`), unos 15 s por escena.
- Control de Whisper: 4 de 7 escenas quedaron bajo el 25 %; las escenas 2, 3 y 5 quedaron entre
  26 % y 48 %, en parte porque Whisper escribe «14» donde el guion dice «catorce».
- El reel duraba 66 s; se aceleró la voz un 12 % (`--velocidad 1.12`) para dejarlo en 59 s.
- Qué tal salió el clon y qué haría distinto: me pareció que salió algo bien pero volvería a grabarlo ya que me parece que por momentos se diferenciaba bastante de mi voz, también para mejorar la entonación y volverlo más interesante de escuchar. Tal vez sería mejor grabar parte del guión para que sea más cercano.

## Cómo correrlo

Requiere [uv](https://docs.astral.sh/uv/). Los modelos (unos 2,3 GB) se descargan la primera vez.

```bash
cd tarea2_clase
uv sync

# 1. Prompt para pegar en chat.qwen.ai; la respuesta va en respuesta.txt
uv run python guion.py --texto informe.md --solo-prompt > prompt.txt
uv run python guion.py --texto informe.md --respuesta respuesta.txt

# 2. Revisar salidas/guion.json a mano contra informe.md

# 3. Voz, subtítulos y video (con tu propia grabación en mi_voz.m4a)
uv run python hacer_reel.py --voz mi_voz.m4a --autor "Josselin" \
    --fuente "NASA FIRMS, WorldPop, Sentinel-2" --device mps --velocidad 1.12
```

Para rehacer solo el video sin volver a clonar la voz: añade `--reusar-voz`.

## Estructura

```
informe.md          texto largo (README de la tarea anterior)
guion.py            prompt para Qwen y lectura de su respuesta, con alerta ¡¡
hacer_reel.py       voz clonada, control de Whisper, cuadros, video y posts
respuesta.txt       lo que respondió Qwen (guion original, sin corregir)
salidas/            guion.json (revisado), reel.mp4, reel.srt, portada.png, posts.md
```
