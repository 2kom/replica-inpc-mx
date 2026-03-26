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

- versiones 2010 y 2018 → `LaspeyresDirecto` — $INPC = \sum_j w_j \cdot I_j$
- versiones 2013 y 2024 → `LaspeyresEncadenado` — $INPC = f \cdot \sum_j w_j \cdot \theta_j \cdot I_j$

Para 2013, θ=1 para todos los genéricos: los ponderadores ENIGH 2010 fueron alineados
al periodo base dic 2010, por lo que no hay desfase que normalizar.
Para 2024, $θ_j = \frac{100}{I_j^{2Q Jul 2024}}$ por genérico: los ponderadores ENIGH 2022
están referenciados a jul 2024 mientras los índices publicados tienen base jul 2018.

La canasta codifica qué estrategia usar: `encadenamiento` vacío → directo,
`encadenamiento` con valores → encadenado.

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
- `escritor_csv.py` implementa `EscritorResultados`
- `almacen_artefactos_fs.py` implementa `AlmacenArtefactos`

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
│       │   │   ├── base.py
│       │   │   ├── estrategia.py
│       │   │   ├── laspeyres.py
│       │   │   └── encadenado.py
│       │   ├── correspondencia.py
│       │   ├── validar_inpc.py
│       │   ├── periodos.py
│       │   ├── tipos.py
│       │   └── errores.py
│       ├── aplicacion/
│       │   ├── casos_uso/
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
| Correspondencia | unicodedata (stdlib)        | Normalización exacta genérico↔genérico             |
| HTTP            | requests                    | Simple, sin necesidad de async en v1               |
| CLI             | argparse                    | Stdlib, sin dependencia extra para CLI secundario  |
| Testing         | pytest                      | Estándar de facto en Python                        |
| Visualización   | plotnine                    | Presente en el proyecto de referencia              |
| Columnar        | pyarrow                     | Presente en el proyecto de referencia              |
| Empaquetado     | setuptools + pyproject.toml | Estándar moderno, src layout                       |

**Dependencias runtime** (`[project.dependencies]` en `pyproject.toml`):
pandas, numpy, requests, python-dateutil, plotnine, pyarrow

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
                  · vincula genérico↔genérico (normalización exacta)
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

### 5.1 CanastaCanonica

**Representación:** DataFrame-backed. `generico` es el índice. El DataFrame se expone
directamente vía `.df`. La versión se almacena como atributo privado y se expone como
propiedad de solo lectura. Display automático en Jupyter vía `_repr_html_`.

