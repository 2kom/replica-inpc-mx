# Diseño del sistema — replica-inpc-mx

Documento vivo. Refleja el estado actual de las decisiones de diseño del sistema.
El historial de cambios vive en git.

---

## Índice

- [Diseño del sistema — replica-inpc-mx](#diseño-del-sistema--replica-inpc-mx)
  - [Índice](#índice)
  - [1. Arquitectura](#1-arquitectura)
    - [1.1 Patrón principal: Hexagonal (Ports \& Adapters)](#11-patrón-principal-hexagonal-ports--adapters)
    - [1.2 Patrones de diseño](#12-patrones-de-diseño)
      - [Strategy — cálculo del INPC](#strategy--cálculo-del-inpc)
      - [Facade — api/corrida.py](#facade--apicorridapy)
      - [Repository — persistencia de corridas y artefactos](#repository--persistencia-de-corridas-y-artefactos)
      - [Adapter — infraestructura](#adapter--infraestructura)
  - [2. Estructura del proyecto](#2-estructura-del-proyecto)
  - [3. Stack técnico](#3-stack-técnico)
  - [4. Flujo de datos](#4-flujo-de-datos)
  - [5. Contratos del dominio](#5-contratos-del-dominio)
    - [5.1 CanastaCanonica](#51-canastacanonica)
    - [5.2 SerieNormalizada](#52-serienormalizada)
    - [5.3 Periodo](#53-periodo)
    - [5.4 ResultadoCalculo](#54-resultadocalculo)
    - [5.5 ResumenValidacion](#55-resumenvalidacion)
    - [5.6 ReporteDetalladoValidacion](#56-reportedetalladovalidacion)
    - [5.7 DiagnosticoFaltantes](#57-diagnosticofaltantes)
    - [5.8 CalculadorBase](#58-calculadorbase)
    - [5.9 tipos.py — tipos compartidos](#59-tipospy--tipos-compartidos)
      - [VersionCanasta](#versioncanasta)
      - [RANGOS\_VALIDOS](#rangos_validos)
      - [ManifestCorrida](#manifestcorrida)
      - [ResultadoCorrida](#resultadocorrida)
    - [5.10 correspondencia.py](#510-correspondenciapy)
    - [5.11 validar\_inpc.py](#511-validar_inpcpy)
  - [6. Capa de aplicación](#6-capa-de-aplicación)
    - [6.1 Puertos](#61-puertos)
      - [6.1.1 LectorCanasta](#611-lectorcanasta)
      - [6.1.2 LectorSeries](#612-lectorseries)
      - [6.1.3 FuenteValidacion](#613-fuentevalidacion)
      - [6.1.4 EscritorResultados](#614-escritorresultados)
      - [6.1.5 RepositorioCorridas](#615-repositoriocorridas)
      - [6.1.6 AlmacenArtefactos](#616-almacenartefactos)
    - [6.2 EjecutarCorrida](#62-ejecutarcorrida)
  - [7. Infraestructura](#7-infraestructura)
    - [7.1 Formato del CSV canasta](#71-formato-del-csv-canasta)
    - [7.2 Formato del CSV de series](#72-formato-del-csv-de-series)
    - [7.3 Repositorio de corridas (filesystem)](#73-repositorio-de-corridas-filesystem)
    - [7.4 Almacén de artefactos (filesystem)](#74-almacén-de-artefactos-filesystem)
  - [8. Estrategia de errores](#8-estrategia-de-errores)
    - [8.1 Jerarquía de excepciones](#81-jerarquía-de-excepciones)
    - [8.2 Propagación](#82-propagación)
    - [8.3 Traducción en adaptadores](#83-traducción-en-adaptadores)
  - [9. Estrategia de testing](#9-estrategia-de-testing)
    - [9.1 Tipos de test](#91-tipos-de-test)
    - [9.2 Fixtures](#92-fixtures)
    - [9.3 Mock de la API del INEGI](#93-mock-de-la-api-del-inegi)
    - [9.4 Criterio de suficiencia para v1](#94-criterio-de-suficiencia-para-v1)
  - [10. Decisiones y razones](#10-decisiones-y-razones)
    - [10.1 `SerieNormalizada` en formato ancho](#101-serienormalizada-en-formato-ancho)
    - [10.2 `generico_original` como diccionario](#102-generico_original-como-diccionario)
    - [10.3 Correspondencia genérico↔genérico por normalización exacta](#103-correspondencia-genéricogenérico-por-normalización-exacta)
    - [10.4 pandas en el dominio](#104-pandas-en-el-dominio)
    - [10.5 `ponderador` y `encadenamiento` como `str`](#105-ponderador-y-encadenamiento-como-str)
    - [10.6 `Periodo` como tipo propio](#106-periodo-como-tipo-propio)
    - [10.7 Categorías de clasificación version-específicas](#107-categorías-de-clasificación-version-específicas)
    - [10.8 Tolerancia numérica por versión](#108-tolerancia-numérica-por-versión)
    - [10.9 Reglas de `estado_corrida`](#109-reglas-de-estado_corrida)
    - [10.10 Detección de `null_por_faltantes`](#1010-detección-de-null_por_faltantes)
    - [10.11 Firma de `validar_inpc.py`](#1011-firma-de-validar_inpcpy)
    - [10.12 `id_corrida` en `ResultadoCalculo`](#1012-id_corrida-en-resultadocalculo)
  - [11. Gaps conocidos y mejoras futuras](#11-gaps-conocidos-y-mejoras-futuras)
    - [11.1 `estado_validacion_global` no distingue cobertura parcial](#111-estado_validacion_global-no-distingue-cobertura-parcial)
    - [11.2 Validación por niveles en `LectorCanastaCsv`](#112-validación-por-niveles-en-lectorcanastacsv)
    - [11.3 Agregados CCIF en `LectorSeriesCsv`](#113-agregados-ccif-en-lectorseriescsv)
    - [11.4 Detección dinámica del header en `LectorSeriesCsv`](#114-detección-dinámica-del-header-en-lectorseriescsv)
    - [11.5 ñ en canasta intermedia](#115-ñ-en-canasta-intermedia)
    - [11.6 Formato de series BIE en versiones 2010 y 2013](#116-formato-de-series-bie-en-versiones-2010-y-2013)
    - [11.7 Cobertura parcial de periodos no reportada explícitamente](#117-cobertura-parcial-de-periodos-no-reportada-explícitamente)
    - [11.8 `AlmacenArtefactos.obtener` devuelve índice como string](#118-almacenartefactosobtener-devuelve-índice-como-string)

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

La persistencia es opcional por corrida — ver §6.2. Cuando `persistir=False`,
estos puertos no se invocan y pueden ser `None`.

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
│  · normaliza índice   │       │                           │
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
        id_corrida: str,
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

#### RANGOS_VALIDOS

Diccionario que define los periodos válidos por versión de canasta. Es conocimiento
del dominio — los rangos son fijos y están determinados por las fechas de vigencia
de cada canasta base del INPC.

```python
RANGOS_VALIDOS: dict[VersionCanasta, tuple[Periodo, Periodo | None]] = {
    2010: (Periodo(2010, 12, 2), Periodo(2013, 4, 1)),
    2013: (Periodo(2013, 4, 1), Periodo(2018, 7, 2)),
    2018: (Periodo(2018, 7, 2), Periodo(2024, 7, 2)),
    2024: (Periodo(2024, 7, 2), None),  # None = hasta el último periodo disponible
}
```

El `fin = None` para la canasta 2024 indica que no hay límite superior — se usan
todos los periodos disponibles desde `2Q Jul 2024` en adelante.

`RANGOS_VALIDOS` se usa en `ejecutar_corrida.py` para filtrar la `SerieNormalizada`
antes de pasarla a `correspondencia.py` — ver §6.2 paso 3.5.

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

### 5.11 validar_inpc.py

Función del dominio que construye los tres artefactos de validación a partir del resultado del cálculo y los datos del INEGI ya obtenidos por el caso de uso.

```python
def validar(
    resultado: ResultadoCalculo,
    inegi: dict[Periodo, float | None],
    canasta: CanastaCanonica,
    serie: SerieNormalizada,
    id_corrida: str,
) -> tuple[ResumenValidacion, ReporteDetalladoValidacion, DiagnosticoFaltantes]:
```

| Parámetro   | Tipo                            | Notas                                                    |
| ----------- | ------------------------------- | -------------------------------------------------------- |
| `resultado` | `ResultadoCalculo`              | INPC calculado por periodo                               |
| `inegi`     | `dict[Periodo, float \| None]`  | Dict vacío `{}` si la fuente no estaba disponible        |
| `canasta`   | `CanastaCanonica`               | Para contar genéricos esperados y ponderadores totales   |
| `serie`     | `SerieNormalizada`              | Para calcular cobertura por periodo — en v1 siempre 100% |
| `id_corrida`| `str`                           | Para etiquetar los artefactos                            |

**Comportamiento cuando `inegi` es vacío:** todos los periodos reciben `estado_validacion = 'no_disponible'` y los campos de error quedan en `NaN`. `estado_validacion_global` en `ResumenValidacion` = `'no_disponible'`.

---

## 6. Capa de aplicación

Contiene los contratos de puertos y los casos de uso. No conoce CSV, filesystem ni APIs
— solo opera con los contratos definidos en esta sección.

---

### 6.1 Puertos

Los puertos son los contratos que el dominio impone a sus dependencias externas.
Cada puerto es un `Protocol` de Python — el dominio depende de la interfaz, no de la
implementación concreta. Un nuevo adaptador (xlsx, SQL, API, etc.) solo necesita
implementar el puerto correspondiente sin tocar el dominio.

`VersionCanasta`, `ManifestCorrida` y `ResultadoCorrida` se definen en `dominio/tipos.py`
— ver §5.9.

---

#### 6.1.1 LectorCanasta

Recibe una fuente de datos y devuelve una `CanastaCanonica` lista para usar.
La versión se pasa explícitamente para que el lector sepa qué columnas esperar
y cómo interpretar el archivo.

```python
class LectorCanasta(Protocol):
    def leer(self, ruta: Path, version: VersionCanasta) -> CanastaCanonica: ...
```

---

#### 6.1.2 LectorSeries

Recibe un archivo de series y devuelve una `SerieNormalizada` lista para usar.
Resuelve internamente la orientación (horizontal/vertical), la presencia de
metadatos y el encoding. No filtra por versión — esa responsabilidad es del
caso de uso.

```python
class LectorSeries(Protocol):
    def leer(self, ruta: Path) -> SerieNormalizada: ...
```

---

#### 6.1.3 FuenteValidacion

Obtiene el INPC publicado por el INEGI para los periodos solicitados.
Devuelve `None` por periodo cuando el INEGI no tiene dato para ese periodo.
Lanza excepción cuando la fuente no está disponible — el caso de uso la captura
y marca la validación como `no_disponible`.

```python
class FuenteValidacion(Protocol):
    def obtener(self, periodos: list[Periodo]) -> dict[Periodo, float | None]: ...
```

---

#### 6.1.4 EscritorResultados

Exporta los artefactos de resultado al usuario. `ResultadoCalculo` no se exporta
directamente — sus datos están contenidos en `ReporteDetalladoValidacion`.

```python
class EscritorResultados(Protocol):
    def escribir_reporte(self, reporte: ReporteDetalladoValidacion, ruta: Path) -> None: ...
    def escribir_diagnostico(self, diagnostico: DiagnosticoFaltantes, ruta: Path) -> None: ...
```

---

#### 6.1.5 RepositorioCorridas

Persiste y recupera los metadatos de cada corrida. `listar()` devuelve todos los
`id_corrida` registrados — necesario para reconstruir historiales y unir resultados
de distintas versiones.

```python
class RepositorioCorridas(Protocol):
    def guardar(self, manifest: ManifestCorrida) -> None: ...
    def obtener(self, id_corrida: str) -> ManifestCorrida: ...
    def listar(self) -> list[str]: ...
```

---

#### 6.1.6 AlmacenArtefactos

Persiste y recupera los artefactos **computados** por el pipeline. No almacena
los insumos (canasta, serie) — su trazabilidad queda cubierta por las rutas en
`ManifestCorrida`. Los artefactos que guarda son: `resultado`, `resumen`,
`reporte` y `diagnostico`.

Opera con DataFrames genéricos — no necesita conocer el tipo de artefacto,
solo el nombre con el que se guardó.

```python
class AlmacenArtefactos(Protocol):
    def guardar(self, id_corrida: str, nombre: str, df: pd.DataFrame) -> None: ...
    def obtener(self, id_corrida: str, nombre: str) -> pd.DataFrame: ...
```

> **Formato:** el adaptador filesystem usa **Parquet** (`pyarrow`), ya incluido en
> las dependencias. Parquet preserva la estructura del MultiIndex (niveles y nombres)
> de forma nativa — necesario para la combinación futura de reportes entre versiones
> y subíndices. Los índices `Periodo` se serializan a string (`str(Periodo)`) antes
> de guardar; `obtener` los devuelve como string — ver §11.8.

---

### 6.2 EjecutarCorrida

Caso de uso central. Orquesta todos los pasos del pipeline en un solo llamado
y es lo que `api/corrida.py` invoca internamente.

Los puertos se inyectan en el constructor — el composition root es `api/corrida.py`.
`ruta_salida` es configuración del entorno (fija por deployment), no varía por corrida.

```python
class EjecutarCorrida:
    def __init__(
        self,
        lector_canasta: LectorCanasta,
        lector_series: LectorSeries,
        fuente_validacion: FuenteValidacion,
        repositorio: RepositorioCorridas | None = None,
        almacen: AlmacenArtefactos | None = None,
        escritor: EscritorResultados | None = None,
        ruta_salida: Path | None = None,
    ) -> None: ...

    def ejecutar(
        self,
        ruta_canasta: Path,
        ruta_series: Path,
        version: VersionCanasta,
        persistir: bool = False,
    ) -> ResultadoCorrida: ...
```

**Pasos en orden:**

1. Si `persistir=True` y alguno de `repositorio`, `almacen`, `escritor`, `ruta_salida` es `None` → lanza `ErrorConfiguracion`
2. Generar `id_corrida` (UUID) y crear `ManifestCorrida`
3. `LectorCanasta.leer(ruta_canasta, version)` → `CanastaCanonica`
4. `LectorSeries.leer(ruta_series)` → `SerieNormalizada` (todos los periodos del archivo; no depende del paso 3)
5. Filtrar columnas de `serie` a `RANGOS_VALIDOS[version]` → `SerieNormalizada` con solo los periodos válidos. Si ninguna columna cae en el rango → `PeriodosInsuficientes`
6. `correspondencia.py` — valida y alinea genérico↔genérico
7. `para_canasta(canasta).calcular(canasta, serie, id_corrida)` → `ResultadoCalculo`
8. `FuenteValidacion.obtener(periodos)` — si lanza `ErrorValidacion`: continúa con validación `no_disponible`
9. `validar_inpc.py` — construye `ResumenValidacion`, `ReporteDetalladoValidacion`, `DiagnosticoFaltantes`
10. Si `persistir=True`:
    - `RepositorioCorridas.guardar(manifest)` → `data/runs/<id_corrida>/`
    - `AlmacenArtefactos.guardar(...)` para `resultado`, `resumen`, `reporte`, `diagnostico` → `data/runs/<id_corrida>/`
    - `EscritorResultados.escribir_reporte()` + `escribir_diagnostico()` → `output/`
11. Devolver `ResultadoCorrida`

**Extensibilidad:** el caso de uso no necesita cambiar al agregar nuevas versiones —
la selección de estrategia en `para_canasta()` absorbe la extensión.

**Errores:** cualquier `ErrorImportacion`, `ErrorDominio` o `ErrorCalculo` falla la corrida
inmediatamente. `ErrorValidacion` no falla la corrida — ver §8.

---

## 7. Infraestructura

Adaptadores concretos que implementan los puertos de §6.1. El dominio y la capa de
aplicación no conocen estos detalles — solo operan con los contratos.

---

### 7.1 Formato del CSV canasta

Todas las versiones de canasta (2010, 2013, 2018, 2024) comparten el mismo esquema
de CSV intermedio. Este archivo es generado en el proceso de preparación de datos
(fuera del pipeline de cálculo) a partir de los archivos fuente (.xlsx, .pdf).

**Esquema:**

| Columna                  | Tipo     | Notas                                              |
| ------------------------ | -------- | -------------------------------------------------- |
| `generico`               | `str`    | Índice — nombre del genérico                       |
| `ponderador`             | `float`  | Peso del genérico; suma 100 por versión            |
| `encadenamiento`         | `float`  | Factor de encadenamiento; vacío en 2010 y 2018     |
| `COG`                    | `str`    | Clasificación por objeto del gasto                 |
| `CCIF`                   | `str`    | Clasificación del consumo individual por finalidad |
| `inflacion 1`            | `str`    | Categoría de inflación nivel 1                     |
| `inflacion 2`            | `str`    | Categoría de inflación nivel 2                     |
| `inflacion 3`            | `str`    | Categoría de inflación nivel 3                     |
| `SCIAN 1`                | `str`    | Clasificación SCIAN nivel 1                        |
| `SCIAN 2`                | `str`    | Clasificación SCIAN nivel 2                        |
| `canasta basica`         | `str`    | `'X'` si pertenece, vacío si no                    |
| `canasta consumo minimo` | `str`    | `'X'` si pertenece, vacío si no                    |

`LectorCanastaCsv` lee `generico` como índice y convierte `ponderador` y
`encadenamiento` a `str` antes de construir `CanastaCanonica` — ver §10.5.
Las columnas de clasificación (COG, CCIF, etc.) se pasan al DataFrame sin modificar.

**Normalización del índice:** el índice `generico` se normaliza con la misma función
que `LectorSeriesCsv` aplica para producir `generico_limpio`: eliminar tildes vocálicas
(`á`→`a`, etc.), conservar `ñ`, eliminar puntuación y convertir a minúsculas. Esto
garantiza que ambas fuentes sean comparables directamente en `correspondencia.py`.
Verificado: con normalización simétrica los 299 genéricos de la canasta 2018 coinciden
exactamente con los 299 extraídos de las series BIE.

La función de normalización está implementada en `infraestructura/csv/_utils.py`
y es compartida por `LectorCanastaCsv` y `LectorSeriesCsv`.

**Adaptador:**

```python
class LectorCanastaCsv:
    def leer(self, ruta: Path, version: VersionCanasta) -> CanastaCanonica: ...
```

**Errores que lanza:**

| Error                  | Causa                                              |
| ---------------------- | -------------------------------------------------- |
| `ArchivoNoEncontrado`  | El archivo no existe en la ruta indicada           |
| `ArchivoVacio`         | El archivo existe pero está vacío                  |
| `ArchivoCorrupto`      | El archivo no es un CSV válido                     |
| `EncodingNoLegible`    | El archivo no puede decodificarse                  |
| `ColumnasMinFaltantes` | Faltan columnas requeridas del esquema canónico    |

---

### 7.2 Formato del CSV de series

Archivo descargado desde el BIE del INEGI. Todas las versiones comparten el mismo
formato de exportación con dos variantes: con columnas de metadatos o sin ellas.

**Encabezado INEGI:** siempre 5 líneas a saltar (`skiprows=5`): 4 líneas de
metadatos institucionales + 1 línea vacía.

**Orientación horizontal** (filas = genéricos, columnas = periodos):

| Columna                         | Notas                                                   |
| ------------------------------- | ------------------------------------------------------- |
| `Título` (posición 0)           | Descripción larga del genérico o agregado               |
| Metadatos opcionales            | `Periodicidad`, `Unidad`, `Base`, `Aviso`, etc.         |
| `Cifra`, `Serie`                | Presentes en ambas variantes; se descartan              |
| `1Q Ene 2018`, `2Q Ene 2018`, … | Columnas de periodo; formato `[12]Q Mes YYYY`           |

**Orientación vertical** (filas = periodos, columnas = genéricos): el `Título`
en posición 0 contiene las cadenas de periodo; el resto de columnas son los
títulos largos de las series. Se normaliza a horizontal transponiendo.

**Detección de orientación:**

1. Leer con `skiprows=5`. Si `df.columns[0] != 'Título'` → `ArchivoCorrupto` (encabezado incorrecto o skiprows desalineado).
2. Si `'Cifra' in df.columns` → horizontal.
3. Si `'Cifra' in df.iloc[:, 0].values` → vertical.
4. Si ninguno → `OrientacionNoDetectable`.

El metadata (`Periodicidad`, `Unidad`, `Base`, etc.) se descarta implícitamente: en horizontal se conservan solo columnas cuyo nombre coincide con el patrón de periodo; en vertical se conservan solo filas cuyo `Título` coincide con ese patrón.

**Extracción del genérico desde `Título`:** se aplica regex `\b\d{3}\b\s*(.*)`
sobre cada fila. Solo las filas con código de 3 dígitos son genéricos — el resto
son agregados CCIF y se descartan (ver §11.3).

**Normalización de nombres:** se eliminan tildes vocálicas (`á`→`a`, etc.),
se conserva `ñ`, se elimina puntuación y se pone en minúsculas. El resultado
es `generico_limpio`; el nombre antes de normalizar es `generico_original`.
Implementada en `infraestructura/csv/_utils.py`, compartida con `LectorCanastaCsv`.

**Parseo de periodos:** `"1Q Ene 2018"` → `Periodo(2018, 1, 1)`. Mes en
español abreviado (`Ene`…`Dic`). Se usa `Periodo.desde_str()` internamente;
si el string no puede parsearse lanza `PeriodoNoInterpretable` directamente
(la traducción ocurre en `periodos.py`, no en el adaptador).

**Adaptador:**

```python
class LectorSeriesCsv:
    def leer(self, ruta: Path) -> SerieNormalizada: ...
```

**Errores que lanza:**

| Error                      | Causa                                                         |
| -------------------------- | ------------------------------------------------------------- |
| `ArchivoNoEncontrado`      | El archivo no existe en la ruta indicada                      |
| `ArchivoVacio`             | El archivo existe pero está vacío                             |
| `ArchivoCorrupto`          | El archivo no es un CSV válido, o `df.columns[0] != 'Título'` |
| `EncodingNoLegible`        | No se puede decodificar con cp1252 ni con latin-1             |
| `OrientacionNoDetectable`  | No se puede determinar si el archivo es horizontal o vertical |
| `PeriodoNoInterpretable`   | Una columna de periodo no puede parsearse                     |
| `SerieVacia`               | Ninguna fila tiene código de 3 dígitos en el `Título`         |

---

### 7.3 Repositorio de corridas (filesystem)

`RepositorioCorridas` persiste el `ManifestCorrida` de cada corrida como un archivo
JSON en `data/runs/<id_corrida>/manifest.json`.

**Esquema JSON:**

```json
{
  "id_corrida": "uuid-string",
  "version": 2018,
  "ruta_canasta": "/ruta/absoluta/canasta.csv",
  "ruta_series": "/ruta/absoluta/series.csv",
  "fecha": "2026-03-30T14:23:00.123456"
}
```

| Campo          | Tipo Python    | Serialización JSON       |
| -------------- | -------------- | ------------------------ |
| `id_corrida`   | `str`          | string                   |
| `version`      | `int`          | number                   |
| `ruta_canasta` | `Path`         | string (`str(path)`)     |
| `ruta_series`  | `Path`         | string (`str(path)`)     |
| `fecha`        | `datetime`     | ISO 8601 (`isoformat()`) |

**`listar()`:** escanea los subdirectorios de `data/runs/` y devuelve los nombres
de aquellos que contienen un `manifest.json`. Directorios sin manifest se ignoran.
Si `data/runs/` no existe, devuelve lista vacía.

**Adaptador:**

```python
class RepositorioCorridasFs:
    def __init__(self, ruta_base: Path) -> None: ...
    def guardar(self, manifest: ManifestCorrida) -> None: ...
    def obtener(self, id_corrida: str) -> ManifestCorrida: ...
    def listar(self) -> list[str]: ...
```

**Errores que lanza:**

| Error                   | Causa                                         |
| ----------------------- | --------------------------------------------- |
| `ArtefactoNoEncontrado` | No existe `manifest.json` para ese id_corrida |

---

### 7.4 Almacén de artefactos (filesystem)

`AlmacenArtefactos` persiste los DataFrames computados por el pipeline como archivos
Parquet en `data/runs/<id_corrida>/<nombre>.parquet`.

**Artefactos guardados:** `resultado`, `resumen`, `reporte`, `diagnostico`.

**Serialización de `Periodo`:** los objetos `Periodo` en el índice o en columnas
se convierten a string con `str(Periodo)` antes de guardar (produce `"1Q Ene 2024"`).
El MultiIndex de `reporte` (`["periodo", "subindice"]`) se preserva gracias a Parquet.

**`obtener()`:** devuelve el DataFrame con el índice como string — no re-parsea
`Periodo`. Ver gap §11.8.

**Adaptador:**

```python
class AlmacenArtefactosFs:
    def __init__(self, ruta_base: Path) -> None: ...
    def guardar(self, id_corrida: str, nombre: str, df: pd.DataFrame) -> None: ...
    def obtener(self, id_corrida: str, nombre: str) -> pd.DataFrame: ...
```

**Errores que lanza:**

| Error                   | Causa                                             |
| ----------------------- | ------------------------------------------------- |
| `ArtefactoNoEncontrado` | No existe el archivo Parquet para ese artefacto   |

---

## 8. Estrategia de errores

### 8.1 Jerarquía de excepciones

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
class SerieVacia(ErrorImportacion): ...
class PeriodosInsuficientes(ErrorImportacion): ...

# Errores de dominio — invariante violado al construir un contrato
class ErrorDominio(ReplicaInpcError): ...
class InvarianteViolado(ErrorDominio): ...

# Errores de cálculo — fallan la corrida inmediatamente
class ErrorCalculo(ReplicaInpcError): ...
class CorrespondenciaInsuficiente(ErrorCalculo):
    def __init__(self, faltantes: list[str]) -> None: ...
class PonderadorFaltante(ErrorCalculo): ...
class CanastaSinGenericos(ErrorCalculo): ...

# Errores de validación — no fallan la corrida
class ErrorValidacion(ReplicaInpcError): ...
class FuenteNoDisponible(ErrorValidacion): ...
class RespuestaInvalida(ErrorValidacion): ...

# Errores de configuración — el sistema fue ensamblado incorrectamente
class ErrorConfiguracion(ReplicaInpcError): ...

# Errores de persistencia — fallo al leer o escribir artefactos internos
class ErrorPersistencia(ReplicaInpcError): ...
class ArtefactoNoEncontrado(ErrorPersistencia): ...
```

### 8.2 Propagación

Los errores se lanzan lo más cerca posible de donde ocurren y se capturan
en el caso de uso, que decide qué hacer con ellos. Las capas intermedias
no capturan ni envuelven — dejan pasar.

| Error              | Dónde se lanza                     | Quién lo captura | Efecto                     |
| ------------------ | ---------------------------------- | ---------------- | -------------------------- |
| `ErrorImportacion` | adaptador (infraestructura)        | caso de uso      | falla la corrida           |
| `ErrorDominio`     | constructor del contrato (dominio) | caso de uso      | falla la corrida           |
| `ErrorCalculo`     | dominio (cálculo)                  | caso de uso      | falla la corrida           |
| `ErrorValidacion`  | adaptador (infraestructura)        | caso de uso      | validación `no_disponible` |

### 8.3 Traducción en adaptadores

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

## 9. Estrategia de testing

### 9.1 Tipos de test

| Componente            | Tipo        | Nota                                                                            |
| --------------------- | ----------- | ------------------------------------------------------------------------------- |
| Contratos del dominio | Unit        |                                                                                 |
| `Periodo`             | Unit        | Explícito — parseo, orden, hash, `to_timestamp()`                               |
| Lógica de cálculo     | Unit        | Solo `LaspeyresDirecto` en v1; `LaspeyresEncadenado` se agrega con canasta 2024 |
| `correspondencia.py`  | Unit        |                                                                                 |
| Adaptadores CSV       | Integration | Archivos reales                                                                 |
| Casos de uso          | Integration | Archivos reales                                                                 |
| `api/corrida.py`      | Integration | Archivos reales                                                                 |
| API INEGI             | Integration | Mockeada — ver §9.3                                                             |
| `interfaces/cli.py`   | ——————————— | Fuera de v1                                                                     |

---

### 9.2 Fixtures

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

### 9.3 Mock de la API del INEGI

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

### 9.4 Criterio de suficiencia para v1

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

## 10. Decisiones y razones

### 10.1 `SerieNormalizada` en formato ancho

**Decisión:** DataFrame con `generico_limpio` como índice y objetos `Periodo` como columnas.

**Alternativa considerada:** formato largo — columnas `generico_limpio`, `periodo`, `indice`.

**Razón:** el cálculo Laspeyres sobre todos los periodos es una multiplicación matricial directa entre el vector de ponderadores y la matriz de índices. El formato ancho lo hace eficiente y legible. El formato largo requeriría un pivot antes de cada cálculo.

---

### 10.2 `generico_original` como diccionario

**Decisión:** `generico_original` vive en `serie.mapeo` como `dict[str, str]` (`generico_limpio → generico_original`), fuera del DataFrame.

**Alternativa considerada:** columna opcional en el DataFrame de `SerieNormalizada`.

**Razón:** `generico_original` es dato de trazabilidad, no de cálculo. Mantenerlo fuera del DataFrame evita que aparezca en operaciones sobre la matriz de índices y deja claro su propósito.

---

### 10.3 Correspondencia genérico↔genérico por normalización exacta

**Decisión:** matching exacto después de normalizar — quitar tildes + lowercase (`unicodedata`). `rapidfuzz` removido del stack.

**Alternativa considerada:** matching fuzzy con `rapidfuzz`.

**Razón:** la divergencia entre nombres de series y canasta es sistemática y determinista — los ponderadores fueron extraídos sin tildes mientras las series las conservan. Después de normalizar ambos lados, los 299 genéricos de la canasta 2018 coinciden exactamente. El fuzzy resolvía un problema que la normalización resuelve de forma predecible y sin riesgo de falsos positivos entre genéricos con nombres parecidos.

---

### 10.4 pandas en el dominio

**Decisión:** los contratos del dominio usan DataFrames de pandas directamente.

**Alternativa considerada:** dominio sin dependencias externas, pandas solo en infraestructura.

**Razón:** el proyecto es notebook-first. Aislar pandas del dominio agregaría una capa de conversión sin beneficio real — el dominio siempre va a operar sobre estructuras tabulares. El hexágono aísla formato y fuente de datos, no librerías de procesamiento.

---

### 10.5 `ponderador` y `encadenamiento` como `str`

**Decisión:** se almacenan como `str` en `CanastaCanonica`. La conversión a `float` ocurre solo en el momento del cálculo.

**Alternativa considerada:** almacenar directamente como `float`.

**Razón:** los archivos fuente tienen precisión decimal que puede perderse en la conversión binaria a `float`. Almacenar como `str` preserva el valor exacto extraído del CSV oficial. La conversión a `float` en el cálculo no acumula error adicional porque se aplica una sola vez por operación.

---

### 10.6 `Periodo` como tipo propio

**Decisión:** value object `Periodo` con atributos `año`, `mes`, `quincena`.

**Alternativa considerada:** `str` con formato `"1Q Ene 2020"` o `pd.Timestamp`.

**Razón:** una quincena no tiene representación natural en Python ni en pandas. `str` no permite sorting natural ni uso como clave hashable confiable. `pd.Timestamp` requiere una convención arbitraria para el día (día 1 o día 16) que no es un dato real. `Periodo` encapsula esa convención en `to_timestamp()` y expone sorting, hash e igualdad de forma explícita.

---

### 10.7 Categorías de clasificación version-específicas

**Decisión:** las columnas `CCIF`, `COG`, `inflacion_1/2/3` en `CanastaCanonica` usan `pd.Categorical` con las categorías de cada versión. No hay mapeo cross-versión en v1.

**Advertencia para v2:** entre versiones hay cambios de nombre de categorías (ej. `"Comunicaciones"` en 2018 → `"Información y comunicación"` en 2024). Un join directo entre canastas de distintas versiones producirá categorías no coincidentes. Cuando se implementen subíndices en v2, se requerirá un componente de mapeo explícito entre categorías de versiones.

---

### 10.8 Tolerancia numérica por versión

**Decisión:** la tolerancia para marcar `estado_validacion = diferencia_detectada` es fija por versión:

| Versión | Tolerancia (`error_absoluto`) | Nota                                      |
| ------- | ----------------------------- | ----------------------------------------- |
| 2010    | `<= 0.0005`                   | provisional — sin validación empírica aún |
| 2013    | `<= 0.0005`                   | provisional — sin validación empírica aún |
| 2018    | `<= 0.0005`                   | basada en experiencia previa              |
| 2024    | `<= 0.005`                    | mayor variación por encadenamiento        |

**Razón:** las diferencias observadas entre el INPC replicado y el publicado por el INEGI varían por versión — la canasta 2024 usa Laspeyres encadenado con normalización, lo que introduce mayor variación numérica acumulada. Una tolerancia única global sería demasiado estricta para 2024 o demasiado laxa para 2018. Las tolerancias de 2010 y 2013 son provisionales y deben revisarse cuando se implemente y pruebe con datos reales.

---

### 10.9 Reglas de `estado_corrida`

**Decisión:** `estado_corrida` en `ResumenValidacion` se determina a partir de `estado_calculo` por periodo:

| Condición                                                    | `estado_corrida` |
| ------------------------------------------------------------ | ---------------- |
| Todos los periodos con `estado_calculo = 'ok'`               | `'ok'`           |
| Algunos periodos con `estado_calculo = 'null_por_faltantes'` | `'parcial'`      |
| Todos los periodos con `estado_calculo != 'ok'`              | `'fallida'`      |

---

### 10.10 Detección de `null_por_faltantes`

**Decisión:** la detección de valores faltantes en la serie por periodo es responsabilidad del calculador (`LaspeyresDirecto`, `LaspeyresEncadenado`), no de `validar_inpc.py`.

**Razón:** el calculador es quien conoce si el cálculo fue íntegro. Si la serie tiene NaN para un genérico en un periodo, ese periodo se marca como `estado_calculo = 'null_por_faltantes'` e `inpc_replicado = NaN`. `validar_inpc.py` solo valida — no recalcula ni inspecciona la serie.

---

### 10.11 Firma de `validar_inpc.py`

**Decisión:** el dominio no recibe el puerto `FuenteValidacion` — recibe el dict ya obtenido por `ejecutar_corrida.py`. Si la fuente no estaba disponible, el caso de uso pasa `{}`. Ver contrato completo en §5.11.

---

### 10.12 `id_corrida` en `ResultadoCalculo`

**Decisión:** `ejecutar_corrida.py` genera el UUID y lo pasa como parámetro `id_corrida: str` a `calcular()`. La firma de `CalculadorBase.calcular()` se actualiza para incluirlo.

**Razón:** el calculador no debe generar IDs — esa responsabilidad pertenece al caso de uso. Pasar el `id_corrida` como parámetro mantiene el calculador como función pura.

---

## 11. Gaps conocidos y mejoras futuras

Decisiones de diseño que se tomaron con limitaciones conocidas. Cada entrada registra el comportamiento actual, el problema identificado y la mejora propuesta para cuando el trigger se cumpla.

---

### 11.1 `estado_validacion_global` no distingue cobertura parcial

**Comportamiento actual:** `estado_validacion_global` tiene tres estados: `'ok'`, `'diferencia_detectada'`, `'no_disponible'`. El estado `'ok'` se asigna cuando todos los periodos comparados pasaron la tolerancia, aunque al menos uno no haya sido comparado.

**Problema:** un usuario que solo lee `ResumenValidacion` puede interpretar `'ok'` como validación completa cuando en realidad al menos un periodo no fue comparado contra el INEGI. El detalle de cobertura solo es visible en `ReporteDetalladoValidacion`.

**Mejora propuesta:** agregar el estado `'ok_parcial'` para cuando al menos un periodo pasó la comparación pero al menos uno quedó sin comparar. Requiere actualizar los invariantes de `ResumenValidacion` y `ReporteDetalladoValidacion`, y la lógica de `validar_inpc.py`.

**Cuándo implementar:** cuando `FuenteValidacion` esté implementada y haya datos reales que permitan observar cobertura parcial en la práctica.

---

### 11.2 Validación por niveles en `LectorCanastaCsv`

**Comportamiento actual:** `LectorCanastaCsv` valida todas las columnas del esquema canónico o falla. No hay distinción entre "mínimo para calcular INPC" y "completo para calcular subíndices".

**Problema:** en el futuro puede haber CSVs que solo tengan `ponderador` y `encadenamiento` (suficientes para INPC) pero sin clasificaciones (COG, CCIF, etc.). Con el validador actual, ese CSV falla aunque el cálculo sea posible.

**Mejora propuesta:** agregar un parámetro `nivel` al método `leer` y actualizar el Protocol `LectorCanasta`. Tres niveles: `"inpc"` (solo ponderador), `"subindices"` (+ clasificaciones), `"completo"` (todas las columnas).

**Cuándo implementar:** cuando se requiera calcular subíndices en v2.

---

### 11.3 Agregados CCIF en `LectorSeriesCsv`

**Comportamiento actual:** `LectorSeriesCsv` filtra y descarta todas las filas que no tienen código de 3 dígitos en el `Título` — es decir, descarta los agregados CCIF (`01 Alimentos...`, `01.1 Alimentos`, etc.).

**Problema:** en v2 los subíndices requieren las series de los agregados CCIF, no solo los genéricos.

**Mejora propuesta:** agregar un parámetro `incluir_agregados: bool = False` al método `leer`.

**Cuándo implementar:** cuando se implemente el cálculo de subíndices en v2.

---

### 11.4 Detección dinámica del header en `LectorSeriesCsv`

**Comportamiento actual:** `LectorSeriesCsv` usa `skiprows=5` fijo para saltar el encabezado de INEGI, asumiendo que siempre son exactamente 5 líneas.

**Problema:** si INEGI cambia el formato de exportación (más o menos líneas de encabezado), el lector fallaría silenciosamente — leería datos incorrectos sin lanzar error.

**Mejora propuesta:** detectar dinámicamente la fila del header contando la moda de separadores (comas) en las primeras 25 líneas y usando la primera fila que alcanza ese conteo como header. Enfoque usado en el proyecto anterior (`archivos.py: cargar_de_raw`).

**Cuándo implementar:** si se detecta que INEGI cambia su formato de exportación, o al implementar soporte para otras fuentes de series.

---

### 11.5 ñ en canasta intermedia

**Comportamiento actual:** los CSV de canasta intermedia (2010, 2013, 2018, 2024) tienen los nombres de genéricos sin ñ (ej: `"pina"` en lugar de `"piña"`). La normalización de `LectorSeriesCsv` conserva ñ, lo que causaría mismatch en genéricos con ñ si ambas fuentes no son consistentes.

**Problema:** los nombres normalizados de las series tendrán ñ (ej: `"piña"`) pero los índices de la canasta no (ej: `"pina"`), haciendo que `alinear_genericos` falle para esos genéricos.

**Mejora propuesta:** regenerar los CSV de canasta intermedia con ñ donde corresponda.

**Cuándo implementar:** antes de implementar corridas de cualquier versión — prerrequisito para que el matching funcione en los 11 genéricos afectados (ej: piña, pañales, enseñanza adicional).

---

### 11.6 Formato de series BIE en versiones 2010 y 2013

**Comportamiento actual:** `LectorSeriesCsv` extrae genéricos con el patrón `\b\d{3}\b` en el campo `Título`. Verificado solo contra series de la canasta 2018.

**Problema:** las series 2010 y 2013 descargadas del BIE podrían tener un formato de título distinto donde los códigos de genérico no sean de 3 dígitos. Si no hay matches, el lector lanzaría `SerieVacia` sin indicar que el problema es de formato.

**Mejora propuesta:** verificar el formato real de las series 2010/2013 en el BIE y ajustar el patrón si es necesario.

**Cuándo implementar:** antes de implementar corridas 2010 y 2013.

---

### 11.7 Cobertura parcial de periodos no reportada explícitamente

**Comportamiento actual:** el paso 4 de `ejecutar_corrida.py` filtra la `SerieNormalizada` al rango de `RANGOS_VALIDOS[version]`. Si la serie cubre solo parte del rango (ej. llega hasta `1Q Ene 2022` en lugar de `2Q Jul 2024`), la corrida continúa con los periodos disponibles. La cobertura parcial es inferible comparando `total_periodos_esperados` con `total_periodos_calculados` en `ResumenValidacion`, pero no hay un indicador explícito.

**Problema:** `estado_corrida = 'parcial'` está semánticamente reservado para cuando el cálculo produjo `null_por_faltantes` en algunos periodos — no para cuando la serie no cubre el rango completo. Estos son dos tipos distintos de parcialidad que el diseño actual no distingue.

**Mejora propuesta:** agregar un nuevo valor a `estado_corrida` (ej. `'cobertura_incompleta'`) o un campo booleano `cobertura_periodo_completa` a `ResumenValidacion`.

**Cuándo implementar:** cuando el reporte de cobertura sea un requerimiento explícito del usuario final.

---

### 11.8 `AlmacenArtefactos.obtener` devuelve índice como string

**Comportamiento actual:** `AlmacenArtefactosFs.obtener` lee el Parquet y devuelve el DataFrame con el índice `Periodo` como string (`"1Q Ene 2024"`). La estructura del MultiIndex (niveles, nombres) se preserva gracias a Parquet, pero los valores siguen siendo strings.

**Problema:** el consumidor que llame a `obtener` y quiera operar sobre el DataFrame con lógica de dominio (ordenar por periodo, filtrar por rango) tendrá que re-parsear el índice manualmente con `Periodo.desde_str()`.

**Mejora propuesta:** agregar métodos tipados por artefacto (`obtener_resultado`, `obtener_reporte`, etc.) que re-parseen el índice y devuelvan el tipo correcto.

**Cuándo implementar:** cuando haya un caso de uso que necesite operar sobre artefactos recuperados del almacén (ej. comparar corridas, generar históricos).
