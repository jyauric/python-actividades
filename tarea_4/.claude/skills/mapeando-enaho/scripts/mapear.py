"""Mapa coroplético de la pobreza monetaria por departamento (ENAHO 2024) y comparación con la referencia.

    uv run .claude/skills/mapeando-enaho/scripts/mapear.py

Une salidas/indicadores.csv con datos/peru_departamental_simple.geojson POR CÓDIGO (ubigeo[:2] = FIRST_IDDP),
nunca por nombres. Guarda mapas/pobreza_departamento_2024.png y salidas/comparacion_referencia_mapa.csv.
Códigos de salida: 2 = falta la base (usar antes limpiando-enaho); 1 = la unión no da 25 unidades válidas.
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import geopandas as gpd  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

RAIZ = Path(__file__).resolve().parents[4]          # tarea_4/
SKILL = Path(__file__).resolve().parents[1]
INDICADORES = RAIZ / "salidas" / "indicadores.csv"
GEOJSON = RAIZ / "datos" / "peru_departamental_simple.geojson"
REFERENCIA = SKILL / "referencias" / "pobreza_departamento_2024.csv"   # copia de la sesión 16
MAPA = RAIZ / "mapas" / "pobreza_departamento_2024.png"
COMPARACION = RAIZ / "salidas" / "comparacion_referencia_mapa.csv"

# Paleta (skill dataviz): superficie, texto y rampa secuencial azul (claro -> oscuro), una clase por color.
SUPERFICIE, TEXTO, TEXTO_2 = "#fcfcfb", "#0b0b0b", "#52514e"
CORTES = [0, 10, 20, 30, 40, 50]                     # 5 clases de 10 pp: [0,10) [10,20) ... [40,50]
COLORES = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
LIMA_CALLAO = {"07", "15"}
VENTANA_LIMA = (-77.35, -12.45, -76.65, -11.70)      # lon_min, lat_min, lon_max, lat_max del recuadro


def nombre(depto):
    return " ".join(p.lower() if p in {"DE", "DEL"} else p.capitalize() for p in depto.split())


def conjuncion_y(palabra):
    p = palabra.lower()
    return "e" if p.startswith("i") or (p.startswith("hi") and p[2:3] not in {"a", "e", "o", "u"}) else "y"


def enumerar(nombres):
    if len(nombres) == 1:
        return nombres[0]
    return f"{', '.join(nombres[:-1])} {conjuncion_y(nombres[-1])} {nombres[-1]}"


def cargar():
    if not INDICADORES.exists():
        print("ERROR: falta salidas/indicadores.csv. Usa primero la skill limpiando-enaho.", file=sys.stderr)
        sys.exit(2)
    ind = pd.read_csv(INDICADORES, dtype={"codigo": "string"})
    dep = ind[ind.nivel == "departamento"][["codigo", "categoria", "pobreza_pct"]]
    geo = gpd.read_file(GEOJSON)
    geo["codigo"] = geo["FIRST_IDDP"].astype("string").str.zfill(2)
    mapa = geo.merge(dep, on="codigo", how="left", validate="1:1")   # unión por código, 1 a 1
    errores = []
    if len(mapa) != 25:
        errores.append(f"se esperaban 25 unidades y hay {len(mapa)}")
    sin_dato = mapa.loc[mapa.pobreza_pct.isna(), "NOMBDEP"].tolist()
    if sin_dato:
        errores.append(f"unidades sin dato: {sin_dato}")
    if not LIMA_CALLAO <= set(mapa.codigo):
        errores.append("Lima (15) y Callao (07) no están como unidades separadas")
    if errores:
        print("ERROR en la unión territorial: " + "; ".join(errores), file=sys.stderr)
        sys.exit(1)
    print(f"[OK] Unión por código (ubigeo[:2] = FIRST_IDDP): {len(mapa)} unidades, todas con dato; "
          "Lima (15) y Callao (07) separados")
    return mapa


def comparar(mapa):
    ref = pd.read_csv(REFERENCIA, dtype={"ccdd": "string"}).rename(
        columns={"ccdd": "codigo", "pobreza_pct": "referencia_sesion16"})
    c = ref.merge(mapa[["codigo", "pobreza_pct"]], on="codigo", how="left", validate="1:1")
    c = c.rename(columns={"pobreza_pct": "obtenido_facpob07"})
    c["diferencia_pp"] = (c.obtenido_facpob07 - c.referencia_sesion16).round(2)
    c.to_csv(COMPARACION, index=False)
    peor = c.loc[c.diferencia_pp.abs().idxmax()]
    print(f"Comparación con la referencia de la sesión 16 -> {COMPARACION.relative_to(RAIZ)}: "
          f"{(c.diferencia_pp.abs() <= 0.1).sum()} de {len(c)} departamentos a ≤ 0.1 pp; "
          f"máxima diferencia {peor.diferencia_pp:+.2f} pp ({nombre(peor.departamento)}). "
          "Explicación: conteo de miembros del hogar (ver limpiando-enaho/reference.md).")


def dibujar(mapa):
    mapa["clase"] = pd.cut(mapa.pobreza_pct, CORTES, right=False, labels=False, include_lowest=True)
    mapa.loc[mapa.pobreza_pct >= CORTES[-1], "clase"] = len(COLORES) - 1
    mapa["color"] = mapa.clase.astype(int).map(dict(enumerate(COLORES)))

    altos = mapa[mapa.pobreza_pct >= 40].sort_values("pobreza_pct", ascending=False)
    if len(altos):
        titulo = f"{enumerar([nombre(n) for n in altos.categoria])}: más de 40 % de su población en pobreza monetaria"
    else:
        top = mapa.loc[mapa.pobreza_pct.idxmax()]
        titulo = f"{nombre(top.categoria)} tiene la mayor pobreza monetaria ({top.pobreza_pct:.1f} %)"

    fig, ax = plt.subplots(figsize=(7.6, 9.2), dpi=150)
    fig.patch.set_facecolor(SUPERFICIE)
    ax.set_facecolor(SUPERFICIE)
    mapa.plot(ax=ax, color=mapa.color, edgecolor=SUPERFICIE, linewidth=0.8)
    ax.set_axis_off()

    # Recuadro ampliado: Lima y Callao (Callao casi no se ve a escala nacional)
    lon0, lat0, lon1, lat1 = VENTANA_LIMA
    ins = ax.inset_axes([0.01, 0.06, 0.34, 0.30])
    mapa.plot(ax=ins, color=mapa.color, edgecolor=SUPERFICIE, linewidth=1.2)
    ins.set_xlim(lon0, lon1)
    ins.set_ylim(lat0, lat1)
    ins.set_xticks([])
    ins.set_yticks([])
    ins.set_xlabel("")
    ins.set_ylabel("")
    ins.set_facecolor(SUPERFICIE)
    for lado in ins.spines.values():
        lado.set_color(TEXTO_2)
        lado.set_linewidth(0.8)
    ax.indicate_inset_zoom(ins, edgecolor=TEXTO_2, linewidth=0.8)
    for cod, (dx, dy) in {"07": (-0.14, 0.02), "15": (0.12, 0.05)}.items():
        fila = mapa[mapa.codigo == cod].iloc[0]
        ins.annotate(f"{nombre(fila.categoria)}\n{fila.pobreza_pct:.1f} %", xy=(-77.12 if cod == "07" else -76.95,
                     -12.0 if cod == "07" else -11.95), xytext=(dx, dy), textcoords="offset fontsize",
                     fontsize=8, color=TEXTO, ha="center",
                     bbox={"facecolor": SUPERFICIE, "edgecolor": "none", "pad": 1.5, "alpha": 0.9})
    ins.set_title("Lima y Callao (ampliado)", fontsize=8, color=TEXTO_2, pad=3)

    conteo = mapa.clase.astype(int).value_counts()
    etiquetas = [f"{CORTES[i]}–{CORTES[i + 1]} %  ({conteo.get(i, 0)} dep.)" for i in range(len(COLORES))]
    ax.legend(handles=[Patch(facecolor=c, edgecolor="none") for c in COLORES], labels=etiquetas,
              title="% de la población en\npobreza monetaria", title_fontsize=8.5, fontsize=8.5,
              frameon=False, loc="upper left", bbox_to_anchor=(0.0, 1.0), labelcolor=TEXTO_2)

    fig.text(0.03, 0.975, titulo, ha="left", va="top", fontsize=11.5, fontweight="bold", color=TEXTO, wrap=True)
    fig.text(0.03, 0.935, "Pobreza monetaria por departamento. Perú, 2024 (% de la población; 5 clases de 10 pp)",
             ha="left", va="top", fontsize=9, color=TEXTO_2)
    fig.text(0.03, 0.012,
             "Fuente: INEI – ENAHO 2024 (módulos 34 y 02). Residentes habituales, ponderado con facpob07. "
             "Elaboración propia.\nLímites departamentales: GeoJSON del repositorio del curso (sesión 06). "
             "Unión por código: ubigeo[:2] = FIRST_IDDP.", ha="left", va="bottom", fontsize=7.2, color=TEXTO_2)
    fig.subplots_adjust(top=0.92, bottom=0.05, left=0.02, right=0.98)
    MAPA.parent.mkdir(exist_ok=True)
    fig.savefig(MAPA, facecolor=SUPERFICIE)
    plt.close(fig)
    print(f"Guardado: {MAPA.relative_to(RAIZ)}")


def main():
    mapa = cargar()
    comparar(mapa)
    dibujar(mapa)


if __name__ == "__main__":
    main()
