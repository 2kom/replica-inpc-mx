# Uso de `tools/generar_canasta.py`

## Objetivo

`tools/generar_canasta.py` genera un archivo CSV que es la canasta intermedia
que usa este repo, esto a partir de archivos oficiales del INEGI. Es el paso
previo al cálculo: su salida es el insumo que recibe `Corrida.ejecutar()`.

Para obtener el xlsx y el PDF que necesita este script, ver
[guias/obtener_ponderadores.md](../guias/obtener_ponderadores.md).

La herramienta trabaja en tres modos:

1. Extraccion desde un archivo `.xlsx`.
2. Extraccion desde un archivo `.xlsx` + enriquecimiento/validacion con un archivo `.pdf` (Anexos del Documento metodologico INPC).
3. Sincronizacion de `SCIAN sector` y `SCIAN rama` desde la canasta 2013 hacia la 2010.

El resultado principal es un archivo `ponderadores_<version>.csv` con un esquema fijo de 15 columnas. En los modos de extraccion tambien se genera un JSON de registro con resumen, diferencias y warnings.

## Requisitos

- Ejecutar el comando desde la raiz del repo:

```bash
python tools/generar_canasta.py ...
```

- Python `>=3.10`.  
- Dependencias del proyecto mas las dependencias opcionales de herramientas:

```bash
pip install -e '.[tools]'
```

Eso instala, entre otras, las librerias que usa esta herramienta:

- `openpyxl`
- `pdfplumber`

## Sintaxis del CLI

```bash
python tools/generar_canasta.py [-h] [--version {2010,2013,2018,2024}] [--xlsx XLSX] \
                                [--pdf PDF] [-o SALIDA] [--preferir {pdf,csv}] \
                                [--sincronizar] [--csv-fuente CSV_FUENTE] \
                                [--csv-destino CSV_DESTINO]
```

## Modos de uso

### 1. Extraccion solo `xlsx`

Usa unicamente el archivo de ponderadores en `xlsx`.

```bash
python tools/generar_canasta.py --version 2018 --xlsx ruta/al/archivo.xlsx -o salida/
```

Este modo:

- extrae lo que la version puede leerse desde el `xlsx`;
- normaliza los textos;
- genera `salida/ponderadores_<version>.csv`;
- genera `salida/xlsx_<version>_<timestamp>.json`.

Las columnas cuya fuente sea `pdf` o `sync` quedan vacias.

### 2. Extraccion `xlsx` + `pdf`

Usa el `xlsx` como base y el `pdf` para enriquecer y validar clasificaciones.

```bash
python tools/generar_canasta.py --version 2018 --xlsx ruta/al/archivo.xlsx \
  --pdf ruta/al/anexo.pdf -o salida/
```

Si quieres evitar preguntas interactivas cuando haya diferencias entre ambas fuentes:

```bash
python tools/generar_canasta.py --version 2018 --xlsx ruta/al/archivo.xlsx \
  --pdf ruta/al/anexo.pdf --preferir pdf -o salida/
```

o

```bash
python tools/generar_canasta.py --version 2018 --xlsx ruta/al/archivo.xlsx \
  --pdf ruta/al/anexo.pdf --preferir csv -o salida/
```

Este modo:

- extrae `xlsx` y `pdf`;
- normaliza ambas fuentes;
- cruza por `generico` normalizado;
- compara `ponderador` con la precision visible del PDF;
- rellena automaticamente columnas cuya fuente oficial es `pdf`;
- registra diferencias, faltantes y warnings;
- genera `salida/ponderadores_<version>.csv`;
- genera `salida/pdf_<version>_<timestamp>.json`.

Notas importantes:

- `csv` en `--preferir csv` significa "conservar el valor actual de la salida base", que normalmente viene del `xlsx`.
- Si no pasas `--preferir`, la herramienta pregunta conflicto por conflicto.
- En la resolucion interactiva, `Enter` elige `pdf`.
- Las diferencias de `ponderador` no se resuelven automaticamente: se reportan, pero el valor final de `ponderador` sigue siendo el del `xlsx`.

### 3. Sincronizacion SCIAN 2013 -> 2010

Sobrescribe `SCIAN sector` y `SCIAN rama` del CSV 2010 usando como fuente el CSV 2013 ya generado.

```bash
python tools/generar_canasta.py --sincronizar \
  --csv-fuente salida/ponderadores_2013.csv \
  --csv-destino salida/ponderadores_2010.csv
```

