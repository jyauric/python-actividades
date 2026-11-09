# Referencia – limpiando-enaho

## Datos (INEI – ENAHO 2024, formato STATA)

| Archivo | Unidad | Filas | Llaves | Peso |
|---|---|---|---|---|
| `datos/966-Modulo34.zip` → `sumaria-2024.dta` | hogar | 33,691 | `conglome`, `vivienda`, `hogar` | `factor07` |
| `datos/966-Modulo02.zip` → `enaho01-2024-200.dta` | persona | 117,721 | las tres + `codperso` | `facpob07` |

Descarga: https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip y
https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo02.zip

El módulo 34 trae también `sumaria-2024-12g.dta` (12 grupos de gasto en lugar de 8); se usa `sumaria-2024.dta`, como en la sesión 16.

## Variables usadas (etiquetas tomadas de los propios .dta)

| Variable | Archivo | Etiqueta | Valores |
|---|---|---|---|
| `conglome`, `vivienda`, `hogar`, `codperso` | ambos | llaves | texto: conservan ceros iniciales |
| `ubigeo` | sumaria | ubicación | texto de 6 dígitos; `ubigeo[:2]` = departamento |
| `pobreza` | sumaria | pobreza | 1 = pobre extremo · 2 = pobre no extremo · 3 = no pobre |
| `estrato` | sumaria | estrato geográfico | 1–5: centros poblados de 2 000 a más habitantes · 6: de 500 a 1 999 · 7–8: área de empadronamiento rural |
| `mieperho` | sumaria | total de miembros del hogar | entero |
| `factor07` | sumaria | factor de expansión anual (proyecciones CPV-2007) | hogares |
| `p204` | miembros | ¿es miembro del hogar? | 1 = sí · 2 = no |
| `p205` | miembros | ¿se encuentra ausente del hogar 30 días o más? | 1 = sí · 2 = no |
| `p206` | miembros | ¿está presente en el hogar 30 días o más? | 1 = sí · 2 = no |
| `p207` | miembros | sexo | 1 = hombre · 2 = mujer |
| `facpob07` | miembros | factor de expansión anual de población (proyecciones CPV-2007) | personas |

## Reglas de procesamiento

1. Llaves como texto (no convertir a número).
2. Residentes habituales: `((p204 == 1) & (p205 == 2)) | ((p204 == 2) & (p206 == 1))`.
3. Unión personas → hogar con `merge(..., validate="m:1")`; se comprueba que no se pierdan ni dupliquen filas.
4. `departamento = ubigeo[:2]`; `urbano = estrato <= 5` (regla de la sesión 16; según las etiquetas de `estrato`, clasifica como urbanos los centros poblados de 2 000 habitantes o más); `pobre = pobreza <= 2`.
5. Toda cifra se pondera con `facpob07`: tasa = Σ(pobre × facpob07) / Σ facpob07 × 100. No se usan promedios simples.

## Valores de referencia y tolerancias

Fuente: enunciado de la Tarea 4 (issue #201, d2cml-ai/Data-Science-Python).

| Indicador | Método | Referencia | Tolerancia | Tipo | Justificación |
|---|---|---|---|---|---|
| Residentes habituales | — | 108,664 | exacto | esencial | conteo |
| Unidades territoriales | — | 25 | exacto | esencial | conteo |
| Pobreza nacional | principal (`facpob07`) | 27.6 % | ± 0.1 pp | esencial | fijada por el enunciado |
| Pobreza nacional | sumaria (`factor07 × mieperho`) | 27.6 % | ± 0.1 pp | informativo (control cruzado) | explica la diferencia por ponderación |
| Pobreza urbana | sumaria | 24.8 % | ± 0.1 pp | esencial | ver nota |
| Pobreza rural | sumaria | 39.3 % | ± 0.1 pp | esencial | ver nota |
| Pobreza urbana y rural | principal (`facpob07`) | — | sin tolerancia | `[INFO]` | se informa la cifra y su diferencia con el método sumaria |

**Nota (diagnóstico del 8/11/2026).** Con `facpob07` la pobreza rural dio 39.44 % (0.14 pp sobre 39.3). Al calcular por los dos métodos:

| Regla | Urbana `facpob07` | Urbana sumaria | Rural `facpob07` | Rural sumaria |
|---|---|---|---|---|
| `estrato <= 5` | 24.74 | 24.81 | 39.44 | 39.30 |
| `estrato <= 6` | 24.82 | 24.88 | 41.48 | 41.34 |

Las referencias urbana/rural del enunciado se reproducen con el método de la sumaria y `estrato <= 5`. La diferencia con `facpob07` es de **ponderación**, no un error de datos (el enunciado admite “diferencias de redondeo y ponderación debidamente explicadas”). Por eso urbano/rural se validan con el método sumaria (lo que comprueba la clasificación urbano/rural) y las cifras con `facpob07`, que son las que usan los gráficos y mapas, se informan con su diferencia. La tolerancia urbano/rural (± 0.1 pp) es decisión propia: el enunciado solo la fija para la nacional y dice “aproximadamente” para urbano/rural.

Según el README de la sesión 16, la pobreza nacional 2024 da 27.53 % con personas y `facpob07`, y 27.58 % con la sumaria y `factor07 × mieperho`.

Si una validación esencial falla, el script se detiene (código 1) y no guarda indicadores ni la base. Los resultados no se corrigen para que coincidan con las referencias: se investiga la causa.
