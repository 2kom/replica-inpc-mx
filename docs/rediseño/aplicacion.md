# Rediseño aplicacion/

## Capa aplicacion/

### Decisiones generales

- Contiene contratos de puertos y lógica de orquestación. No conoce detalles de infraestructura — opera con `Protocol`.
- `EjecutarCorrida` **eliminado** — lógica distribuida en 4 casos de uso: `calcular_historia`, `calcular_variacion`, `calcular_incidencia`, `verificar`.
- `LectorCanasta` / `LectorSeries` sobreviven — `_ejecutar_una_canasta` los usa vía inyección. `api/flujos.py` es el composition root que inyecta los concretos.
- `api/insumos.py` sigue acoplado directo a `infraestructura/csv/` — acoplamiento temporal explícito, ver `docs/rediseño/api.md §Acoplamiento`.
- Casos de uso reciben rutas (`Path`) + versiones, no objetos de dominio pre-cargados.
- Helper privado `_ejecutar_una_canasta` encapsula el pipeline de preparación + cálculo de una sola canasta. Los 4 casos de uso lo comparten.

### Inventario de contratos v1 → v2

| Contrato v1 | Destino v2 |
|---|---|
| `LectorCanasta` | sin cambio de interfaz |
| `LectorSeries` | sin cambio de interfaz |
| `FuenteValidacion` | sin cambio |
| `AlmacenArtefactos` | sin cambio |
| `EscritorResultados` | actualizar tipos: `ReporteDetalladoValidacion` → `Resultado` (base v2) |
| `RepositorioCorridas` | actualizar tipos: `ManifestCorrida` → `ManifestUnidad` |
| `EjecutarCorrida` | **eliminado** — distribuido en los 4 casos de uso |
| `_rellenar_faltantes` | sin cambio — permanece en `casos_uso/` como helper privado |
| `_referencia_empalme_desde_resultado` | sin cambio — permanece en `casos_uso/` como helper privado |

**Nuevos en v2:**

- `_ejecutar_una_canasta` — helper privado; pipeline de una canasta
- `calcular_historia` — orquesta múltiples canastas → `ResultadoIndice` empalmado y rebased
- `calcular_variacion` — historia + variaciones → `ResultadoVariacion`
- `calcular_incidencia` — historia + incidencias → `ResultadoIncidencia`
- `verificar` — historia + variaciones + incidencias + validación INEGI → `Validacion*`

### Pendientes — próxima sesión

- Firma exacta de `calcular_historia`: ¿`list[Path]` + `list[VersionCanasta]` separados o `list[tuple[Path, VersionCanasta]]`?
- ¿`calcular_variacion` / `calcular_incidencia` reutilizan `ResultadoIndice` ya calculado o recalculan desde rutas?
- ¿Casos de uso como clases (constructor para inyección) o funciones sueltas con puertos como parámetros?
- ¿`EscritorResultados` y `RepositorioCorridas` persisten en v2 o se difieren a v3?
- `exportar(resultado, path)` de `api/flujos.py` — ¿delega a `EscritorResultados` o infra directo?

---

## Puertos

### LectorCanasta — SIN CAMBIO

```python
class LectorCanasta(Protocol):
    def leer(self, ruta: Path, version: VersionCanasta) -> CanastaCanonica: ...
```

Usado por `_ejecutar_una_canasta`. `api/flujos.py` inyecta `LectorCanastaCsv`. Ver `docs/diseño.md §7.1.1`.

---

### LectorSeries — SIN CAMBIO

```python
class LectorSeries(Protocol):
    def leer(self, ruta: Path) -> SerieNormalizada: ...
```

Usado por `_ejecutar_una_canasta`. `api/flujos.py` inyecta `LectorSeriesCsv`. Ver `docs/diseño.md §7.1.2`.

---

### FuenteValidacion — SIN CAMBIO

Sin modificaciones. Usado por `verificar`. Ver `docs/diseño.md §7.1.3`.

---

### AlmacenArtefactos — SIN CAMBIO

Sin modificaciones. Ver `docs/diseño.md §7.1.6`.

---

### EscritorResultados — ACTUALIZAR (firmas provisionales)

```python
class EscritorResultados(Protocol):
    def escribir(self, resultado: Resultado, ruta: Path) -> None: ...
```

`ReporteDetalladoValidacion` y `DiagnosticoFaltantes` absorbidos en `ValidacionX` v2 — el puerto recibe el tipo base `Resultado`. Ver `docs/diseño.md §7.1.4`.

Pendiente: confirmar si persiste en v2 o se difiere.

---

### RepositorioCorridas — ACTUALIZAR (firmas provisionales)

