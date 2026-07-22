# Uso de `tools/generar_canasta.py`

## Objetivo

Genera una canasta intermedia en CSV, utilizada después para construir la
canasta canónica del cálculo del INPC.

## Estado actual

El **modo de extracción `xlsx`** (sin `pdf`) funciona de punta a punta para
las 4 versiones. El **modo `xlsx + pdf`** (`--pdf`) funciona también para las
**4 versiones**: `extraccion_pdf.py` tiene implementadas `_extraer_2010`,
`_extraer_2013`, `_extraer_2018` y `_extraer_2024`. En **2010**, `SCIAN
sector`/`SCIAN rama` quedan vacíos aunque se use `--pdf` (el pdf 2010 no trae
SCIAN; `FUENTES_POSIBLES` los marca como `sync`, se llenan solo con
`--sincronizar`, todavía sin cuerpo). El modo `xlsx + pdf`
tampoco escribe registro JSON aún (solo el CSV), a diferencia del modo
`xlsx` solo. El modo `--sincronizar` (`_ejecutar_sincronizacion`) sigue sin
cuerpo. Ver §Cruce `xlsx` + `pdf` y §Diseño futuro: sincronización.

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

Para la extracción de `pdf` (ver §Cruce `xlsx` + `pdf`) hace falta además `pdftotext`,
que **no se instala vía `pip`** — no hay wheel precompilado en PyPI para
Windows/Mac, solo código fuente que requiere compilar contra `poppler-cpp`.
Se instala vía `conda-forge`, que sí trae binarios listos para Linux/Windows/Mac:

```bash
conda install -c conda-forge pdftotext
```

## Comando funcional

Extracción solo `xlsx`, cualquier versión:

```bash
python tools/generar_canasta.py --version 2018 --xlsx ruta/a/xlsx/2018.xlsx -o salida/
```

Extracción `xlsx + pdf`, cualquier versión:

```bash
python tools/generar_canasta.py --version 2013 --xlsx ruta/a/xlsx/2013.xlsx \
  --pdf ruta/al/manual/completo/2013.pdf -o salida/
```

Con `--preferir {pdf,xlsx}` se salta las preguntas interactivas del cruce y
resuelve todas las discrepancias automático hacia esa fuente. Sin
`--preferir`, cada discrepancia real se pregunta en consola (Enter = `pdf`).
Ver §Cruce `xlsx` + `pdf` para el detalle del algoritmo.

### Parámetros

| Parámetro | Descripción |
| --- | --- |
| `--version` | Versión de canasta a extraer: `2010`, `2013`, `2018`, `2024`. Con `--pdf`, las 4 funcionan. |
| `--xlsx` | Ruta al archivo xlsx de ponderadores. |
| `--pdf` | Opcional. Ruta al **manual completo** de INEGI (no al anexo pre-recortado) — `extraccion_pdf.py` lee un rango de páginas directo del manual. |
| `--preferir {pdf,xlsx}` | Opcional, requiere `--pdf`. Preferencia automática para resolver discrepancias del cruce, sin preguntar en consola. |
| `-o` | Directorio de salida para el CSV (y el registro JSON, solo en modo `xlsx` sin `pdf` — ver §Estado actual). Se crea automáticamente si no existe. |

### Archivos generados

Modo `xlsx` (sin `pdf`) deja en `salida/`:

- `ponderadores_{version}.csv` — la canasta intermedia. Ver §Esquema del
  CSV de salida para el detalle de columnas.
- `xlsx_{version}_{fecha}.json` — un registro con el resumen de la
  extracción. Ver §Registro JSON.

Modo `xlsx + pdf` deja solo `ponderadores_{version}.csv` — sin JSON de
registro todavía (pendiente).

## Limitaciones actuales

- Con `--version 2010 --pdf`, `SCIAN sector`/`SCIAN rama` quedan vacíos
  igual (el pdf 2010 no trae Anexo SCIAN; esas columnas dependen de
  `--sincronizar`, todavía sin cuerpo).
- `--sincronizar`, `--csv-fuente` y `--csv-destino` son aceptados por el
  parser (incluida su validación de rutas), pero `_ejecutar_sincronizacion`
  no tiene cuerpo: la corrida termina sin error y sin generar nada.
- El modo `xlsx + pdf` no escribe registro JSON (a diferencia del modo
  `xlsx` solo).
- El cruce (`match.py`) asume que `df_xlsx` y `df_pdf` tienen el mismo largo
  y que, tras ordenar cada uno por `generico`, la fila `i` de uno corresponde
  a la fila `i` del otro — sin verificarlo. Esto vale porque en teoría el
  texto de `generico` es el mismo entre `xlsx` y `pdf` (confirmado con datos
  reales de 2013: 283/283 idénticos tras ordenar; también verificado en 2018:
  299/299 y en 2024: 292/292); si algún genérico divergiera en texto entre
  ambas fuentes, el orden alfabético podría desalinear filas sin que el
  cruce lo detecte.