Este modo:

- lee ambos CSV;
- valida que ambos tengan `generico`, `SCIAN sector` y `SCIAN rama`;
- valida que el CSV fuente tenga SCIAN completo;
- valida que no haya duplicados tras normalizar `generico`;
- valida que ambos archivos tengan exactamente el mismo conjunto de genericos;
- pide confirmacion explicita por stdin;
- sobrescribe en sitio `SCIAN sector` y `SCIAN rama` del archivo destino.

Notas importantes:

- Este modo no usa `--version`, `--xlsx`, `--pdf` ni `-o`.
- Este modo no genera JSON de registro.
- El archivo `--csv-destino` se reescribe en el mismo path.
- Si no hay stdin interactivo, la herramienta falla con `RuntimeError`.

Para automatizar la confirmacion:

```bash
printf 's\n' | python tools/generar_canasta.py --sincronizar \
  --csv-fuente salida/ponderadores_2013.csv \
  --csv-destino salida/ponderadores_2010.csv
```

## Parametros

| Parametro | Aplica a | Descripcion |
| --- | --- | --- |
| `--version` | extraccion | Version soportada: `2010`, `2013`, `2018`, `2024`. |
| `--xlsx` | extraccion | Ruta al archivo oficial de ponderadores en `xlsx`. |
| `--pdf` | extraccion opcional | Ruta al PDF de anexos/metodologia. |
| `-o` | extraccion | Directorio donde se escriben el CSV y el JSON. Se crea automaticamente si no existe. Ruta recomendada dentro del proyecto: `data/inputs/canastas/`. |
| `--preferir {pdf,csv}` | `xlsx + pdf` | Resuelve automaticamente diferencias de clasificacion entre ambas fuentes. |
| `--sincronizar` | sincronizacion | Activa el modo de copia de SCIAN 2013 -> 2010. |
| `--csv-fuente` | sincronizacion | CSV 2013 ya generado. |
| `--csv-destino` | sincronizacion | CSV 2010 ya generado y que sera sobrescrito. |

## Validaciones del CLI

### En extraccion

La herramienta exige:

- `--version`
- `--xlsx`
- `-o`

Ademas:

- `--version` solo acepta `2010`, `2013`, `2018`, `2024`;
- `--xlsx` debe existir;
- si se pasa `--pdf`, tambien debe existir `--xlsx`.

### En sincronizacion

La herramienta exige:

- `--sincronizar`
- `--csv-fuente`
- `--csv-destino`

Ademas:

- ambos archivos deben existir;
- ambos deben tener las columnas requeridas;
- el CSV fuente debe tener `SCIAN sector` y `SCIAN rama` completos en todos los genericos;
- los dos archivos deben tener el mismo conjunto de genericos tras normalizacion.

## Archivos generados

### Modo `xlsx`

- CSV final:

```text
<salida>/ponderadores_<version>.csv
```

- Registro JSON:

```text
<salida>/xlsx_<version>_<YYYYMMDD_HHMMSS>.json
```

### Modo `xlsx + pdf`

- CSV final:

```text
<salida>/ponderadores_<version>.csv
```

- Registro JSON:

```text
<salida>/pdf_<version>_<YYYYMMDD_HHMMSS>.json
```

### Modo `--sincronizar`

- Reescribe:

```text
<csv-destino>
```

- No genera JSON.

## Esquema fijo del CSV de salida

Sin importar la version o el modo, el CSV final siempre se escribe con estas 15 columnas y en este orden:

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

Si alguna columna no existe en el DataFrame intermedio, `escribir.py` la crea vacia antes de escribir el CSV.

## Significado de las columnas

| Columna | Contenido |
| --- | --- |
| `generico` | Nombre normalizado del generico. |
| `ponderador` | Ponderador del generico tal como viene del `xlsx`. |
| `encadenamiento` | Factor de encadenamiento. Solo se llena en 2013 y 2024. |
| `COG` | Clasificacion por objeto del gasto. |
| `CCIF division` | Clasificacion de Consumo por Finalidades Division. |
| `CCIF grupo` | Clasificacion de Consumo por Finalidades Grupo. |
| `CCIF clase` | Clasificacion de Consumo por Finalidades Clase. |
| `inflacion componente` | Componentes de inflacion. |
| `inflacion subcomponente` | Subcomponentes de inflacion. |
| `inflacion agrupacion` | Agrupaciones de inflacion. |
| `SCIAN sector` | Sector SCIAN. Conserva el codigo al inicio. |
| `SCIAN rama` | Rama SCIAN. Conserva el codigo al inicio. |
| `durabilidad` | Categoria de durabilidad. Solo se llena en 2018 y 2024 cuando se usa `pdf`. |
| `canasta basica` | `X` si pertenece, vacio si no. |
| `canasta consumo minimo` | `X` si pertenece, vacio si no. Solo aplica en 2024. |

