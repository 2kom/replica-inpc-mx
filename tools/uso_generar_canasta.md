# Uso de `tools/generar_canasta.py`

## Objetivo

Genera una canasta intermedia en CSV, utilizada después para construir la
canasta canónica del cálculo del INPC.

## Estado actual

Hoy solo funciona de punta a punta el **modo de extracción `xlsx`** (sin
`pdf`). El CLI ya acepta `--pdf` y `--sincronizar`, pero sus modos
(`_ejecutar_xlsx_pdf`, `_ejecutar_sincronizacion`) todavía no tienen cuerpo:
la corrida termina sin error y sin generar ningún archivo. Ver §Diseño
futuro: PDF y sincronización.

## Instalación

- Ejecutar el comando desde la raíz del repo:

```bash
python tools/generar_canasta.py ...
```

- Python `>=3.10`.
- Dependencias del proyecto más las dependencias opcionales de ponderadores:

```bash
pip install -e '.[ponderadores]'
```

Eso instala, entre otras, las librerías que usa esta herramienta:

- `openpyxl`

Para la extracción de `pdf` (ver §Diseño futuro) hace falta además `pdftotext`,
que **no se instala vía `pip`** — no hay wheel precompilado en PyPI para
Windows/Mac, solo código fuente que requiere compilar contra `poppler-cpp`.
Se instala vía `conda-forge`, que sí trae binarios listos para Linux/Windows/Mac:

```bash
conda install -c conda-forge pdftotext
```

## Comando funcional

Hoy el único comando que produce salida real es la extracción solo `xlsx`:

```bash
python tools/generar_canasta.py --version 2018 --xlsx ruta/a/xlsx/2018.xlsx -o salida/
```

### Parámetros

| Parámetro | Descripción |
| --- | --- |
| `--version` | Versión de canasta a extraer: `2010`, `2013`, `2018`, `2024`. |
| `--xlsx` | Ruta al archivo xlsx de ponderadores. |
| `-o` | Directorio de salida para el CSV y el registro JSON. Se crea automáticamente si no existe. |

### Archivos generados

Esta corrida deja en `salida/`:

- `ponderadores_{version}.csv` — la canasta intermedia. Ver §Esquema del
  CSV de salida para el detalle de columnas.
- `xlsx_{version}_{fecha}.json` — un registro con el resumen de la
  extracción. Ver §Registro JSON.

## Limitaciones actuales

- `--pdf`, `--preferir`, `--sincronizar`, `--csv-fuente` y `--csv-destino`
  son aceptados por el parser (incluida su validación de rutas), pero el
  modo correspondiente no hace nada todavía: la corrida termina sin error y
  sin generar ni CSV ni JSON. Si no estás seguro de qué modo vas a disparar,
  usá solo `--version`, `--xlsx` y `-o`.
- Para el modo `xlsx` que sí funciona, la herramienta exige:
  - `--version`, `--xlsx` y `-o`;
  - que `--xlsx` exista y sea un archivo (no un directorio);
  - que `-o`, si ya existe, sea un directorio.
- Si falta algo o una ruta no es válida en estos chequeos, el CLI corta con
  un mensaje de error puntual, sin traceback. Esto aplica solo a la
  validación de argumentos — un fallo interno durante la extracción (xlsx
  corrupto, hoja con nombre distinto al esperado, etc.) sí puede mostrar un
  traceback normal de Python.

## Documentación interna

_A partir de acá es referencia para quien toca el código de
`tools/canasta_inpc/`, no hace falta para usar la herramienta._

### Esquema del CSV de salida

El CSV final siempre tiene estas 15 columnas fijas, en este orden
(`COLUMNAS_BASE` en `tools/canasta_inpc/esquema.py`) — esto describe el
contrato final del pipeline completo; hoy, con solo el modo `xlsx`
implementado, varias columnas quedan vacías porque su única fuente posible
es `pdf` o `sync` (ver §Fuentes por columna y versión):

1. `generico`
2. `ponderador`
3. `encadenamiento`
4. `COG`
5. `CCIF division`
6. `CCIF grupo`
7. `CCIF clase`
8. `inflacion componente`
9. `inflacion subcomponente`
10. `inflacion agrupacion`
11. `SCIAN sector`
12. `SCIAN rama`
13. `durabilidad`
14. `canasta basica`
15. `canasta consumo minimo`

**Reglas generales** (no aplican a los encabezados):

