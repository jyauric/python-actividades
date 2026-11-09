"""Gráficos de pobreza monetaria (ENAHO 2024) a partir de salidas/indicadores.csv (ya ponderado y validado).

    uv run .claude/skills/graficando-enaho/scripts/graficar.py --tipo todos
    uv run .claude/skills/graficando-enaho/scripts/graficar.py --tipo area|sexo|departamento

Guarda PNG en figuras/. Los títulos se arman con las cifras del CSV: no hay cifras escritas a mano.
Si falta salidas/indicadores.csv, termina con código 2: hay que correr antes la skill limpiando-enaho.
"""
import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

RAIZ = Path(__file__).resolve().parents[4]          # tarea_4/
INDICADORES = RAIZ / "salidas" / "indicadores.csv"
FIGURAS = RAIZ / "figuras"

# Paleta (skill dataviz, paleta de referencia validada): superficie clara, texto, azul secuencial.
SUPERFICIE, TEXTO, TEXTO_2, GRILLA = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
AZUL, AZUL_CLARO, AZUL_OSCURO = "#2a78d6", "#86b6ef", "#1c5cab"

FUENTE = ("Fuente: INEI – ENAHO 2024 (módulos 34 y 02). Residentes habituales, ponderado con facpob07. "
          "Elaboración propia.")
NOTA_REDONDEO = ("Diferencias calculadas con cifras sin redondear; pueden diferir en ±0,1 de la resta de los "
                 "valores mostrados.")


def nombre(depto):
    """'MADRE DE DIOS' -> 'Madre de Dios' (se mantiene la grafía del archivo de referencia, sin tildes)."""
    return " ".join(p.lower() if p in {"DE", "DEL"} else p.capitalize() for p in depto.split())


def conjuncion_y(palabra):
    """'y' pasa a 'e' ante palabra que empieza con sonido /i/ (I-, Hi- + consonante): 'e Ica'; no ante 'Hie-'/'Hia-'."""
    p = palabra.lower()
    if p.startswith("i") or (p.startswith("hi") and p[2:3] not in {"a", "e", "o", "u"}):
        return "e"
    return "y"


def lienzo(alto=4.8, ancho=8.0):
    fig, ax = plt.subplots(figsize=(ancho, alto), dpi=150)
    fig.patch.set_facecolor(SUPERFICIE)
    ax.set_facecolor(SUPERFICIE)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(GRILLA)
    ax.tick_params(colors=TEXTO_2, length=0)
    return fig, ax


def textos(fig, titulo, subtitulo, nota_extra=""):
    fig.text(0.02, 0.97, titulo, ha="left", va="top", fontsize=12.5, fontweight="bold", color=TEXTO)
    fig.text(0.02, 0.905, subtitulo, ha="left", va="top", fontsize=9.5, color=TEXTO_2)
    pie = FUENTE + (f"\n{nota_extra}" if nota_extra else "")
    fig.text(0.02, 0.015, pie, ha="left", va="bottom", fontsize=7.5, color=TEXTO_2)


def guardar(fig, archivo):
    FIGURAS.mkdir(exist_ok=True)
    ruta = FIGURAS / archivo
    fig.savefig(ruta, facecolor=SUPERFICIE)
    plt.close(fig)
    print(f"Guardado: {ruta.relative_to(RAIZ)}")


