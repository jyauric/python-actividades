"""Servidor MCP del BCRP. Empiecen aquí: buscar_series ya funciona; completen los TODO hasta que pasen las pruebas.

    uv run pytest                                           # el contrato: las 8 pruebas deben pasar
    uv run server.py                                        # el servidor, por stdio
    claude mcp add --scope project bcrp -- uv run server.py # conectarlo a Claude Code

Las cuentas las hace Python, no el modelo: así cada cifra sale de una llamada que se puede repetir.
"""
import re
import time
import unicodedata
from datetime import date
from functools import cache
from pathlib import Path

import httpx
import pandas as pd
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

AQUI = Path(__file__).parent
CATALOGO = AQUI / "datos" / "catalogo_bcrp.csv"
URL_CATALOGO = "https://estadisticas.bcrp.gob.pe/estadisticas/series/metadata"
API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
SOLO_LECTURA = {"readOnlyHint": True, "openWorldHint": True}

mcp = FastMCP("bcrp", instructions=(
    "Series oficiales del Banco Central de Reserva del Perú (BCRP). Primero busca el código con buscar_series; "
    "luego usa resumen para variaciones, promedios y extremos, y serie para los datos. No calcules a mano: "
    "cita siempre el código de la serie y el periodo."))


def _sin_tildes(s):
    return unicodedata.normalize("NFD", str(s).lower()).encode("ascii", "ignore").decode()


@cache
def catalogo():
    """El catálogo oficial: 17 mil series en unos 7 MB. Se baja una vez y queda en datos/."""
    if not CATALOGO.exists():
        CATALOGO.parent.mkdir(exist_ok=True)
        r = httpx.get(URL_CATALOGO, timeout=120)
        r.raise_for_status()
        CATALOGO.write_text(r.content.decode("latin-1"), encoding="utf-8")
    df = pd.read_csv(CATALOGO, sep=";", dtype=str).fillna("")
    df = df.rename(columns={"Código de serie": "codigo", "Categoría de serie": "categoria", "Grupo de serie": "grupo",
                            "Nombre de serie": "nombre", "Frecuencia": "frecuencia",
                            "Fecha de actualización": "actualizada", "Fecha de inicio": "inicio"})
    df["texto"] = (df.categoria + " " + df.grupo + " " + df.nombre).map(_sin_tildes)
    return df


def _ficha(codigo):
    fila = catalogo().query("codigo == @codigo")
    if fila.empty:
        raise ToolError(f"No existe el código de serie {codigo!r}. Búsquenlo con buscar_series.")
    f = fila.iloc[0]
    return {"codigo": f.codigo, "nombre": f"{f.grupo} - {f.nombre}", "categoria": f.categoria,
            "frecuencia": f.frecuencia, "inicio": f.inicio, "actualizada": f.actualizada}


@mcp.tool(annotations=SOLO_LECTURA)
def buscar_series(texto: str, frecuencia: str | None = None, limite: int = 10) -> list[dict]:
    """Busca series del BCRP por palabras: todas deben aparecer en la categoría, el grupo o el nombre.

    Ejemplos: "ipc 12 meses", "tipo de cambio interbancario venta", "reservas internacionales netas",
    "tasa de referencia", "cobre precio". frecuencia: "Diaria", "Mensual", "Trimestral" o "Anual".
    Devuelve el código, el nombre completo, la frecuencia y desde cuándo hay datos. Si no hay resultados,
    prueben con menos palabras.
    """
    df = catalogo()
    m = pd.Series(True, index=df.index)
    for palabra in _sin_tildes(texto).split():
        m &= df.texto.str.contains(re.escape(palabra))
    if frecuencia:
        m &= df.frecuencia.str.lower() == frecuencia.lower()
    # primero las series vigentes y, entre ellas, las de nombre más corto (las más generales)
    sel = df[m]
    orden = sel.assign(vieja=sel.actualizada < "2025", largo=(sel.grupo + sel.nombre).str.len())
    return [_ficha(c) for c in orden.sort_values(["vieja", "largo"]).head(limite).codigo]


# --- TODO 1 · serie ---------------------------------------------------------------------------------------------
# La API: f"{API}/{codigo}/json/{desde}/{hasta}" responde {"config": {...}, "periods": [{"name": ..., "values": [...]}]}

MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
         "jul": 7, "ago": 8, "set": 9, "sep": 9, "oct": 10, "nov": 11, "dic": 12}


