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

---

### `Validacion*` — pre-armado vs bajo demanda

`dominio.md` documenta las propiedades `.resumen`, `.reporte` y `.diagnostico` de `ValidacionIndice`, `ValidacionVariacion` y `ValidacionIncidencia` con la nota "cálculo bajo demanda; no se almacena" (ver `dominio.md:951-955`, `:1072-1076`, `:1102-1106`, `:1127-1131`, `:1195-1199`).

**Reinterpretación adoptada (Fase 2.4):** las tres propiedades se calculan **fuera** del `ResultadoX` subyacente — las funciones de Fase 8 (`validar_indices`, `validar_variaciones`, `validar_incidencias`) las arman y se las pasan al constructor de `Validacion*`. Las clases las **almacenan** como atributos privados y las exponen como properties.

**Por qué:** los DataFrames extendidos (con cols INEGI: `indice_inegi`, `error_absoluto`, `estado_validacion`, etc.) no son derivables del `.df` minimal del `ResultadoX`. La función validadora es quien tiene acceso al puerto `FuenteValidacion` y al cálculo de comparación.

**"Bajo demanda" se reinterpreta como:** "no se computan dentro del `ResultadoX` ni se derivan del `.df` minimal — viven en la función validadora y se pasan al `Validacion*` ya armados". El acceso vía `.resumen` etc. es directo (atributo), no recalculado.

Este delta NO cambia los contratos de datos (esquemas de columnas, NaN, índices) — solo aclara el flujo de construcción.

---

### `ManifestUnidad` — rutas opcionales

`dominio.md` y el inventario inicial declaraban `ManifestUnidad.ruta_canasta: Path` y `ruta_series: Path` como obligatorios. En la práctica, los calculadores de dominio (`LaspeyresDirecto`, `LaspeyresEncadenadoT1`, `LaspeyresEncadenadoT2`) operan sobre `CanastaCanonica` y `SerieNormalizada` ya cargadas en memoria — no conocen filesystem.

**Decisión adoptada (Fase 3):** ambos campos se vuelven `Path | None` con default `None`. La capa I/O (lectores CSV, `cargar_canasta`, `cargar_serie`) los inyecta cuando los conoce; los cálculos in-memory los dejan en `None` sin inventar rutas falsas.

```python
# v2 (Fase 3)
@dataclass
class ManifestUnidad:
    id_corrida: str
    version: VersionCanasta
    tipo: str
    calculador: Literal["LaspeyresDirecto", "LaspeyresEncadenadoT1", "LaspeyresEncadenadoT2"]
    ruta_canasta: Path | None = None
    ruta_series: Path | None = None
    fecha: datetime = field(default_factory=datetime.now)
```

`fecha` también pasa a `default_factory=datetime.now` (naive, por consistencia con tests Fase 2). La migración a timezone-aware es candidata a cleanup posterior.

---

## Plan de implementación v1 → v2

Estrategia: big bang en rama `v2`, módulo por módulo. Tests por fase, no al final. Borrado de código v1 solo cuando su reemplazo v2 está verde.

Cada fase se detalla en un plan propio antes de iniciarla.

### Snapshot operativo de tests v1

Material temporal para Fase 0. Se elimina al consolidar `docs/rediseño/` en Fase 11.1.

Total: 25 archivos `test_*.py` en `tests/` (capturado 2026-05-13 con `find tests -type f -name 'test_*.py'`).

**Mueren completos — Fase 10.6:**
- `tests/integration/test_almacen_artefactos_fs.py`
- `tests/integration/test_repositorio_corridas_fs.py`
- `tests/integration/test_escritor_resultados_csv.py`

**Renombrar — Fase 4:**
- `tests/unit/test_combinar.py` → `tests/unit/test_empalmar.py`