## Normalizacion de texto

Antes de escribir el CSV final, la herramienta normaliza textos con estas reglas:

- convierte a minusculas;
- colapsa espacios repetidos;
- quita tildes vocalicas;
- conserva la enie;
- elimina prefijos numericos del inicio en la mayoria de columnas de texto, por ejemplo `1.`, `01-`, `2)`.

Excepciones:

- `ponderador` no se normaliza;
- `encadenamiento` no se normaliza;
- `canasta basica` no se normaliza;
- `canasta consumo minimo` no se normaliza;
- `SCIAN sector` y `SCIAN rama` conservan su prefijo/codigo numerico.

Consecuencia practica:

- los textos del CSV final quedan en minusculas;
- `CCIF division`, `CCIF grupo`, `CCIF clase`, `COG` y categorias de inflacion salen normalizadas;
- `SCIAN sector` y `SCIAN rama` salen normalizadas, pero con codigo al inicio;
- las marcas de pertenencia salen como `X` o vacio.

## Versiones soportadas

### 2010

Referencia del proyecto: `283` genericos.

Hojas `xlsx` esperadas:

- `Ponderadores INPC INEGI`

Fuente por columna:

- Desde `xlsx`: `generico`, `ponderador`, `COG`, `inflacion componente`, `inflacion subcomponente`, `inflacion agrupacion`, `canasta basica`
- Desde `pdf`: `CCIF division`, `CCIF grupo`, `CCIF clase`
- Desde `sync`: `SCIAN sector`, `SCIAN rama`

Columnas que quedan vacias en el CSV final:

- `encadenamiento`
- `durabilidad`
- `canasta consumo minimo`

Flujo recomendado:

1. Generar 2013 con `xlsx + pdf`.
2. Generar 2010 con `xlsx + pdf`.
3. Ejecutar `--sincronizar` para copiar SCIAN 2013 -> 2010.

Ejemplo:

```bash
python tools/generar_canasta.py --version 2010 --xlsx tools/test/2010.xlsx \
  --pdf tools/test/anexo_2010.pdf --preferir pdf -o salida/
```

### 2013

Referencia del proyecto: `283` genericos.

Hojas `xlsx` esperadas:

- `Ponderadores INPC INEGI`
- `Ponderadores INPC COICOP INEGI`

Fuente por columna:

- Desde `xlsx`: `generico`, `ponderador`, `encadenamiento`, `COG`, `CCIF division`, `inflacion componente`, `inflacion subcomponente`, `inflacion agrupacion`, `canasta basica`
- Desde `pdf`: `CCIF grupo`, `CCIF clase`, `SCIAN sector`, `SCIAN rama`

Columnas que quedan vacias en el CSV final:

- `durabilidad`
- `canasta consumo minimo`

Ejemplo:

```bash
python tools/generar_canasta.py --version 2013 --xlsx tools/test/2013.xlsx \
  --pdf tools/test/anexo_2013.pdf --preferir pdf -o salida/
```

### 2018

Referencia del proyecto: `299` genericos.

Hojas `xlsx` esperadas:

- `Objeto de gasto`
- `CCIF`

Fuente por columna:

- Desde `xlsx`: `generico`, `ponderador`, `COG`, `CCIF division`, `inflacion componente`, `inflacion subcomponente`, `inflacion agrupacion`, `canasta basica`
- Desde `pdf`: `CCIF grupo`, `CCIF clase`, `SCIAN sector`, `SCIAN rama`, `durabilidad`

Columnas que quedan vacias en el CSV final:

- `encadenamiento`
- `canasta consumo minimo`

Nota:

- El parser PDF 2018 tambien puede extraer `COG`, pero la fuente configurada para el CSV final sigue siendo el `xlsx`. Ese valor del `pdf` sirve sobre todo para contraste y deteccion de diferencias.

