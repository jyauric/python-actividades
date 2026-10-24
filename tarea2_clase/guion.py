"""Del texto largo al guion del reel.

1) uv run python guion.py --texto informe.md --solo-prompt > prompt.txt
   Pega prompt.txt en chat.qwen.ai y guarda la respuesta como respuesta.txt.
2) uv run python guion.py --texto informe.md --respuesta respuesta.txt
   Guarda salidas/guion.json y marca con ¡¡ las cifras que no están tal cual en el texto.
"""

import argparse
import json
import re
import sys
from pathlib import Path

PROMPT = """Eres guionista de reels de divulgación científica. Convierte el TEXTO en el guion
de un reel vertical de 30 a 60 segundos, en español, narrado en primera persona por la autora.

Reglas:
- Usa SOLO hechos y cifras que estén en el TEXTO. No inventes, no redondees, no exageres.
- Respeta los matices: "exposición" no es "afectación"; un mínimo no es un total.
- Entre 6 y 8 escenas. Cada "frase" tiene de 10 a 22 palabras (en total, 90 a 140 palabras).
- Escribe las cifras con dígitos, igual que en el TEXTO (por ejemplo 696 000, 26 %).
- "cifra" es el número grande que se ve en pantalla (o "" si no hay) y "etiqueta" lo explica
  en menos de 8 palabras.
- La primera escena engancha con una pregunta; la última cierra con el hallazgo principal.
- Escribe además tres posts para acompañar el reel: LinkedIn (80-120 palabras),
  Instagram (40-70 palabras, con 3-5 hashtags) y X (máximo 260 caracteres).

Responde SOLO con este JSON, sin texto antes ni después:
{{"titulo": "...",
  "escenas": [{{"frase": "...", "cifra": "...", "etiqueta": "..."}}],
  "posts": {{"linkedin": "...", "instagram": "...", "x": "..."}}}}

TEXTO:
<<<
{texto}
>>>
"""

NUM = re.compile(r"\d+(?:[ .]\d{3})*(?:,\d+)?")


def leer_texto(ruta: Path) -> str:
    if ruta.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        return "\n".join(p.extract_text() or "" for p in PdfReader(ruta).pages)
    texto = ruta.read_text(encoding="utf-8")
    # Quita imágenes y enlaces de Markdown: no aportan al guion.
    texto = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", texto)
    return re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", texto)


def numeros(s: str) -> set[str]:
    """Números normalizados: '695 812' y '695.812' -> '695812'."""
    return {re.sub(r"[ .]", "", n) for n in NUM.findall(s.replace(" ", " ").replace("\xa0", " "))}


def extraer_json(respuesta: str) -> dict:
    respuesta = re.sub(r"```(?:json)?", "", respuesta)
    ini, fin = respuesta.find("{"), respuesta.rfind("}")
    if ini < 0 or fin < 0:
        sys.exit("No encontré un JSON en la respuesta.")
    return json.loads(respuesta[ini : fin + 1])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--texto", type=Path, default=Path("informe.md"))
    ap.add_argument("--solo-prompt", action="store_true")
    ap.add_argument("--respuesta", type=Path)
    ap.add_argument("--salida", type=Path, default=Path("salidas/guion.json"))
    args = ap.parse_args()

    texto = leer_texto(args.texto)
    if args.solo_prompt:
        print(PROMPT.format(texto=texto))
        return
    if not args.respuesta:
        sys.exit("Usa --solo-prompt o --respuesta respuesta.txt")

    guion = extraer_json(args.respuesta.read_text(encoding="utf-8"))
    en_texto = numeros(texto)
    alertas = 0
    for i, esc in enumerate(guion["escenas"], 1):
        fuera = sorted(numeros(esc["frase"] + " " + esc.get("cifra", "")) - en_texto)
        esc["no_esta_en_texto"] = fuera
        marca = "¡¡ " if fuera else "   "
        alertas += bool(fuera)
        print(f"{marca}{i}. [{esc.get('cifra', '')}] {esc['frase']}")
        if fuera:
            print(f"      ¡¡ cifras que no están tal cual en el texto: {', '.join(fuera)}")
    palabras = sum(len(e["frase"].split()) for e in guion["escenas"])
    print(f"\n{len(guion['escenas'])} escenas, {palabras} palabras (~{palabras / 2.5:.0f} s). "
          f"Escenas con alertas: {alertas}.")
    for red, post in guion.get("posts", {}).items():
        fuera = sorted(numeros(post) - en_texto)
        if fuera:
            print(f"¡¡ post {red}: cifras que no están en el texto: {', '.join(fuera)}")

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(guion, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Guardado {args.salida}. Revísalo contra {args.texto} antes de hacer el reel.")


if __name__ == "__main__":
    main()
