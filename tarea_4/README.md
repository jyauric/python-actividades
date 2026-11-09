# Tarea 4 – Agente de investigación socioeconómica (MCP del BCRP + Skills de la ENAHO)

Tarea 4 del curso Python Intermedio ([issue #201](https://github.com/d2cml-ai/Data-Science-Python/issues/201)).

## 1. Objetivo

Construir un agente en Claude Code que responda preguntas socioeconómicas del Perú con **datos oficiales** y **cálculos verificables**: series del BCRP mediante un servidor MCP propio y microdatos de la ENAHO 2024 (INEI) mediante tres Skills. Pregunta de investigación:

> ¿Cuánto aumentaron los precios de los alimentos frente al resto de la canasta en Lima Metropolitana entre diciembre de 2019 y diciembre de 2024, y qué diferencias de pobreza monetaria había entre departamentos y entre las áreas urbana y rural del Perú en 2024?

Informe: [`informes/informe_final.md`](informes/informe_final.md).

## 2. Arquitectura

```
Pregunta en lenguaje natural ──► Claude Code (agente)
        │                                   │
        ├─► MCP bcrp (mcp/server.py) ──► API del BCRP  → series, resúmenes, comparaciones
        ├─► Skills (.claude/skills/)  ──► ENAHO 2024    → limpieza + validación → gráficos → mapa
        └─► informes/grafico_bcrp.py  (usa comparar_series del MCP) → gráfico BCRP
                                    ▼
                  figuras/, mapas/, salidas/, informes/informe_final.md
```

Las cifras las calcula Python (MCP y scripts de las Skills); el modelo no hace cuentas a mano.

## 3. Herramientas MCP (`mcp/server.py`, FastMCP)

| Elemento | Qué hace |
|---|---|
| `buscar_series(texto, frecuencia, limite)` | Busca series en el catálogo del BCRP (venía hecha en la plantilla de la sesión 04). |
| `serie(codigo, desde, hasta)` | Descarga los datos de una serie (fechas por frecuencia, reintentos, omite `n.d.`, error claro si el código no existe). |
| `resumen(codigo, desde, hasta)` | Primero, último, cambio, variación %, promedio, máximo y mínimo; incluye una nota: en series que ya son tasas, usar el cambio en pp. |
| **`comparar_series(codigo_a, codigo_b, desde, hasta)`** (propia) | Compara **variaciones** de dos series (periodo y anuales dic.–dic.), diferencia en pp y cuál creció más; rechaza frecuencias distintas. |
| Recurso `bcrp://serie/{codigo}` | Ficha de la serie. |
| Prompt `informe(tema)` | Plantilla con 7 reglas (citar código, periodo y fuente; tasas en pp; sin causalidad; no suponer disponibilidad de datos). |

Pruebas: 8 originales de la sesión 04 (sin modificar) + 2 propias de `comparar_series` → **10 passed** ([`salidas/pruebas_mcp.txt`](salidas/pruebas_mcp.txt)). `buscar_series` y las 8 pruebas originales provienen del material de la sesión 04.

## 4. Skills (`.claude/skills/`)

| Skill | Qué hace | Salidas |
|---|---|---|
| `limpiando-enaho` | Lee módulos 34 y 02 (llaves como texto), filtra residentes habituales, une con `validate="m:1"`, pondera con `facpob07`, valida y se detiene si algo esencial falla. Detalle en [`reference.md`](.claude/skills/limpiando-enaho/reference.md). | `salidas/validacion.txt`, `salidas/indicadores.csv`, `salidas/personas_2024.parquet` (no se sube) |
| `graficando-enaho` | Gráficos ponderados: urbano vs. rural (total y extrema), por sexo y por departamento. Usa `limpiando-enaho` primero si falta la base. | `figuras/` |
| `mapeando-enaho` | Mapa coroplético; unión por código `ubigeo[:2] = FIRST_IDDP`, 25 unidades, Lima y Callao separados; compara con la referencia de la sesión 16. | `mapas/`, `salidas/comparacion_referencia_mapa.csv` |

## 5. Fuentes y descarga de datos

Los datos originales no se suben (`datos/` está en `.gitignore`). Descargarlos en `tarea_4/datos/`:

```bash
mkdir -p datos
curl -L -o datos/966-Modulo34.zip https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip
curl -L -o datos/966-Modulo02.zip https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo02.zip
curl -L -o datos/peru_departamental_simple.geojson https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson
```

BCRP: API pública de https://estadisticas.bcrp.gob.pe/estadisticas/series/ (sin clave). Series usadas: `PN39445PM` (IPC Alimentos y Bebidas), `PN38706PM` (IPC sin Alimentos y Bebidas), `PN38705PM` (IPC total); índices Dic.2021 = 100, Lima Metropolitana.

## 6. Instalación con `uv`

```bash
cd tarea_4
uv sync          # instala fastmcp, httpx, pandas, pyarrow, geopandas, matplotlib y pytest (pyproject.toml / uv.lock)
```

## 7. Conectar el MCP a Claude Code

El archivo [`.mcp.json`](.mcp.json) registra el servidor `bcrp` (`uv run mcp/server.py`). Ejecutar `claude` **desde `tarea_4/`**, aprobar el servidor del proyecto y comprobar con `/mcp`. Uso: recurso `@bcrp:bcrp://serie/PN39445PM`; prompt `/mcp__bcrp__informe <tema>`.

## 8. Reproducir procesamiento y pruebas

```bash
uv run pytest mcp/ -q                                                # 10 pruebas del MCP
uv run .claude/skills/limpiando-enaho/scripts/limpiar.py             # limpieza + validación
uv run .claude/skills/graficando-enaho/scripts/graficar.py --tipo todos
uv run .claude/skills/mapeando-enaho/scripts/mapear.py               # mapa + comparación con referencia
uv run informes/grafico_bcrp.py                                      # gráfico BCRP
uv run evaluacion/evaluar.py                                         # evaluación Modo A vs. B (usa claude -p)
```

Validación ENAHO 2024 (`salidas/validacion.txt`): 108,664 residentes; 25 unidades territoriales; pobreza nacional **27.53 %** (referencia 27.6 ± 0.1). La diferencia con las referencias (hasta 0.14 pp en rural y 0.52 pp por departamento) se explica por el conteo de miembros del hogar (`mieperho` vs. residentes habituales): ver [`reference.md`](.claude/skills/limpiando-enaho/reference.md).

## 9. Resultados de la evaluación

Mismas 10 preguntas (4 BCRP, 4 ENAHO, 2 combinadas), Haiku, sesiones separadas:

| Modo | Correctas | Incorrectas | No responde | Tiempo promedio |
|---|---|---|---|---|
| A – sin MCP ni Skills | 1/10 | 0 | 9 | 6.3 s |
| B – con MCP y Skills | 8/10 | 1 | 1 | 17.0 s |

Detalle y observaciones de validez en [`evaluacion/comparacion.md`](evaluacion/comparacion.md) y [`evaluacion/resultados.csv`](evaluacion/resultados.csv).

## 10. Limitaciones y problemas encontrados

- Las series de precios son de **Lima Metropolitana**; la pobreza es nacional, por área y por departamento. Precios 2019–2024 vs. pobreza 2024 (corte).
- Diferencias de ponderación con las referencias (conteo de miembros del hogar), documentadas.
- Sin intervalos de confianza; resultados descriptivos (asociación, no causalidad).
- `urbano = estrato <= 5` es la regla de la sesión 16; no se verificó que sea la definición oficial del INEI.
- Problemas encontrados y corregidos: ver la sección “Errores detectados y corregidos” del informe (afirmación falsa del agente sobre disponibilidad de datos, validación rural fallida y diagnosticada, regla de redondeo, precisión de la definición de urbano).
- En la evaluación, el Modo B tomó en una pregunta una cifra de referencia guardada en `salidas/validacion.txt` (ver `comparacion.md`).

## 11. Ejemplo de una ejecución completa

Ejecución integrada en una sola sesión de Claude Code (MCP `comparar_series` + `resumen`, script del gráfico BCRP y las Skills `limpiando-enaho`, `graficando-enaho` y `mapeando-enaho`) que produjo el informe: [`evidencias_ia/integracion/03_ejecucion_integrada.txt`](evidencias_ia/integracion/03_ejecucion_integrada.txt).

## 12. Evidencias del uso de IA

Conversaciones exportadas de Claude Code (Opción B: exportación), en orden:

| Archivo | Contenido |
|---|---|
| `evidencias_ia/00_desarrollo_chat_tarea_4_Python2.txt` | Conversación principal de desarrollo: decisiones, MCP, Skills, diagnósticos, gráficos, informe y evaluación |
| `evidencias_ia/mcp/01_prueba_mcp_claude_code.txt` | Prueba del MCP en Claude Code (recurso, prompt y herramientas) |
| `evidencias_ia/skills/02_activacion_skills.txt` | Activación por lenguaje natural y coordinación entre Skills |
| `evidencias_ia/integracion/03_ejecucion_integrada.txt` | Ejecución integrada MCP + Skills e informe |

La evaluación se ejecutó con `claude -p` sin guardar sesiones (`--no-session-persistence`); sus respuestas, fuentes y herramientas usadas por pregunta quedan en `evaluacion/resultados.csv`. En los exports se reemplazaron las rutas absolutas del equipo por `~/`.
