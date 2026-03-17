# Diseño del sistema — replica-inpc-mx

Documento vivo. Refleja el estado actual de las decisiones de diseño del sistema.
El historial de cambios vive en git.

---

## 1. Arquitectura

### 1.1 Patrón principal: Hexagonal (Ports & Adapters)

El dominio y los casos de uso no conocen CSV, filesystem, APIs ni bases de datos.
Solo conocen contratos (puertos). La infraestructura implementa esos contratos mediante adaptadores.

Esto permite agregar nuevas fuentes de entrada, formatos de salida o interfaces
sin modificar la lógica de negocio.

**Capas:**

| Capa               | Responsabilidad                                         |
| ------------------ | ------------------------------------------------------- |
| `api/`             | Fachada para notebooks — punto de entrada del usuario   |
| `dominio/`         | Lógica de negocio pura, sin dependencias externas       |
| `aplicacion/`      | Casos de uso y contratos de puertos                     |
| `infraestructura/` | Adaptadores concretos (CSV, filesystem, API INEGI, SQL) |
| `interfaces/`      | CLI                                                     |

### 1.2 Patrones de diseño

#### Strategy — cálculo del INPC

`laspeyres.py` y `encadenado.py` implementan la misma interfaz `CalculadorBase`.
El sistema selecciona la estrategia según la versión de canasta:

- versiones 2018 y 2010 → Laspeyres directo
- versiones 2013 y 2024 → Laspeyres encadenado

Agregar una nueva variante de cálculo no requiere modificar el código existente.

#### Facade — api/corrida.py

`api/corrida.py` expone una interfaz simple al usuario del notebook,
ocultando la orquestación interna de casos de uso:

```python
corrida = Corrida.desde_archivos(canasta="...", series="...")
corrida.calcular()
corrida.validar()
corrida.exportar()
```

#### Repository — persistencia de corridas y artefactos

`RepositorioCorridas` y `AlmacenArtefactos` son puertos que abstraen
dónde y cómo se persiste cada corrida.
En v1 se implementan sobre filesystem. Si se agrega SQL, se implementa
el mismo puerto sin tocar el dominio.

#### Adapter — infraestructura

Cada módulo en `infraestructura/` adapta una tecnología concreta al contrato
del puerto correspondiente:

- `lector_canasta_csv.py` implementa `LectorCanasta`
- `lector_series_csv.py` implementa `LectorSeries`
- `fuente_validacion_api.py` implementa `FuenteValidacion`
- `repositorio_corridas_fs.py` implementa `RepositorioCorridas`

---

## 2. Estructura del proyecto

`data/` y `output/` están en `.gitignore`.

```text
replica-inpc-mx/
├── src/
│   └── replica_inpc/
│       ├── api/
│       │   ├── __init__.py
│       │   └── corrida.py
│       ├── dominio/
│       │   ├── modelos/
│       │   │   ├── canasta.py
│       │   │   ├── serie.py
│       │   │   ├── resultado.py
│       │   │   └── validacion.py
│       │   ├── calculo/
│       │   │   ├── estrategia.py
│       │   │   ├── laspeyres.py
│       │   │   └── encadenado.py
│       │   ├── correspondencia.py
│       │   ├── periodos.py
│       │   └── errores.py
│       ├── aplicacion/
│       │   ├── casos_uso/
│       │   │   ├── importar_canasta.py
│       │   │   ├── importar_series.py
│       │   │   ├── calcular_inpc.py
│       │   │   ├── validar_inpc.py
│       │   │   ├── exportar_corrida.py
│       │   │   └── ejecutar_corrida.py
│       │   └── puertos/
│       │       ├── lector_canasta.py
│       │       ├── lector_series.py
│       │       ├── fuente_validacion.py
│       │       ├── escritor_resultados.py
│       │       ├── repositorio_corridas.py
│       │       └── almacen_artefactos.py
│       ├── infraestructura/
│       │   ├── csv/
│       │   │   ├── lector_canasta_csv.py
│       │   │   ├── lector_series_csv.py
│       │   │   └── escritor_csv.py
│       │   ├── filesystem/
│       │   │   ├── repositorio_corridas_fs.py
│       │   │   └── almacen_artefactos_fs.py
│       │   ├── inegi/
│       │   │   └── fuente_validacion_api.py
│       │   └── sql/
│       │       ├── repositorio_corridas_sql.py
│       │       └── almacen_artefactos_sql.py
│       ├── interfaces/
│       │   └── cli.py
│       └── __init__.py
├── notebooks/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── data/                   # gitignored
│   ├── inputs/
│   │   ├── series/
│   │   └── canastas/
│   └── runs/
│       └── <id_corrida>/
│           ├── manifest.json
│           ├── canasta_canonica.csv
│           ├── series_normalizadas.csv
│           ├── resumen_validacion.csv
│           ├── reporte_detallado_validacion.csv
│           └── diagnostico_faltantes.csv
├── output/                 # gitignored
├── docs/
├── pyproject.toml
└── README.md
```

