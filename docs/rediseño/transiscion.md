# Objetivo

el objetivo de este archivo es meter toda la informacion que no vaya en los documentos de las secciones dedicadas, al final este documento debe de redistriburi la informacion en sus repsectivas secciones y se eliminara

## Extraído de `api.md`

### Origen: `## Capa api/` → `### Acoplamiento — decisión v2`

Destino: `api.md ## Decisiones` (ya existe; ver `api.md §D1`).

- **Hoy:** `api/` llama `infraestructura/csv/` directo. Pragmático, suficiente para v2.
- **Futuro:** migrar a puertos + DI (`aplicacion/puertos/`) cuando se agreguen fuentes distintas (SQL, HTTP, etc.). `config.py` inyectará el adaptador concreto al arrancar. Los modelos de dominio no cambian — solo se agrega el adaptador nuevo.

---

### Origen: `## Capa api/` → `### Pendientes generales`

Destino: resolver cada ítem y cerrar o descartar. No son documentación final.

- `config.py`: env var vs singleton vs híbrido — **resuelto**: híbrido (`get_token()` busca env var primero, luego `set_token`)
- Re-export de errores tipados (`rep.errores`) — **resuelto**: SÍ, ver `api.md §D4`
- Re-export de `Periodo*` y factory `periodo_desde_str` — **resuelto**: SÍ

---

### Origen: `## Módulo por módulo` → `### indices.py` → nota histórica

Destino: `api.md ## Decisiones` o `dominio.md ## Decisiones §D7`.

- `empalmar` reemplaza a `combinar` de v1.

---

## Extraido de `dominio.md`

### Origen: `## Capa dominio/` -> `### Decisiones generales`

- `variaciones.py` e `incidencias.py` se mueven de `dominio/` raíz → `dominio/calculo/`

---

### Origen: `## Capa dominio/` -> `### Jerarquía de tipos — decisión v2`

```
Resultado  (base)
├── ResultadoIndice       ← renombrado desde ResultadoCalculo; input de variaciones/incidencias/validaciones
├── ResultadoVariacion    ← análisis; terminal
└── ResultadoIncidencia   ← análisis; terminal

Validacion  (base)
├── ValidacionIndice      ← contiene ResultadoIndice
├── ValidacionVariacion   ← contiene ResultadoVariacion
└── ValidacionIncidencia  ← contiene ResultadoIncidencia
```

---

### Origen: `## Capa dominio/` -> `### Inventario de contratos v1 → v2`

| Contrato v1 | Destino v2 |
|---|---|
| `CanastaCanonica` | sin cambio |
| `SerieNormalizada` | sin cambio |
| `PeriodoQuincenal` / `PeriodoMensual` | sin cambio |
| `ResultadoCalculo` | → `ResultadoIndice` + base `Resultado` |
| `ResumenValidacion` | → `ResultadoIndice.resumen` (sin columnas INEGI) |
| `ReporteDetalladoValidacion` | → `ResultadoIndice.reporte` (sin columnas INEGI) |
| `DiagnosticoFaltantes` | → `ResultadoIndice.diagnostico` (sin cambio de esquema) |
| `CalculadorBase` / `LaspeyresDirecto` / `LaspeyresEncadenadoT1` / `LaspeyresEncadenadoT2` | sin cambio (internos) |
| `tipos.py` | sin cambio |
| `correspondencia.py` | sin cambio |
| `ResultadoVariacion` | sin cambio de clase; vive en `dominio/modelos/variacion.py`; agrega manifiesto + resumen/reporte/diagnostico propios |
| `ResumenValidacionVariaciones` | **eliminado** |
| `ReporteValidacionVariaciones` | → `ValidacionVariacion.reporte` |
| `ResultadoIncidencia` | sin cambio de clase; vive en `dominio/modelos/incidencia.py`; agrega manifiesto + resumen/reporte/diagnostico propios |
| `ResumenValidacionIncidencias` | → `ValidacionIncidencia.resumen` |
| `ReporteValidacionIncidencias` | → `ValidacionIncidencia.reporte` |
| `validar_inpc.py` | sin cambio (interno — alimenta `ValidacionIndice`) |
| `validar_variaciones.py` | sin cambio (interno — alimenta `ValidacionVariacion`) |
| `validar_incidencias.py` | sin cambio (interno — alimenta `ValidacionIncidencia`) |

**Nuevos en v2:**
- `Resultado` (base abstracta)
- `Validacion` (base) → `ValidacionIndice`, `ValidacionVariacion`, `ValidacionIncidencia`
- `ManifestUnidad` — dataclass embebida en `ResultadoIndice.manifiesto`
- `ManifestDerivado` — dataclass embebida en `ResultadoVariacion` / `ResultadoIncidencia`
- `DiagnosticoValidacion` — cobertura temporal de API INEGI (propuesto §12.14)

---

### Origen: `## Funciones de dominio` → notas de migración (→ D6 / D7)

Extraídas al reestructurar la sección para seguir la plantilla. Destino: D6 y D7 en `dominio.md ## Decisiones`.

- **Reubicación de funciones a `dominio/calculo/`** (→ D6): las funciones `variacion_periodica/acumulada_anual/desde` e `incidencia_periodica/acumulada_anual/desde` se mueven de `dominio/variaciones.py` y `dominio/incidencias.py` → `dominio/calculo/variaciones.py` y `dominio/calculo/incidencias.py`. Nota: `ResultadoVariacion` y `ResultadoIncidencia` (las clases) permanecen en `dominio/modelos/`.
- **`empalmar` reemplaza a `combinar`** (→ D7): renombre v1→v2.
- **Migración de `validar_*.py`** (→ D7): lógica sin cambio; tipo de retorno actualizado: objetos sueltos → `ValidacionX` correspondiente.

---

### Origen: `## Capa dominio/` -> `### Estructura de dominio.md`

```
## Contratos de datos
   Resultado (base)
   ResultadoIndice
   ResultadoVariacion
   ResultadoIncidencia
   Validacion (base)
   ValidacionIndice
   ValidacionVariacion
   ValidacionIncidencia

## Funciones de dominio
   transformaciones de ResultadoIndice  (empalmar, rebasar, a_mensual)
   cálculo de variaciones               (variacion_periodica, etc.)
   cálculo de incidencias               (incidencia_periodica, etc.)
   consulta de variaciones              (inflacion_en, inflacion_acumulada, etc.)
   consulta de incidencias              (incidencia_en, incidencia_acumulada, etc.)
   validación interna                   (validar_indices, validar_variaciones, validar_incidencias)
```

---

### Origen: bloque previo a `## Semántica compartida` -> `### Contratos sin cambio`

Sin modificaciones en v2. Ver `docs/diseño.md` para esquema completo.

| Contrato | Archivo | Referencia |
|---|---|---|
| `CanastaCanonica` | `dominio/modelos/canasta.py` | diseño.md §5.1 |
| `SerieNormalizada` | `dominio/modelos/serie.py` | diseño.md §5.2 |
| `PeriodoQuincenal`, `PeriodoMensual`, `periodo_desde_str` | `dominio/periodos.py` | diseño.md §5.3 |
| `VersionCanasta`, `INDICE_POR_TIPO`, `RANGOS_VALIDOS` | `dominio/tipos.py` | diseño.md §5.9 |
| `CalculadorBase` (interfaz interna) | `dominio/calculo/` | diseño.md §5.8 |

---

### Origen: `## Contratos de datos`