def grafico_area(ind):
    d = ind[ind.nivel == "area"].set_index("categoria").loc[["Urbana", "Rural"]]
    u, r = d.loc["Urbana", "pobreza_pct"], d.loc["Rural", "pobreza_pct"]   # sin redondear: se redondea al mostrar
    mayor, menor = ("rural", "urbana") if r >= u else ("urbana", "rural")
    titulo = (f"La pobreza {mayor} ({max(u, r):.1f} %) supera en {abs(r - u):.1f} pp a la {menor} "
              f"({min(u, r):.1f} %)")
    fig, ax = lienzo()
    fig.subplots_adjust(top=0.80, bottom=0.21, left=0.08, right=0.97)
    x = range(len(d))
    extrema = d.pobreza_extrema_pct
    no_extrema = d.pobreza_pct - d.pobreza_extrema_pct
    ax.bar(x, extrema, width=0.45, color=AZUL_OSCURO, edgecolor=SUPERFICIE, linewidth=2, label="Pobreza extrema")
    ax.bar(x, no_extrema, bottom=extrema, width=0.45, color=AZUL_CLARO, edgecolor=SUPERFICIE, linewidth=2,
           label="Pobreza no extrema")
    for i, (cat, fila) in enumerate(d.iterrows()):
        ax.text(i, fila.pobreza_pct + 0.8, f"{fila.pobreza_pct:.1f} %", ha="center", va="bottom",
                fontsize=10, fontweight="bold", color=TEXTO)
        ax.text(i, fila.pobreza_extrema_pct / 2, f"{fila.pobreza_extrema_pct:.1f} %", ha="center",
                va="center", fontsize=8.5, color="white")
    ax.set_xticks(list(x), [f"{c}" for c in d.index], fontsize=10, color=TEXTO)
    ax.set_ylim(0, max(d.pobreza_pct) * 1.18)
    ax.set_ylabel("% de la población", color=TEXTO_2, fontsize=9)
    ax.yaxis.grid(True, color=GRILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left", fontsize=9, labelcolor=TEXTO_2)
    textos(fig, titulo, "Pobreza monetaria total y extrema por área de residencia. Perú, 2024 (% de la población)",
           "Área urbana: centros poblados de 2 000 habitantes a más (estrato 1–5).\n" + NOTA_REDONDEO)
    guardar(fig, "pobreza_area_2024.png")


def grafico_sexo(ind):
    d = ind[ind.nivel == "sexo"].set_index("categoria").loc[["Mujer", "Hombre"]]
    m, h = d.loc["Mujer", "pobreza_pct"], d.loc["Hombre", "pobreza_pct"]   # sin redondear: se redondea al mostrar
    titulo = f"Pobreza monetaria: mujeres {m:.1f} % y hombres {h:.1f} % (diferencia de {abs(m - h):.1f} pp)"
    fig, ax = lienzo()
    fig.subplots_adjust(top=0.80, bottom=0.21, left=0.08, right=0.97)
    x = range(len(d))
    ax.bar(x, d.pobreza_pct, width=0.45, color=AZUL, edgecolor=SUPERFICIE, linewidth=2)
    for i, v in enumerate(d.pobreza_pct):
        ax.text(i, v + 0.6, f"{v:.1f} %", ha="center", va="bottom", fontsize=10, fontweight="bold", color=TEXTO)
    ax.set_xticks(list(x), ["Mujeres", "Hombres"], fontsize=10, color=TEXTO)
    ax.set_ylim(0, max(d.pobreza_pct) * 1.25)
    ax.set_ylabel("% de la población", color=TEXTO_2, fontsize=9)
    ax.yaxis.grid(True, color=GRILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    textos(fig, titulo, "Pobreza monetaria por sexo. Perú, 2024 (% de la población)",
           "No se calcularon intervalos de confianza: una diferencia pequeña puede no ser estadísticamente "
           "significativa.\n" + NOTA_REDONDEO)
    guardar(fig, "pobreza_sexo_2024.png")


def grafico_departamento(ind):
    d = ind[ind.nivel == "departamento"].sort_values("pobreza_pct")   # el mayor queda arriba
    nac = round(ind.loc[ind.nivel == "nacional", "pobreza_pct"].iloc[0], 1)
    alto, bajo = d.iloc[-1], d.iloc[0]
    titulo = (f"{nombre(alto.categoria)} tiene la mayor pobreza monetaria ({alto.pobreza_pct:.1f} %) "
              f"{conjuncion_y(nombre(bajo.categoria))} {nombre(bajo.categoria)} la menor ({bajo.pobreza_pct:.1f} %)")
    fig, ax = lienzo(alto=8.2, ancho=8.0)
    fig.subplots_adjust(top=0.89, bottom=0.08, left=0.19, right=0.95)
    y = range(len(d))
    ax.barh(y, d.pobreza_pct, height=0.62, color=AZUL, edgecolor=SUPERFICIE, linewidth=1, zorder=2)
    for i, v in enumerate(d.pobreza_pct):   # fondo del color de la superficie: la línea no tapa la cifra
        ax.text(v + 0.5, i, f"{v:.1f}", va="center", fontsize=8, color=TEXTO_2, zorder=4,
                bbox={"facecolor": SUPERFICIE, "edgecolor": "none", "pad": 1})
    ax.axvline(nac, color=TEXTO_2, linestyle="--", linewidth=1, zorder=3)
    ax.text(nac + 0.4, len(d) - 0.4, f"Promedio nacional: {nac:.1f} %", fontsize=8.5, color=TEXTO_2, va="bottom")
    ax.set_yticks(list(y), [nombre(c) for c in d.categoria], fontsize=9, color=TEXTO)
    ax.set_xlim(0, max(d.pobreza_pct) * 1.12)
    ax.set_ylim(-0.6, len(d) + 0.3)
    ax.set_xlabel("% de la población", color=TEXTO_2, fontsize=9)
    ax.xaxis.grid(True, color=GRILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    textos(fig, titulo, "Pobreza monetaria por departamento. Perú, 2024 (% de la población)")
    fig.texts[1].set_y(0.935)
    guardar(fig, "pobreza_departamento_2024.png")


GRAFICOS = {"area": grafico_area, "sexo": grafico_sexo, "departamento": grafico_departamento}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tipo", choices=[*GRAFICOS, "todos"], default="todos")
    args = parser.parse_args()
    if not INDICADORES.exists():
        print("ERROR: falta salidas/indicadores.csv. Usa primero la skill limpiando-enaho.", file=sys.stderr)
        sys.exit(2)
    ind = pd.read_csv(INDICADORES, dtype={"codigo": "string"})
    for tipo in (GRAFICOS if args.tipo == "todos" else [args.tipo]):
        GRAFICOS[tipo](ind)


if __name__ == "__main__":
    main()