def _anio(texto, rango=None):
    """Año de 4 dígitos. Las series diarias ('01.Oct.26') y trimestrales ('T1.25') traen el año con 2 dígitos.

    1) Si se conoce el rango pedido (año desde, año hasta), se elige el siglo con el que el año cae dentro del
       rango: pedir 2026-10-01 a 2026-10-15 y recibir '26' solo puede ser 2026. No se adivina.
    2) Respaldo si nada calza: aa <= año actual (2 últimos dígitos) -> 20aa; si no -> 19aa.
       En el catálogo del BCRP (revisado el 8/11/2026) las series diarias empiezan en 1991 y las trimestrales
       en 1978, así que el respaldo también sería correcto con los datos actuales.
    """
    a = int(texto)
    if len(texto) != 2:
        return a
    if rango:
        desde, hasta = rango
        for siglo in (2000, 1900):
            if desde <= siglo + a <= hasta:
                return siglo + a
    return 2000 + a if a <= date.today().year % 100 else 1900 + a


def _fecha_api(fecha, frecuencia):
    """Pasa la fecha del usuario al formato que pide la API: 2025-1 (mensual y trimestral), 2025-01-15 (diaria), 2025 (anual)."""
    f, frec = str(fecha).strip(), frecuencia.lower()
    if frec == "diaria":
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", f):
            raise ToolError(f"Fecha {fecha!r} no válida para una serie diaria: usen AAAA-MM-DD, por ejemplo 2026-10-01.")
        return f
    if frec == "anual":
        if not re.fullmatch(r"\d{4}", f[:4]):
            raise ToolError(f"Fecha {fecha!r} no válida para una serie anual: usen AAAA, por ejemplo 2025.")
        return f[:4]
    if frec == "trimestral":
        m = re.fullmatch(r"(\d{4})-T?([1-4])", f, flags=re.IGNORECASE)
        if not m:
            raise ToolError(f"Fecha {fecha!r} no válida para una serie trimestral: usen AAAA-T1 … AAAA-T4.")
        return f"{m[1]}-{int(m[2])}"
    m = re.fullmatch(r"(\d{4})-(\d{1,2})", f)  # mensual
    if not m or not 1 <= int(m[2]) <= 12:
        raise ToolError(f"Fecha {fecha!r} no válida para una serie mensual: usen AAAA-MM, por ejemplo 2025-01.")
    return f"{m[1]}-{int(m[2])}"


def _periodo(nombre, frecuencia, rango=None):
    """Nombre que devuelve la API -> periodo uniforme. rango = (año desde, año hasta) pedidos, para _anio.
    'Ene.2025' -> '2025-01' · '01.Oct.26' -> '2026-10-01' · 'T1.25' -> '2025-T1' · '2025' -> '2025'."""
    n, frec = nombre.strip(), frecuencia.lower()
    if frec == "diaria":
        dia, mes, a = n.split(".")
        return f"{_anio(a, rango)}-{MESES[mes.lower()[:3]]:02d}-{int(dia):02d}"
    if frec == "trimestral":
        t, a = n.split(".")
        return f"{_anio(a, rango)}-{t.upper()}"
    if frec == "anual":
        return n
    mes, a = n.split(".")  # mensual
    return f"{_anio(a)}-{MESES[mes.lower()[:3]]:02d}"


def _pedir(url, intentos=3):
    """Pide JSON a la API. Si responde HTML (muchos pedidos seguidos) o falla la red, espera y reintenta."""
    for i in range(intentos):
        try:
            r = httpx.get(url, timeout=60)
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError):  # ValueError: la respuesta no era JSON
            if i == intentos - 1:
                raise ToolError(f"El BCRP no respondió con datos válidos tras {intentos} intentos: {url}")
            time.sleep(2 * (i + 1))


@cache
def _serie(codigo, desde, hasta):
    """Baja la serie una sola vez por (codigo, desde, hasta): las siguientes llamadas usan la caché."""
    ficha = _ficha(codigo)  # ToolError con el código si no existe
    frec = ficha["frecuencia"]
    url = f"{API}/{codigo}/json/{_fecha_api(desde, frec)}/{_fecha_api(hasta, frec)}"
    rango = (int(str(desde).strip()[:4]), int(str(hasta).strip()[:4]))  # años con 4 dígitos, ya validados arriba
    datos = []
    for p in _pedir(url).get("periods", []):
        try:
            valor = float(p["values"][0])
        except (ValueError, IndexError, TypeError):  # "n.d." u otros vacíos: se omiten
            continue
        datos.append((_periodo(p["name"], frec, rango), valor))
    if not datos:
        raise ToolError(f"La serie {codigo} no tiene datos entre {desde} y {hasta}.")
    return ficha, tuple(datos), url


@mcp.tool(annotations=SOLO_LECTURA)
def serie(codigo: str, desde: str, hasta: str) -> dict:
    """Descarga los datos oficiales de una serie del BCRP entre dos fechas (incluidas).

    Formato de las fechas según la frecuencia de la serie: mensual "2025-01", trimestral "2025-T1",
    diaria "2026-10-01", anual "2025". Si no conocen el código, usen antes buscar_series.
    Devuelve código, nombre, frecuencia, datos [{periodo, valor}] y la URL de la fuente. Omite los valores "n.d.".
    """
    ficha, datos, url = _serie(codigo.strip().upper(), desde, hasta)
    return {"codigo": ficha["codigo"], "nombre": ficha["nombre"], "frecuencia": ficha["frecuencia"],
            "datos": [{"periodo": p, "valor": v} for p, v in datos], "fuente": url}

