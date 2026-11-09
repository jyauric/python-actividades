---
name: limpiando-enaho
description: Limpia y valida la ENAHO 2024 del INEI (módulo 34 sumaria y módulo 02 miembros) y calcula la pobreza monetaria ponderada con factores de expansión, nacional, por área urbana/rural, por sexo y por departamento. Úsala cuando pidan limpiar, unir o validar la ENAHO, o calcular pobreza monetaria en el Perú. Las skills graficando-enaho y mapeando-enaho la usan primero si no existe salidas/personas_2024.parquet.
---

# Limpiando la ENAHO 2024

1. **Datos.** Comprueba que existan `datos/966-Modulo34.zip` y `datos/966-Modulo02.zip`. Si falta alguno, detente y pide al usuario descargarlo (enlaces en `reference.md`). No busques datos en otra fuente.

2. **Limpieza y validación.** Desde la raíz del proyecto corre exactamente:

   ```bash
   uv run ${CLAUDE_SKILL_DIR}/scripts/limpiar.py
   ```

3. **Si falla, detente.** Si el comando termina con error o `salidas/validacion.txt` tiene alguna línea `[FALLA]`, muestra el reporte al usuario y no calcules nada más. No modifiques el script ni las referencias para que la validación pase.

4. **Responde con los archivos, no con cuentas a mano.** Lee `salidas/validacion.txt` y `salidas/indicadores.csv`. Toda cifra que des debe salir de esos archivos e indicar: INEI – ENAHO 2024, residentes habituales, ponderado con `facpob07`. Menciona las líneas `[REVISAR]` e `[INFO]`, con su explicación (p. ej. las diferencias de ponderación entre `facpob07` y `factor07 × mieperho` descritas en `reference.md`).

5. Para el detalle de variables, reglas y tolerancias, consulta `reference.md`.