```python
class CanastaCanonica:
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

| Invariante              | Regla                                        |
| ----------------------- | -------------------------------------------- |
| Versión válida          | `version` in `{2010, 2013, 2018, 2024}`      |
| Genérico no vacío       | ningún valor del índice es string vacío      |
| Ponderador positivo     | `float(ponderador) > 0` para cada fila       |
| Sin duplicados          | el índice no tiene valores repetidos         |
| Suma de ponderadores    | `abs(sum(ponderador) - 100) <= 1e-5`         |
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

| Invariante              | Regla                                                                         |
| ----------------------- | ----------------------------------------------------------------------------- |
| Versión válida          | `version` in `{2010, 2013, 2018, 2024}`                                       |
| Sin duplicados          | el índice no tiene valores repetidos                                          |
| Al menos un periodo     | el DataFrame no está vacío                                                    |
| `estado_calculo` válido | valores in `{'ok', 'null_por_faltantes', 'fallida'}`                          |
| Consistencia ok         | si `estado_calculo == 'ok'` → `inpc_replicado` no NaN y `motivo_error` NaN    |
| Consistencia fallo      | si `estado_calculo != 'ok'` → `inpc_replicado` NaN y `motivo_error` con valor |

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

| Columna                      | dtype pandas    | Notas                                               |
| ---------------------------- | --------------- | --------------------------------------------------- |
| `version`                    | `int`           |                                                     |
| `total_periodos_esperados`   | `int`           |                                                     |
| `total_periodos_calculados`  | `int`           |                                                     |
| `total_periodos_con_null`    | `int`           |                                                     |
| `error_absoluto_max`         | `float` / `NaN` | NaN si validación no disponible                     |
| `error_relativo_max`         | `float` / `NaN` | NaN si validación no disponible                     |
| `total_faltantes_indice`     | `int`           |                                                     |
| `total_faltantes_ponderador` | `int`           |                                                     |
| `estado_validacion_global`   | `object` (str)  | `'ok'`, `'diferencia_detectada'`, `'no_disponible'` |
| `estado_corrida`             | `object` (str)  | `'ok'`, `'parcial'`, `'fallida'`                    |

**Invariantes — validados al construir:**

| Invariante                        | Regla                                                        |
| --------------------------------- | ------------------------------------------------------------ |
| Al menos una fila                 | el DataFrame no está vacío                                   |
| Versión válida                    | `version` in `{2010, 2013, 2018, 2024}`                      |
| `estado_corrida` válido           | valores in `{'ok', 'parcial', 'fallida'}`                    |
| `estado_validacion_global` válido | valores in `{'ok', 'diferencia_detectada', 'no_disponible'}` |
| Periodos calculados               | `total_periodos_calculados` <= `total_periodos_esperados`    |
| Periodos null                     | `total_periodos_con_null` <= `total_periodos_calculados`     |

---

### 5.6 ReporteDetalladoValidacion

**Representación:** DataFrame-backed. Índice compuesto `(Periodo, subindice)` — agrupa
todos los subíndices de una corrida. `id_corrida` como atributo. `version` como columna.

**Nota v1:** en v1 el único subíndice calculado es el INPC general, por lo que `subindice`
toma siempre el valor `"INPC general"`. El índice compuesto se mantiene para que en v2,
al agregar subíndices, el schema no cambie — solo aparecen más filas.

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

| Invariante                 | Regla                                                                                            |
| -------------------------- | ------------------------------------------------------------------------------------------------ |
| Versión válida             | `version` in `{2010, 2013, 2018, 2024}`                                                          |
| `estado_calculo` válido    | valores in `{'ok', 'null_por_faltantes', 'fallida'}`                                             |
| `estado_validacion` válido | valores in `{'ok', 'diferencia_detectada', 'no_disponible'}`                                     |
| Consistencia ok            | si `estado_calculo == 'ok'` → `inpc_replicado` no NaN                                            |
| Consistencia fallo         | si `estado_calculo != 'ok'` → `inpc_replicado` NaN                                               |
| Consistencia validacion    | si `estado_validacion == 'no_disponible'` → `inpc_inegi`, `error_absoluto`, `error_relativo` NaN |
| Al menos una fila          | el DataFrame no está vacío                                                                       |

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

| Invariante              | Regla                                              |
| ----------------------- | -------------------------------------------------- |
| Versión válida          | `version` in `{2010, 2013, 2018, 2024}`            |
| `nivel_faltante` válido | valores in `{'periodo', 'estructural'}`            |
| `tipo_faltante` válido  | valores in `{'indice', 'ponderador'}`              |
| Consistencia índice     | si `tipo_faltante == 'indice'` → `periodo` no NaN  |
| Consistencia ponderador | si `tipo_faltante == 'ponderador'` → `periodo` NaN |

El DataFrame puede estar vacío — cero filas indica que no se detectaron faltantes en la corrida.

---

### 5.8 CalculadorBase

**Representación:** `ABC` interno del dominio. Define el contrato que deben cumplir
`LaspeyresDirecto` y `LaspeyresEncadenado`. Se usa `ABC` (no `Protocol`) porque ambas
implementaciones viven dentro del dominio y su relación con la base debe ser explícita.

```python
from abc import ABC, abstractmethod

class CalculadorBase(ABC):
    @abstractmethod
    def calcular(
        self,
        canasta: CanastaCanonica,
        serie: SerieNormalizada,
    ) -> ResultadoCalculo: ...
```

**Selección de implementación — `estrategia.py`:**

La selección vive en `dominio/calculo/estrategia.py` como función de fábrica.
La canasta codifica qué estrategia usar: `encadenamiento` vacío → directo,
con valores → encadenado.

```python
def para_canasta(canasta: CanastaCanonica) -> CalculadorBase:
    if canasta.df["encadenamiento"].isna().all():
        return LaspeyresDirecto()
    return LaspeyresEncadenado()
