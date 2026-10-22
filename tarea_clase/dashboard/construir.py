"""Arma dashboard/index.html con los resultados del notebook.

Lee solo resultados/, figs/rio_tambo_dnbr_web.png y la base de distritos, y mete esos
datos como JSON dentro de la plantilla. Correr después del notebook:

    uv run python dashboard/construir.py
"""

import base64
import json
import warnings
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry.polygon import orient

warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS")   # buffer de ~100 m
RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "resultados"
AQUI = Path(__file__).resolve().parent


def filas(df):
    # JSON sin NaN: pandas los escribe como null
    return json.loads(df.to_json(orient="records", force_ascii=False))


# límites de departamento, simplificados para la web (~1 km)
distritos = gpd.read_file(RAIZ / "data" / "distritos_peru.geojson").to_crs(4326)
deps = distritos.dissolve(by="departamento", as_index=False)[["departamento", "geometry"]]
deps["geometry"] = (deps.buffer(0.001).buffer(-0.001)       # cierra huecos entre distritos
                    .simplify(0.01, preserve_topology=True)
                    .apply(lambda g: orient(g, sign=-1.0) if g.geom_type == "Polygon"
                           else type(g)([orient(p, sign=-1.0) for p in g.geoms])))
# d3 pide los anillos exteriores en sentido horario: orient(sign=-1)
geo = json.loads(deps.to_json(drop_id=True))
for f in geo["features"]:
    f["geometry"]["coordinates"] = json.loads(
        json.dumps(f["geometry"]["coordinates"]),
        parse_float=lambda v: round(float(v), 3))

incendios = pd.read_csv(RES / "incendios_peru.csv")
incendios["personas_5km"] = incendios.personas_5km.round()
incendios["personas_5km_max"] = incendios.personas_5km_max.round()
departamentos = pd.read_csv(RES / "departamentos.csv")
departamentos["personas_5km"] = departamentos.personas_5km.round()
departamentos["poblacion_dep"] = departamentos.poblacion_dep.round()
departamentos = departamentos.rename(columns={"%_expuesta": "pct_expuesta"})

rio_tambo = filas(pd.read_csv(RES / "rio_tambo.csv"))[0]
principal = (incendios[(incendios.distrito == "RIO TAMBO") & (incendios.provincia == "SATIPO")]
             .sort_values("focos", ascending=False).iloc[0])
rio_tambo["incendio"] = int(principal.incendio)

png = (RAIZ / "figs" / "rio_tambo_dnbr_web.png").read_bytes()

datos = {
    "resumen": filas(pd.read_csv(RES / "resumen.csv"))[0],
    "sensibilidad": filas(pd.read_csv(RES / "sensibilidad.csv")),
    "incendios": filas(incendios),
    "departamentos": filas(departamentos),
    "rio_tambo": rio_tambo,
    "severidad": filas(pd.read_csv(RES / "rio_tambo_severidad.csv")),
    "focos_rt": filas(pd.read_csv(RES / "focos_rio_tambo.csv")),
    "bordes": filas(pd.read_csv(RES / "rio_tambo_dnbr_bordes.csv"))[0],
    "dnbr_png": "data:image/png;base64," + base64.b64encode(png).decode(),
    "geo": geo,
}
texto = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
texto = texto.replace("</", "<\\/")   # que ningún texto cierre el <script>

plantilla = (AQUI / "plantilla.html").read_text(encoding="utf-8")
assert "__DATOS__" in plantilla
(AQUI / "index.html").write_text(plantilla.replace("__DATOS__", texto), encoding="utf-8")
print(f"dashboard/index.html: {len(texto) / 1024:,.0f} KB de datos")