**Migrar adaptando tipos v2:**
- Fase 2 (modelos): `tests/unit/test_resultado.py` (split por modelo derivado).
- Fase 3 (cálculo índices): `tests/unit/test_laspeyres.py`, `tests/unit/test_encadenado.py`, `tests/unit/test_estrategia.py`, `tests/unit/test_subindices.py`, `tests/unit/test_rellenar_faltantes.py`.
- Fase 4 (conversión): `tests/unit/test_conversion.py`.
- Fase 5 (derivados): `tests/unit/test_variaciones.py`, `tests/unit/test_incidencias.py`.
- Fase 8 (validación): `tests/unit/test_validacion_inpc.py`, `tests/unit/test_validar_mensual.py`, `tests/unit/test_validar_quincenal_resultado.py`, `tests/unit/test_validar_variaciones.py`, `tests/unit/test_validar_incidencias.py`.
- Fase 9 (api): `tests/unit/test_api_validacion.py`, `tests/unit/test_api_validacion_variaciones.py`.

**Sin cambio probable:**
- `tests/unit/test_periodos.py`, `tests/unit/test_correspondencia.py`.
- `tests/integration/test_fuente_validacion_api.py` (solo rename `obtener` → `obtener_indices`).
- `tests/integration/test_lector_canasta_csv.py`, `tests/integration/test_lector_series_csv.py`.

### Fases

#### Fase 0 — Preparación

Sin código productivo. Deja la rama lista para que las fases siguientes solo agreguen archivos.

- 0.1 Scaffolding mínimo de paquetes: crear `__init__.py` en `dominio/modelos/`, `dominio/calculo/`, `dominio/consulta/`, `dominio/validacion/`, `aplicacion/casos_uso/` (carpetas vacías no se trackean en git).
- 0.2 Snapshot mental: anotar qué tests v1 morirán vs migrarán.

#### Fase 1 — Tipos y base abstracta

Fundación de tipos v2 antes de tocar modelos derivados.

- 1.1 `dominio/tipos.py`: agregar `ManifestUnidad`, `ManifestDerivado` (con campo `clase: str`).
- 1.2 `dominio/modelos/base.py`: clases `Resultado` (ABC), `Validacion` (ABC), `Vista`.
- 1.3 Tests `modelos/base`: invariantes, `__repr__`, igualdad estructural.

#### Fase 1.5 — Aislamiento de superficie v1

Bloqueador descubierto antes de Fase 2: `dominio/tipos.py` importa `ResultadoCalculo`, `ResumenValidacion`, etc. desde `dominio/modelos/`. Si Fase 2 sobreescribe `modelos/validacion.py` y `resultado.py`, `tipos.py` rompe → `import replica_inpc` rompe → toda la suite falla en collection.

**Política nueva (sustituye "v1 intacto"):** v1 queda aislado como legacy temporal — fuera de superficie pública y fuera de suite activa. Suite verde significa "superficie v2 activa + lo no migrado permitido importa/prueba bien", no "v1 sigue funcionando".

- 1.5.1 Vaciar `src/replica_inpc/__init__.py`: dejar solo `PeriodoMensual`, `PeriodoQuincenal`, `periodo_desde_str`, `VersionCanasta`. Resto se reintroduce en Fase 9.
- 1.5.2 Refactorizar `dominio/tipos.py`: eliminar imports runtime hacia `dominio/modelos/{resultado,validacion,variacion,incidencia}.py`. Verificable con `rg -n "from replica_inpc\.dominio\.modelos" src/replica_inpc/dominio/tipos.py` → sin matches.
- 1.5.3 Mover `ManifestCorrida` y `ResultadoCorrida` a `dominio/_legacy.py` (archivo nuevo, prefijo `_` marca interno/temporal). Estos objetos se instancian en runtime, por lo que `TYPE_CHECKING` no aplica.
- 1.5.4 Actualizar consumidores de `ManifestCorrida`/`ResultadoCorrida` para importar desde `dominio._legacy`. Inventario previo con `rg` antes del cambio.
- 1.5.5 Borrar tests claramente muertos (persistencia v1, sin equivalente v2):
  - `tests/integration/test_almacen_artefactos_fs.py`
  - `tests/integration/test_repositorio_corridas_fs.py`
  - `tests/integration/test_escritor_resultados_csv.py`
