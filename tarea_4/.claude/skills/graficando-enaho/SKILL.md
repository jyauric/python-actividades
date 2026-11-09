---
name: graficando-enaho
description: Hace gráficos de la pobreza monetaria del Perú con la ENAHO 2024 (INEI) - urbano vs rural (total y extrema), por sexo y por departamento - con cifras ponderadas, título analítico, unidades y fuente, y los guarda en figuras/. Úsala cuando pidan graficar, visualizar o comparar la pobreza por área, sexo o departamento con la ENAHO.
---

# Graficando la ENAHO 2024

1. **Base procesada.** Si no existen `salidas/indicadores.csv` y `salidas/personas_2024.parquet`, usa primero la skill `limpiando-enaho` y continúa solo si su validación termina sin `[FALLA]`.

2. **Gráfico.** Desde la raíz del proyecto corre, según lo pedido:

   ```bash
   uv run ${CLAUDE_SKILL_DIR}/scripts/graficar.py --tipo area          # urbano vs rural (total y extrema)
   uv run ${CLAUDE_SKILL_DIR}/scripts/graficar.py --tipo sexo          # mujeres vs hombres
   uv run ${CLAUDE_SKILL_DIR}/scripts/graficar.py --tipo departamento  # 25 departamentos, ordenados
   uv run ${CLAUDE_SKILL_DIR}/scripts/graficar.py --tipo todos         # los tres
   ```

   Si el script termina con código 2, falta la base: vuelve al paso 1.

3. **Respuesta.** Indica la ruta del PNG en `figuras/` y describe lo que muestra con las cifras de `salidas/indicadores.csv` (no calcules a mano). Cita la fuente: INEI – ENAHO 2024, residentes habituales, ponderado con `facpob07`.

4. **Cuidado al interpretar.** No se calcularon intervalos de confianza: no afirmes que una diferencia pequeña (p. ej. entre sexos) es significativa. Describe asociaciones, no causas.