---

## 3. Stack técnico

| Componente      | Decisión                    | Razón                                              |
| --------------- | --------------------------- | -------------------------------------------------- |
| Python          | 3.10                        | `match/case` disponible, compatible con el entorno |
| DataFrames      | pandas                      | Notebook-first, display automático en Jupyter      |
| Numérico        | numpy                       | Operaciones vectorizadas en el cálculo             |
| Correspondencia | rapidfuzz                   | Matching fuzzy genérico↔genérico                   |
| HTTP            | requests                    | Simple, sin necesidad de async en v1               |
| CLI             | argparse                    | Stdlib, sin dependencia extra para CLI secundario  |
| Testing         | pytest                      | Estándar de facto en Python                        |
| Visualización   | plotnine                    | Presente en el proyecto de referencia              |
| Columnar        | pyarrow                     | Presente en el proyecto de referencia              |
| Empaquetado     | setuptools + pyproject.toml | Estándar moderno, src layout                       |

**Dependencias runtime** (`[project.dependencies]` en `pyproject.toml`):
pandas, numpy, rapidfuzz, requests, python-dateutil, plotnine, pyarrow

**Dependencias de desarrollo** (`[project.optional-dependencies.dev]`):
pytest, ipython, jupyter, ipykernel

Instalación:

```bash
pip install -e ".[dev]"
```

---

## 4. Flujo de datos

```text
ENTRADAS
────────────────────────────────────────────────────────────
canasta_intermedia.csv                  series_genericos.csv
        │                                       │
        ▼                                       ▼
┌───────────────────────┐       ┌───────────────────────────┐
│  lector_canasta_csv   │       │     lector_series_csv     │
│  · valida columnas    │       │  · detecta encoding       │
│  · valida version     │       │    (cp1252 / latin-1)     │
└───────────┬───────────┘       │  · detecta orientación    │
            │                   │    (horizontal / vertical) │
            ▼                   │  · elimina metadatos      │
   canasta_intermedia           └──────────────┬────────────┘
   (representacion interna)                    │
            │                                  ▼
            ▼                          SerieNormalizada
   construir_canasta_canonica
            │
            ▼
   CanastaCanomica
            │                                  │
            └──────────────┬───────────────────┘
                           ▼
                  correspondencia.py
                  · vincula genérico↔genérico (rapidfuzz)
                  · falla si correspondencia insuficiente
                           │
                           ▼
                   laspeyres.py
                   · INPC = Σ ωₖ · Iₖ por periodo
                   · null si falta índice en periodo
                   · falla si falta ponderador
                           │
                           ▼
                   ResultadoCalculo
                           │
                           ▼
              ┌────────────────────────┐
              │  fuente_validacion_api │
              │  · descarga INPC INEGI │
              │  · si falla →          │
              │    no_disponible       │
              └────────────┬───────────┘
                           │
                           ▼
              ResumenValidacion
              ReporteDetalladoValidacion
              DiagnosticoFaltantes
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
     data/runs/<id_corrida>/         output/
     (trazabilidad interna)    (exportación del usuario)

INTERFACES
────────────────────────────────────────────────────────────
api/corrida.py      ← notebook (interfaz principal)
interfaces/cli.py   ← terminal (interfaz secundaria)
```

---

## 5. Contratos del dominio

### 5.1 CanastaCanoNica

**Representación:** DataFrame-backed. `generico` es el índice. El DataFrame se expone
directamente vía `.df`. La versión se almacena como atributo privado y se expone como
propiedad de solo lectura. Display automático en Jupyter vía `_repr_html_`.