- 1.5.6 Mover tests migrables a `tests/_legacy/legacy_test_*.py` (prefix `legacy_test_` no se colecciona por pytest default). Preservan especificación v1 para traducción a v2 por fase. Conteo y enumeración previa, no estimación.
- 1.5.7 Verificación:
  - `rg -n "from replica_inpc\.dominio\.modelos" src/replica_inpc/dominio/tipos.py` → sin matches.
  - `conda run -n replica-inpc python -c "import replica_inpc; from replica_inpc.dominio.tipos import VersionCanasta"` → OK.
  - `conda run -n replica-inpc pytest --collect-only -q` → solo recolecta tests activos; `_legacy/` ausente.
  - `conda run -n replica-inpc pytest -q` → verde.

#### Fase 2 — Modelos derivados

Cuatro commits, uno por archivo. Sin lógica de cálculo todavía.

- 2.1 `modelos/indice.py`: `ResultadoIndice` + tests.
- 2.2 `modelos/variacion.py`: `ResultadoVariacion` + tests.
- 2.3 `modelos/incidencia.py`: `ResultadoIncidencia` + tests.
- 2.4 `modelos/validacion.py`: `ValidacionIndice`, `ValidacionVariacion`, `ValidacionIncidencia` + tests.

#### Fase 3 — Cálculo de índices

Adaptar lógica v1 (sin reescribir matemática) para que retorne tipos v2.

- 3.1 `calculo/base.py`: `CalculadorBase` con tipos v2.
- 3.2 `calculo/laspeyres_directo.py`: retorno `ResultadoIndice`.
- 3.3 `calculo/laspeyres_encadenado.py`: ídem (T1 + T2).
- 3.4 Tests `calculo/`: migrar fixtures v1.

#### Fase 4 — Conversión

Transformaciones de `ResultadoIndice` → `ResultadoIndice`. Necesarias para construir fixtures realistas en Fase 5.

- 4.1 `conversion.py`: rename `combinar` → `empalmar` + tests.
- 4.2 `conversion.py`: `rebasar` (adaptar v1) + tests.
- 4.3 `conversion.py`: `a_mensual` (adaptar v1) + tests.

#### Fase 5 — Cálculo de derivados

Funciones que producen `ResultadoVariacion` / `ResultadoIncidencia` a partir de `ResultadoIndice` (típicamente ya empalmado/rebasado/convertido por Fase 4).

- 5.1 `calculo/variaciones.py`: `variacion_periodica`, `variacion_acumulada_anual`, `variacion_desde` + tests.
- 5.2 `calculo/incidencias.py`: mover v1, adaptar tipos + tests.

#### Fase 6 — Consulta

Funciones thin sobre `ResultadoVariacion` / `ResultadoIncidencia`. Sin estado.

- 6.1 `consulta/variaciones.py`: `inflacion_en`, `inflacion_acumulada`, `inflacion_promedio`, `inflacion_maxima`, `inflacion_minima` + tests.
- 6.2 `consulta/incidencias.py`: `incidencia_en`, `incidencia_acumulada`, `incidencia_promedio`, `incidencia_mayor`, `incidencia_menor` + tests.

#### Fase 7 — Aplicación

Puerto v2 y único caso de uso. Bloqueante para Fase 8.

- 7.1 `aplicacion/puertos/fuente_validacion.py` v2 (3 métodos: `obtener_indices`, `obtener_variaciones`, `obtener_incidencias`).
- 7.2 Revisar `puertos/lector_canasta.py` y `lector_series.py` (probable sin cambio).
- 7.3 `aplicacion/casos_uso/calcular_historia.py` + tests.

