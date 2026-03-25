# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Entorno y comandos

```bash
# Activar entorno
conda activate replica-inpc

# Instalar en modo editable (desde la raíz del repo)
pip install -e ".[dev]"

# Correr todos los tests
pytest

# Correr un test específico
pytest tests/unit/test_periodos.py::test_construccion_valida

# Linting
ruff check src/
```

## Arquitectura

Arquitectura hexagonal (Ports & Adapters). El dominio no conoce CSV, filesystem ni APIs.

```
dominio/        → lógica pura, sin dependencias externas
aplicacion/     → casos de uso + contratos de puertos (Protocol)
infraestructura/→ adaptadores concretos (CSV, filesystem, API INEGI)
api/            → fachada para notebooks (Corrida)
interfaces/     → CLI (fuera de v1)
```

El diseño completo vive en `docs/diseño.md`. Leerlo antes de tocar cualquier módulo nuevo.

## Contratos del dominio implementados

Todos en `src/replica_inpc/dominio/`:

- `periodos.py` — `Periodo(año, mes, quincena)`: value object hashable y sortable
- `errores.py` — jerarquía de excepciones; todo hereda de `ReplicaInpcError`
- `modelos/canasta.py` — `CanastaCanonica(df, version)`: `generico` es el índice, no columna
- `modelos/serie.py` — `SerieNormalizada(df, mapeo)`: índice `generico_limpio`, columnas son `Periodo`
- `modelos/resultado.py` — `ResultadoCalculo(df, id_corrida)`: índice `Periodo`
- `modelos/validacion.py` — `ResumenValidacion`, `ReporteDetalladoValidacion`, `DiagnosticoFaltantes`

## Convenciones críticas

- Los invariantes se lanzan con `InvarianteViolado`, nunca con `ValueError`
- `ponderador` y `encadenamiento` son `str` en `CanastaCanonica`; se convierten con `astype(float)` solo al calcular
- `_repr_html_` siempre lleva `# type: ignore[operator]` (bug en stubs de pandas)
- `VersionCanasta = Literal[2010, 2013, 2018, 2024]` se define en `dominio/tipos.py` (pendiente de implementar); por ahora los modelos usan `int`

## Siguiente módulo a implementar

`dominio/tipos.py` — ver `docs/diseño.md` §5.9 para el contrato completo.