```

| Versión    | Implementación        | Archivo                         |
| ---------- | --------------------- | ------------------------------- |
| 2010, 2018 | `LaspeyresDirecto`    | `dominio/calculo/laspeyres.py`  |
| 2013, 2024 | `LaspeyresEncadenado` | `dominio/calculo/encadenado.py` |

El caso de uso `calcular_inpc.py` no necesita saber qué estrategia existe —
solo llama `para_canasta(canasta).calcular(canasta, serie)`.

---

### 5.9 tipos.py — tipos compartidos

`tipos.py` define los tipos compartidos por los puertos, los casos de uso y la API.
No contienen lógica de negocio — son estructuras de datos puras.

#### VersionCanasta

Alias de tipo que restringe los valores de versión al conjunto soportado por el sistema.

```python
VersionCanasta = Literal[2010, 2013, 2018, 2024]
```

**Nota:** reemplaza `int` como tipo de `version` en todos los modelos de §5.1–§5.7.

---

#### ManifestCorrida

Registra la intención de la corrida: qué archivos se usaron, qué versión y cuándo.
Se crea al inicio del pipeline, antes de calcular nada.

```python
@dataclass
class ManifestCorrida:
    id_corrida: str
    version: VersionCanasta
    ruta_canasta: Path
    ruta_series: Path
    fecha: datetime
```

| Campo          | Tipo             | Notas                              |
| -------------- | ---------------- | ---------------------------------- |
| `id_corrida`   | `str`            | UUID generado por el caso de uso   |
| `version`      | `VersionCanasta` |                                    |
| `ruta_canasta` | `Path`           |                                    |
| `ruta_series`  | `Path`           |                                    |
| `fecha`        | `datetime`       | momento de inicio de la corrida    |

No valida invariantes al construirse.

---

#### ResultadoCorrida

Agrupa todos los artefactos producidos por el pipeline.
Es lo que devuelve `ejecutar_corrida.py` al final.

```python
@dataclass
class ResultadoCorrida:
    manifest: ManifestCorrida
    resultado: ResultadoCalculo
    resumen: ResumenValidacion
    reporte: ReporteDetalladoValidacion
    diagnostico: DiagnosticoFaltantes
```

| Campo        | Tipo                          | Notas                              |
| ------------ | ----------------------------- | ---------------------------------- |
| `manifest`   | `ManifestCorrida`             | archivos usados, versión, fecha    |
| `resultado`  | `ResultadoCalculo`            | INPC replicado por periodo         |
| `resumen`    | `ResumenValidacion`           | vista compacta de la corrida       |
| `reporte`    | `ReporteDetalladoValidacion`  | comparación periodo a periodo      |
| `diagnostico`| `DiagnosticoFaltantes`        | faltantes detectados               |

No valida invariantes al construirse.
El `id_corrida` se accede vía `corrida.manifest.id_corrida`.

---

### 5.10 correspondencia.py

Función del dominio que verifica y alinea los genéricos entre una `CanastaCanonica`
y una `SerieNormalizada`. Es el paso previo obligatorio al cálculo.

```python
def alinear_genericos(
    canasta: CanastaCanonica,
    serie: SerieNormalizada,
) -> SerieNormalizada: ...
```

**Qué hace:**

1. Verifica que cada genérico del índice de la canasta tenga correspondencia en el índice de la serie
2. Si falta alguno → lanza `CorrespondenciaInsuficiente` con la lista de genéricos no encontrados
3. Filtra la serie para quedarse solo con los genéricos de la canasta
4. Ordena el índice de la serie para que coincida con el orden de la canasta
5. Devuelve la `SerieNormalizada` resultante

**Precondición:** la normalización (quitar tildes + lowercase) ya fue aplicada por
`LectorSeries` al producir `generico_limpio`. Esta función compara strings directos,
sin normalización adicional.

**Contrato de fallo:**

| Condición | Excepción |
| --------- | --------- |
| Algún genérico de la canasta no tiene serie | `CorrespondenciaInsuficiente(faltantes)` |

Donde `faltantes` es la lista de nombres de genéricos de la canasta que no se encontraron
en la serie.

---

## 6. Contratos de puertos

Los puertos son los contratos que el dominio impone a sus dependencias externas.
Cada puerto es un `Protocol` de Python — el dominio depende de la interfaz, no de la
implementación concreta. Un nuevo adaptador (xlsx, SQL, API, etc.) solo necesita
implementar el puerto correspondiente sin tocar el dominio.

`VersionCanasta`, `ManifestCorrida` y `ResultadoCorrida` se definen en `dominio/tipos.py`
— ver §5.9.

---

### 6.1 LectorCanasta

Recibe una fuente de datos y devuelve una `CanastaCanonica` lista para usar.
La versión se pasa explícitamente para que el lector sepa qué columnas esperar
y cómo interpretar el archivo.

```python
class LectorCanasta(Protocol):
    def leer(self, ruta: Path, version: VersionCanasta) -> CanastaCanonica: ...
