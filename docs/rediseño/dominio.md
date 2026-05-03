# Rediseño dominio/

## Capa dominio/

### Decisiones generales

- Dominio puro: sin IO, sin dependencias externas, sin strings de periodos (recibe solo `Periodo*`)
- `ResultadoCalculo` **eliminado** — renombrado a `ResultadoIndice` (breaking change v2)
- `ResultadoIndice` **no** embebe canasta — canasta es parámetro explícito donde se requiere
- `ResultadoIndice` agrega atributo `periodo_base: PeriodoQuincenal | None` — `None` = escala nativa de la canasta; set por `rebasar()`
- `empalmar` verifica `periodo_base` compatible entre inputs y propaga reporte/diagnostico/resumen (merge automático)
- `ResumenValidacionVariaciones` eliminado — dead code desde v1.2.4; absorbido por `ValidacionVariacion`
- `variaciones.py` e `incidencias.py` se mueven de `dominio/` raíz → `dominio/calculo/`
- Invariantes siguen lanzando `InvarianteViolado`, nunca `ValueError`

### Jerarquía de tipos — decisión v2

Dos jerarquías paralelas, independientes:

```
Resultado  (base)
├── ResultadoIndice       ← renombrado desde ResultadoCalculo; input de variaciones/incidencias/validaciones
├── ResultadoVariacion    ← análisis; terminal
└── ResultadoIncidencia   ← análisis; terminal

ResultadoValidacion  (base)
├── ValidacionIndice      ← contiene ResultadoIndice
├── ValidacionVariacion   ← contiene ResultadoVariacion
└── ValidacionIncidencia  ← contiene ResultadoIncidencia
```

`ValidacionX` **contiene** un `ResultadoX` vía composición — no hereda de `Resultado`.

**`Resultado` (base)** — mínimo compartido con semántica real:
- `.df` — DataFrame interno; escape hatch para análisis externos (scipy, networkx, etc.)
- `.pipe(fn, *args, **kwargs)` — encadenamiento estilo pandas
- `_repr_html_`
- `.como_tabla(ancho: bool = False)`
- `.resumen` — abstracto; cada subclase implementa con su propio esquema
- `.reporte` — abstracto; cada subclase implementa con su propio esquema
- `.diagnostico` — abstracto; cada subclase implementa con su propio esquema

**`ResultadoValidacion` (base)** provee:
- `.calculo` — referencia al `ResultadoX` validado
- `.resumen`
- `.reporte`
- `.diagnostico`

### Inventario de contratos v1 → v2

| Contrato v1 | Destino v2 |
|---|---|
| `CanastaCanonica` | sin cambio |
| `SerieNormalizada` | sin cambio |
| `PeriodoQuincenal` / `PeriodoMensual` | sin cambio |
| `ResultadoCalculo` | → `ResultadoIndice` + base `Resultado` |
| `ResumenValidacion` | → `ResultadoIndice.resumen` (sin columnas INEGI) |
| `ReporteDetalladoValidacion` | → `ResultadoIndice.reporte` (sin columnas INEGI) |
| `DiagnosticoFaltantes` | → `ResultadoIndice.diagnostico` (sin cambio de esquema) |
| `CalculadorBase` / `LaspeyresDirecto` / `LaspeyresEncadenado` | sin cambio (internos) |
| `tipos.py` | sin cambio |
| `correspondencia.py` | sin cambio |
| `ResultadoVariacion` | sin cambio de clase; mueve a `dominio/calculo/`; agrega manifiesto + resumen/reporte/diagnostico propios |
| `ResumenValidacionVariaciones` | **eliminado** |
| `ReporteValidacionVariaciones` | → `ValidacionVariacion.reporte` |
| `ResultadoIncidencia` | sin cambio de clase; mueve a `dominio/calculo/`; agrega manifiesto + resumen/reporte/diagnostico propios |
| `ResumenValidacionIncidencias` | → `ValidacionIncidencia.resumen` |
| `ReporteValidacionIncidencias` | → `ValidacionIncidencia.reporte` |
| `validar_inpc.py` | sin cambio (interno — alimenta `ValidacionIndice`) |
| `validar_variaciones.py` | sin cambio (interno — alimenta `ValidacionVariacion`) |
| `validar_incidencias.py` | sin cambio (interno — alimenta `ValidacionIncidencia`) |

**Nuevos en v2:**
- `Resultado` (base abstracta)
- `ResultadoValidacion` (base) → `ValidacionIndice`, `ValidacionVariacion`, `ValidacionIncidencia`
- `ManifestUnidad` — dataclass embebida en `ResultadoIndice.manifiesto`
- `ManifestDerivado` — dataclass embebida en `ResultadoVariacion` / `ResultadoIncidencia`
- `DiagnosticoValidacion` — cobertura temporal de API INEGI (propuesto §12.14)

### Manifiesto por subtipo

**`ResultadoIndice.manifiesto: list[ManifestUnidad]`** — combinable:

```python
@dataclass
class ManifestUnidad:
    id_corrida: str
    version: VersionCanasta
    ruta_canasta: Path
    ruta_series: Path
    fecha: datetime
```

Un elemento para canasta simple; `empalmar` concatena listas. `resumen` se recalcula desde df merged + manifiestos concatenados.

**`ResultadoVariacion.manifiesto` / `ResultadoIncidencia.manifiesto`: `ManifestDerivado`** — no combinable (terminales):

```python
@dataclass
class ManifestDerivado:
    id_corrida: str   # hereda del ResultadoIndice origen
    tipo: str
    descripcion: str  # "mensual", "desde Ene 2015 hasta Dic 2024", etc.
    fecha: datetime
```

### Estructura de `dominio.md`

```
## Contratos de datos
   Resultado (base)
   ResultadoIndice
   ResultadoVariacion
   ResultadoIncidencia
   ResultadoValidacion (base)
   ValidacionIndice
   ValidacionVariacion
   ValidacionIncidencia

## Funciones de dominio
   transformaciones de ResultadoIndice  (empalmar, rebasar, a_mensual)
   cálculo de variaciones               (variacion_periodica, etc.)
   cálculo de incidencias               (incidencia_periodica, etc.)
   validación interna                   (validar_inpc, validar_variaciones, validar_incidencias)
```

### Pendientes — próxima sesión

- Esquemas nuevos de `ResultadoVariacion.resumen` / `.reporte` / `.diagnostico`
- Esquemas nuevos de `ResultadoIncidencia.resumen` / `.reporte` / `.diagnostico`
- Contratos completos: `ValidacionIndice`, `ValidacionVariacion`, `ValidacionIncidencia`
- Contrato de `empalmar`: compatibilidad `periodo_base=None` cross-version vs same-version
- `ResultadoVariacion` — ¿agregar `estado_calculo` en df para consistencia con `ResultadoIncidencia`?
- Actualizar `api.md`: parámetro `tipo` en `calcular_indice`; firmas completas de `api/incidencias.py`

---

## Contratos de datos
