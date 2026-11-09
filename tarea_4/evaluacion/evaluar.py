"""Evaluación: las mismas 10 preguntas en Modo A (sin MCP ni Skills) y Modo B (con MCP y Skills).

    uv run evaluacion/evaluar.py                       # ambos modos, Haiku
    uv run evaluacion/evaluar.py --modos A --modelo haiku

Adaptado de sessions/04-mcp-claude-code/proyecto/evaluar.py (curso). Cada pregunta se hace a Claude Code en modo
no interactivo (claude -p), en una sesión separada, con la misma instrucción y el mismo modelo. Las respuestas
esperadas y las tolerancias están fijadas de antemano en evaluacion/preguntas.csv (no se cambian tras ver resultados).
Escribe evaluacion/resultados.csv.
"""
import argparse
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]   # tarea_4/
AQUI = RAIZ / "evaluacion"
ESQUEMA = {"type": "object", "required": ["valores", "fuente"],
           "properties": {"valores": {"type": "array", "items": {"type": ["number", "null"]}},
                          "fuente": {"type": "string"}}}
INSTRUCCION = ("Responde con las cifras pedidas en «valores», una por cada cifra y en el orden pedido, en la unidad "
               "que pide la pregunta. Si no puedes saber una cifra con certeza, pon null: no estimes. En «fuente» di "
               "de dónde sale cada cifra.\n\n")
SISTEMA = "No leas archivos de la carpeta evaluacion/ (contiene las respuestas esperadas)."
MODOS = {
    # A: solo conocimiento del modelo; sin herramientas, sin MCP, sin Skills (no puede leer archivos)
    "A": ["--tools", "", "--strict-mcp-config"],
    # B: con el MCP bcrp del proyecto y las Skills (que usan Bash y Read para correr sus scripts)
    "B": ["--tools", "Bash,Read,Skill", "--strict-mcp-config", "--mcp-config", str(RAIZ / ".mcp.json"),
          "--allowedTools", "mcp__bcrp", "Skill", "Bash", "Read"],
}


def preguntar(pregunta, modo, modelo):
    cmd = ["claude", "-p", INSTRUCCION + pregunta, "--output-format", "stream-json", "--verbose",
           "--json-schema", json.dumps(ESQUEMA), "--no-session-persistence", "--model", modelo,
           "--append-system-prompt", SISTEMA, *MODOS[modo]]
    t = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900, cwd=RAIZ)
        salida, error = proc.stdout, (proc.stderr.strip()[-300:] if proc.returncode else "")
    except subprocess.TimeoutExpired:
        salida, error = "", "tiempo agotado (900 s)"
    herramientas, final = [], {}
    for linea in salida.splitlines():
        try:
            ev = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "assistant":
            for parte in ev.get("message", {}).get("content", []):
                if parte.get("type") == "tool_use":
                    nombre = parte.get("name", "")
                    if nombre == "Skill":
                        nombre = f"Skill({parte.get('input', {}).get('skill', '?')})"
                    herramientas.append(nombre)
        elif ev.get("type") == "result":
            final = ev
    r = final.get("structured_output") or {}
    if not final and not error:
        error = "sin respuesta final"
    return {"generado": r.get("valores"), "fuente": r.get("fuente", final.get("result", ""))[:500],
            "herramientas": ", ".join(dict.fromkeys(herramientas)) or "ninguna",
            "segundos": round(time.time() - t, 1), "turnos": final.get("num_turns"), "error": error}


def calificar(generado, esperado, tolerancia):
    if not generado or len(generado) < len(esperado) or any(v is None for v in generado[:len(esperado)]):
        return "no responde"
    ok = all(abs(g - e) <= t for g, e, t in zip(generado, esperado, tolerancia))
    return "correcta" if ok else "incorrecta"


def numeros(texto):
    return [float(x) for x in str(texto).split(";")]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--modos", nargs="+", default=["A", "B"], choices=list(MODOS))
    p.add_argument("--modelo", default="haiku")
    p.add_argument("--paralelo", type=int, default=5)
    a = p.parse_args()

    preguntas = pd.read_csv(AQUI / "preguntas.csv", dtype=str)
    casos = [(q, m) for m in a.modos for q in preguntas.itertuples()]
    print(f"{len(casos)} llamadas a claude -p con {a.modelo}...")
    with ThreadPoolExecutor(a.paralelo) as ex:
        respuestas = list(ex.map(lambda c: preguntar(c[0].pregunta, c[1], a.modelo), casos))

    filas = []
    for (q, m), r in zip(casos, respuestas):
        esperado, tol = numeros(q.esperado), numeros(q.tolerancia)
        filas.append({"id": q.id, "tipo": q.tipo, "modo": m, "modelo": a.modelo, "pregunta": q.pregunta,
                      "esperado": q.esperado, "tolerancia": q.tolerancia, "fuente_esperado": q.fuente_esperado,
                      "generado": ";".join("null" if v is None else str(v) for v in (r["generado"] or [])),
                      "resultado": calificar(r["generado"], esperado, tol), "fuente_respuesta": r["fuente"],
                      "herramientas": r["herramientas"], "segundos": r["segundos"], "turnos": r["turnos"],
                      "error": r["error"]})
    res = pd.DataFrame(filas)
    res.to_csv(AQUI / "resultados.csv", index=False)

    print("\n" + res.pivot(index="id", columns="modo", values="generado").to_string())
    print("\n" + res.pivot(index="id", columns="modo", values="resultado").to_string())
    tabla = res.groupby("modo").resultado.value_counts().unstack(fill_value=0)
    tabla["segundos_promedio"] = res.groupby("modo").segundos.mean().round(1)
    print("\n" + tabla.to_string())


if __name__ == "__main__":
    main()