```python
class CanastaCanoNica:
    def __init__(self, df: pd.DataFrame, version: int) -> None:
        # df: generico como índice, columnas según esquema canónico
        # validaciones al construir
        ...

    @property
    def version(self) -> int: ...

    @property
    def df(self) -> pd.DataFrame: ...

    def _repr_html_(self) -> str:
        return self.df._repr_html_()
```

**Esquema del DataFrame (índice: `generico`):**

| Columna                  | dtype pandas        | Notas                                                 |
| ------------------------ | ------------------- | ----------------------------------------------------- |
| `ponderador`             | `object` (str)      | texto decimal exacto del archivo fuente               |
| `encadenamiento`         | `object` (str/NaN)  | texto decimal exacto; NaN cuando no aplica            |
| `COG`                    | `pd.Categorical`    |                                                       |
| `CCIF`                   | `pd.Categorical`    |                                                       |
| `inflacion_1`            | `pd.Categorical`    |                                                       |
| `inflacion_2`            | `pd.Categorical`    |                                                       |
| `inflacion_3`            | `pd.Categorical`    |                                                       |
| `SCIAN_sector`           | `pd.Categorical`    | número + nombre, ej. `"32 Industrias manufactureras"` |
| `SCIAN_sector_numero`    | `pd.Categorical`    | solo el código, ej. `"32"`                            |
| `SCIAN_rama`             | `pd.Categorical`    | código + nombre, ej. `"3241 Fabricación de..."`       |
| `SCIAN_rama_numero`      | `pd.Categorical`    | solo el código, ej. `"3241"`                          |
| `canasta_basica`         | `bool`              |                                                       |
| `canasta_consumo_minimo` | `pd.BooleanDtype()` | nullable; `pd.NA` cuando no aplica a la versión       |

**Invariantes — validados al construir:**

| Invariante | Regla |
| --- | --- |
| Versión válida | `version` in `{2010, 2013, 2018, 2024}` |
| Genérico no vacío | ningún valor del índice es string vacío |
| Ponderador positivo | `float(ponderador) > 0` para cada fila |
| Sin duplicados | el índice no tiene valores repetidos |
| Suma de ponderadores | `abs(sum(ponderador) - 100) <= 1e-5` |
| Encadenamiento positivo | cuando presente: `float(encadenamiento) > 0` |

---

### 5.2 SerieNormalizada

**Representación:** DataFrame-backed, formato ancho. `generico_limpio` es el índice.
Las columnas son objetos `Periodo`. Los valores son `float64` o `NaN`.
`serie.mapeo` expone la correspondencia `generico_limpio → generico_original`.

```python
class SerieNormalizada:
    def __init__(
        self,
        df: pd.DataFrame,
        mapeo: dict[str, str] | None = None,
    ) -> None: ...

    @property
    def df(self) -> pd.DataFrame: ...

    @property
    def mapeo(self) -> dict[str, str]: ...  # generico_limpio → generico_original

    def _repr_html_(self) -> str:
        return self.df._repr_html_()
```

**Esquema del DataFrame:**

| Dimensión  | Tipo               | Notas                              |
| ---------- | ------------------ | ---------------------------------- |
| Índice     | `str`              | `generico_limpio`                  |
| Columnas   | `Periodo`          | una columna por quincena           |
| Valores    | `float64` / `NaN`  | NaN cuando falta el índice         |

**Invariantes — validados al construir:**

| Invariante                  | Regla                                          |
| --------------------------- | ---------------------------------------------- |
| Genérico no vacío           | ningún valor del índice es string vacío        |
| Sin duplicados              | el índice no tiene valores repetidos           |
| Al menos un periodo         | el DataFrame tiene al menos una columna        |
| Columnas son periodos       | todos los nombres de columna son `Periodo`     |
| Valores no negativos        | todo valor numérico es ≥ 0                     |

---

### 5.3 Periodo

**Representación:** value object en `dominio/periodos.py`. Almacena `año`, `mes` y
`quincena`. Sortable, hashable, convertible a `pd.Timestamp` para graficación.