- Para el modo `xlsx` solo, la herramienta exige:
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
al cruzar `xlsx` y `pdf` (`match.py`, ver §Cruce `xlsx` + `pdf`, las 4
versiones). Ver `FUENTES_POSIBLES` en `tools/canasta_inpc/esquema.py`.

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
  el xlsx de 2024 sí lo traiga) — el prefijo consistente en las 4 versiones lo
  repone `extraccion_pdf.py`, no la extracción de xlsx. Ver §Fuentes por
  columna y versión, §Cruce `xlsx` + `pdf`.

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

## Cruce `xlsx` + `pdf`

Implementado en `tools/canasta_inpc/match.py` (`match_dfs`), disparado por
`_ejecutar_xlsx_pdf` cuando se pasa `--pdf`. Hoy produce resultado real con
las 4 versiones.

### Algoritmo

1. Se alinean `df_xlsx` y `df_pdf` ordenando ambos por `generico` — se asume
   mismo largo y correspondencia fila a fila tras ordenar (ver nota de
   §Limitaciones actuales sobre este supuesto).
2. Se recorre columna por columna, en el orden de `COLUMNAS_BASE`. Para cada
   columna, `FUENTES_POSIBLES[version]` dice cuántas fuentes hay que cruzar:
   - **ambas fuentes** → se compara (grupo A o B, ver abajo);
   - **una sola fuente** → se copia esa columna directo, sin comparar;
   - **ninguna** (o solo `sync`, que no participa de este cruce) → columna
     vacía.
3. **Grupo A — fila por fila** (`generico`, `ponderador`, `encadenamiento`):
   se compara cada fila individual. Si coincide, no hay nada que resolver.
   Para `ponderador`/`encadenamiento`, una discrepancia dentro de la
   tolerancia de redondeo (los decimales de la fuente menos precisa caben en
   los de la más precisa) se resuelve sola, quedándose con el valor de mayor
   precisión, sin preguntar. Una discrepancia real se resuelve fila por
   fila, una por una.
4. **Grupo B — categórica, agrupada por par único** (`COG`, `CCIF
   division/grupo/clase`, `inflacion componente/subcomponente/agrupacion`,
   `SCIAN sector/rama`, `durabilidad`, `canasta basica`, `canasta consumo
   minimo`): las discrepancias se agrupan por el par único
   `(valor_xlsx, valor_pdf)` — si 5 genéricos comparten el mismo par (ej. el
   caso real de 2018, `"ropa y calzado"` vs `"prendas de vestir y calzado"`
   en `CCIF division`, 29 filas), se resuelve una sola vez, no 29.
5. Cada discrepancia real (grupo A o B) se resuelve con `--preferir` si vino
   el flag (sin preguntar), o si no, con un prompt en consola — Enter u
   otra respuesta no reconocida = `pdf`.

### `--preferir`

`--preferir pdf` o `--preferir xlsx` salta todos los prompts y resuelve
automático hacia esa fuente — aplica igual a **todas** las columnas
cruzadas, incluido `ponderador`/
`encadenamiento` (no hay excepción: una discrepancia numérica real sigue el
mismo `--preferir` que el resto, solo la tolerancia de redondeo se resuelve
aparte, sin consultar `--preferir`).

### Pendiente

- `resolver.py` no existe como archivo aparte — su responsabilidad (resolver
  discrepancias) ya vive dentro de `match.py`.
- Sin registro JSON para este modo (ver §Estado actual).

## Diseño futuro: sincronización

_Pendiente_ — `sincronizar.py` no existe todavía. Lo de acá describe la
intención del CLI para `--sincronizar`, no algo que hoy genere resultados.

### Parámetros previstos (sincronización)

| Parámetro | Descripción |
| --- | --- |
| `--sincronizar` | Activa el modo de copia de SCIAN 2013 -> 2010. |
| `--csv-fuente` | CSV de canasta 2013 ya generado (fuente). |
| `--csv-destino` | CSV de canasta 2010 ya generado (destino, se sobrescribirá). |

El modo se decide por los flags presentes: **`--sincronizar`** presente ->
modo sincronización (tiene prioridad sobre `--pdf` si ambos se pasan).

### Validaciones ya activas

Aunque el modo no hace nada todavía, el parser ya valida sus argumentos:

- `--csv-fuente` y `--csv-destino` (ambos) son obligatorios;
- `--csv-fuente` debe existir y ser un archivo (no un directorio);
- `--csv-destino` debe existir y ser un archivo (no un directorio).

### Ejemplo de la sintaxis prevista (no genera salida todavía)

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
