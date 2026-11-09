---
name: mapeando-enaho
description: Hace un mapa coroplético de la pobreza monetaria por departamento del Perú con la ENAHO 2024 (INEI), uniendo por código (ubigeo[:2] = FIRST_IDDP), con 25 unidades, Lima y Callao separados, 5 clases de 10 pp y leyenda en %, y lo compara con la referencia de la sesión 16. Úsala cuando pidan un mapa o la distribución territorial de la pobreza por departamento.
---

# Mapeando la ENAHO 2024

1. **Base procesada.** Si no existe `salidas/indicadores.csv` (o `salidas/personas_2024.parquet`), usa primero la skill `limpiando-enaho` y continúa solo si su validación termina sin `[FALLA]`. Comprueba también que exista `datos/peru_departamental_simple.geojson`; si falta, pide al usuario descargarlo (enlace en el README).

2. **Mapa.** Desde la raíz del proyecto corre:

   ```bash
   uv run ${CLAUDE_SKILL_DIR}/scripts/mapear.py
   ```

   Código 2 = falta la base (vuelve al paso 1). Código 1 = la unión territorial no da 25 unidades válidas: muestra el error y detente; no unas por nombres.

3. **Respuesta.** Indica la ruta `mapas/pobreza_departamento_2024.png` y describe el mapa con las cifras de `salidas/indicadores.csv` (no calcules a mano). Menciona la comparación de `salidas/comparacion_referencia_mapa.csv` con la referencia de la sesión 16 y su explicación (conteo de miembros del hogar; ver `limpiando-enaho/reference.md`). Cita: INEI – ENAHO 2024, residentes habituales, ponderado con `facpob07`.

4. **Cuidado al interpretar.** Describe la distribución territorial y asociaciones; no afirmes causas.