```

---

### 6.2 LectorSeries

Recibe un archivo de series y devuelve una `SerieNormalizada` lista para usar.
Resuelve internamente la orientación (horizontal/vertical), la presencia de
metadatos y el encoding. No filtra por versión — esa responsabilidad es del
caso de uso.

```python
class LectorSeries(Protocol):
    def leer(self, ruta: Path) -> SerieNormalizada: ...
```

---

### 6.3 FuenteValidacion

Obtiene el INPC publicado por el INEGI para los periodos solicitados.
Devuelve `None` por periodo cuando el INEGI no tiene dato para ese periodo.
Lanza excepción cuando la fuente no está disponible — el caso de uso la captura
y marca la validación como `no_disponible`.

```python
class FuenteValidacion(Protocol):
    def obtener(self, periodos: list[Periodo]) -> dict[Periodo, float | None]: ...
```

---

### 6.4 EscritorResultados

Exporta los artefactos de resultado al usuario. `ResultadoCalculo` no se exporta
directamente — sus datos están contenidos en `ReporteDetalladoValidacion`.

```python
class EscritorResultados(Protocol):
    def escribir_reporte(self, reporte: ReporteDetalladoValidacion, ruta: Path) -> None: ...
    def escribir_diagnostico(self, diagnostico: DiagnosticoFaltantes, ruta: Path) -> None: ...
```

---

### 6.5 RepositorioCorridas

Persiste y recupera los metadatos de cada corrida. `listar()` devuelve todos los
`id_corrida` registrados — necesario para reconstruir historiales y unir resultados
de distintas versiones.

```python
class RepositorioCorridas(Protocol):
    def guardar(self, id_corrida: str, manifest: ManifestCorrida) -> None: ...
    def obtener(self, id_corrida: str) -> ManifestCorrida: ...
    def listar(self) -> list[str]: ...
```

> **Pendiente:** `id_corrida` en `guardar` es redundante — ya está dentro de
> `manifest.id_corrida`. Revisar cuando se implemente el adaptador.

---

### 6.6 AlmacenArtefactos

Persiste y recupera los artefactos generados por una corrida para trazabilidad
interna. Opera con DataFrames genéricos — no necesita conocer el tipo de artefacto,
solo el nombre con el que se guardó.

```python
class AlmacenArtefactos(Protocol):
    def guardar(self, id_corrida: str, nombre: str, df: pd.DataFrame) -> None: ...
    def obtener(self, id_corrida: str, nombre: str) -> pd.DataFrame: ...
