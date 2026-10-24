"""Del guion revisado al reel: tu voz clonada (Qwen3-TTS) + subtítulos (Whisper) + video (ffmpeg).

uv run python hacer_reel.py --voz mi_voz.m4a --autor "Josselin" \
    --fuente "NASA FIRMS, WorldPop, Sentinel-2" --device mps

Lee salidas/guion.json y escribe en salidas/: reel.mp4, reel.srt, portada.png, posts.md.
"""

import argparse
import json
import re
import subprocess
import textwrap
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import soundfile as sf
from num2words import num2words
from PIL import Image, ImageDraw, ImageFont

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
W, H = 1080, 1920
FONDO, TEXTO, ACENTO, GRIS = (18, 18, 22), (245, 245, 245), (255, 122, 48), (160, 160, 168)
AVISO = "Voz generada con IA"
FUENTES = "/System/Library/Fonts/Supplemental/"


def fuente(tam: int, negrita: bool = False) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FUENTES + ("Arial Bold.ttf" if negrita else "Arial.ttf"), tam)
    except OSError:
        return ImageFont.load_default(tam)


def ffmpeg(*args: str) -> None:
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", *args], check=True)


def audio16k(ruta: Path) -> np.ndarray:
    """Audio mono a 16 kHz para Whisper, decodificado con el ffmpeg de imageio-ffmpeg."""
    crudo = subprocess.run([FFMPEG, "-loglevel", "error", "-i", str(ruta), "-f", "f32le",
                            "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(crudo, np.float32)


# --- Texto para hablar: las cifras se leen en palabras --------------------------------------

def _num(m: re.Match) -> str:
    s = m.group(0).replace(" ", "").replace(".", "")
    if "," in s:
        ent, dec = s.split(",")
        return f"{num2words(int(ent), lang='es')} coma {num2words(int(dec), lang='es')}"
    return num2words(int(s), lang="es")


def para_hablar(frase: str) -> str:
    t = frase.replace(" ", " ").replace("\xa0", " ")
    t = re.sub(r"~\s*", "cerca de ", t)
    t = re.sub(r"≤\s*(\S+ \S+)", r"\1 o menos", t)
    t = re.sub(r"≥\s*", "al menos ", t)
    t = re.sub(r"(\d)\s*%", r"\1 por ciento", t)
    t = re.sub(r"(\d)\s*ha\b", r"\1 hectáreas", t)
    t = re.sub(r"(\d)\s*km\b", r"\1 kilómetros", t)
    t = re.sub(r"\d{1,3}(?: \d{3})+(?:,\d+)?|\d+(?:,\d+)?", _num, t)
    return t


# --- Imágenes -------------------------------------------------------------------------------

def centrado(d: ImageDraw.ImageDraw, y: int, texto: str, f, color, ancho: int) -> int:
    for linea in textwrap.wrap(texto, ancho):
        w = d.textlength(linea, font=f)
        d.text(((W - w) / 2, y), linea, font=f, fill=color)
        y += int(f.size * 1.25)
    return y


def pie(d: ImageDraw.ImageDraw, autor: str, fuente_datos: str) -> None:
    # Arriba y con margen: abajo y en los bordes van los botones de cada app.
    centrado(d, 230, AVISO, fuente(38, True), ACENTO, 40)
    centrado(d, 285, f"{autor} · Fuente: {fuente_datos}", fuente(30), GRIS, 60)


def tarjeta(esc: dict) -> Image.Image | None:
    """La figura de la escena ("imagen", y "recorte" opcional en fracciones x0, y0, x1, y1)
    sobre una tarjeta blanca de 960 x 700 como máximo."""
    if not esc.get("imagen"):
        return None
    fig = Image.open(esc["imagen"]).convert("RGB")
    if esc.get("recorte"):
        x0, y0, x1, y1 = esc["recorte"]
        fig = fig.crop((int(x0 * fig.width), int(y0 * fig.height), int(x1 * fig.width), int(y1 * fig.height)))
    fig.thumbnail((920, 660), Image.LANCZOS)
    card = Image.new("RGB", (fig.width + 40, fig.height + 40), (255, 255, 255))
    card.paste(fig, (20, 20))
    return card


def escena_png(esc: dict, palabras: list[str], actual: int, ruta: Path,
               autor: str, fuente_datos: str, card: Image.Image | None = None) -> None:
    img = Image.new("RGB", (W, H), FONDO)
    d = ImageDraw.Draw(img)
    if card is None:
        y = 560
        if esc.get("cifra"):
            y = centrado(d, y, esc["cifra"], fuente(170, True), ACENTO, 9) + 20
        y = centrado(d, y, esc.get("etiqueta", ""), fuente(60, True), TEXTO, 26)
        if esc.get("nota"):
            centrado(d, y + 10, esc["nota"], fuente(30), GRIS, 58)
        subtitulo(d, palabras, actual, 1180, 50)
    else:
        img.paste(card, ((W - card.width) // 2, 360 + (700 - card.height) // 2))
        y = 1085
        if esc.get("cifra"):
            y = centrado(d, y, esc["cifra"], fuente(110, True), ACENTO, 12)
        y = centrado(d, y, esc.get("etiqueta", ""), fuente(46, True), TEXTO, 34)
        if esc.get("nota"):  # nota al pie: define un término de la escena
            y = centrado(d, y + 4, esc["nota"], fuente(28), GRIS, 62)
        subtitulo(d, palabras, actual, max(y + 25, 1390), 44)
    pie(d, autor, fuente_datos)
    img.save(ruta)


def subtitulo(d: ImageDraw.ImageDraw, palabras: list[str], actual: int, y: int, tam: int) -> None:
    """Las palabras de la escena; la que suena va en naranja."""
    f, margen = fuente(tam, True), 110
    lineas, linea, ancho = [], [], 0.0
    esp = d.textlength(" ", font=f)
    for i, p in enumerate(palabras):
        w = d.textlength(p, font=f)
        if linea and ancho + esp + w > W - 2 * margen:
            lineas.append(linea)
            linea, ancho = [], 0.0
        ancho += (esp if linea else 0) + w
        linea.append((i, p, w))
    if linea:
        lineas.append(linea)
    for linea in lineas:
        x = (W - (sum(w for _, _, w in linea) + esp * (len(linea) - 1))) / 2
        for i, p, w in linea:
            d.text((x, y), p, font=f, fill=ACENTO if i == actual else TEXTO)
            x += w + esp
        y += int(f.size * 1.3)


def portada_png(guion: dict, ruta: Path, autor: str, fuente_datos: str) -> None:
    img = Image.new("RGB", (W, H), FONDO)
    d = ImageDraw.Draw(img)
    centrado(d, 650, guion.get("titulo", ""), fuente(96, True), TEXTO, 18)
    pie(d, autor, fuente_datos)
    img.save(ruta)


# --- Subtítulos -----------------------------------------------------------------------------

def palabras_guion(frase: str) -> list[str]:
    """Palabras de la frase revisada; '~696 000' o '26 %' cuentan como una sola."""
    return re.findall(r"\S*\d(?: \d{3})+\S*(?: %)?|\S+ %|\S+", frase)


def inicios(frase: str, oidas: list, dur: float) -> list[float]:
    """Inicio de cada palabra del guion. Los subtítulos muestran el texto revisado, no lo que
    Whisper transcribió; de Whisper solo se toma cuándo empieza y termina el habla, y el tiempo
    se reparte según lo largo de cada palabra al decirla."""
    tokens = palabras_guion(frase)
    ini, fin = (oidas[0].start, oidas[-1].end) if oidas else (0.0, dur)
    pesos = np.array([len(para_hablar(t)) + 1 for t in tokens], float)
    return list(ini + (fin - ini) * np.concatenate([[0], np.cumsum(pesos)[:-1]]) / pesos.sum())


def hms(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--guion", type=Path, default=Path("salidas/guion.json"))
    ap.add_argument("--voz", type=Path, default=Path("mi_voz.m4a"))
    ap.add_argument("--autor", default="")
    ap.add_argument("--fuente", default="")
    ap.add_argument("--tts", default="Qwen/Qwen3-TTS-12Hz-0.6B-Base")
    ap.add_argument("--whisper", default="small")
    ap.add_argument("--device", default="mps")
    ap.add_argument("--salidas", type=Path, default=Path("salidas"))
    ap.add_argument("--velocidad", type=float, default=1.0, help="1.1 = 10 %% más rápido")
    ap.add_argument("--reusar-voz", action="store_true",
                    help="usa salidas/tmp/escena_XX.wav ya generados y solo rehace el video")
    args = ap.parse_args()

    import torch
    from faster_whisper import WhisperModel
    from jiwer import wer
    from qwen_tts import Qwen3TTSModel

    out = args.salidas
    tmp = out / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    guion = json.loads(args.guion.read_text(encoding="utf-8"))
    escenas = guion["escenas"]

    # 1. Tu voz de referencia: a WAV mono 24 kHz y transcrita (Qwen la necesita con su texto).
    asr = WhisperModel(args.whisper, device="cpu", compute_type="int8")
    if not args.reusar_voz:
        ref = tmp / "ref.wav"
        ffmpeg("-i", str(args.voz), "-ac", "1", "-ar", "24000", str(ref))
        segs, _ = asr.transcribe(audio16k(ref), language="es")
        ref_texto = " ".join(s.text.strip() for s in segs)
        print(f"Tu grabación dice: {ref_texto}")

    # 2. Clonar la voz, escena por escena.
    if not args.reusar_voz:
        print(f"Cargando {args.tts} en {args.device}...")
        tts = Qwen3TTSModel.from_pretrained(args.tts, device_map=args.device, dtype=torch.float32)
        prompt = tts.create_voice_clone_prompt(ref_audio=str(ref), ref_text=ref_texto)
    limpiar = lambda s: re.sub(r"[^\wáéíóúñü ]", "", s.lower())
    pausa = 0.35
    audios, duraciones, tiempos, sr = [], [], [], 24000
    for i, esc in enumerate(escenas, 1):
        texto = para_hablar(esc["frase"])
        if args.reusar_voz:
            wav, sr = sf.read(tmp / f"escena_{i:02d}.wav", dtype="float32")
            segs, _ = asr.transcribe(audio16k(tmp / f"escena_{i:02d}.wav"), language="es", word_timestamps=True)
            audios.append(wav)
            duraciones.append(len(wav) / sr)
            tiempos.append([w for s in segs for w in s.words])
            continue
        print(f"  voz {i}/{len(escenas)}: {texto}")
        # Control: Whisper vuelve a escuchar la escena; si entiende mal > 25 %, se genera otra vez.
        for intento in range(2):
            wavs, sr = tts.generate_voice_clone(text=texto, language="Spanish", voice_clone_prompt=prompt,
                                                  max_new_tokens=400)  # tope: ~33 s por escena
            wav = np.concatenate([wavs[0].astype(np.float32), np.zeros(int(pausa * sr), np.float32)])
            sf.write(tmp / f"escena_{i:02d}.wav", wav, sr)
            segs, _ = asr.transcribe(audio16k(tmp / f"escena_{i:02d}.wav"), language="es", word_timestamps=True)
            palabras = [w for s in segs for w in s.words]
            error = wer(limpiar(texto), limpiar(" ".join(w.word for w in palabras)) or "-")
            print(f"    intento {intento + 1}: Whisper entendió mal el {error:.0%}")
            if error <= 0.25:
                break
        audios.append(wav)
        duraciones.append(len(wav) / sr)
        tiempos.append(palabras)
    voz = tmp / "voz.wav"
    sf.write(voz, np.concatenate(audios), sr)
    v = args.velocidad
    if v != 1.0:
        ffmpeg("-i", str(tmp / "voz.wav"), "-af", f"atempo={v}", str(tmp / "voz_v.wav"))
        voz = tmp / "voz_v.wav"
    duraciones = [dur / v for dur in duraciones]

    # 3. Subtítulos (.srt, una línea por escena) y video: un cuadro por palabra que suena.
    PORTADA = 1.5
    portada_png(guion, out / "portada.png", args.autor, args.fuente)
    lista = [f"file '{(out / 'portada.png').resolve()}'\nduration {PORTADA}"]
    srt, t0, k = [], PORTADA, 0
    for i, (esc, dur, oidas) in enumerate(zip(escenas, duraciones, tiempos), 1):
        textos = palabras_guion(esc["frase"])
        t_ini = [t / v for t in inicios(esc["frase"], oidas, dur * v)]
        srt.append(f"{i}\n{hms(t0 + t_ini[0])} --> {hms(t0 + dur - pausa / v)}\n{esc['frase']}\n")
        card = tarjeta(esc)
        # Cortes: inicio de cada palabra; el cuadro j muestra la palabra j en naranja.
        cortes = [0.0] + t_ini[1:] + [dur]
        for j in range(len(cortes) - 1):
            png = tmp / f"c_{k:04d}.png"
            escena_png(esc, textos, j, png, args.autor, args.fuente, card)
            lista.append(f"file '{png.resolve()}'\nduration {max(cortes[j + 1] - cortes[j], 0.04):.3f}")
            k += 1
        t0 += dur
    lista.append(f"file '{png.resolve()}'")  # el demuxer concat ignora la duración de la última
    (out / "reel.srt").write_text("\n".join(srt), encoding="utf-8")
    (tmp / "lista.txt").write_text("\n".join(lista), encoding="utf-8")
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(tmp / "lista.txt"),
           "-i", str(voz), "-af", "adelay=1500:all=1,loudnorm=I=-14:TP=-1.5:LRA=11",
           "-ar", "48000", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
           "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart",
           str(out / "reel.mp4"))

    # 5. Posts, con el aviso al final de cada uno.
    posts = guion.get("posts", {})
    md = [f"# Posts: {guion.get('titulo', '')}\n"]
    for red, nombre in [("linkedin", "LinkedIn"), ("instagram", "Instagram"), ("x", "X")]:
        if red in posts:
            md.append(f"## {nombre}\n\n{posts[red].strip()}\n\n{AVISO}. Fuente: {args.fuente}.\n")
    (out / "posts.md").write_text("\n".join(md), encoding="utf-8")

    total = PORTADA + sum(duraciones)
    print(f"\nListo: {out / 'reel.mp4'} ({total:.0f} s), reel.srt, portada.png, posts.md")
    if not 30 <= total <= 60:
        print("¡¡ El reel debe durar entre 30 y 60 s: acorta o alarga frases en guion.json.")


if __name__ == "__main__":
    main()