```python
class RepositorioCorridas(Protocol):
    def guardar(self, manifest: ManifestUnidad) -> None: ...
    def obtener(self, id_corrida: str) -> ManifestUnidad: ...
    def listar(self) -> list[str]: ...
```

`ManifestCorrida` → `ManifestUnidad` (v2). Ver `docs/diseño.md §7.1.5`.

Pendiente: confirmar si persiste en v2 o se difiere.

---

## Casos de uso

### `_ejecutar_una_canasta` — NUEVO (helper privado)

Pipeline de preparación + cálculo para una sola canasta. No es público — solo lo llaman los casos de uso de este módulo.

```python
def _ejecutar_una_canasta(
    ruta_canasta: Path,
    ruta_series: Path,
    version: VersionCanasta,
    lector_canasta: LectorCanasta,
    lector_series: LectorSeries,
    referencia_empalme: dict[str, float] | None = None,
) -> ResultadoIndice:
```

**Pasos en orden:**

1. `lector_canasta.leer(ruta_canasta, version)` → `CanastaCanonica`
2. `lector_series.leer(ruta_series)` → `SerieNormalizada`
3. Filtrar columnas de `serie` a `RANGOS_VALIDOS[version]`. Si vacío → `PeriodosInsuficientes`
4. `alinear_genericos(canasta, serie)` → `SerieNormalizada`
5. `_rellenar_faltantes(serie)` → `(SerieNormalizada, imputados)`
6. Si `referencia_empalme is not None` y canasta usa encadenamiento: aplicar. Si canasta no usa encadenamiento: `UserWarning` + ignorar.
7. `para_canasta(canasta, referencia_empalme or {}).calcular(canasta, serie, id_corrida, tipo)` → `ResultadoIndice`

---

### `calcular_historia` — NUEVO (firmas provisionales)

```python
def calcular_historia(
    canastas: list[Path],
    series: list[Path],
    versiones: list[VersionCanasta],
    lector_canasta: LectorCanasta,
    lector_series: LectorSeries,
) -> ResultadoIndice:
```

**Pasos en orden:**

1. Para cada trío `(ruta_canasta, ruta_serie, version)` en orden: llamar `_ejecutar_una_canasta`. Para canastas con encadenamiento (2013, 2024), pasar `ResultadoIndice` anterior como `referencia_empalme`.
2. `empalmar(resultados[:2])` → tramo 2010–2013
3. `rebasar(tramo, PeriodoQuincenal(2018, 7, 2))` → escala `2Q Jul 2018=100`
4. `empalmar([tramo_rebased] + resultados[2:])` → `ResultadoIndice` completo

Notas:

- Historia completa = 4 canastas (2010, 2013, 2018, 2024). Canasta única = `_ejecutar_una_canasta` directo sin empalme.
- El `periodo_base` de rebase es invariante del dominio INEGI — no configurable por el usuario en este caso de uso.

---

### `calcular_variacion` — NUEVO (firmas provisionales)

```python
def calcular_variacion(
    canastas: list[Path],
    series: list[Path],
    versiones: list[VersionCanasta],
    frecuencia: str,
    lector_canasta: LectorCanasta,
    lector_series: LectorSeries,
) -> ResultadoVariacion:
```

Llama `calcular_historia` internamente → aplica función de variaciones del dominio (`dominio/calculo/variaciones.py`).

---

### `calcular_incidencia` — NUEVO (firmas provisionales)

```python
def calcular_incidencia(
    canastas: list[Path],
    series: list[Path],
    versiones: list[VersionCanasta],
    frecuencia: str,
    lector_canasta: LectorCanasta,
    lector_series: LectorSeries,
) -> ResultadoIncidencia:
```

Llama `calcular_historia` internamente → aplica función de incidencias del dominio (`dominio/calculo/incidencias.py`).

---

### `verificar` — NUEVO (firmas provisionales)

```python
def verificar(
    canastas: list[Path],
    series: list[Path],
    versiones: list[VersionCanasta],
    lector_canasta: LectorCanasta,
    lector_series: LectorSeries,
    fuente_validacion: FuenteValidacion,
) -> tuple[ValidacionIndice, ValidacionVariacion, ValidacionIncidencia]:
```

Orquesta los 3 casos de uso anteriores → pasa resultados a las funciones de validación del dominio (`dominio/validar_inpc.py`, `dominio/validar_variaciones.py`, `dominio/validar_incidencias.py`).

`FuenteValidacion` inyectado — `api/flujos.py` lo construye desde `config.get_token()`. Si `FuenteValidacion` lanza `ErrorValidacion`: continúa con validación `no_disponible`, mismo comportamiento que v1.