- todo en minúsculas;
- sin acentos, salvo la ñ;
- sin signos de puntuación, espacios simples entre palabras (ni dobles, ni al
  inicio/final);
- si no hay información para una columna, el valor es un string vacío `""`;
- si el DataFrame trae columnas fuera de estas 15, `guardar_csv` las descarta
  e imprime una advertencia (no lanza excepción) — decisión deliberada, no
  se valida el esquema del lado de quien arma el DataFrame.

**Reglas por columna:**

| Columna(s) | Regla |
| --- | --- |
| `generico` | Reglas generales; solo se eliminan prefijos numéricos estructurales, nunca números que sean parte del nombre. |
| `ponderador`, `encadenamiento` | Se guardan en `str`, con todos los decimales tal cual vienen en el xlsx (sin redondear/truncar), punto decimal. |
| `COG`, `inflacion *`, `durabilidad` | Reglas generales + se elimina el prefijo numérico estructural (ej. `"01 alimentos"` → `"alimentos"`). |
| `CCIF *` | Reglas generales, sin eliminar el prefijo numérico en el contrato final (ej. `"01.1.1 alimentos ..."` se conserva tal cual) — **hoy, en el modo solo `xlsx`, `CCIF division` sale sin prefijo**, ver §Notas de la extracción solo `xlsx`. |
| `SCIAN *` | Reglas generales; código y nombre separados por un espacio simple. `SCIAN sector` inicia con código de 2 dígitos; `SCIAN rama` con código de exactamente 4 dígitos. |
| `canasta basica`, `canasta consumo minimo` | Categorías binarias, ver abajo. |

**Columnas binarias (`canasta basica`, `canasta consumo minimo`):**

- `"X"` si el genérico pertenece, `"-"` si no pertenece;
- se asume que no hay datos faltantes dentro de una columna con información
  (sin validación);
- `canasta consumo minimo` no tiene información antes de 2024, así que en
  2010/2013/2018 toda la columna es `""`.

### Fuentes por columna y versión

Para cada columna, en qué archivo(s) es *posible* encontrar el dato —no cuál
es la fuente final elegida cuando hay más de una opción; esa decisión ocurre
al cruzar `xlsx` y `pdf` y todavía no está implementada. Ver
`FUENTES_POSIBLES` en `tools/canasta_inpc/esquema.py`.

| columna | 2010 | 2013 | 2018 | 2024 |
| --- | --- | --- | --- | --- |
| `generico` | xlsx, pdf | xlsx, pdf | xlsx, pdf | xlsx, pdf |
| `ponderador` | xlsx, pdf | xlsx, pdf | xlsx, pdf | xlsx, pdf |
| `encadenamiento` | — | xlsx, pdf | — | xlsx |
| `COG` | xlsx, pdf | xlsx | xlsx, pdf | xlsx |
| `CCIF division` | pdf | xlsx, pdf | xlsx, pdf | xlsx, pdf |
| `CCIF grupo` | pdf | pdf | pdf | pdf |
| `CCIF clase` | pdf | pdf | pdf | pdf |
| `inflacion componente` | xlsx | xlsx | xlsx | xlsx |
| `inflacion subcomponente` | xlsx | xlsx | xlsx | xlsx |
| `inflacion agrupacion` | xlsx | xlsx | xlsx | xlsx |
| `SCIAN sector` | sync | pdf | pdf | pdf |
| `SCIAN rama` | sync | pdf | pdf | pdf |
| `durabilidad` | — | — | pdf | pdf |
| `canasta basica` | xlsx | xlsx | xlsx | xlsx |
| `canasta consumo minimo` | — | — | — | xlsx |

`sync` = se copia de otra versión ya generada (2013 → 2010, modo
`--sincronizar`). `—` = ninguna fuente, columna vacía.

### Hojas esperadas por versión

Referencia rápida para confirmar que el `xlsx` es el archivo oficial
correcto. Detalle de columnas/posiciones (implementación, no uso) vive en
`LAYOUTS_XLSX` (`esquema.py`), no acá.

| Versión | Hoja con genérico/ponderador (COG) | Hoja CCIF |
| --- | --- | --- |
| 2010 | `Ponderadores INPC INEGI` | no aplica (CCIF sale del pdf) |
| 2013 | `Ponderadores INPC INEGI` | `Ponderadores INPC COICOP INEGI` |
| 2018 | `Objeto de gasto` | `CCIF` |
| 2024 | `Objeto de gasto` | `CCIF` |