Ejemplo:

```bash
python tools/generar_canasta.py --version 2018 --xlsx tools/test/2018.xlsx \
  --pdf tools/test/anexo_2018.pdf --preferir pdf -o salida/
```

### 2024

Referencia del proyecto: `292` genericos.

Hojas `xlsx` esperadas:

- `Objeto de gasto`
- `CCIF`

Fuente por columna:

- Desde `xlsx`: `generico`, `ponderador`, `encadenamiento`, `COG`, `CCIF division`, `inflacion componente`, `inflacion subcomponente`, `inflacion agrupacion`, `canasta basica`, `canasta consumo minimo`
- Desde `pdf`: `CCIF grupo`, `CCIF clase`, `SCIAN sector`, `SCIAN rama`, `durabilidad`

Ejemplo:

```bash
python tools/generar_canasta.py --version 2024 --xlsx tools/test/2024.xlsx \
  --pdf tools/test/anexo_2024.pdf --preferir pdf -o salida/
```

### Resumen de fuentes por version y columna

| columna                  | 2010 | 2013 | 2018 | 2024 |
| ------------------------ | ---- | ---- | ---- | ---- |
| generico                 | xlsx | xlsx | xlsx | xlsx |
| ponderador               | xlsx | xlsx | xlsx | xlsx |
| encadenamiento           |  —   | xlsx |  —   | xlsx |
| COG                      | xlsx | xlsx | xlsx | xlsx |
| CCIF division            | pdf  | xlsx | xlsx | xlsx |
| CCIF grupo               | pdf  | pdf  | pdf  | pdf  |
| CCIF clase               | pdf  | pdf  | pdf  | pdf  |
| inflacion componente     | xlsx | xlsx | xlsx | xlsx |
| inflacion subcomponente  | xlsx | xlsx | xlsx | xlsx |
| inflacion agrupacion     | xlsx | xlsx | xlsx | xlsx |
| SCIAN sector             | sync | pdf  | pdf  | pdf  |
| SCIAN rama               | sync | pdf  | pdf  | pdf  |
| durabilidad              |  —   |  —   | pdf  | pdf  |
| canasta basica           | xlsx | xlsx | xlsx | xlsx |
| canasta consumo minimo   |  —   |  —   |  —   | xlsx |

xlsx = se extrae del archivo xlsx\
pdf  = se extrae del archivo pdf\
sync = se copia de otra version (2013 -> 2010 via --sincronizar)\
—    = sin fuente, columna queda vacia

## Como cruza `xlsx` y `pdf`

El cruce se hace por `generico` ya normalizado. No hay fuzzy matching ni reglas manuales en este paso.

Cuando un generico existe en ambos:

- si una columna cuya fuente es `pdf` viene vacia en la base y con valor en el `pdf`, la herramienta la llena automaticamente;
- si una clasificacion existe en ambas fuentes y el valor coincide, solo queda registrada como comprobada;
- si una clasificacion existe en ambas fuentes y el valor difiere, se marca como conflicto y se resuelve con `--preferir` o interactivamente.

Cuando un generico no hace match:

- si esta en `xlsx` pero no en `pdf`, la fila permanece en la salida y se registra un warning;
- si esta en `pdf` pero no en `xlsx`, no se agrega a la salida y se registra un warning.

## Comparacion de ponderadores

En modo `xlsx + pdf`, la herramienta compara `ponderador` del `xlsx` contra el `ponderador` extraido del `pdf`.

La precision usada es:

- `2010`: 4 decimales
- `2013`: 5 decimales
- `2018`: 4 decimales
- `2024`: 4 decimales

Si no coinciden:

- se registra la diferencia en el JSON y en los warnings de consola;
- no se reemplaza automaticamente el `ponderador` del `xlsx`.

## Salida por consola

En los modos de extraccion la herramienta imprime un resumen con:

- version;
- numero de genericos extraidos;
- cantidad de encadenamientos, cuando aplica;
- resumen por clasificacion;
- rutas del CSV y del JSON.

En modo `xlsx + pdf` tambien puede imprimir warnings por:

- genericos del `xlsx` sin match en `pdf`;
- genericos del `pdf` sin match en `xlsx`;
- `ponderador` no coincidente;
- falla en `validacion_conteo`.

En modo `--sincronizar` imprime:

- archivo fuente;
- archivo destino;
- cantidad de genericos sincronizados;
- cantidad de celdas SCIAN actualizadas.

## Recomendaciones operativas

- Usa los archivos oficiales del INEGI correspondientes exactamente a la version que quieres generar.
- Corre el comando desde la raiz del repo.
- En automatizacion o CI, usa `--preferir pdf` o `--preferir csv` para evitar prompts interactivos.
- Para 2010, no des por terminada la salida hasta correr `--sincronizar` con el CSV 2013.
- Haz respaldo del CSV destino antes de sincronizar, porque se sobrescribe en el mismo path.
- Si el `pdf` es escaneado, no tiene texto seleccionable o cambia mucho de formato respecto al documento esperado, `pdfplumber` puede no extraer bien y el flujo puede fallar o producir muchos warnings.

## Troubleshooting rapido

### Error: `--version es obligatorio para extraccion`

Falta `--version` en un modo de extraccion.

### Error: `--xlsx es obligatorio para extraccion`

Falta `--xlsx` en un modo de extraccion.

### Error: `-o es obligatorio para extraccion`

Falta el directorio de salida en un modo de extraccion.

### Error: `No se encontro --xlsx` o `No se encontro --pdf`

La ruta no existe o no corresponde al archivo esperado.

### La herramienta pregunta por cada diferencia

Eso es normal cuando usas `xlsx + pdf` sin `--preferir`.

### Error en sincronizacion por stdin

`--sincronizar` requiere confirmacion. Si lo ejecutas sin stdin interactivo, usa:

```bash
printf 's\n' | python tools/generar_canasta.py --sincronizar \
  --csv-fuente salida/ponderadores_2013.csv \
  --csv-destino salida/ponderadores_2010.csv
```

### Error por genericos duplicados tras normalizar

Dos filas distintas terminan con el mismo `generico` una vez normalizado. Hay que corregir el insumo antes de sincronizar.

### Muchos `sin_match_pdf` o `sin_match_xlsx`

Normalmente indica uno de estos problemas:

- el `pdf` no corresponde a la version del `xlsx`;
- el `pdf` no es el anexo esperado;
- el parser encontro cambios de formato que rompen la extraccion;
- el documento fuente no es el oficial o fue alterado.

---

## Flujo interno por modo

### Extraccion solo `xlsx`

1. `extraer_xlsx.py` lee el `xlsx` segun el layout de la version.
2. `normalizar.py` normaliza `generico` y clasificaciones de texto.
3. `escribir.py` genera el CSV final de 15 columnas fijas.
4. `registro.py` genera el JSON de registro tipo `xlsx`.

### Extraccion `xlsx` + `pdf`

1. `extraer_xlsx.py` extrae la base desde el `xlsx`.
2. `extraer_pdf.py` extrae clasificaciones complementarias desde el `pdf`.
3. `normalizar.py` normaliza ambas fuentes.
4. `matching.py` cruza por `generico`, verifica `ponderador` y detecta diferencias.
5. `resolver.py` decide que valor conservar cuando hay conflicto.
6. `escribir.py` genera el CSV final.
7. `registro.py` genera el JSON de registro tipo `pdf`.

### Sincronizacion SCIAN

1. `sincronizar.py` lee ambos CSV.
2. Valida columnas, duplicados, completitud de SCIAN y correspondencia de genericos.
3. Pide confirmacion.
4. Sobrescribe `SCIAN sector` y `SCIAN rama` del destino.
5. Reescribe el CSV destino con el esquema fijo.

## Registro JSON

### Registro tipo `xlsx`

Se genera en extraccion solo `xlsx` y contiene, entre otros:

- `tipo`
- `xlsx`
- `csv`
- `version`
- `genericos`
- `ponderadores`
- `encadenamientos`
- `clasificaciones`
- `genericos_detalle`

### Registro tipo `pdf`

Se genera en extraccion `xlsx + pdf` y contiene, ademas de lo anterior:

- `pdf`
- `columnas_enriquecidas`
- `columnas_compartidas`
- `enriquecimiento`
- `sin_match_pdf`
- `sin_match_xlsx`
- `ponderador_no_coincide`
- `agregaciones`
- `diferencias_resueltas`
- `validacion_conteo`

`validacion_conteo` verifica que todas las columnas cuya fuente es `pdf` hayan quedado pobladas para todos los genericos esperados del CSV final. Si falla, la consola imprime warning.
