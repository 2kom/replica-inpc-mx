# Obtener ponderadores — INPC 2010, 2013, 2018 y 2024

> Las capturas de pantalla de esta guía corresponden al sitio del INEGI
> (inegi.org.mx) y se incluyen únicamente con fines ilustrativos.

Los ponderadores son dos archivos: un **xlsx** con la estructura de ponderaciones
y el **documento metodológico completo** en PDF (no hace falta recortarlo —
`tools/generar_canasta.py` lee directo el rango de páginas que necesita).
Ambos se usan como entrada de `tools/generar_canasta.py` para generar la
canasta intermedia.

Esta guía cubre la descarga para las canastas 2010, 2013, 2018 y 2024 — 2010
y 2013 comparten la interfaz de 2018 en el sitio del INEGI (sección
Históricas), con las variantes indicadas en cada paso.

---

## INPC 2010, 2013 y 2018

### 1. Ir a la página del programa INPC 2018

Misma URL de partida que para las series:

```text
https://www.inegi.org.mx/programas/inpc/2018/
```

Ruta equivalente en el sitio del INEGI:

> Inicio -> Programas de Información -> Históricas -> Índices de Precios ->
> Índice Nacional de Precios al Consumidor (INPC) -> Base 2ª Quincena Julio 2018

![Página del programa INPC 2018 en el sitio del INEGI](img/series_01_programa.png)

> Para **2010** y **2013** se sigue la misma ruta, cambiando solo el último
> paso: en vez de **Base 2ª Quincena Julio 2018**, es **Base 2ª Quincena
> Diciembre 2010** (2010 y 2013 comparten esa misma base publicada por el
> INEGI, previa al cambio de base de 2018).

### 2. Descargar el xlsx

En la pestaña **Documentación**, expandir la sección **Ponderadores del INPC**
y descargar el archivo XLSX de:

> **Por Objeto del Gasto. Nacional Por Genérico. 2ª Quincena Julio 2018 = 100**

> Para **2010** y **2013** la interfaz es distinta a la de 2018: no hay una
> sección "Ponderadores del INPC" aparte — el xlsx vive junto con el PDF
> metodológico, dentro de una sola sección expandible **"INPC base
> diciembre 2010=100"** en la pestaña **Documentación**. Ahí se llama
> **"Ponderadores con la ENIGH 2010 y factores de encadenamiento del INPC"**.

### 3. Descargar el documento metodológico

En la misma pestaña, expandir la sección **Metodología** y hacer clic en
**Documento Metodológico INPC**.

![Secciones Ponderadores del INPC y Metodología en la pestaña Documentación](img/ponderadores_02_seccion_documentacion.png)

En la página de la publicación, hacer clic en el botón **PDF** y descargar
el archivo.

![Página de la publicación del Documento Metodológico INPC](img/ponderadores_03_publicacion.png)

> Para **2010** y **2013**, el PDF está en esa misma sección **"INPC base
> diciembre 2010=100"** (no en una sección "Metodología" separada),
> etiquetado **"Documento metodológico INPC con ponderadores de la ENIGH
> 2010"** — se descarga directo con el botón **PDF**, sin pasar por una
> página de publicación aparte.

### 4. Dónde colocar los archivos

No hay una ruta obligatoria — las rutas se pasan como argumentos al script.
Se recomienda colocarlos en:

```text
data/inputs/canastas/
```

### 5. Siguiente paso

Con el xlsx y el documento metodológico completo (PDF) listos, ejecutar
`generar_canasta.py` — no hace falta recortar el PDF, `--pdf` recibe el
manual completo tal cual se descargó:

```bash
python tools/generar_canasta.py --version 2018 \
  --xlsx data/inputs/canastas/ponderadores_2018.xlsx \
  --pdf data/inputs/canastas/manual_2018.pdf \
  --preferir pdf \
  -o data/inputs/canastas/
```

> Se usa `--preferir pdf` porque existe al menos una diferencia conocida entre
> ambas fuentes: la división CCIF aparece como **"Ropa y calzado"** en el xlsx
> y como **"Prendas de Vestir y Calzado"** en el manual. Se asume que el manual
> es la fuente correcta. Sin `--preferir pdf`, el script preguntará
> interactivamente qué valor conservar en cada conflicto detectado.

Ver [tools/uso_generar_canasta.md](../tools/uso_generar_canasta.md) para el
detalle completo del script.

---

## INPC 2024

### 1. Ir a la página del programa INPC 2024

Misma URL de partida que para las series 2024:

```text
https://www.inegi.org.mx/programas/inpc/2018a/
```

Ruta equivalente en el sitio del INEGI:

> Inicio -> Programas de Información -> Índices de Precios ->
> Índice Nacional de Precios al Consumidor (INPC)

![Página del programa INPC 2024 en el sitio del INEGI](img/series_06_programa.png)

### 2. Descargar el xlsx (2024)

En la pestaña **Documentación**, expandir las secciones correspondientes.

![Secciones Ponderadores del INPC y Metodología en la pestaña Documentación](img/ponderadores_06_seccion_documentacion.png)

Para el **xlsx**: descargar el archivo de ponderadores por Objeto del Gasto, nacional por genérico, base segunda quincena julio 2018 = 100.

### 3. Descargar el documento metodológico (2024)

En la misma pestaña, hacer clic en **Documento Metodológico INPC**.

![Página de la publicación del Documento Metodológico INPC 2024](img/ponderadores_07_publicacion.png)

En la página de la publicación, hacer clic en el botón **PDF** y descargar el archivo.

### 4. Dónde colocar los archivos (2024)

No hay una ruta obligatoria — las rutas se pasan como argumentos al script.
Se recomienda colocarlos en:

```text
data/inputs/canastas/
```

### 5. Siguiente paso (2024)

Con el xlsx y el documento metodológico completo (PDF) listos, ejecutar
`generar_canasta.py` — no hace falta recortar el PDF, `--pdf` recibe el
manual completo tal cual se descargó:

```bash
python tools/generar_canasta.py --version 2024 \
  --xlsx data/inputs/canastas/ponderadores_2024.xlsx \
  --pdf data/inputs/canastas/manual_2024.pdf \
  --preferir pdf \
  -o data/inputs/canastas/
```

Ver [tools/uso_generar_canasta.md](../tools/uso_generar_canasta.md) para el
detalle completo del script.