```

---

### Orquestación del pipeline — ejecutar_corrida.py

`ejecutar_corrida.py` es el caso de uso central. Orquesta todos los pasos del pipeline
en un solo llamado y es lo que `api/corrida.py` invoca internamente.

**Entradas:** `ruta_canasta: Path`, `ruta_series: Path`, `version: VersionCanasta`

**Pasos en orden:**

1. Generar `id_corrida` (UUID) y crear `ManifestCorrida`
2. `LectorCanasta.leer(ruta_canasta, version)` → `CanastaCanonica`
3. `LectorSeries.leer(ruta_series)` → `SerieNormalizada` (no depende del paso 2 — podrían correr en paralelo, pero en v1 se ejecutan secuencialmente)
4. `correspondencia.py` — valida y alinea genérico↔genérico
5. `para_canasta(canasta).calcular(canasta, serie)` → `ResultadoCalculo`
6. `FuenteValidacion.obtener(periodos)` — si lanza `ErrorValidacion`: continúa con validación `no_disponible`
7. `validar_inpc.py` — recibe `ResultadoCalculo`, llama a `FuenteValidacion`, construye `ResumenValidacion`, `ReporteDetalladoValidacion`, `DiagnosticoFaltantes`
8. `RepositorioCorridas.guardar(id_corrida, manifest)` + `AlmacenArtefactos.guardar(...)` para canasta, series y artefactos → `data/runs/<id_corrida>/`
9. `EscritorResultados.escribir_reporte()` + `escribir_diagnostico()` → `output/`
10. Devolver `ResultadoCorrida`

**Extensibilidad:** el caso de uso no necesita cambiar al agregar nuevas versiones —
la selección de estrategia en `para_canasta()` absorbe la extensión.

**Errores:** cualquier `ErrorImportacion`, `ErrorDominio` o `ErrorCalculo` falla la corrida
inmediatamente. `ErrorValidacion` no falla la corrida — ver §7.

---

## 7. Estrategia de errores

### 7.1 Jerarquía de excepciones

Todas las excepciones del sistema heredan de `ReplicaInpcError` y se definen
en `dominio/errores.py`. Las capas superiores solo necesitan importar desde el
dominio — nunca desde infraestructura.

```python
# Base
class ReplicaInpcError(Exception): ...

# Errores de importación — fallan la corrida inmediatamente
class ErrorImportacion(ReplicaInpcError): ...
class ArchivoNoEncontrado(ErrorImportacion): ...
class ArchivoVacio(ErrorImportacion): ...
class ArchivoCorrupto(ErrorImportacion): ...
class EncodingNoLegible(ErrorImportacion): ...
class OrientacionNoDetectable(ErrorImportacion): ...
class ColumnasMinFaltantes(ErrorImportacion): ...
class CanastaNoSoportada(ErrorImportacion): ...
class PeriodoNoInterpretable(ErrorImportacion): ...
class VersionNoCoincide(ErrorImportacion): ...

# Errores de dominio — invariante violado al construir un contrato
class ErrorDominio(ReplicaInpcError): ...
class InvarianteViolado(ErrorDominio): ...

# Errores de cálculo — fallan la corrida inmediatamente
class ErrorCalculo(ReplicaInpcError): ...
class CorrespondenciaInsuficiente(ErrorCalculo):
    def __init__(self, faltantes: list[str]) -> None: ...
class PonderadorFaltante(ErrorCalculo): ...
class SerieVacia(ErrorCalculo): ...
class CanastaSinGenericos(ErrorCalculo): ...

# Errores de validación — no fallan la corrida
class ErrorValidacion(ReplicaInpcError): ...
class FuenteNoDisponible(ErrorValidacion): ...
class RespuestaInvalida(ErrorValidacion): ...
```

### 7.2 Propagación

Los errores se lanzan lo más cerca posible de donde ocurren y se capturan
en el caso de uso, que decide qué hacer con ellos. Las capas intermedias
no capturan ni envuelven — dejan pasar.

| Error              | Dónde se lanza                     | Quién lo captura | Efecto                     |
| ------------------ | ---------------------------------- | ---------------- | -------------------------- |
| `ErrorImportacion` | adaptador (infraestructura)        | caso de uso      | falla la corrida           |
| `ErrorDominio`     | constructor del contrato (dominio) | caso de uso      | falla la corrida           |
| `ErrorCalculo`     | dominio (cálculo)                  | caso de uso      | falla la corrida           |
| `ErrorValidacion`  | adaptador (infraestructura)        | caso de uso      | validación `no_disponible` |

### 7.3 Traducción en adaptadores

Los adaptadores traducen excepciones externas a errores propios del sistema
antes de que lleguen al caso de uso. El caso de uso nunca ve `FileNotFoundError`,
`UnicodeDecodeError` ni excepciones de librerías externas.

```python
# Ejemplo en lector_series_csv.py
try:
    df = pd.read_csv(ruta, encoding="cp1252")