# --- TODO 2 · resumen -------------------------------------------------------------------------------------------

NOTA_TASAS = ("Si la serie ya es una tasa o porcentaje (p. ej. 'var% 12 meses'), usa 'cambio' en puntos "
              "porcentuales; 'variacion_pct' solo tiene sentido para niveles e índices.")
# El catálogo del BCRP no informa la unidad de medida (columna vacía en las 17,167 series, revisado el 8/11/2026),
# así que no se intenta adivinar si una serie es tasa: se devuelven ambos cálculos y esta nota, siempre.


def _punto(par):
    periodo, valor = par
    return {"periodo": periodo, "valor": round(valor, 4)}


@mcp.tool(annotations=SOLO_LECTURA)
def resumen(codigo: str, desde: str, hasta: str) -> dict:
    """Resume una serie del BCRP entre dos fechas, con cálculos hechos en Python (no los hagas a mano).

    Devuelve: primero y ultimo {periodo, valor}; cambio = ultimo - primero; variacion_pct = (ultimo/primero - 1)*100;
    promedio; maximo y minimo {periodo, valor}; n (número de datos); código, nombre, URL de la fuente y una nota.
    Ojo con la unidad: si la serie YA es una tasa o porcentaje (p. ej. "var% 12 meses"), lo que tiene sentido
    es "cambio" (en puntos porcentuales), no "variacion_pct". variacion_pct sirve para niveles e índices.
    Fechas como en serie: mensual "2025-01", trimestral "2025-T1", diaria "2026-10-01", anual "2025".
    """
    ficha, datos, url = _serie(codigo.strip().upper(), desde, hasta)
    valores = [v for _, v in datos]
    primero, ultimo = datos[0], datos[-1]
    return {
        "codigo": ficha["codigo"], "nombre": ficha["nombre"], "frecuencia": ficha["frecuencia"],
        "n": len(datos),
        "primero": _punto(primero),
        "ultimo": _punto(ultimo),
        "cambio": round(ultimo[1] - primero[1], 4),
        "variacion_pct": round((ultimo[1] / primero[1] - 1) * 100, 4) if primero[1] != 0 else None,
        "promedio": round(sum(valores) / len(valores), 4),
        "maximo": _punto(max(datos, key=lambda d: d[1])),  # si hay empate, el primer periodo
        "minimo": _punto(min(datos, key=lambda d: d[1])),
        "fuente": url,
        "nota": NOTA_TASAS,
    }

# --- TODO 3 · herramienta propia: comparar_series ------------------------------------------------------------------
# Compara VARIACIONES (no niveles), para que se puedan comparar series de distinta unidad o base.

def _variacion(v0, v1):
    return round((v1 / v0 - 1) * 100, 4) if v0 != 0 else None


def _variaciones_anuales(datos):
    """Último dato de cada año frente al último dato del año anterior, en %. Solo años con ambos datos.
    Con datos mensuales completos es diciembre contra diciembre; si el último año está incompleto,
    'hasta' muestra hasta qué periodo llega (p. ej. 2026-10 frente a 2025-12)."""
    ultimo_del_anio = {}
    for periodo, valor in sorted(datos):  # ordenados: queda el último periodo de cada año
        ultimo_del_anio[int(periodo[:4])] = (periodo, valor)
    salida = []
    for anio in sorted(ultimo_del_anio):
        if anio - 1 in ultimo_del_anio:
            (p0, v0), (p1, v1) = ultimo_del_anio[anio - 1], ultimo_del_anio[anio]
            salida.append({"anio": anio, "desde": p0, "hasta": p1, "variacion_pct": _variacion(v0, v1)})
    return salida