#### Fase 8 — Validación

Tres funciones puras que reciben `FuenteValidacion` por inyección.

**Prerequisito bloqueante:** cerrar contratos en `dominio.md §Validación interna` (hoy marcada PENDIENTE). Sin contrato firmado, no iniciar.

- 8.1 `validacion/indices.py`: `validar_indices` → `ValidacionIndice` + tests.
- 8.2 `validacion/variaciones.py`: `validar_variaciones` → `ValidacionVariacion` + tests.
- 8.3 `validacion/incidencias.py`: `validar_incidencias` → `ValidacionIncidencia` + tests.

#### Fase 9 — API flat

Superficie pública estilo pandas. Siete módulos + tests de integración end-to-end.

- 9.1 `api/config.py`: `set_token`, `limpiar_cache`, tolerancias.
- 9.2 `api/insumos.py`: `cargar_canasta`, `cargar_serie`.
- 9.3 `api/indices.py`: `calcular_indice`, `empalmar`, `rebasar`, `a_mensual`.
- 9.4 `api/variaciones.py`: series + análisis.
- 9.5 `api/incidencias.py`: series + análisis.
- 9.6 `api/validaciones.py`: `validar_indice/variacion/incidencia` + `TIPOS_CON_VALIDACION`.
- 9.7 `api/flujos.py`: `calcular_historia`.
- 9.8 Tests integración end-to-end.

#### Fase 10 — Limpieza

Borrar código v1 muerto. Cada eliminación con su commit. Lista conocida abajo.

**Regla de scope:** si durante la barrida aparece un símbolo no listado, no se asume muerto. Parar y decidir explícitamente antes de borrar.

- 10.1 Borrar `infraestructura/filesystem/` (incluye `almacen_artefactos_fs.py`, `repositorio_corridas_fs.py`).
- 10.2 Borrar `infraestructura/csv/escritor_resultados_csv.py`.
- 10.3 Borrar puntos de entrada v1: `api/corrida.py`, `aplicacion/casos_uso/ejecutar_corrida.py`.
- 10.4 Borrar contratos v1 muertos: `AlmacenArtefactos`, `RepositorioCorridas`, `EscritorResultados`, `ManifestCorrida`, `ResultadoCorrida`.
- 10.5 Borrar exports v1 muertos en `__init__.py` (raíz y subpaquetes): solo símbolos enumerados arriba — `Corrida`, `EjecutarCorrida`, `ResultadoCorrida`, `ManifestCorrida`, `combinar` (alias v1), `AlmacenArtefactos`, `RepositorioCorridas`, `EscritorResultados`. No tocar exports v2.
- 10.6 Borrar tests v1 huérfanos existentes: `tests/integration/test_almacen_artefactos_fs.py`, `tests/integration/test_repositorio_corridas_fs.py`, `tests/integration/test_escritor_resultados_csv.py`. Más cualquier otro que referencie clases eliminadas y aparezca durante la migración.
- 10.7 Verificación final:
  - `ruff check --select F401 src/ tests/` (imports no usados locales).
  - `pytest --collect-only` (detecta imports rotos cross-archivo que F401 ignora).
  - `pytest` suite completa verde.

#### Fase 11 — Cierre

Consolidación documental y tag.

- 11.1 Consolidar `docs/rediseño/` → `docs/diseño.md`.
- 11.2 Actualizar `CLAUDE.md` (sección "Contratos del dominio implementados").
- 11.3 Suite completa verde.
- 11.4 Tag `v2.0.0` + entrada en `docs/requerimientos/tags.md`.

### Política

- No avanzar de fase con tests rojos.
- Un módulo = un commit con su suite verde.
- Si una fase desborda scope esperado (>5 commits extra), parar y replanear.
- Plan detallado por fase se redacta antes de iniciarla; al cerrar la fase, su detalle se archiva o se elimina.
