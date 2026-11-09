"""Limpia la ENAHO 2024 (módulos 34 y 02), calcula la pobreza monetaria ponderada y la valida.

    uv run .claude/skills/limpiando-enaho/scripts/limpiar.py      # desde la raíz del proyecto (tarea_4/)

Salidas en salidas/:
    validacion.txt         reporte de validaciones ([OK] / [FALLA] / [REVISAR])
    indicadores.csv        pobreza ponderada nacional, por área, sexo y departamento
    personas_2024.parquet  base de residentes habituales unida a su hogar (la usan graficando y mapeando)

Si falla una validación esencial, escribe validacion.txt, NO guarda indicadores ni la base y termina con código 1.
Los resultados nunca se corrigen para que coincidan con las referencias.
"""
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[4]          # tarea_4/
DATOS, SALIDAS = RAIZ / "datos", RAIZ / "salidas"
ZIP_SUMARIA, DTA_SUMARIA = DATOS / "966-Modulo34.zip", "966-Modulo34/sumaria-2024.dta"
ZIP_MIEMBROS, DTA_MIEMBROS = DATOS / "966-Modulo02.zip", "966-Modulo02/enaho01-2024-200.dta"

LLAVES_HOGAR = ["conglome", "vivienda", "hogar"]
LLAVES_PERSONA = LLAVES_HOGAR + ["codperso"]

# Valores de referencia del enunciado (issue #201). Se usan SOLO para comparar; nunca como resultado.
REF = {"residentes": 108_664, "departamentos": 25,
       "pobreza_nacional": 27.6, "pobreza_urbana": 24.8, "pobreza_rural": 39.3}
TOL_PP = 0.1   # nacional: tolerancia fijada por el enunciado; urbano/rural: misma tolerancia, decisión propia

# Nombres de los 25 departamentos (ubigeo[:2]), tal como en referencias/pobreza_departamento_2024.csv (sesión 16)
DEPARTAMENTOS = {
    "01": "AMAZONAS", "02": "ANCASH", "03": "APURIMAC", "04": "AREQUIPA", "05": "AYACUCHO",
    "06": "CAJAMARCA", "07": "CALLAO", "08": "CUSCO", "09": "HUANCAVELICA", "10": "HUANUCO",
    "11": "ICA", "12": "JUNIN", "13": "LA LIBERTAD", "14": "LAMBAYEQUE", "15": "LIMA",
    "16": "LORETO", "17": "MADRE DE DIOS", "18": "MOQUEGUA", "19": "PASCO", "20": "PIURA",
    "21": "PUNO", "22": "SAN MARTIN", "23": "TACNA", "24": "TUMBES", "25": "UCAYALI",
}


def leer(zip_path, nombre, columnas):
    """Lee un .dta desde su .zip, con nombres en minúscula y las llaves como texto (conservan ceros iniciales)."""
    if not zip_path.exists():
        sys.exit(f"ERROR: falta {zip_path.relative_to(RAIZ)}. Descárguenlo según el README (enlaces del INEI).")
    with zipfile.ZipFile(zip_path) as z, z.open(nombre) as f:
        df = pd.read_stata(f, convert_categoricals=False)
    df.columns = df.columns.str.lower()
    faltan = sorted(set(columnas) - set(df.columns))
    if faltan:
        sys.exit(f"ERROR: faltan las columnas {faltan} en {nombre}.")
    df = df[columnas].copy()
    for c in set(columnas) & set(LLAVES_PERSONA + ["ubigeo"]):
        df[c] = df[c].astype("string")
    return df


def tasa(df, peso, indicador):
    """Porcentaje ponderado: suma de pesos de quienes cumplen la condición / suma total de pesos × 100."""
    return 100 * (df[indicador] * df[peso]).sum() / df[peso].sum()


