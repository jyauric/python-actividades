"""Gráfico BCRP del informe: variación anual (dic.–dic.) de dos series, con los cálculos de comparar_series del MCP.

    uv run informes/grafico_bcrp.py                                   # alimentos vs resto, dic-2019 a dic-2024
    uv run informes/grafico_bcrp.py --a PN39445PM --b PN38706PM --desde 2019-12 --hasta 2024-12

Las cifras salen de comparar_series (mcp/server.py), el mismo código que usa el servidor MCP: no se escriben a mano.
"""
import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]           # tarea_4/
sys.path.insert(0, str(RAIZ / "mcp"))                 # carpeta del servidor (sin __init__.py: no tapa la librería mcp)
from server import comparar_series  # noqa: E402

FIGURAS = RAIZ / "figuras"
SUPERFICIE, TEXTO, TEXTO_2, GRILLA = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
COLOR_A, COLOR_B = "#2a78d6", "#eb6834"               # paleta categórica de referencia (dataviz): slots 1 y 2


def etiqueta(nombre):
    """'Índice de precios … - IPC Alimentos y Bebidas' -> 'Alimentos y bebidas'."""
    parte = nombre.split(" - ")[-1].replace("IPC ", "").strip()
    return parte[:1].upper() + parte[1:].lower()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--a", default="PN39445PM")
    p.add_argument("--b", default="PN38706PM")
    p.add_argument("--desde", default="2019-12")
    p.add_argument("--hasta", default="2024-12")
    args = p.parse_args()

    r = comparar_series(args.a, args.b, args.desde, args.hasta)
    a, b, anios = r["a"], r["b"], r["por_anio"]
    na, nb = etiqueta(a["nombre"]), etiqueta(b["nombre"])

    mas = [x for x in anios if x["diferencia_pp"] > 0]
    mayor = max(anios, key=lambda x: x["diferencia_pp"])
    comparado = "el resto de la canasta" if nb.lower().startswith("sin ") else nb.lower()
    titulo = (f"Los precios de {na.lower()} subieron más que {comparado} en {len(mas)} de {len(anios)} años;\n"
              f"la mayor diferencia fue en {mayor['anio']} ({mayor['diferencia_pp']:+.1f} pp)")
    ambito = "Lima Metropolitana. " if all("Lima Metropolitana" in s["nombre"] for s in (a, b)) else ""
    subtitulo = (f"Variación anual del IPC, diciembre a diciembre (%). {ambito}\n"
                 f"Acumulado {a['primero']['periodo']} a {a['ultimo']['periodo']}: "
                 f"{na.lower()} {a['variacion_pct']:+.1f} %, {nb.lower()} {b['variacion_pct']:+.1f} % "
                 f"(diferencia {r['diferencia_pp']:+.1f} pp)")

    fig, ax = plt.subplots(figsize=(8.6, 5.0), dpi=150)
    fig.patch.set_facecolor(SUPERFICIE)
    ax.set_facecolor(SUPERFICIE)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(GRILLA)
    ax.tick_params(colors=TEXTO_2, length=0)

    x = range(len(anios))
    ancho = 0.36
    for desplaz, clave, color, nombre in ((-ancho / 2, "a", COLOR_A, na), (ancho / 2, "b", COLOR_B, nb)):
        valores = [v[clave] for v in anios]
        ax.bar([i + desplaz for i in x], valores, width=ancho, color=color, edgecolor=SUPERFICIE, linewidth=2,
               label=f"{nombre} ({a['codigo'] if clave == 'a' else b['codigo']})")
        for i, v in enumerate(valores):
            ax.text(i + desplaz, v + (0.25 if v >= 0 else -0.25), f"{v:.1f}", ha="center",
                    va="bottom" if v >= 0 else "top", fontsize=8.5, color=TEXTO)
    ax.axhline(0, color=GRILLA, linewidth=1)
    ax.set_xticks(list(x), [str(v["anio"]) for v in anios], fontsize=10, color=TEXTO)
    ax.set_ylabel("Variación anual (%)", color=TEXTO_2, fontsize=9)
    ax.set_ylim(min(0, min(min(v["a"], v["b"]) for v in anios)) * 1.2,
                max(max(v["a"], v["b"]) for v in anios) * 1.18)
    ax.yaxis.grid(True, color=GRILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper right", fontsize=9, labelcolor=TEXTO_2)

    fig.subplots_adjust(top=0.74, bottom=0.20, left=0.08, right=0.98)
    fig.text(0.02, 0.975, titulo, ha="left", va="top", fontsize=11.5, fontweight="bold", color=TEXTO,
             linespacing=1.3)
    fig.text(0.02, 0.865, subtitulo, ha="left", va="top", fontsize=8.6, color=TEXTO_2, linespacing=1.4)
    fig.text(0.02, 0.015,
             f"Fuente: BCRP, series {a['codigo']} y {b['codigo']} (índices, base Dic.2021 = 100). "
             "Cálculos: comparar_series (mcp/server.py). Elaboración propia.\n"
             "Diferencias calculadas con cifras sin redondear; pueden diferir en ±0,1 de la resta de los "
             "valores mostrados.\n"
             f"Datos: {a['fuente']}\n       {b['fuente']}",
             ha="left", va="bottom", fontsize=6.8, color=TEXTO_2)

    FIGURAS.mkdir(exist_ok=True)
    salida = FIGURAS / f"bcrp_{a['codigo']}_vs_{b['codigo']}_{args.desde}_{args.hasta}.png"
    fig.savefig(salida, facecolor=SUPERFICIE)
    plt.close(fig)
    print(f"Guardado: {salida.relative_to(RAIZ)}")
    print(f"{na}: {a['variacion_pct']:+.2f} % | {nb}: {b['variacion_pct']:+.2f} % | "
          f"diferencia {r['diferencia_pp']:+.2f} pp")
    for v in anios:
        print(f"  {v['anio']}: {v['a']:.2f} vs {v['b']:.2f} ({v['diferencia_pp']:+.2f} pp)")


if __name__ == "__main__":
    main()