except FileNotFoundError:
    raise ArchivoNoEncontrado(ruta)
except UnicodeDecodeError:
    raise EncodingNoLegible(ruta)
```

Esto mantiene los casos de uso independientes de las librerías concretas
y hace que los errores sean predecibles desde cualquier adaptador.

---

## 8. Estrategia de testing

### 8.1 Tipos de test

| Componente            | Tipo        | Nota                                                                            |
| --------------------- | ----------- | ------------------------------------------------------------------------------- |
| Contratos del dominio | Unit        |                                                                                 |
| `Periodo`             | Unit        | Explícito — parseo, orden, hash, `to_timestamp()`                               |
| Lógica de cálculo     | Unit        | Solo `LaspeyresDirecto` en v1; `LaspeyresEncadenado` se agrega con canasta 2024 |
| `correspondencia.py`  | Unit        |                                                                                 |
| Adaptadores CSV       | Integration | Archivos reales                                                                 |
| Casos de uso          | Integration | Archivos reales                                                                 |
| `api/corrida.py`      | Integration | Archivos reales                                                                 |
| API INEGI             | Integration | Mockeada — ver §8.3                                                             |
| `interfaces/cli.py`   | ——————————— | Fuera de v1                                                                     |

---

### 8.2 Fixtures

Los fixtures viven en `tests/fixtures/` y son de dos tipos.

**Sintéticos** — construidos a mano con 5-10 genéricos ficticios. Son la base del suite.
Cubren las variantes de archivo de series:

| Orientación | Metadatos | Ruido                                               |
| ----------- | --------- | --------------------------------------------------- |
| Horizontal  | Con       | Sin                                                 |
| Horizontal  | Sin       | Sin                                                 |
| Vertical    | Con       | Sin                                                 |
| Vertical    | Sin       | Sin                                                 |
| Horizontal  | Con       | Con ruido (subclasificaciones, índices adicionales) |

Un CSV de canasta sintético por versión soportada en v1.

**Test de humo** — usa los archivos reales de `docs/requerimientos/` para verificar
que el sistema procesa un archivo INEGI real sin errores. No verifica el resultado
numérico en detalle.

---

### 8.3 Mock de la API del INEGI

`FuenteValidacion` se mockea en todos los tests — nunca se llama a la API real.
Los mocks cubren cuatro escenarios:

| Escenario          | Comportamiento esperado                                |
| ------------------ | ------------------------------------------------------ |
| Respuesta normal   | Devuelve valores para todos los periodos               |
| Periodo sin dato   | Devuelve `None` para algún periodo                     |
| API no disponible  | Lanza excepción → validación `no_disponible`           |
| Respuesta inválida | Lanza `RespuestaInvalida` → validación `no_disponible` |

```python
# Ejemplo de mock para respuesta normal
class FuenteValidacionFalsa:
    def obtener(self, periodos: list[Periodo]) -> dict[Periodo, float | None]:
        return {p: 134.471 for p in periodos}
