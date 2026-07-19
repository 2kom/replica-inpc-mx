# Uso de `tools/generar_canasta.py`

## Objetivo

`tools/generar_canasta.py` genera un archivo CSV que es la canasta intermedia que luego se utilizara para la canasta canonica que es con la que se haran los calculos

## Requisitos

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
- `pdfplumber`

## Cómo se usa esta herramienta?

### Sintaxis

```bash
python tools/generar_canasta.py [-h] [--version {2010,2013,2018,2024}] [--xlsx XLSX] \
                                [--pdf PDF] [-o SALIDA] [--preferir {pdf,csv}] \
                                [--sincronizar] [--csv-fuente CSV_FUENTE] \
                                [--csv-destino CSV_DESTINO]
```

### Parámetros

| Parámetro | Aplica a | Descripción |
| --- | --- | --- |
| `--version` | extracción | Versión de canasta a extraer: `2010`, `2013`, `2018`, `2024`. |
| `--xlsx` | extracción | Ruta al archivo xlsx de ponderadores. |
| `--pdf` | extracción, opcional | Ruta al archivo pdf de anexos. |
| `-o` | extracción | Directorio de salida para el CSV y el registro JSON. Se crea automáticamente si no existe. |
| `--preferir {pdf,csv}` | extracción, requiere `--pdf` | Preferencia automática para resolver diferencias de nombre/clasificación entre `xlsx` y `pdf` — no aplica a diferencias de `ponderador`, esas solo se reportan (el valor final siempre queda el del `xlsx`). |
| `--sincronizar` | sincronización | Activa el modo de copia de SCIAN 2013 -> 2010. |
| `--csv-fuente` | sincronización | CSV de canasta 2013 ya generado (fuente). |
| `--csv-destino` | sincronización | CSV de canasta 2010 ya generado (destino, se sobrescribe). |

### Modos

El modo se decide por los flags presentes:

- **`--sincronizar`** presente -> modo sincronización.
- **`--pdf`** presente (sin `--sincronizar`) -> modo extracción `xlsx + pdf`.
- Si no -> modo extracción solo `xlsx`.

### Validaciones

En modo sincronización, la herramienta exige:

- `--csv-fuente` y `--csv-destino` (ambos);
- que `--csv-fuente` exista y sea un archivo (no un directorio);
- que `--csv-destino` exista y sea un archivo (no un directorio).

En modo extracción, la herramienta exige:

- `--version`, `--xlsx` y `-o`;
- que `--xlsx` exista y sea un archivo;
- que `-o`, si ya existe, sea un directorio;
- que `--pdf`, si se pasa, exista y sea un archivo;
- que `--preferir` solo se use junto con `--pdf`.

Si falta algo o una ruta no es válida, el CLI corta con un mensaje de error puntual (no lanza traceback).

### Ejemplos

Extracción solo `xlsx`:

```bash
python tools/generar_canasta.py --version 2018 --xlsx ruta/a/xlsx/2018.xlsx -o salida/
```

Nos devuelve un archivo `ponderadores_2018.csv` en `salida/`, además de un JSON de registro con el resumen de la extracción.

Extracción `xlsx` + `pdf`, con `--preferir` para evitar prompts interactivos:

```bash
python tools/generar_canasta.py --version 2018 --xlsx ruta/a/xlsx/2018.xlsx \
  --pdf ruta/a/pdf/anexo_2018.pdf --preferir pdf -o salida/
```

Nos devuelve un archivo `ponderadores_2018.csv` en `salida/`, con las diferencias de nombre/clasificación resueltas a favor de lo encontrado en el pdf, además de un JSON de registro con el resumen del cruce y las diferencias encontradas.

Sincronización SCIAN 2013 → 2010:

```bash
python tools/generar_canasta.py --sincronizar \
  --csv-fuente salida/ponderadores_2013.csv \
  --csv-destino salida/ponderadores_2010.csv
```

Sobrescribe las columnas `SCIAN sector` y `SCIAN rama` de `ponderadores_2010.csv` (destino) con los valores de `ponderadores_2013.csv` (fuente); no genera ningún archivo nuevo ni JSON de registro.

## Documentación de la herramienta

Pendiente — se completa a medida que se reconstruye cada módulo (ver
`tools/canasta_inpc/`). Hoy `esquema.py` está implementado; el resto de la
lógica de extracción/cruce/registro todavía no.

### Esquema del CSV de salida

Sin importar la versión o el modo, el CSV final siempre tiene estas 15
columnas fijas, en este orden (`COLUMNAS_BASE` en
`tools/canasta_inpc/esquema.py`):

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
- si no hay información para una columna, el valor es un string vacío `""`.

**Reglas por columna:**

| Columna(s) | Regla |
| --- | --- |
| `generico` | Reglas generales; solo se eliminan prefijos numéricos estructurales, nunca números que sean parte del nombre. |
| `ponderador`, `encadenamiento` | Se guardan en `str`, con todos los decimales tal cual vienen en el xlsx (sin redondear/truncar), punto decimal. |
| `COG`, `inflacion *`, `durabilidad` | Reglas generales + se elimina el prefijo numérico estructural (ej. `"01 alimentos"` → `"alimentos"`). |
| `CCIF *` | Reglas generales, sin eliminar el prefijo numérico (ej. `"01.1.1 alimentos ..."` se conserva tal cual). |
| `SCIAN *` | Reglas generales; código y nombre separados por un espacio simple. `SCIAN sector` inicia con código de 2 dígitos; `SCIAN rama` con código de exactamente 4 dígitos. |
| `canasta basica`, `canasta consumo minimo` | Categorías binarias, ver abajo. |

**Columnas binarias (`canasta basica`, `canasta consumo minimo`):**

- `"x"` si el genérico pertenece, `"-"` si no pertenece;
- si la columna tiene información, todas sus filas deben ser exclusivamente
  `"x"` o `"-"` — no se permiten strings vacíos;
- si no hay información para la columna completa, es un error, salvo la
  excepción conocida: `canasta consumo minimo` no tiene información antes de
  2024, así que en 2010/2013/2018 toda la columna es `""`.

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

### Modos de extracción, cruce xlsx+pdf, sincronización SCIAN, registro JSON

_Pendiente_ — módulos aún no reconstruidos (`extraccion_xlsx.py`,
`extraer_pdf.py`, `matching.py`, `resolver.py`, `sincronizar.py`,
`escribir.py`, `registro.py`).
