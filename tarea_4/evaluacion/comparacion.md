# Comparación: Modo A (sin MCP ni Skills) vs. Modo B (con MCP y Skills)

## Diseño

- **10 preguntas** (`preguntas.csv`): 4 BCRP, 4 ENAHO y 2 combinadas. Las respuestas esperadas y las tolerancias se fijaron **antes** de ejecutar y salen de fuentes oficiales o cálculos independientes del agente: valores de la web del BCRP verificados manualmente (8/11/2026), cifras del enunciado (issue #201), la referencia departamental de la sesión 16 y el `preguntas.csv` de la sesión 04.
- **Ejecución** (`evaluar.py`, adaptado del `evaluar.py` de la sesión 04): cada pregunta en una sesión separada de `claude -p`, mismo modelo (**Haiku**), misma instrucción (responder en JSON con valores y fuente; `null` si no se sabe con certeza) y la indicación de no leer `evaluacion/`.
  - **Modo A:** sin herramientas (`--tools ""`), sin MCP (`--strict-mcp-config`), sin Skills. Solo conocimiento del modelo.
  - **Modo B:** MCP `bcrp` del proyecto + herramientas `Skill`, `Bash`, `Read`.
- **Criterio:** correcta si todas las cifras pedidas caen dentro de la tolerancia; “no responde” si alguna es `null`.

## Resultados (`resultados.csv`)

| | Correctas | Incorrectas | No responde | Tiempo promedio (s) | Tiempo mín.–máx. (s) |
|---|---|---|---|---|---|
| **Modo A** | **1/10** | 0 | 9 | 6.3 | 3.6–8.8 |
| **Modo B** | **8/10** | 1 | 1 | 17.0 | 7.4–43.9 |

| Pregunta | Esperado | Modo A | Modo B | Herramientas en B |
|---|---|---|---|---|
| b1 índice alimentos dic-2024 | 119.53 | null | 119.5292 ✔ | buscar_series, serie |
| b2 índice IPC dic-2019 | 92.14 | null | 92.1400 ✔ | buscar_series, serie |
| b3 variación IPC 2019–2024 | 23.91 | null | 23.91 ✔ | buscar_series, resumen |
| b4 inflación 12 m dic-2025 | 1.5088 | null | 1.51 ✔ | buscar_series, serie |
| e1 pobreza nacional | 27.6 | 27.6 ✔ | 27.6 ✔ ⚠️ | buscar_series, Bash, Read |
| e2 residentes habituales | 108,664 | null | 108,664 ✔ | Bash |
| e3 pobreza urbana | 24.8 | null | null | buscar_series, Bash |
| e4 pobreza rural | 39.3 | null | 39.3 ✔ ⚠️ | buscar_series, Bash |
| c1 pobreza nacional + var. alimentos | 27.6; 31.95 | null; null | 27.53; 31.94 ✔ | buscar_series, resumen, Bash, Read |
| c2 pobreza Lima + var. IPC | 27.1; 23.91 | null; null | 26.89; 23.91 ✘ | buscar_series, resumen, Bash |

## Qué mejoró y qué no

- **Mejoraron con MCP y Skills:** 7 preguntas (las 4 del BCRP, e2, e4 y c1). En el Modo A el modelo respondió `null` y explicó que no tenía acceso a los datos: **no inventó cifras**.
- **Igual en ambos modos:** e1 (correcta en los dos; la pobreza nacional 2024 es una cifra que el modelo conoce o que está en los archivos del proyecto).
- **Sin respuesta en B:** e3 (urbana). El agente tenía el cálculo propio pero respondió `null` porque no pudo confirmar la cifra publicada por el INEI: la instrucción pedía no estimar.
- **Incorrecta en B:** c2. La parte BCRP es correcta (23.91); la pobreza de Lima con el método principal da 26.89 % frente a 27.1 % de la referencia (diferencia de 0.21 pp > 0.1). Es la diferencia por conteo de miembros del hogar documentada en `limpiando-enaho/reference.md`, prevista antes de ejecutar.
- **Tiempo:** B tarda en promedio 2.7 veces más (17.0 s vs. 6.3 s) porque consulta herramientas; las preguntas ENAHO fueron las más lentas (hasta 43.9 s).

## Observaciones de la revisión manual (validez)

1. ⚠️ **e1: acceso indirecto a la referencia.** El agente respondió 27.6 tomando la cifra de referencia que figura en `salidas/validacion.txt`, no su propio cálculo (27.53 %). El resultado no cambia (27.53 también está dentro de ± 0.1), pero es un acceso indirecto a la respuesta esperada que debe declararse.
2. ⚠️ **e4: método distinto del principal.** El agente respondió 39.3 usando el valor del método de la sumaria (39.30 %, calculado por `limpiar.py` como validación), no el del método principal (`facpob07`: 39.44 %, que habría quedado fuera de ± 0.1).
3. Las respuestas del BCRP citan código de serie, periodo y URL de la API; los valores coinciden con los verificados manualmente en la web del BCRP.

## Errores principales

- **Modo A:** falta de datos (9 de 10 sin respuesta). No hubo cifras inventadas.
- **Modo B:** (i) tomar una cifra de referencia del propio proyecto en lugar del cálculo (e1); (ii) elegir el método que coincide con la referencia sin decirlo como método principal (e4); (iii) exceso de prudencia (e3); (iv) diferencia metodológica conocida (c2).

## Conclusión

Con el MCP del BCRP y las Skills de la ENAHO, el agente pasó de **1/10 a 8/10** respuestas correctas, a costa de unos 11 segundos más por pregunta. La mejora es clara en el BCRP (0/4 → 4/4), donde las cifras salen de la API oficial con su fuente. En la ENAHO la mejora es real pero con matices: dos aciertos dependen de cifras que el propio proyecto guarda junto a sus validaciones (e1, e4), lo que muestra que, en un sistema así, los archivos de validación pueden filtrar la respuesta esperada. Una mejora posible es separar las referencias del enunciado de las salidas que lee el agente.

Limitaciones de la evaluación: 10 preguntas, una sola ejecución por pregunta y un solo modelo (Haiku); los resultados pueden variar entre ejecuciones.