### Notas de la extracción solo `xlsx`

- `CCIF division` **siempre** queda sin prefijo numérico en este modo (aunque
  el xlsx de 2024 sí lo traiga) — el prefijo consistente en las 4 versiones
  lo deberá reponer `extraer_pdf.py` cuando exista, no la extracción de
  xlsx. Ver §Fuentes por columna y versión.

### Registro JSON (modo solo `xlsx`)

Cada corrida escribe `{salida}/xlsx_{version}_{YYYYMMDD_HHMMSS_ffffff}.json` además
del CSV (`escribir_registro_xlsx` en `tools/canasta_inpc/registro.py`):

| Campo | Contenido |
| --- | --- |
| `tipo` | Siempre `"xlsx"`. |
| `xlsx`, `csv` | Rutas de entrada/salida usadas en la corrida. |
| `version` | Versión de canasta. |
| `genericos` | Cantidad de genéricos extraídos. |
| `ponderadores`, `encadenamientos` | Cantidad con valor no vacío; `encadenamientos` es `null` en versiones sin esa columna (2010/2018). |
| `clasificaciones` | Por cada columna de clasificación presente (`COG`, `CCIF division`, `inflacion *`, `canasta *`): cuántos genéricos la tienen y qué categorías únicas aparecen. |
| `genericos_detalle` | Un `{generico, ponderador, [encadenamiento]}` por fila — útil para diffear entre corridas sin abrir el CSV. |

## Diseño futuro: PDF y sincronización

_Pendiente_ — módulos aún no reconstruidos (`extraer_pdf.py`, `matching.py`,
`resolver.py`, `sincronizar.py`). Lo de acá describe la intención del CLI,
no algo que hoy genere resultados.

### Parámetros previstos

| Parámetro | Aplica a | Descripción |
| --- | --- | --- |
| `--pdf` | extracción, opcional | Ruta al archivo pdf de anexos. |
| `--preferir {pdf,csv}` | extracción, requiere `--pdf` | Preferencia automática para resolver diferencias de nombre/clasificación entre `xlsx` y `pdf` — no aplica a diferencias de `ponderador`, esas solo se reportan (el valor final siempre queda el del `xlsx`). |
| `--sincronizar` | sincronización | Activa el modo de copia de SCIAN 2013 -> 2010. |
| `--csv-fuente` | sincronización | CSV de canasta 2013 ya generado (fuente). |
| `--csv-destino` | sincronización | CSV de canasta 2010 ya generado (destino, se sobrescribirá). |

El modo se decide por los flags presentes:

- **`--sincronizar`** presente -> modo sincronización.
- **`--pdf`** presente (sin `--sincronizar`) -> modo extracción `xlsx + pdf`.

### Validaciones ya activas para estos modos

Aunque los modos no hacen nada todavía, el parser ya valida sus argumentos:

En modo sincronización:

- `--csv-fuente` y `--csv-destino` (ambos) son obligatorios;
- `--csv-fuente` debe existir y ser un archivo (no un directorio);
- `--csv-destino` debe existir y ser un archivo (no un directorio).

En modo extracción con `--pdf`:

- `--pdf`, si se pasa, debe existir y ser un archivo;
- `--preferir` solo puede usarse junto con `--pdf`.

### Ejemplos de la sintaxis prevista (no generan salida todavía)

Extracción `xlsx` + `pdf`, con `--preferir` para evitar prompts interactivos:

```bash
python tools/generar_canasta.py --version 2018 --xlsx ruta/a/xlsx/2018.xlsx \
  --pdf ruta/a/pdf/anexo_2018.pdf --preferir pdf -o salida/
```

Cuando esté implementado, debería devolver un archivo `ponderadores_2018.csv`
en `salida/`, con las diferencias de nombre/clasificación resueltas a favor
de lo encontrado en el pdf, además de un JSON de registro con el resumen del
cruce y las diferencias encontradas.

Sincronización SCIAN 2013 → 2010:

```bash
python tools/generar_canasta.py --sincronizar \
  --csv-fuente salida/ponderadores_2013.csv \
  --csv-destino salida/ponderadores_2010.csv
```

Cuando esté implementado, debería sobrescribir las columnas `SCIAN sector` y
`SCIAN rama` de `ponderadores_2010.csv` (destino) con los valores de
`ponderadores_2013.csv` (fuente); sin generar ningún archivo nuevo ni JSON
de registro.