def main():
    lineas, fallas = [], []

    def validar(nombre, ok, detalle, esencial=True):
        estado = "OK" if ok else ("FALLA" if esencial else "REVISAR")
        lineas.append(f"[{estado}] {nombre}: {detalle}")
        if not ok and esencial:
            fallas.append(nombre)

    def informar(nombre, detalle):
        """Solo informa una cifra (sin tolerancia): p. ej. diferencias de ponderación ya explicadas."""
        lineas.append(f"[INFO] {nombre}: {detalle}")

    # 1-2. Lectura
    sumaria = leer(ZIP_SUMARIA, DTA_SUMARIA, LLAVES_HOGAR + ["ubigeo", "estrato", "pobreza", "mieperho", "factor07"])
    miembros = leer(ZIP_MIEMBROS, DTA_MIEMBROS, LLAVES_PERSONA + ["p204", "p205", "p206", "p207", "facpob07"])
    validar("Llave de hogar única en la sumaria", not sumaria.duplicated(LLAVES_HOGAR).any(),
            f"{len(sumaria):,} hogares")

    # 3. Residentes habituales: (miembro y no ausente 30+ días) o (no miembro y presente 30+ días)
    residente = ((miembros.p204 == 1) & (miembros.p205 == 2)) | ((miembros.p204 == 2) & (miembros.p206 == 1))
    personas = miembros[residente].copy()
    validar("Residentes habituales", len(personas) == REF["residentes"],
            f"obtenido {len(personas):,}; referencia {REF['residentes']:,} (de {len(miembros):,} filas del módulo 02)")
    validar("Llave de persona única entre residentes", not personas.duplicated(LLAVES_PERSONA).any(),
            f"{len(personas):,} personas")

    # 4. Unión persona -> hogar (muchas personas, un hogar). validate="m:1" detiene si la sumaria tuviera duplicados.
    n_antes = len(personas)
    base = personas.merge(sumaria, on=LLAVES_HOGAR, how="left", validate="m:1", indicator=True)
    validar("La unión no pierde ni duplica filas", len(base) == n_antes, f"{n_antes:,} -> {len(base):,}")
    sin_hogar = int((base["_merge"] != "both").sum())
    validar("Todas las personas encuentran su hogar", sin_hogar == 0, f"sin hogar: {sin_hogar:,}")
    base = base.drop(columns="_merge")

    # 5. Variables de análisis
    base["departamento"] = base.ubigeo.str[:2]
    base["nombre_departamento"] = base.departamento.map(DEPARTAMENTOS)
    base["urbano"] = base.estrato <= 5                       # regla de la sesión 16
    base["area"] = base.urbano.map({True: "Urbana", False: "Rural"})
    base["pobre"] = (base.pobreza <= 2).astype(int)          # 1 = pobre extremo, 2 = pobre no extremo
    base["pobre_extremo"] = (base.pobreza == 1).astype(int)
    base["sexo"] = base.p207.map({1: "Hombre", 2: "Mujer"})

    pesos_ok = bool(base.facpob07.notna().all() and (base.facpob07 > 0).all())
    validar("Factor de expansión facpob07 sin vacíos y positivo", pesos_ok,
            f"población expandida {base.facpob07.sum():,.0f}")
    deptos = set(base.departamento.dropna())
    validar("Unidades territoriales (ubigeo[:2])", deptos == set(DEPARTAMENTOS),
            f"obtenido {len(deptos)}; referencia {REF['departamentos']}")
    sin_sexo = int(base.sexo.isna().sum())
    validar("Residentes con sexo informado", sin_sexo == 0, f"sin dato: {sin_sexo:,}", esencial=False)

    # 6. Indicadores ponderados con facpob07
    filas = []

    def agregar(nivel, codigo, categoria, df):
        filas.append({"nivel": nivel, "codigo": codigo, "categoria": categoria,
                      "pobreza_pct": round(tasa(df, "facpob07", "pobre"), 2),
                      "pobreza_extrema_pct": round(tasa(df, "facpob07", "pobre_extremo"), 2),
                      "personas_muestra": len(df), "poblacion_expandida": round(df.facpob07.sum())})

    agregar("nacional", "", "PERU", base)
    for area, g in base.groupby("area"):
        agregar("area", "", area, g)
    for sexo, g in base.groupby("sexo"):
        agregar("sexo", "", sexo, g)
    for depto, g in base.groupby("departamento"):
        agregar("departamento", depto, DEPARTAMENTOS.get(depto, "?"), g)
    indicadores = pd.DataFrame(filas)

    nacional = tasa(base, "facpob07", "pobre")
    urbana = tasa(base[base.urbano], "facpob07", "pobre")
    rural = tasa(base[~base.urbano], "facpob07", "pobre")
    validar("Pobreza nacional (facpob07)", abs(nacional - REF["pobreza_nacional"]) <= TOL_PP,
            f"obtenido {nacional:.2f} %; referencia {REF['pobreza_nacional']} % ± {TOL_PP}")
    # 7. Método de la sumaria: hogares expandidos a personas con factor07 × mieperho (sin unión ni filtro).
    #    Diagnóstico del 8/11/2026: las referencias urbana (24.8) y rural (39.3) del enunciado se reproducen con
    #    este método; con facpob07 difieren por ponderación (hasta 0.14 pp en rural). Por eso urbano/rural se
    #    validan con este método (comprueba la clasificación estrato <= 5) y las cifras con facpob07 se informan.
    sumaria["peso_personas"] = sumaria.factor07 * sumaria.mieperho
    sumaria["pobre"] = (sumaria.pobreza <= 2).astype(int)
    sumaria["urbano"] = sumaria.estrato <= 5
    control = tasa(sumaria, "peso_personas", "pobre")
    urbana_s = tasa(sumaria[sumaria.urbano], "peso_personas", "pobre")
    rural_s = tasa(sumaria[~sumaria.urbano], "peso_personas", "pobre")
    validar("Control cruzado: pobreza nacional con la sumaria (factor07 × mieperho)",
            abs(control - REF["pobreza_nacional"]) <= TOL_PP,
            f"{control:.2f} %; método principal {nacional:.2f} %; diferencia {control - nacional:+.2f} pp",
            esencial=False)
    validar("Pobreza urbana, método sumaria (factor07 × mieperho)", abs(urbana_s - REF["pobreza_urbana"]) <= TOL_PP,
            f"obtenido {urbana_s:.2f} %; referencia {REF['pobreza_urbana']} % ± {TOL_PP}")
    validar("Pobreza rural, método sumaria (factor07 × mieperho)", abs(rural_s - REF["pobreza_rural"]) <= TOL_PP,
            f"obtenido {rural_s:.2f} %; referencia {REF['pobreza_rural']} % ± {TOL_PP}")
    informar("Pobreza urbana, método principal (facpob07)",
             f"{urbana:.2f} %; diferencia con método sumaria {urbana - urbana_s:+.2f} pp (ponderación)")
    informar("Pobreza rural, método principal (facpob07)",
             f"{rural:.2f} %; diferencia con método sumaria {rural - rural_s:+.2f} pp (ponderación)")

    # 8-9. Reporte y salidas
    SALIDAS.mkdir(exist_ok=True)
    encabezado = [
        "Validación ENAHO 2024 (INEI) – limpiando-enaho",
        f"Ejecutado: {datetime.now():%Y-%m-%d %H:%M}",
        f"Archivos: {DTA_SUMARIA}, {DTA_MIEMBROS}",
        "Método principal: residentes habituales (módulo 02) unidos a la sumaria; ponderación facpob07.",
        "",
    ]
    resumen = ["", f"Resultado: {'FALLA en ' + ', '.join(fallas) if fallas else 'todas las validaciones esenciales OK'}"]
    (SALIDAS / "validacion.txt").write_text("\n".join(encabezado + lineas + resumen) + "\n", encoding="utf-8")
    print("\n".join(encabezado + lineas + resumen))

    if fallas:
        for f in ("indicadores.csv", "personas_2024.parquet"):   # no dejar salidas viejas que parezcan válidas
            (SALIDAS / f).unlink(missing_ok=True)
        sys.exit(1)

    indicadores.to_csv(SALIDAS / "indicadores.csv", index=False)
    columnas = LLAVES_PERSONA + ["ubigeo", "departamento", "nombre_departamento", "estrato", "urbano", "area",
                                 "p207", "sexo", "pobreza", "pobre", "pobre_extremo", "facpob07",
                                 "mieperho", "factor07"]
    base[columnas].to_parquet(SALIDAS / "personas_2024.parquet", index=False)


if __name__ == "__main__":
    main()