```python
class Periodo:
    def __init__(self, año: int, mes: int, quincena: int) -> None: ...

    @classmethod
    def desde_str(cls, texto: str) -> "Periodo": ...  # "1Q Ene 2018"

    def to_timestamp(self) -> pd.Timestamp: ...  # 1Q → día 1, 2Q → día 16

    def __str__(self) -> str: ...       # "1Q Ene 2018"
    def __repr__(self) -> str: ...
    def __eq__(self, other) -> bool: ...
    def __hash__(self) -> int: ...
    def __lt__(self, other) -> bool: ...
```

---

### 5.4 ResultadoCalculo

**Representación:** DataFrame-backed. `Periodo` es el índice. `version` vive como
columna (permite unir resultados de distintas versiones). `id_corrida` como atributo.

```python
class ResultadoCalculo:
    def __init__(self, df: pd.DataFrame, id_corrida: str) -> None: ...

    @property
    def id_corrida(self) -> str: ...

    @property
    def df(self) -> pd.DataFrame: ...

    def _repr_html_(self) -> str:
        return self.df._repr_html_()
```

**Esquema del DataFrame (índice: `Periodo`):**

| Columna          | dtype pandas      | Notas                                          |
| ---------------- | ----------------- | ---------------------------------------------- |
| `version`        | `int`             |                                                |
| `inpc_replicado` | `float64` / `NaN` | NaN cuando `estado_calculo != 'ok'`            |
| `estado_calculo` | `object` (str)    | `'ok'`, `'null_por_faltantes'`, `'fallida'`    |
| `motivo_error`   | `object` (str/NaN)| NaN cuando `estado_calculo == 'ok'`            |

**Invariantes — validados al construir:**

| Invariante | Regla |
| --- | --- |
| Versión válida | `version` in `{2010, 2013, 2018, 2024}` |
| Sin duplicados | el índice no tiene valores repetidos |
| Al menos un periodo | el DataFrame no está vacío |
| `estado_calculo` válido | valores in `{'ok', 'null_por_faltantes', 'fallida'}` |
| Consistencia ok | si `estado_calculo == 'ok'` → `inpc_replicado` no NaN y `motivo_error` NaN |
| Consistencia fallo | si `estado_calculo != 'ok'` → `inpc_replicado` NaN y `motivo_error` con valor |

---

### 5.5 ResumenValidacion

**Representación:** DataFrame-backed. `id_corrida` es el índice. `version` como columna
(permite historiales con múltiples versiones y subíndices).

```python
class ResumenValidacion:
    def __init__(self, df: pd.DataFrame) -> None: ...

    @property
    def df(self) -> pd.DataFrame: ...

    def _repr_html_(self) -> str:
        return self.df._repr_html_()
```

**Esquema del DataFrame (índice: `id_corrida`):**

| Columna | dtype pandas | Notas |
| --- | --- | --- |
| `version` | `int` | |
| `total_periodos_esperados` | `int` | |
| `total_periodos_calculados` | `int` | |
| `total_periodos_con_null` | `int` | |
| `error_absoluto_max` | `float` / `NaN` | NaN si validación no disponible |
| `error_relativo_max` | `float` / `NaN` | NaN si validación no disponible |
| `total_faltantes_indice` | `int` | |
| `total_faltantes_ponderador` | `int` | |
| `estado_validacion_global` | `object` (str) | `'ok'`, `'diferencia_detectada'`, `'no_disponible'` |
| `estado_corrida` | `object` (str) | `'ok'`, `'parcial'`, `'fallida'` |

**Invariantes — validados al construir:**

| Invariante | Regla |
| --- | --- |
| Versión válida | `version` in `{2010, 2013, 2018, 2024}` |
| `estado_corrida` válido | valores in `{'ok', 'parcial', 'fallida'}` |
| `estado_validacion_global` válido | valores in `{'ok', 'diferencia_detectada', 'no_disponible'}` |
| Periodos calculados | `total_periodos_calculados` <= `total_periodos_esperados` |
| Periodos null | `total_periodos_con_null` <= `total_periodos_calculados` |

---

### 5.6 ReporteDetalladoValidacion

**Representación:** DataFrame-backed. Índice compuesto `(Periodo, subindice)` — agrupa
todos los subíndices de una corrida. `id_corrida` como atributo. `version` como columna.

