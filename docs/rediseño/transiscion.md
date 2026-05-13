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

---

## Delta de implementación

Cambios concretos v1→v2 para referencia rápida durante la implementación. Complementa el inventario de contratos de arriba.

### `tipos.py` — corrección al inventario

La fila `tipos.py → sin cambio` del inventario es incorrecta. Cambios reales:

| v1 | v2 |
|---|---|
| `ManifestCorrida` | **eliminado** → reemplazado por `ManifestUnidad` + `ManifestDerivado` |
| `ResultadoCorrida` | **eliminado** → absorbido por `ResultadoIndice` |
| `VersionCanasta`, `INDICE_POR_TIPO`, `RANGOS_VALIDOS` | sin cambio |
| — | `ManifestUnidad` (nuevo) |
| — | `ManifestDerivado` (nuevo, con campo `clase: str`) |

---

### `clase_variacion` / `clase_incidencia` — frecuencia embebida

En v1, la frecuencia de una variación/incidencia periódica vivía en dos atributos separados:

```python
# v1
rv.clase_variacion  # "periodica"
rv.descripcion      # "mensual"  ← frecuencia aquí

ri.clase_incidencia  # "periodica"
ri.frecuencia        # "mensual"  ← atributo separado
```

En v2, la frecuencia está embebida en `clase_*`:

```python
# v2
rv.clase_variacion   # "periodica_mensual"  ← sin descripcion ni frecuencia separados
ri.clase_incidencia  # "periodica_mensual"
```

Atributos que **desaparecen**: `rv.descripcion` (como portador de frecuencia) y `ri.frecuencia`.

Valores posibles en v2 para `clase_variacion` y `clase_incidencia`:
`"periodica_quincenal"`, `"periodica_mensual"`, `"periodica_bimestral"`, `"periodica_trimestral"`, `"periodica_cuatrimestral"`, `"periodica_semestral"`, `"periodica_anual"`, `"acumulada_anual"`, `"desde"`.

`"periodica_quincenal"` solo válido con resultados quincenales.

---

### `api/validacion.py` — colapso de funciones

v1 tiene 5 funciones separadas por frecuencia de periodos. v2 colapsa a 3:

| v1 | v2 |
|---|---|
| `validar_mensual(resultado, token)` | `validar_indice(resultado, token)` |
| `validar_quincenal(resultado, token)` | ↑ misma función; detecta PeriodoMensual/Quincenal |
| `validar_variaciones_mensual(rv, token)` | `validar_variacion(rv, token)` |
| `validar_variaciones_quincenal(rv, token)` | ↑ misma función |
| `validar_incidencias_mensual(ri, token)` | `validar_incidencia(ri, token)` |

El dict `_FRECUENCIAS_INEGI = {"mensual": "periodica", "anual": "interanual"}` desaparece. En v2 el mapeo se deriva directamente de `clase_variacion`:

```python
# v2 — lógica de traducción en dominio/validacion/variaciones.py
_MAPEO = {
    "periodica_quincenal": "periodica",
    "periodica_mensual":   "periodica",
    "periodica_anual":     "interanual",
    "acumulada_anual":     "acumulada_anual",
}
```

Ver `aplicacion.md §Mapeo desde contratos de dominio` para el contrato completo.

---

### Eliminaciones en `infraestructura/`

| archivo | motivo |
|---|---|
| `infraestructura/filesystem/almacen_artefactos_fs.py` | puerto `AlmacenArtefactos` eliminado |
| `infraestructura/filesystem/repositorio_corridas_fs.py` | puerto `RepositorioCorridas` eliminado |
| `infraestructura/filesystem/` (directorio) | vacío tras las eliminaciones |
| `infraestructura/csv/escritor_resultados_csv.py` | puerto `EscritorResultados` eliminado |

---

### `aplicacion/puertos/fuente_validacion.py` — protocolo v2

v1 declara un solo método `obtener`. v2 declara tres:

```python
# v2
class FuenteValidacion(Protocol):
    def obtener_indices(self, periodos): ...
    def obtener_variaciones(self, periodos, tipo_variacion): ...
    def obtener_incidencias(self, periodos, tipo_incidencia): ...
```

El archivo v1 debe reemplazarse completo. Ver `aplicacion.md §FuenteValidacion`.

---

### `infraestructura/inegi/fuente_validacion_api.py` — TODOs marcados

Dos renombres pendientes (comentarios `# TODO v2` ya en el archivo):
- `_VARIACIONES_POR_TIPO` → `_VARIACIONES_POR_TIPO_MENSUAL`
- `def obtener` → `def obtener_indices`