```

---

### 8.4 Criterio de suficiencia para v1

El suite es suficiente cuando cubre los siguientes comportamientos:

- Corrida completa exitosa (canasta 2018, series completas)
- Corrida con faltantes en series → periodos en `null`
- Corrida con faltante en ponderador → falla inmediata
- Corrida con API no disponible → continúa, validación `no_disponible`
- Corrida con respuesta inválida de API → continúa, validación `no_disponible`
- Invariantes de todos los contratos del dominio
- `Periodo`: parseo, orden, hash, `to_timestamp()`
- Las 4 variantes de archivo de series (con/sin metadatos × horizontal/vertical)
- Correspondencia: match exitoso; match fallido por cobertura insuficiente
- Test de humo con datos reales (canasta 2018)

---

## 9. Decisiones y razones

### 9.1 `SerieNormalizada` en formato ancho

**Decisión:** DataFrame con `generico_limpio` como índice y objetos `Periodo` como columnas.

**Alternativa considerada:** formato largo — columnas `generico_limpio`, `periodo`, `indice`.

**Razón:** el cálculo Laspeyres sobre todos los periodos es una multiplicación matricial directa entre el vector de ponderadores y la matriz de índices. El formato ancho lo hace eficiente y legible. El formato largo requeriría un pivot antes de cada cálculo.

---

### 9.2 `generico_original` como diccionario

**Decisión:** `generico_original` vive en `serie.mapeo` como `dict[str, str]` (`generico_limpio → generico_original`), fuera del DataFrame.

**Alternativa considerada:** columna opcional en el DataFrame de `SerieNormalizada`.

**Razón:** `generico_original` es dato de trazabilidad, no de cálculo. Mantenerlo fuera del DataFrame evita que aparezca en operaciones sobre la matriz de índices y deja claro su propósito.

---

### 9.3 Correspondencia genérico↔genérico por normalización exacta

**Decisión:** matching exacto después de normalizar — quitar tildes + lowercase (`unicodedata`). `rapidfuzz` removido del stack.

**Alternativa considerada:** matching fuzzy con `rapidfuzz`.

**Razón:** la divergencia entre nombres de series y canasta es sistemática y determinista — los ponderadores fueron extraídos sin tildes mientras las series las conservan. Después de normalizar ambos lados, los 299 genéricos de la canasta 2018 coinciden exactamente. El fuzzy resolvía un problema que la normalización resuelve de forma predecible y sin riesgo de falsos positivos entre genéricos con nombres parecidos.

---

### 9.4 pandas en el dominio

**Decisión:** los contratos del dominio usan DataFrames de pandas directamente.

**Alternativa considerada:** dominio sin dependencias externas, pandas solo en infraestructura.

**Razón:** el proyecto es notebook-first. Aislar pandas del dominio agregaría una capa de conversión sin beneficio real — el dominio siempre va a operar sobre estructuras tabulares. El hexágono aísla formato y fuente de datos, no librerías de procesamiento.

---

### 9.5 `ponderador` y `encadenamiento` como `str`

**Decisión:** se almacenan como `str` en `CanastaCanonica`. La conversión a `float` ocurre solo en el momento del cálculo.

**Alternativa considerada:** almacenar directamente como `float`.

**Razón:** los archivos fuente tienen precisión decimal que puede perderse en la conversión binaria a `float`. Almacenar como `str` preserva el valor exacto extraído del CSV oficial. La conversión a `float` en el cálculo no acumula error adicional porque se aplica una sola vez por operación.

---

### 9.6 `Periodo` como tipo propio

**Decisión:** value object `Periodo` con atributos `año`, `mes`, `quincena`.

**Alternativa considerada:** `str` con formato `"1Q Ene 2020"` o `pd.Timestamp`.

**Razón:** una quincena no tiene representación natural en Python ni en pandas. `str` no permite sorting natural ni uso como clave hashable confiable. `pd.Timestamp` requiere una convención arbitraria para el día (día 1 o día 16) que no es un dato real. `Periodo` encapsula esa convención en `to_timestamp()` y expone sorting, hash e igualdad de forma explícita.

---

### 9.7 Categorías de clasificación version-específicas

**Decisión:** las columnas `CCIF`, `COG`, `inflacion_1/2/3` en `CanastaCanonica` usan `pd.Categorical` con las categorías de cada versión. No hay mapeo cross-versión en v1.

**Advertencia para v2:** entre versiones hay cambios de nombre de categorías (ej. `"Comunicaciones"` en 2018 → `"Información y comunicación"` en 2024). Un join directo entre canastas de distintas versiones producirá categorías no coincidentes. Cuando se implementen subíndices en v2, se requerirá un componente de mapeo explícito entre categorías de versiones.

---

### 9.8 Tolerancia numérica por versión

**Decisión:** la tolerancia para marcar `estado_validacion = diferencia_detectada` es configurable por versión:

| Versión | Tolerancia (`error_absoluto`) |
| ------- | ----------------------------- |
| 2018    | `<= 0.0005`                   |
| 2024    | `<= 0.005`                    |

**Razón:** las diferencias observadas entre el INPC replicado y el publicado por el INEGI varían por versión — la canasta 2024 usa Laspeyres encadenado con normalización, lo que introduce mayor variación numérica acumulada. Una tolerancia única global sería demasiado estricta para 2024 o demasiado laxa para 2018.