```python
class ReporteDetalladoValidacion:
    def __init__(self, df: pd.DataFrame, id_corrida: str) -> None: ...

    @property
    def id_corrida(self) -> str: ...

    @property
    def df(self) -> pd.DataFrame: ...

    def _repr_html_(self) -> str:
        return self.df._repr_html_()
```

**Esquema del DataFrame (índice compuesto: `(Periodo, subindice)`):**

| Columna                      | dtype pandas      | Notas                                               |
| ---------------------------- | ----------------- | --------------------------------------------------- |
| `version`                    | `int`             |                                                     |
| `inpc_replicado`             | `float` / `NaN`   | NaN cuando `estado_calculo != 'ok'`                 |
| `inpc_inegi`                 | `float` / `NaN`   | NaN cuando `estado_validacion == 'no_disponible'`   |
| `error_absoluto`             | `float` / `NaN`   | NaN cuando `estado_validacion == 'no_disponible'`   |
| `error_relativo`             | `float` / `NaN`   | NaN cuando `estado_validacion == 'no_disponible'`   |
| `estado_calculo`             | `object` (str)    | `'ok'`, `'null_por_faltantes'`, `'fallida'`         |
| `motivo_error`               | `object` (str/NaN)|                                                     |
| `estado_validacion`          | `object` (str)    | `'ok'`, `'diferencia_detectada'`, `'no_disponible'` |
| `total_genericos_esperados`  | `int`             |                                                     |
| `total_genericos_con_indice` | `int`             |                                                     |
| `total_genericos_sin_indice` | `int`             |                                                     |
| `cobertura_genericos_pct`    | `float`           |                                                     |
| `ponderador_total_esperado`  | `float`           |                                                     |
| `ponderador_total_cubierto`  | `float`           |                                                     |

**Invariantes — validados al construir:**

| Invariante | Regla |
| --- | --- |
| Versión válida | `version` in `{2010, 2013, 2018, 2024}` |
| `estado_calculo` válido | valores in `{'ok', 'null_por_faltantes', 'fallida'}` |
| `estado_validacion` válido | valores in `{'ok', 'diferencia_detectada', 'no_disponible'}` |
| Consistencia ok | si `estado_calculo == 'ok'` → `inpc_replicado` no NaN |
| Consistencia fallo | si `estado_calculo != 'ok'` → `inpc_replicado` NaN |
| Consistencia validacion | si `estado_validacion == 'no_disponible'` → `inpc_inegi`, `error_absoluto`, `error_relativo` NaN |
| Al menos una fila | el DataFrame no está vacío |

---

### 5.7 DiagnosticoFaltantes

**Representación:** DataFrame-backed. Índice entero por defecto. `id_corrida` y `version`
como columnas (parte del dato, para trazabilidad por corrida).

```python
class DiagnosticoFaltantes:
    def __init__(self, df: pd.DataFrame) -> None: ...

    @property
    def df(self) -> pd.DataFrame: ...

    def _repr_html_(self) -> str:
        return self.df._repr_html_()
```

**Esquema del DataFrame (índice entero):**

| Columna          | dtype pandas       | Notas                                          |
| ---------------- | ------------------ | ---------------------------------------------- |
| `id_corrida`     | `object` (str)     |                                                |
| `version`        | `int`              |                                                |
| `periodo`        | `Periodo` / `NaN`  | NaN cuando `tipo_faltante == 'ponderador'`     |
| `generico`       | `object` (str)     |                                                |
| `nivel_faltante` | `object` (str)     | `'periodo'`, `'estructural'`                   |
| `tipo_faltante`  | `object` (str)     | `'indice'`, `'ponderador'`                     |
| `detalle`        | `object` (str)     |                                                |

**Invariantes — validados al construir:**

| Invariante | Regla |
| --- | --- |
| Versión válida | `version` in `{2010, 2013, 2018, 2024}` |
| `nivel_faltante` válido | valores in `{'periodo', 'estructural'}` |
| `tipo_faltante` válido | valores in `{'indice', 'ponderador'}` |
| Consistencia índice | si `tipo_faltante == 'indice'` → `periodo` no NaN |
| Consistencia ponderador | si `tipo_faltante == 'ponderador'` → `periodo` NaN |