@mcp.tool(annotations=SOLO_LECTURA)
def comparar_series(codigo_a: str, codigo_b: str, desde: str, hasta: str) -> dict:
    """Compara cuánto VARIÓ cada una de dos series del BCRP en el mismo periodo, y cuál creció más.

    Úsala con niveles o índices (p. ej. IPC Alimentos y Bebidas vs IPC sin Alimentos y Bebidas, índice Dic.2021=100).
    Las dos series deben tener la misma frecuencia. Fechas como en serie (mensual "2025-01", etc.).
    Para tener la variación anual de un año, pidan desde el último periodo del año anterior:
    desde="2019-12", hasta="2024-12" da las variaciones de 2020 a 2024 y la del periodo completo.
    Devuelve por serie: primero, ultimo, variacion_pct del periodo y variaciones_anuales; además
    diferencia_pp = variacion_pct(a) - variacion_pct(b), crecio_mas, la comparación año a año, fuentes y una nota.
    """
    ca, cb = codigo_a.strip().upper(), codigo_b.strip().upper()
    fa, fb = _ficha(ca), _ficha(cb)  # ToolError con el código si alguno no existe
    if fa["frecuencia"] != fb["frecuencia"]:  # se revisa ANTES de descargar
        raise ToolError(f"No se pueden comparar series de distinta frecuencia: {ca} es {fa['frecuencia']} y "
                        f"{cb} es {fb['frecuencia']}. Elijan dos series con la misma frecuencia.")
    lados = {}
    for lado, codigo in (("a", ca), ("b", cb)):
        ficha, datos, url = _serie(codigo, desde, hasta)
        lados[lado] = {
            "codigo": ficha["codigo"], "nombre": ficha["nombre"],
            "primero": _punto(datos[0]), "ultimo": _punto(datos[-1]),
            "variacion_pct": _variacion(datos[0][1], datos[-1][1]),
            "variaciones_anuales": _variaciones_anuales(datos),
            "fuente": url,
        }
    a, b = lados["a"], lados["b"]
    if a["variacion_pct"] is None or b["variacion_pct"] is None:
        diferencia, crecio_mas = None, None
    else:
        diferencia = round(a["variacion_pct"] - b["variacion_pct"], 4)
        crecio_mas = a["codigo"] if diferencia > 0 else b["codigo"] if diferencia < 0 else "igual"
    anuales_b = {x["anio"]: x for x in b["variaciones_anuales"]}
    por_anio = []
    for xa in a["variaciones_anuales"]:
        xb = anuales_b.get(xa["anio"])
        if xb and xa["variacion_pct"] is not None and xb["variacion_pct"] is not None:
            por_anio.append({"anio": xa["anio"], "a": xa["variacion_pct"], "b": xb["variacion_pct"],
                             "diferencia_pp": round(xa["variacion_pct"] - xb["variacion_pct"], 4)})
    mismo_periodo = (a["primero"]["periodo"], a["ultimo"]["periodo"]) == (b["primero"]["periodo"], b["ultimo"]["periodo"])
    return {
        "frecuencia": fa["frecuencia"], "a": a, "b": b,
        "diferencia_pp": diferencia, "crecio_mas": crecio_mas, "por_anio": por_anio,
        "mismo_periodo": mismo_periodo,  # False: las series no cubren exactamente los mismos periodos
        "nota": NOTA_TASAS,
    }

# --- TODO 4 · recurso ---------------------------------------------------------------------------------------------
# Un recurso lo adjunta el usuario como contexto (en Claude Code: @bcrp:bcrp://serie/PN39445PM);
# una herramienta, en cambio, la decide llamar el modelo.

@mcp.resource("bcrp://serie/{codigo}")
def ficha_serie(codigo: str) -> str:
    """Ficha de una serie del BCRP: código, nombre, categoría, frecuencia, inicio de datos y última actualización."""
    f = _ficha(codigo.strip().upper())
    return "\n".join([
        f"Código: {f['codigo']}",
        f"Nombre: {f['nombre']}",
        f"Categoría: {f['categoria']}",
        f"Frecuencia: {f['frecuencia']}",
        f"Datos desde: {f['inicio']}",
        f"Última actualización: {f['actualizada']}",
        f"Fuente: {URL_CATALOGO}",
    ])


# --- TODO 5 · prompt ----------------------------------------------------------------------------------------------
# Plantilla de instrucciones reutilizable; en Claude Code: /mcp__bcrp__informe <tema>

@mcp.prompt
def informe(tema: str) -> str:
    """Pide un informe breve sobre un tema con series del BCRP, con cifras verificables y citadas."""
    return (
        f"Prepara un informe breve sobre: {tema}.\n\n"
        "Reglas:\n"
        "1. Busca las series con buscar_series y confirma su nombre y frecuencia antes de usarlas.\n"
        "2. No hagas cuentas a mano: usa resumen para una serie y comparar_series para comparar dos.\n"
        "3. Cada cifra debe citar el código de la serie, el periodo y la fuente (URL del BCRP).\n"
        "4. Si una serie ya es una tasa o porcentaje (p. ej. 'var% 12 meses'), expresa sus cambios en puntos "
        "porcentuales, no como variación porcentual.\n"
        "5. Describe asociaciones y diferencias, sin afirmar causalidad.\n"
        "6. Si un dato no está disponible, dilo; no lo estimes ni lo inventes.\n"
        "7. Para saber hasta cuándo hay datos, consulta la serie hasta la fecha actual; no lo supongas."
    )


if __name__ == "__main__":
    mcp.run()
