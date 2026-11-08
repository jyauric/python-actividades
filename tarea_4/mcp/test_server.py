"""El contrato del servidor: si estas pruebas pasan, Claude Code y evaluar.py pueden usarlo.

    uv run pytest -q

Llaman al servidor en memoria, igual que lo haría Claude Code, y piden datos reales al BCRP.
"""
import asyncio

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from server import mcp


async def _con_cliente(f):
    async with Client(mcp) as c:
        return await f(c)


def llamar(herramienta, **args):
    return asyncio.run(_con_cliente(lambda c: c.call_tool(herramienta, args))).data


def test_buscar_encuentra_el_ipc():
    r = llamar("buscar_series", texto="ipc 12 meses", limite=5)
    assert "PN01273PM" in [x["codigo"] for x in r]
    assert {"codigo", "nombre", "frecuencia"} <= r[0].keys()


def test_cuatro_herramientas_como_minimo():
    nombres = {t.name for t in asyncio.run(_con_cliente(lambda c: c.list_tools()))}
    assert {"buscar_series", "serie", "resumen"} <= nombres
    assert len(nombres) >= 4, "falta su herramienta propia"


def test_serie_mensual():
    r = llamar("serie", codigo="PN01271PM", desde="2025-01", hasta="2025-12")
    assert len(r["datos"]) == 12
    assert r["datos"][0]["periodo"] == "2025-01"
    assert r["datos"][2]["valor"] == pytest.approx(0.81, abs=0.01)   # IPC de Lima, marzo de 2025
    assert r["fuente"].startswith("https://estadisticas.bcrp.gob.pe")


def test_serie_diaria():
    r = llamar("serie", codigo="PD04638PD", desde="2026-10-01", hasta="2026-10-15")
    assert r["datos"][0]["periodo"] == "2026-10-01"
    assert r["datos"][-1] == {"periodo": "2026-10-15", "valor": pytest.approx(3.428, abs=0.001)}


def test_resumen_sin_cuentas_a_mano():
    r = llamar("resumen", codigo="PN01273PM", desde="2025-12", hasta="2026-09")
    assert r["primero"]["valor"] == pytest.approx(1.51, abs=0.01)
    assert r["ultimo"]["valor"] == pytest.approx(4.55, abs=0.01)
    assert r["maximo"]["periodo"] == "2026-09"
    assert {"cambio", "variacion_pct", "promedio", "minimo"} <= r.keys()


def test_codigo_inexistente_da_un_error_claro():
    with pytest.raises(ToolError, match="XX999"):
        llamar("serie", codigo="XX999", desde="2025-01", hasta="2025-02")


def test_un_recurso():
    async def contar(c):
        return len(await c.list_resources()) + len(await c.list_resource_templates())
    assert asyncio.run(_con_cliente(contar)) >= 1


def test_un_prompt():
    assert len(asyncio.run(_con_cliente(lambda c: c.list_prompts()))) >= 1


# --- Pruebas propias: comparar_series (no modifican las 8 originales de la sesión 04) -------------------------------

def test_comparar_series_calcula_variaciones():
    """A1: la variación de comparar_series coincide con un cálculo independiente hecho desde los datos de serie,
    y diferencia_pp = variación(a) - variación(b). Series: IPC Alimentos y Bebidas vs IPC Sin Alimentos y Bebidas
    (Lima Metropolitana, índice Dic.2021 = 100)."""
    r = llamar("comparar_series", codigo_a="PN39445PM", codigo_b="PN38706PM", desde="2019-12", hasta="2024-12")
    for lado, codigo in [("a", "PN39445PM"), ("b", "PN38706PM")]:
        datos = llamar("serie", codigo=codigo, desde="2019-12", hasta="2024-12")["datos"]
        esperado = (datos[-1]["valor"] / datos[0]["valor"] - 1) * 100
        assert r[lado]["variacion_pct"] == pytest.approx(esperado, abs=0.01)
    assert r["diferencia_pp"] == pytest.approx(r["a"]["variacion_pct"] - r["b"]["variacion_pct"], abs=0.01)
    assert [x["anio"] for x in r["por_anio"]] == [2020, 2021, 2022, 2023, 2024]
    # A2: valores verificados a mano en la web del BCRP el 8/11/2026 (la web muestra 2 decimales)
    assert r["a"]["primero"]["valor"] == pytest.approx(90.59, abs=0.01)    # PN39445PM, dic-2019
    assert r["a"]["ultimo"]["valor"] == pytest.approx(119.53, abs=0.01)    # PN39445PM, dic-2024


def test_comparar_series_rechaza_frecuencias_distintas():
    """Una serie mensual y una diaria no se comparan: error claro que menciona la frecuencia."""
    with pytest.raises(ToolError, match="frecuencia"):
        llamar("comparar_series", codigo_a="PN39445PM", codigo_b="PD04638PD", desde="2024-01", hasta="2024-12")
