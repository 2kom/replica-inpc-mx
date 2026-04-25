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
    - [5.3 PeriodoQuincenal y PeriodoMensual](#53-periodoquincenal-y-periodomensual)
      - [PeriodoQuincenal](#periodoquincenal)
      - [PeriodoMensual](#periodomensual)
      - [Factory `periodo_desde_str`](#factory-periodo_desde_str)
      - [Convención `to_timestamp()`](#convención-to_timestamp)
    - [5.4 ResultadoCalculo](#54-resultadocalculo)
    - [5.5 ResumenValidacion](#55-resumenvalidacion)
    - [5.6 ReporteDetalladoValidacion](#56-reportedetalladovalidacion)
    - [5.7 DiagnosticoFaltantes](#57-diagnosticofaltantes)
    - [5.8 CalculadorBase](#58-calculadorbase)
      - [5.8.1 LaspeyresDirecto](#581-laspeyresdirecto)
      - [5.8.2 LaspeyresEncadenado](#582-laspeyresencadenado)
      - [5.8.3 grupos\_por\_clasificacion](#583-grupos_por_clasificacion)
    - [5.9 tipos.py — tipos compartidos](#59-tipospy--tipos-compartidos)
      - [VersionCanasta](#versioncanasta)
      - [INDICE\_POR\_TIPO](#indice_por_tipo)
      - [COLUMNAS\_CLASIFICACION](#columnas_clasificacion)
      - [TIPOS\_CON\_VALIDACION](#tipos_con_validacion)
      - [RANGOS\_VALIDOS](#rangos_validos)
      - [ManifestCorrida](#manifestcorrida)
      - [ResultadoCorrida](#resultadocorrida)
    - [5.10 correspondencia.py](#510-correspondenciapy)
    - [5.11 validar\_inpc.py](#511-validar_inpcpy)
      - [`validar` — resultado quincenal](#validar--resultado-quincenal)
      - [`validar_mensual` — resultado mensual (sin cobertura de genéricos)](#validar_mensual--resultado-mensual-sin-cobertura-de-genéricos)
    - [5.12 variaciones.py — `ResultadoVariacion` y funciones de variación](#512-variacionespy--resultadovariacion-y-funciones-de-variación)
      - [Regla drop/keep (todas las funciones)](#regla-dropkeep-todas-las-funciones)
      - [`ResultadoVariacion`](#resultadovariacion)
      - [Funciones públicas](#funciones-públicas)
      - [Helpers privados](#helpers-privados)
    - [5.13 a\_mensual — conversión quincenal → mensual](#513-a_mensual--conversión-quincenal--mensual)
    - [5.14 ResumenValidacionVariaciones](#514-resumenvalidacionvariaciones)
    - [5.15 ReporteValidacionVariaciones](#515-reportevalidacionvariaciones)
    - [5.16 validar\_variaciones.py](#516-validar_variacionespy)
  - [6. Fachada — api/corrida.py](#6-fachada--apicorridapy)
  - [6.2 Fachada de validación — api/validacion.py](#62-fachada-de-validación--apivalidacionpy)
  - [6.3 Validación de variaciones — api/validacion.py](#63-validación-de-variaciones--apivalidacionpy)
    - [ReporteValidacionVariaciones](#reportevalidacionvariaciones)
    - [validar\_variaciones\_quincenal](#validar_variaciones_quincenal)
  - [7. Capa de aplicación](#7-capa-de-aplicación)
    - [7.1 Puertos](#71-puertos)
      - [7.1.1 LectorCanasta](#711-lectorcanasta)
      - [7.1.2 LectorSeries](#712-lectorseries)
      - [7.1.3 FuenteValidacion](#713-fuentevalidacion)
      - [7.1.4 EscritorResultados](#714-escritorresultados)
      - [7.1.5 RepositorioCorridas](#715-repositoriocorridas)
      - [7.1.6 AlmacenArtefactos](#716-almacenartefactos)
    - [7.2 EjecutarCorrida](#72-ejecutarcorrida)
  - [8. Infraestructura](#8-infraestructura)
    - [8.1 Formato del CSV canasta](#81-formato-del-csv-canasta)
    - [8.2 Formato del CSV de series](#82-formato-del-csv-de-series)
    - [8.3 Repositorio de corridas (filesystem)](#83-repositorio-de-corridas-filesystem)
    - [8.4 Almacén de artefactos (filesystem)](#84-almacén-de-artefactos-filesystem)
    - [8.5 Formato de los CSV de salida (escritor)](#85-formato-de-los-csv-de-salida-escritor)
      - [reporte\_\<id\_corrida\>.csv](#reporte_id_corridacsv)
      - [diagnostico\_\<id\_corrida\>.csv](#diagnostico_id_corridacsv)
    - [8.6 FuenteValidacionApi (API del INEGI)](#86-fuentevalidacionapi-api-del-inegi)
    - [8.7 Indicadores de variación mensual (API del INEGI)](#87-indicadores-de-variación-mensual-api-del-inegi)
    - [8.8 Indicadores de variación quincenal (API del INEGI)](#88-indicadores-de-variación-quincenal-api-del-inegi)
  - [9. Estrategia de errores](#9-estrategia-de-errores)
    - [9.1 Jerarquía de excepciones](#91-jerarquía-de-excepciones)
    - [9.2 Propagación](#92-propagación)
    - [9.3 Traducción en adaptadores](#93-traducción-en-adaptadores)
  - [10. Estrategia de testing](#10-estrategia-de-testing)
    - [10.1 Tipos de test](#101-tipos-de-test)
    - [10.2 Fixtures](#102-fixtures)
    - [10.3 Mock de la API del INEGI](#103-mock-de-la-api-del-inegi)
    - [10.4 Criterio de suficiencia para v1](#104-criterio-de-suficiencia-para-v1)
  - [11. Decisiones y razones](#11-decisiones-y-razones)
    - [11.1 `SerieNormalizada` en formato ancho](#111-serienormalizada-en-formato-ancho)
    - [11.2 `generico_original` como diccionario](#112-generico_original-como-diccionario)
    - [11.3 Correspondencia genérico↔genérico por normalización exacta](#113-correspondencia-genéricogenérico-por-normalización-exacta)
    - [11.4 pandas en el dominio](#114-pandas-en-el-dominio)
    - [11.5 `ponderador` y `encadenamiento` como `str`](#115-ponderador-y-encadenamiento-como-str)
    - [11.6 `Periodo` como tipo propio](#116-periodo-como-tipo-propio)
    - [11.7 Categorías de clasificación version-específicas](#117-categorías-de-clasificación-version-específicas)
    - [11.8 Tolerancia numérica por versión](#118-tolerancia-numérica-por-versión)
    - [11.9 Reglas de `estado_corrida`](#119-reglas-de-estado_corrida)
    - [11.10 Detección de `null_por_faltantes`](#1110-detección-de-null_por_faltantes)
    - [11.11 Firma de `validar_inpc.py`](#1111-firma-de-validar_inpcpy)
    - [11.12 `id_corrida` en `ResultadoCalculo`](#1112-id_corrida-en-resultadocalculo)
    - [11.13 Loop de subíndices en `EjecutarCorrida`, no en el calculador](#1113-loop-de-subíndices-en-ejecutarcorrida-no-en-el-calculador)
    - [11.14 Schema condicional en `ReporteDetalladoValidacion`](#1114-schema-condicional-en-reportedetalladovalidacion)
    - [11.15 `TIPOS_CON_VALIDACION` en el dominio, no en infraestructura](#1115-tipos_con_validacion-en-el-dominio-no-en-infraestructura)
    - [11.16 Cache de clase en `FuenteValidacionApi`](#1116-cache-de-clase-en-fuentevalidacionapi)
    - [11.17 UTF-8 como primer encoding en `LectorSeriesCsv`](#1117-utf-8-como-primer-encoding-en-lectorseriescsv)
    - [11.18 Dispatch interno en `CalculadorBase` con helper `grupos_por_clasificacion`](#1118-dispatch-interno-en-calculadorbase-con-helper-grupos_por_clasificacion)
    - [11.19 Vectorización del loop interno de `validar_inpc`](#1119-vectorización-del-loop-interno-de-validar_inpc)
    - [11.20 Implementación de `LaspeyresEncadenado` — derivación de `f_h`](#1120-implementación-de-laspeyresencadenado--derivación-de-f_h)
      - [Primer enfoque (descartado): media ponderada con ponderadores nuevos](#primer-enfoque-descartado-media-ponderada-con-ponderadores-nuevos)
      - [Enfoque final: $f\_h$ desde el resultado de la versión anterior](#enfoque-final-f_h-desde-el-resultado-de-la-versión-anterior)
    - [11.21 Imputación de faltantes en series](#1121-imputación-de-faltantes-en-series)
    - [11.22 `combinar` — función de combinación histórica de `ResultadoCalculo`](#1122-combinar--función-de-combinación-histórica-de-resultadocalculo)
    - [11.23 `RENOMBRES_INDICES` y normalización cross-versión en `combinar`](#1123-renombres_indices-y-normalización-cross-versión-en-combinar)
  - [12. Gaps conocidos y mejoras futuras](#12-gaps-conocidos-y-mejoras-futuras)
    - [12.1 `estado_validacion_global` no distingue cobertura parcial ✓ RESUELTO](#121-estado_validacion_global-no-distingue-cobertura-parcial--resuelto)
    - [12.2 Validación por niveles en `LectorCanastaCsv`](#122-validación-por-niveles-en-lectorcanastacsv)
    - [12.3 Agregados CCIF en `LectorSeriesCsv`](#123-agregados-ccif-en-lectorseriescsv)
    - [12.4 Detección dinámica del header en `LectorSeriesCsv`](#124-detección-dinámica-del-header-en-lectorseriescsv)
    - [12.5 ñ en canasta intermedia ✓ RESUELTO](#125-ñ-en-canasta-intermedia--resuelto)
    - [12.6 Formato de series BIE en versiones 2010 y 2013](#126-formato-de-series-bie-en-versiones-2010-y-2013)
    - [12.7 Cobertura parcial de periodos no reportada explícitamente ✓ RESUELTO](#127-cobertura-parcial-de-periodos-no-reportada-explícitamente--resuelto)
    - [12.8 `AlmacenArtefactos.obtener` devuelve índice como string](#128-almacenartefactosobtener-devuelve-índice-como-string)
    - [12.9 Validación INEGI solo disponible para tipos específicos ✓ RESUELTO](#129-validación-inegi-solo-disponible-para-tipos-específicos--resuelto)
    - [12.10 Incompatibilidad de nombres de categorías entre canastas al combinar resultados ✓ RESUELTO](#1210-incompatibilidad-de-nombres-de-categorías-entre-canastas-al-combinar-resultados--resuelto)
    - [12.11 Salida mensual directa desde `ejecutar_corrida` (v1.x)](#1211-salida-mensual-directa-desde-ejecutar_corrida-v1x)
    - [12.12 `ejecutar` multi-canasta (v2.0)](#1212-ejecutar-multi-canasta-v20)
    - [12.13 Validación de variaciones contra series INEGI (v1.2.4) ✓ RESUELTO](#1213-validación-de-variaciones-contra-series-inegi-v124--resuelto)
    - [12.14 Rediseño de API de validación: `ResultadoCalculo`, `ResultadoValidacion` y wrappers con token (v2.0)](#1214-rediseño-de-api-de-validación-resultadocalculo-resultadovalidacion-y-wrappers-con-token-v20)

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
corrida = Corrida(token_inegi="mi_token")
resultado = corrida.ejecutar(canasta="data/canasta_2018.csv", series="data/series_2018.csv", version=2018)
```

#### Repository — persistencia de corridas y artefactos

`RepositorioCorridas` y `AlmacenArtefactos` son puertos que abstraen
dónde y cómo se persiste cada corrida.
En v1 se implementan sobre filesystem. Si se agrega SQL, se implementa
el mismo puerto sin tocar el dominio.

La persistencia es opcional por corrida — ver §7.2. Cuando `persistir=False`,
estos puertos no se invocan y pueden ser `None`.

#### Adapter — infraestructura

Cada módulo en `infraestructura/` adapta una tecnología concreta al contrato
del puerto correspondiente:

- `lector_canasta_csv.py` implementa `LectorCanasta`
- `lector_series_csv.py` implementa `LectorSeries`
- `fuente_validacion_api.py` implementa `FuenteValidacion`
- `repositorio_corridas_fs.py` implementa `RepositorioCorridas`
- `escritor_resultados_csv.py` implementa `EscritorResultados`
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
│       │   │   ├── validacion.py
│       │   │   └── variacion.py
│       │   ├── calculo/
│       │   │   ├── base.py
│       │   │   ├── estrategia.py
│       │   │   ├── laspeyres.py
│       │   │   ├── encadenado.py
│       │   │   └── subindices.py
│       │   ├── correspondencia.py
│       │   ├── validar_inpc.py
│       │   ├── validar_variaciones.py
│       │   ├── variaciones.py
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
│       │   │   └── escritor_resultados_csv.py
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
pytest, pytest-mock, ipython, jupyter, ipykernel

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
   CanastaCanonica
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

| Columna                   | dtype pandas       | Notas                                                        |
| ------------------------- | ------------------ | ------------------------------------------------------------ |
| `ponderador`              | `object` (str)     | texto decimal exacto del archivo fuente                      |
| `encadenamiento`          | `object` (str/NaN) | texto decimal exacto; NaN cuando no aplica                   |
| `COG`                     | `object` (str)     |                                                              |
| `CCIF division`           | `object` (str)     |                                                              |
| `CCIF grupo`              | `object` (str)     |                                                              |
| `CCIF clase`              | `object` (str)     |                                                              |
| `inflacion componente`    | `object` (str)     |                                                              |
| `inflacion subcomponente` | `object` (str)     |                                                              |
| `inflacion agrupacion`    | `object` (str)     |                                                              |
| `SCIAN sector`            | `object` (str)     | número + nombre, ej. `"32 Industrias manufactureras"`        |
| `SCIAN rama`              | `object` (str)     | código + nombre, ej. `"3241 Fabricación de..."`              |
| `durabilidad`             | `object` (str)     | vacío cuando no aplica a la versión                          |
| `canasta basica`          | `object` (str)     | `"X"` si pertenece, `""` si no                               |
| `canasta consumo minimo`  | `object` (str)     | `"X"` si pertenece, `""` o `null` si no aplica a la versión  |

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

### 5.3 PeriodoQuincenal y PeriodoMensual

Dos value objects en `dominio/periodos.py`. Ambos son sortables, hashables y convertibles a `pd.Timestamp`. Se usan como claves en el MultiIndex de `ResultadoCalculo`, como columnas de `SerieNormalizada` y como argumentos en funciones de variación.

#### PeriodoQuincenal

Representa un periodo quincenal — formato nativo de publicación del INEGI. Renombrado desde `Periodo` en v1.2.3.

```python
class PeriodoQuincenal:
    def __init__(self, año: int, mes: int, quincena: int) -> None: ...
    # quincena ∈ {1, 2}; lanza ValueError si quincena no es 1 ni 2

    @classmethod
    def desde_str(cls, texto: str) -> "PeriodoQuincenal": ...  # "1Q Ene 2018"

    def to_timestamp(self) -> pd.Timestamp: ...  # 1Q → día 15, 2Q → último día del mes

    @property
    def es_mensual(self) -> bool: ...  # siempre False

    def __str__(self) -> str: ...       # "1Q Ene 2018"
    def __repr__(self) -> str: ...      # "PeriodoQuincenal(2018, 1, 1)"
    def __eq__(self, other) -> bool: ...
    def __hash__(self) -> int: ...
    def __lt__(self, other) -> bool: ...
```

Ordering natural: `(año, mes, quincena)`.

#### PeriodoMensual

Representa un periodo mensual. Producido por `a_mensual()` o por la API INEGI (indicador 910392). Nunca es input de `ejecutar_corrida()` ni de `LectorSeriesCsv`.

```python
class PeriodoMensual:
    def __init__(self, año: int, mes: int) -> None: ...

    @classmethod
    def desde_str(cls, texto: str) -> "PeriodoMensual": ...  # "Ene 2018"

    def to_timestamp(self) -> pd.Timestamp: ...  # último día del mes

    @property
    def es_mensual(self) -> bool: ...  # siempre True

    def __str__(self) -> str: ...       # "Ene 2018"
    def __repr__(self) -> str: ...      # "PeriodoMensual(2018, 1)"
    def __eq__(self, other) -> bool: ...
    def __hash__(self) -> int: ...
    def __lt__(self, other) -> bool: ...
```

Ordering natural: `(año, mes)`. Comparación cross-type (`PeriodoQuincenal` vs `PeriodoMensual`) → `NotImplemented` → `TypeError` en runtime. Correcto: un `ResultadoCalculo` nunca mezcla tipos (ver §5.4).

#### Factory `periodo_desde_str`

```python
def periodo_desde_str(texto: str) -> PeriodoQuincenal | PeriodoMensual:
    ...
```

Detecta el formato automáticamente: si el texto comienza con `"[12]Q "` → `PeriodoQuincenal`; de lo contrario → `PeriodoMensual`. Ejemplos:

```python
periodo_desde_str("1Q Ene 2024")  # → PeriodoQuincenal(2024, 1, 1)
periodo_desde_str("Ene 2024")     # → PeriodoMensual(2024, 1)
```

Exportada desde `replica_inpc`. Usada internamente por `variacion_desde` para parsear `desde` y `hasta`.

#### Convención `to_timestamp()`

| Tipo | Regla | Ejemplo |
| ---- | ----- | ------- |
| `PeriodoQuincenal(año, mes, 1)` | día 15 del mes | `1Q Ene 2024` → 15 Ene 2024 |
| `PeriodoQuincenal(año, mes, 2)` | último día del mes | `2Q Ene 2024` → 31 Ene 2024 |
| `PeriodoMensual(año, mes)` | último día del mes | `Ene 2024` → 31 Ene 2024 |

Regla unificada: "último día del periodo". Que `2Q` y mensual del mismo mes coincidan no es problema — un `ResultadoCalculo` es siempre homogéneo y nunca se grafican juntos.

**Breaking change v1.2.3:** hasta v1.2.2 la convención era `1Q → día 1, 2Q → día 16`.

---

### 5.4 ResultadoCalculo

**Representación:** DataFrame-backed. Índice compuesto `(Periodo, indice)` — permite
múltiples subíndices por periodo. `version` y `tipo` como columnas. `id_corrida` como atributo.

```python
class ResultadoCalculo:
    def __init__(self, df: pd.DataFrame, id_corrida: str) -> None: ...

    @property
    def id_corrida(self) -> str: ...

    @property
    def df(self) -> pd.DataFrame: ...

    def como_tabla(self, ancho: bool = False) -> pd.DataFrame: ...

    def _repr_html_(self) -> str:
        return self.como_tabla(ancho=False)._repr_html_()
```

**`como_tabla(ancho=False)`:** devuelve el DataFrame interno en formato largo cuando
`ancho=False` (default — facilita `pd.concat` entre corridas). Con `ancho=True` pivota
`indice_replicado` sobre el nivel `periodo`: filas = valores de `indice` (ej. `"INPC"`),
columnas = periodos. `_repr_html_()` conserva la vista larga; la vista ancha
se obtiene llamando `como_tabla(ancho=True)` explícitamente.

**`combinar(resultados, version_canonica=None)`** — función suelta en `dominio/modelos/resultado.py`, exportada desde `replica_inpc`. Construye un `ResultadoCalculo` continuo a partir de una lista de resultados de distintas canastas. Normaliza automáticamente los nombres de categorías entre versiones para los tipos con correspondencia definida (ver §11.23):

```python
from replica_inpc import combinar

inpc = combinar([r_2010.resultado, r_2013.resultado, r_2018.resultado, r_2024.resultado])
inpc.como_tabla(ancho=True)

# Para tipos con fricción de nombres (ej. CCIF division):
ccif = combinar([r_2018.resultado, r_2024.resultado])           # usa nombres 2024 (default)
ccif = combinar([r_2018.resultado, r_2024.resultado], version_canonica=2018)  # usa nombres 2018
```

Ver §11.22 para la decisión de diseño.

**Esquema del DataFrame interno (índice compuesto: `(PeriodoQuincenal | PeriodoMensual, indice)`):**

| Columna              | dtype pandas      | Notas                                                              |
| -------------------- | ----------------- | ------------------------------------------------------------------ |
| `version`            | `int`             |                                                                    |
| `tipo`               | `object` (str)    | `'inpc'` en v1                                                     |
| `indice_replicado`   | `float64` / `NaN` | NaN cuando `estado_calculo` es `'null_por_faltantes'` o `'fallida'`|
| `estado_calculo`     | `object` (str)    | `'ok'`, `'null_por_faltantes'`, `'fallida'`, `'semi_ok'`           |
| `motivo_error`       | `object` (str/NaN)| NaN cuando `estado_calculo` es `'ok'` o `'semi_ok'`                |

**Semántica de `'semi_ok'`:** el mes fue calculado con solo una quincena disponible (la otra es NaN). `indice_replicado` tiene valor (el de la quincena disponible); `motivo_error` = NaN. No es un fallo — es una advertencia de calidad. Producido exclusivamente por `a_mensual()` (ver §5.13).

**Invariantes — validados al construir:**

| Invariante                | Regla                                                                                                        |
| ------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Versión válida            | `version` in `{2010, 2013, 2018, 2024}`                                                                      |
| Al menos una fila         | el DataFrame no está vacío                                                                                   |
| `estado_calculo` válido   | valores in `{'ok', 'null_por_faltantes', 'fallida', 'semi_ok'}`                                              |
| Consistencia ok/semi_ok   | si `estado_calculo in {'ok', 'semi_ok'}` → `indice_replicado` no NaN y `motivo_error` NaN                    |
| Consistencia fallo        | si `estado_calculo in {'null_por_faltantes', 'fallida'}` → `indice_replicado` NaN y `motivo_error` con valor |
| Homogeneidad de periodos  | todos los periodos del índice son del mismo tipo: todos `PeriodoQuincenal` o todos `PeriodoMensual`          |

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

| Columna                      | dtype pandas    | Notas                                                                                                                             |
| ---------------------------- | --------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `version`                    | `int` o `str`   | `int` para corrida simple; `str` tipo `"2018+2024"` para resultado combinado (`validar_mensual` sobre `combinar`)                 |
| `tipo`                       | `object` (str)  |                                                                                                                                   |
| `periodo_inicio`             | `Periodo`       | primer periodo calculado                                                                                                          |
| `periodo_fin`                | `Periodo`       | último periodo calculado                                                                                                          |
| `total_periodos_esperados`   | `int`           |                                                                                                                                   |
| `total_periodos_calculados`  | `int`           |                                                                                                                                   |
| `total_periodos_con_null`    | `int`           |                                                                                                                                   |
| `error_absoluto_max`         | `float` / `NaN` | **solo cuando `tipo` tiene validación INEGI**; ausente si no                                                                      |
| `error_relativo_max`         | `float` / `NaN` | **solo cuando `tipo` tiene validación INEGI**; ausente si no                                                                      |
| `total_faltantes_indice`     | `int`           |                                                                                                                                   |
| `total_faltantes_ponderador` | `int`           |                                                                                                                                   |
| `estado_validacion_global`   | `object` (str)  | **solo cuando `tipo` tiene validación INEGI**; ausente si no. `'ok'`, `'ok_parcial'`, `'diferencia_detectada'`, `'no_disponible'` |
| `estado_corrida`             | `object` (str)  | `'ok'`, `'ok_parcial'`, `'fallida'`                                                                                               |

**Invariantes — validados al construir:**

| Invariante                        | Regla                                                                                                                               |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Al menos una fila                 | el DataFrame no está vacío                                                                                                          |
| Versión válida                    | cada `version`: `int in {2010, 2013, 2018, 2024}` ó `str` donde cada componente `+`-separado sea versión válida (ej. `"2018+2024"`) |
| `estado_corrida` válido           | valores in `{'ok', 'ok_parcial', 'fallida'}`                                                                                        |
| `estado_validacion_global` válido | cuando presente: valores in `{'ok', 'ok_parcial', 'diferencia_detectada', 'no_disponible'}`                                         |
| Periodos calculados               | `total_periodos_calculados` <= `total_periodos_esperados`                                                                           |
| Periodos null                     | `total_periodos_con_null` <= `total_periodos_calculados`                                                                            |
| Rango de periodos                 | `periodo_inicio` <= `periodo_fin`                                                                                                   |

---

### 5.6 ReporteDetalladoValidacion

**Representación:** DataFrame-backed. Índice compuesto `(Periodo, indice)` — agrupa
todos los índices de una corrida. `id_corrida` como atributo. `version` y `tipo` como columnas.

El esquema del DataFrame varía según si el `tipo` tiene validación INEGI disponible
(ver nota al final de esta sección).

```python
class ReporteDetalladoValidacion:
    def __init__(self, df: pd.DataFrame, id_corrida: str) -> None: ...

    @property
    def id_corrida(self) -> str: ...

    @property
    def df(self) -> pd.DataFrame: ...

    def como_tabla(self, ancho: bool = False) -> pd.DataFrame: ...

    def _repr_html_(self) -> str:
        return self.como_tabla(ancho=False)._repr_html_()
```

**`como_tabla(ancho=False)`:** devuelve el DataFrame interno en formato largo (facilita
`pd.concat` entre corridas). `_repr_html_()` conserva esta vista larga.

**`como_tabla(ancho=True)` — con validación INEGI:**

Pivota las columnas `{indice}_calculado`, `{indice}_inegi`, `error_absoluto`,
`error_relativo` y `estado_validacion` sobre los periodos.

```text
| indice                  | 2Q Jul 2018 | 1Q Ago 2018 | 2Q Ago 2018 |
| ----------------------- | ----------: | ----------: | ----------: |
| {indice}_calculado      | 100.000     | NaN         | 103.500     |
| {indice}_inegi          | 100.002     | NaN         | 103.518     |
| {indice}_error_absoluto | 0.002       | NaN         | 0.018       |
| {indice}_error_relativo | 0.00002     | NaN         | 0.00017     |
| {indice}_estado_valid.  | ok          | no_disp.    | dif_detect. |
```

**`como_tabla(ancho=True)` — sin validación INEGI:**

Pivota las columnas `{indice}_calculado`, `{indice}_estado_calculo`,
`{indice}_motivo_error`, `{indice}_cobertura_pct` y `{indice}_ponderador_cubierto`
sobre los periodos.

```text
| indice                       | 2Q Jul 2018 | 1Q Ago 2018 |
| ---------------------------- | ----------: | ----------: |
| {indice}_calculado           | 100.000     | NaN         |
| {indice}_estado_calculo      | ok          | null_por_f. |
| {indice}_motivo_error        | —           | faltantes   |
| {indice}_cobertura_pct       | 100.0       | 98.9        |
| {indice}_ponderador_cubierto | 100.0       | 97.4        |
```

Para ver todas las columnas del DataFrame interno, usar `.como_tabla(False)`.

**Esquema del DataFrame — con validación INEGI (índice compuesto: `(Periodo, indice)`):**

| Columna                      | dtype pandas      | Notas                                                                                  |
| ---------------------------- | ----------------- | -------------------------------------------------------------------------------------- |
| `version`                    | `int`             |                                                                                        |
| `tipo`                       | `object` (str)    |                                                                                        |
| `indice_replicado`           | `float` / `NaN`   | NaN cuando `estado_calculo not in {'ok', 'semi_ok'}`                                   |
| `indice_inegi`               | `float` / `NaN`   | NaN cuando `estado_validacion == 'no_disponible'`                                      |
| `error_absoluto`             | `float` / `NaN`   | NaN cuando `estado_validacion == 'no_disponible'`                                      |
| `error_relativo`             | `float` / `NaN`   | NaN cuando `estado_validacion == 'no_disponible'`                                      |
| `estado_calculo`             | `object` (str)    | `'ok'`, `'semi_ok'`, `'null_por_faltantes'`, `'fallida'`                               |
| `motivo_error`               | `object` (str/NaN)|                                                                                        |
| `estado_validacion`          | `object` (str)    | `'ok'`, `'diferencia_detectada'`, `'diferencia_detectada_imputado'`, `'no_disponible'` |
| `total_genericos_esperados`  | `int`             |                                                                                        |
| `total_genericos_con_indice` | `int`             |                                                                                        |
| `total_genericos_sin_indice` | `int`             |                                                                                        |
| `cobertura_genericos_pct`    | `float`           |                                                                                        |
| `ponderador_total_esperado`  | `float`           |                                                                                        |
| `ponderador_total_cubierto`  | `float`           |                                                                                        |

**Esquema del DataFrame — sin validación INEGI (índice compuesto: `(Periodo, indice)`):**

| Columna                      | dtype pandas      | Notas                                                    |
| ---------------------------- | ----------------- | -------------------------------------------------------- |
| `version`                    | `int`             |                                                          |
| `tipo`                       | `object` (str)    |                                                          |
| `indice_replicado`           | `float` / `NaN`   | NaN cuando `estado_calculo not in {'ok', 'semi_ok'}`     |
| `estado_calculo`             | `object` (str)    | `'ok'`, `'semi_ok'`, `'null_por_faltantes'`, `'fallida'` |
| `motivo_error`               | `object` (str/NaN)|                                                          |
| `total_genericos_esperados`  | `int`             |                                                          |
| `total_genericos_con_indice` | `int`             |                                                          |
| `total_genericos_sin_indice` | `int`             |                                                          |
| `cobertura_genericos_pct`    | `float`           |                                                          |
| `ponderador_total_esperado`  | `float`           |                                                          |
| `ponderador_total_cubierto`  | `float`           |                                                          |

**Invariantes — validados al construir:**

| Invariante                 | Regla                                                                                                          |
| -------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Versión válida             | `version` in `{2010, 2013, 2018, 2024}`                                                                        |
| `estado_calculo` válido    | valores in `{'ok', 'semi_ok', 'null_por_faltantes', 'fallida'}`                                                |
| `estado_validacion` válido | cuando presente: valores in `{'ok', 'diferencia_detectada', 'diferencia_detectada_imputado', 'no_disponible'}` |
| Consistencia ok/semi_ok    | si `estado_calculo in {'ok', 'semi_ok'}` → `indice_replicado` no NaN                                           |
| Consistencia fallo         | si `estado_calculo not in {'ok', 'semi_ok'}` → `indice_replicado` NaN                                          |
| Consistencia validacion    | cuando presente: si `estado_validacion == 'no_disponible'` → `indice_inegi`, `error_*` NaN                     |
| Al menos una fila          | el DataFrame no está vacío                                                                                     |

**Nota — tipos con validación INEGI disponible:**

Solo los siguientes `tipo` incluyen las columnas de validación en el DataFrame:
`"inpc"`, `"inflacion componente"`, `"inflacion subcomponente"`.

El resto de clasificaciones (`"COG"`, `"CCIF division"`, `"CCIF grupo"`, `"CCIF clase"`,
`"inflacion agrupacion"`, `"SCIAN sector"`, `"SCIAN rama"`, `"durabilidad"`) no tienen
series publicadas por el INEGI que permitan comparación directa.

Estas constantes viven en `dominio/tipos.py` como `TIPOS_CON_VALIDACION` y
`COLUMNAS_CLASIFICACION`.

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

| Columna          | dtype pandas       | Notas                                                  |
| ---------------- | ------------------ | ------------------------------------------------------ |
| `id_corrida`     | `object` (str)     |                                                        |
| `version`        | `int`              |                                                        |
| `tipo`           | `object` (str)     | `'inpc'` en v1                                         |
| `periodo`        | `Periodo` / `NaN`  | NaN cuando `tipo_faltante == 'ponderador'`             |
| `generico`       | `object` (str)     |                                                        |
| `nivel_faltante` | `object` (str)     | `'periodo'`, `'estructural'`                           |
| `tipo_faltante`  | `object` (str)     | `'indice'`, `'ponderador'`, `'indice_imputado'`        |
| `detalle`        | `object` (str)     | para `'indice_imputado'`: `"imputado desde <Periodo>"` |

**Invariantes — validados al construir:**

| Invariante              | Regla                                                                  |
| ----------------------- | ---------------------------------------------------------------------- |
| Versión válida          | `version` in `{2010, 2013, 2018, 2024}`                                |
| `nivel_faltante` válido | valores in `{'periodo', 'estructural'}`                                |
| `tipo_faltante` válido  | valores in `{'indice', 'ponderador', 'indice_imputado'}`               |
| Consistencia índice     | si `tipo_faltante in {'indice', 'indice_imputado'}` → `periodo` no NaN |
| Consistencia ponderador | si `tipo_faltante == 'ponderador'` → `periodo` NaN                     |

**Semántica de `'indice_imputado'`:** el genérico tenía `NaN` en ese periodo en la serie original, pero fue rellenado con el valor del periodo disponible más próximo (ver §11.21). `estado_calculo` queda `'ok'` — el cálculo sí se realizó. La fila en el diagnóstico conserva trazabilidad: el campo `detalle` indica desde qué periodo se tomó el valor.

El DataFrame puede estar vacío — cero filas indica que no se detectaron faltantes ni imputaciones en la corrida.

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
        tipo: str,
    ) -> ResultadoCalculo: ...
```

**Selección de implementación — `estrategia.py`:**

La selección vive en `dominio/calculo/estrategia.py` como función de fábrica.
La canasta codifica qué estrategia usar: `encadenamiento` vacío → directo,
con valores → encadenado.

```python
def para_canasta(
    canasta: CanastaCanonica,
    f_h_por_indice: dict[str, float] | None = None,
) -> CalculadorBase:
    if canasta.df["encadenamiento"].isna().all():
        return LaspeyresDirecto()
    return LaspeyresEncadenado(f_h_por_indice)
```

| Versión    | Implementación        | Archivo                         |
| ---------- | --------------------- | ------------------------------- |
| 2010, 2018 | `LaspeyresDirecto`    | `dominio/calculo/laspeyres.py`  |
| 2013, 2024 | `LaspeyresEncadenado` | `dominio/calculo/encadenado.py` |

El caso de uso `ejecutar_corrida.py` no necesita saber qué estrategia existe —
extrae `f_h_por_indice` del `resultado_referencia` (si lo hay) y llama
`para_canasta(canasta, f_h_por_indice).calcular(canasta, serie, id_corrida, tipo)`.

---

#### 5.8.1 LaspeyresDirecto

Implementa `CalculadorBase` para canastas sin encadenamiento (versiones 2010 y 2018).
El dispatch entre INPC y subíndices ocurre internamente según `tipo`.

**Fórmula (INPC y por subgrupo):**

$$I^t = \frac{\sum_j w_j \cdot I_j^t}{\sum_j w_j}$$

Donde $w_j$ son los ponderadores del grupo e $I_j^t$ es el índice del genérico $j$ en el periodo $t$. Para el INPC completo $\sum_j w_j = 100$; para un subgrupo $\sum_j w_j < 100$. La fórmula es válida en ambos casos sin renormalizar.

**Dispatch interno:**

- `tipo in INDICE_POR_TIPO`: calcula sobre la canasta completa; `indice = INDICE_POR_TIPO[tipo]`.
- `tipo in COLUMNAS_CLASIFICACION`: delega el split a `_subindices.grupos_por_clasificacion()`
  y aplica la fórmula por cada grupo; `indice = categoria` (clave del groupby).

**Comportamiento ante NaN:** si algún genérico tiene `NaN` en un periodo, ese periodo se marca `estado_calculo = 'null_por_faltantes'` e `indice_replicado = NaN`. El resto de periodos se calcula normalmente.

**Archivo:** `dominio/calculo/laspeyres.py`

---

#### 5.8.2 LaspeyresEncadenado

Aplica a canastas con encadenamiento (versiones 2013 y 2024). El factor $f_k$ por genérico se define como el valor del índice publicado del genérico $k$ en el **periodo de traslape** de la versión dividido entre 100:

$$f_k = \frac{I_k^{\text{pub}}[t_{\text{traslape}}]}{100}$$

| Versión | Traslape (`t_traslape`)  |
| ------- | ------------------------ |
| 2013    | `Periodo(2013, 4, 1)`    |
| 2024    | `Periodo(2024, 7, 2)`    |

Las series publicadas ya están encadenadas: $I_k^{\text{pub}} = f_k \cdot I_k^{\text{raw}}$, donde $I_k^{\text{raw}}$ tiene base $t_{\text{traslape}} = 100$. El calculador invierte ese encadenamiento por genérico, aplica Laspeyres sobre los índices crudos y re-encadena el agregado con su propio factor ponderado.

**Obtención de $f_k$ (por genérico):** dos fuentes, en orden de preferencia:

1. **Columna `encadenamiento` de la canasta** — cuando está poblada (versiones 2013 y 2024). Se convierte con `astype(float)`.
2. **Serie en el periodo de traslape** — fallback cuando la columna está ausente o vacía. Se obtiene como `serie.df[RANGOS_VALIDOS[version][0]] / 100`.

**Fórmula para un agregado $h$ (INPC o subíndice):**

$$I_k^{\text{raw}}[t] = \frac{I_k^{\text{pub}}[t]}{f_k} \qquad \text{De-encadenamos por genérico}$$

$$I_h^{\text{raw}}[t] = \frac{\displaystyle\sum_{k \in h} w_k \cdot I_k^{\text{raw}}[t]}{\displaystyle\sum_{k \in h} w_k} \qquad \text{Laspeyres crudo}$$

$$I_h^{\text{pub}}[t] = f_h \cdot I_h^{\text{raw}}[t] \qquad \text{Re-encadenamiento del agregado}$$

**Obtención de $f_h$ (por agregado):** dos fuentes, en orden de preferencia:

1. **Resultado de referencia** — `resultado_referencia.df.at[(traslape, indice), "indice_replicado"] / 100`. Se provee el `ResultadoCalculo` de la versión anterior (2018 para el encadenamiento 2024). Este es el $f_h$ exacto del INEGI: $f_h^{\text{INEGI}} = I_h^{(2018)}[t_{\text{traslape}}] / 100$, calculado con los 299 ponderadores de la estructura anterior.

2. **Media ponderada de $f_k$** — fallback cuando no hay referencia o el índice no está en ella:

$$f_h = \frac{\displaystyle\sum_{k \in h} w_k \cdot f_k}{\displaystyle\sum_{k \in h} w_k}$$

   Esta aproximación usa ponderadores **nuevos** en lugar de los viejos, y produce un error sistemático observable en datos reales (~0.53% relativo). Ver §11.20.

Para el INPC general $\sum_{k \in h} w_k = 100$ (invariante de `CanastaCanonica`). Para subíndices $\sum_{k \in h} w_k < 100$; el denominador correcto es siempre $\sum_{k \in h} w_k$.

En el periodo de traslape con fuente 1: $I_h^{\text{pub}}[t_{\text{traslape}}] \approx f_h \cdot 100$ exacto. Con fuente 2: $\approx$ exacto (los $f_k$ individuales son exactos; el error surge solo al agregar con ponderadores distintos).

**Firma:**

```python
class LaspeyresEncadenado(CalculadorBase):
    def __init__(self, f_h_por_indice: dict[str, float] | None = None) -> None: ...
    def calcular(
        self,
        canasta: CanastaCanonica,
        serie: SerieNormalizada,
        id_corrida: str,
        tipo: str,
    ) -> ResultadoCalculo: ...
```

El constructor recibe `f_h_por_indice` — un diccionario `{nombre_indice: f_h}` extraído de un `resultado_referencia` en el traslape. Si es `None` o un índice no está en el dict, se usa la media ponderada (fuente 2). El dispatch entre INPC y subíndices es interno.

**No-aditividad:** después del periodo de traslape, los subíndices encadenados no necesariamente suman al INPC encadenado. Cada agregado tiene su propio $f_h$. El INEGI advierte esta propiedad explícitamente. El proyecto replica cada índice de forma independiente — no intenta reconstruir el INPC a partir de subíndices.

**Archivo:** `dominio/calculo/encadenado.py`

---

#### 5.8.3 grupos_por_clasificacion

Helper generador usado internamente por `LaspeyresDirecto` y `LaspeyresEncadenado`. Realiza el split de canasta y serie por categoría una sola vez; cada calculador aplica su propia fórmula sobre los pares resultantes.

```python
def grupos_por_clasificacion(
    canasta: CanastaCanonica,
    serie: SerieNormalizada,
    tipo: str,
) -> Iterator[tuple[str, pd.DataFrame, pd.DataFrame]]: ...
```

Yields `(categoria, df_canasta_grupo, df_serie_grupo)` para cada categoría única no vacía de `canasta.df[tipo]` (`dropna=True`). Genéricos sin categoría asignada se excluyen — no pertenecen a ningún subíndice.

**Invariante:** cada subíndice es un Laspeyres independiente sobre su subconjunto de genéricos — no se deriva del INPC general. Los ponderadores del subgrupo suman < 100; la fórmula de §5.8.1 o §5.8.2 usa $\sum w_j$ como denominador, no 100.

**Sin construcción de `CanastaCanonica` por subgrupo:** los pares `(df_canasta_grupo, df_serie_grupo)` son DataFrames crudos. El invariante $\sum w_j = 100$ de `CanastaCanonica` se verifica una sola vez sobre la canasta completa, antes del split.

**Archivo:** `dominio/calculo/subindices.py`

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

#### INDICE_POR_TIPO

Mapeo de `tipo` (parámetro del usuario) al string que se usa como valor en el nivel
`indice` del MultiIndex `(Periodo, indice)`. Aplica únicamente cuando `tipo in INDICE_POR_TIPO`
(cálculo de un índice agregado, no de subíndices por clasificación).

```python
INDICE_POR_TIPO: dict[str, str] = {"inpc": "INPC"}
```

Cuando `tipo in INDICE_POR_TIPO`, `LaspeyresDirecto` deriva internamente:

```python
indice = INDICE_POR_TIPO[tipo]
```

Cuando `tipo in COLUMNAS_CLASIFICACION`, el `indice` de cada fila es el valor de la
categoría directamente (ej. `"subyacente"`, `"no subyacente"`). Ver §5.8.1 y §5.8.3.

---

#### COLUMNAS_CLASIFICACION

Conjunto de nombres de columnas de `CanastaCanonica` que pueden usarse como `tipo`
para calcular subíndices. `EjecutarCorrida` y la fachada aceptan como `tipo` válido
cualquier valor de `INDICE_POR_TIPO` **o** cualquier valor de `COLUMNAS_CLASIFICACION`.

```python
COLUMNAS_CLASIFICACION: frozenset[str] = frozenset({
    "COG",
    "CCIF division",
    "CCIF grupo",
    "CCIF clase",
    "inflacion componente",
    "inflacion subcomponente",
    "inflacion agrupacion",
    "SCIAN sector",
    "SCIAN rama",
    "durabilidad",
    "canasta basica",
})
```

Ver §11.7 para los valores concretos de cada columna en la canasta 2018.

---

#### TIPOS_CON_VALIDACION

Conjunto de tipos para los cuales existen series publicadas por el INEGI que permiten
comparación directa. Controla qué esquema producen `ReporteDetalladoValidacion` y
`ResumenValidacion` — ver §5.5 y §5.6.

```python
TIPOS_CON_VALIDACION: frozenset[str] = frozenset(
    {"inpc", "inflacion componente", "inflacion subcomponente"}
)
```

Los tipos en `COLUMNAS_CLASIFICACION` pero **fuera** de `TIPOS_CON_VALIDACION` generan
un reporte sin columnas de error ni estado de validación.

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
antes de pasarla a `correspondencia.py` — ver §7.2 paso 3.5.

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

`_repr_html_` muestra los 4 artefactos apilados en orden de mayor resumen a mayor
detalle: `resumen` → `reporte` → `diagnostico` → `resultado`. Compatible con
JupyterLab, Jupyter clásico, Google Colab, VS Code y Databricks (DBR >= 11.3).

```python
def _repr_html_(self) -> str:
    return (
        "<h3>Resumen</h3>" + self.resumen._repr_html_() +
        "<h3>Reporte</h3>" + self.reporte._repr_html_() +
        "<h3>Diagnóstico</h3>" + self.diagnostico._repr_html_() +
        "<h3>Resultado</h3>" + self.resultado._repr_html_()
    )
```

Nota: se llama `._repr_html_()` de cada artefacto (no `.df._repr_html_()`). En el caso de
`resultado` y `reporte`, eso conserva la vista larga; para ver la forma ancha hay que usar
`como_tabla(ancho=True)` explícitamente.

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

#### `validar` — resultado quincenal

```python
def validar(
    resultado: ResultadoCalculo,
    inegi: dict[str, dict[PeriodoQuincenal | PeriodoMensual, float | None]],
    canasta: CanastaCanonica,
    serie: SerieNormalizada,
    id_corrida: str,
    imputados: dict[tuple[str, PeriodoQuincenal], PeriodoQuincenal] | None = None,
) -> tuple[ResumenValidacion, ReporteDetalladoValidacion, DiagnosticoFaltantes]:
```

| Parámetro    | Tipo                                                                 | Notas                                                                                                       |
| ------------ | -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `resultado`  | `ResultadoCalculo`                                                   | Resultado calculado; puede contener múltiples índices en el MultiIndex                                      |
| `inegi`      | `dict[str, dict[PeriodoQuincenal \| PeriodoMensual, float \| None]]` | Clave = nombre del índice. Dict vacío `{}` si la fuente no estaba disponible                                |
| `canasta`    | `CanastaCanonica`                                                    | Canasta original completa — se usa para cobertura por subgrupo                                              |
| `serie`      | `SerieNormalizada`                                                   | Serie original completa — se usa para calcular cobertura por periodo                                        |
| `id_corrida` | `str`                                                                | Para etiquetar los artefactos                                                                               |
| `imputados`  | `dict[tuple[str, PeriodoQuincenal], PeriodoQuincenal] \| None`       | Periodos imputados por `_rellenar_faltantes`; opcional                                                      |

**Loop sobre índices:** itera sobre todos los valores únicos del nivel `indice` del MultiIndex
de `resultado`. Para cada índice determina a qué subgrupo de `canasta` pertenece:

- Si `tipo in COLUMNAS_CLASIFICACION`: filtra `canasta.df[tipo] == indice` para obtener los
  ponderadores y genéricos del subgrupo. `ponderador_total_esperado` refleja el peso original
  del subgrupo en el INPC total (no re-normalizado).
- Si `tipo in INDICE_POR_TIPO` (ej. `"inpc"`): usa la canasta completa.

**Esquema condicional:** si `tipo in TIPOS_CON_VALIDACION`, el reporte incluye columnas de
validación INEGI (`indice_inegi`, `error_absoluto`, `error_relativo`, `estado_validacion`) y
el resumen incluye `error_absoluto_max`, `error_relativo_max`, `estado_validacion_global`.
Para el resto de tipos estas columnas están ausentes — ver §5.5 y §5.6.

**Lookup por índice:** para cada `indice` en el loop, la función hace `inegi.get(indice, {})` para obtener el dict de periodos de ese índice específico. Esto unifica el acceso tanto para `"inpc"` (`inegi["INPC"][periodo]`) como para subíndices (`inegi["subyacente"][periodo]`).

**Comportamiento cuando `inegi` es vacío o el índice no tiene entrada:** todos los periodos reciben `estado_validacion = 'no_disponible'` y los campos de error quedan en `NaN`. `estado_validacion_global` en `ResumenValidacion` = `'no_disponible'`.

---

#### `validar_mensual` — resultado mensual (sin cobertura de genéricos)

Función complementaria para validar un `ResultadoCalculo` con `PeriodoMensual` contra índices mensuales publicados por el INEGI. No requiere `canasta` ni `serie` — no calcula cobertura de genéricos (esa información ya está en el reporte quincenal de la misma corrida).

```python
def validar_mensual(
    resultado: ResultadoCalculo,
    inegi: dict[str, dict[PeriodoMensual, float | None]],
) -> tuple[ResumenValidacion, ReporteDetalladoValidacion, DiagnosticoFaltantes]:
```

| Parámetro   | Tipo                                                  | Notas                                                                          |
| ----------- | ----------------------------------------------------- | ------------------------------------------------------------------------------ |
| `resultado` | `ResultadoCalculo`                                    | Periodos deben ser todos `PeriodoMensual`; puede incluir `semi_ok`             |
| `inegi`     | `dict[str, dict[PeriodoMensual, float \| None]]`      | Obtenido con `FuenteValidacionApi(...).obtener(periodos_mensuales)`            |

`id_corrida` se toma de `resultado.id_corrida` — no se pasa como parámetro.

**Retorna tupla de 3** igual que `validar` — `DiagnosticoFaltantes` siempre vacío (sin `serie` no hay info de faltantes). Mantiene el mismo patrón de desempaquetado.

**Tolerancia por versión:** en resultados combinados (`a_mensual(combinar([r2018, r2024]))`), cada fila puede tener distinta `version`. La tolerancia se aplica por fila usando `_TOLERANCIAS[fila["version"]]`, no una sola vez con `iloc[0]`.

**`version` en `ResumenValidacion`:** para corrida simple → `int` (ej. `2018`). Para resultado combinado con múltiples versiones → `str` compuesto `"V1+V2"` (ej. `"2018+2024"`, versiones ordenadas ascendente). La invariante de `ResumenValidacion` acepta ambas formas.

**Diferencias vs `validar`:**

| Aspecto                      | `validar`                                    | `validar_mensual`                               |
| ---------------------------- | -------------------------------------------- | ----------------------------------------------- |
| Tipo de periodos en resultado| `PeriodoQuincenal`                           | `PeriodoMensual`                                |
| Cobertura de genéricos       | Calculada desde `serie`                      | `NaN` — no disponible sin `serie`               |
| `DiagnosticoFaltantes`       | Calculado                                    | Vacío (mismo tipo, mismo patrón de retorno)     |
| Tolerancia                   | Una por corrida (`iloc[0]`)                  | Por fila según `version`                        |
| `semi_ok`                    | No aparece (calculador solo produce quinc.)  | Sí — tratado igual que `ok` para validar        |
| Indicador INEGI              | 910420 (quincenal)                           | 910392 (mensual)                                |

**Flujo típico:**

```python
r_q = corrida.ejecutar(...)                    # quincenal + validación completa
r_m = a_mensual(r_q.resultado)                 # convierte a mensual
fuente = FuenteValidacionApi(token, "inpc")
periodos_m = list(r_m.df.index.get_level_values("periodo").unique())
inegi_m = fuente.obtener(periodos_m)
resumen_m, reporte_m, _ = validar_mensual(r_m, inegi_m)
```

---

### 5.12 variaciones.py — `ResultadoVariacion` y funciones de variación

Módulo de análisis post-cálculo. Dado un `ResultadoCalculo` (de `corrida.ejecutar()` o de `combinar()`), calcula variaciones periódicas, acumuladas anuales, o desde una fecha base arbitraria.

Dos archivos:

- `dominio/modelos/variacion.py` — clase `ResultadoVariacion`
- `dominio/variaciones.py` — funciones públicas + helper privado

Exposición pública vía `replica_inpc/__init__.py` (mismo patrón que `combinar`):

```python
from replica_inpc import variacion_periodica, variacion_desde, variacion_acumulada_anual
```

---

#### Regla drop/keep (todas las funciones)

Después de calcular `variacion = I[t] / I[base] - 1`:

| `indice_replicado[t]` en input | variacion | Acción |
| ------------------------------ | --------- | ------ |
| NOT NaN | NaN (base ausente o base falló) | **DROP** — fila excluida del output |
| NaN | NaN | **KEEP** — índice existía pero su cálculo falló ese periodo |
| NOT NaN | NOT NaN | **KEEP** — variación válida |

El output está ordenado por `(periodo, indice)`.

---

#### `ResultadoVariacion`

```python
class ResultadoVariacion:
    def __init__(
        self,
        df: pd.DataFrame,
        tipo: str,
        descripcion: str,
        clase_variacion: Literal["periodica", "acumulada_anual", "desde"],
        indices_parciales: dict[str, Periodo] | None = None,
        periodos_semiok: frozenset[Periodo] | None = None,
    ) -> None: ...

    @property
    def tipo(self) -> str: ...               # clasificación: "inpc", "CCIF division", etc.
    @property
    def descripcion(self) -> str: ...        # "mensual", "anual", "acumulada_anual", "desde 2Q Ene 2023 hasta 2Q Dic 2024"
    @property
    def clase_variacion(self) -> str: ...    # "periodica", "acumulada_anual" o "desde"
    @property
    def periodos_semiok(self) -> frozenset[Periodo]: ...
    # Periodos con estado_calculo == "semi_ok" en el ResultadoCalculo origen.
    # Poblado automáticamente por variacion_periodica, variacion_acumulada_anual y variacion_desde.
    # Usado por validar_variaciones para excluir periodos cuya base es semi_ok.
    @property
    def df(self) -> pd.DataFrame: ...
    @property
    def indices_parciales(self) -> dict[str, Periodo]: ...
    # Índices cuya base fue ajustada (inicio posterior a `desde`).
    # key = nombre del índice, value = periodo base real usado.
    # Vacío para variacion_periodica y variacion_acumulada_anual.
    # Vacío para variacion_desde cuando incluir_parciales=False.

    def como_tabla(self, ancho: bool = False, pct: bool = True) -> pd.DataFrame: ...
    def _repr_html_(self) -> str: ...
```

**Esquema del DataFrame interno (índice: `periodo`, `indice`):**

| Columna     | dtype pandas | Notas                                        |
| ----------- | ------------ | -------------------------------------------- |
| `variacion` | `float64`    | `I[t] / I[base] - 1`; ver regla drop/keep    |

**`como_tabla(ancho, pct)`:**

- `ancho=False, pct=True` (default): df largo con `variacion * 100`
- `ancho=False, pct=False`: df largo con `variacion` en decimales
- `ancho=True`: pivota — `indice` como filas, `periodo` como columnas; aplica `pct` a los valores

**`_repr_html_`:** muestra encabezado `tipo — descripcion`, seguido de `como_tabla(ancho=False, pct=True)`. Si `indices_parciales` no está vacío, agrega nota con los índices afectados y su periodo base real.

**Invariantes — validados al construir:**

| Invariante               | Regla                                                       |
| ------------------------ | ----------------------------------------------------------- |
| df no vacío              | `df` no puede estar vacío                                   |
| índice correcto          | MultiIndex con niveles `["periodo", "indice"]`              |
| columna `variacion`      | debe existir en `df`                                        |
| `tipo` no vacío          | string no vacío                                             |
| `descripcion` no vacío   | string no vacío                                             |
| `clase_variacion` válido | valor en `{"periodica", "acumulada_anual", "desde"}`        |

---

#### Funciones públicas

**`variacion_periodica(resultado, frecuencia)`**

```python
def variacion_periodica(
    resultado: ResultadoCalculo,
    frecuencia: Literal[
        "quincenal", "mensual", "bimestral", "trimestral",
        "cuatrimestral", "semestral", "anual"
    ],
) -> ResultadoVariacion:
```

Detecta automáticamente si el resultado es quincenal o mensual y aplica el lag correspondiente.

**Datos quincenales** — lag en quincenas (`_LAG_QUINCENAL`):

| frecuencia      | lag |
| --------------- | --- |
| `quincenal`     | 1   |
| `mensual`       | 2   |
| `bimestral`     | 4   |
| `trimestral`    | 6   |
| `cuatrimestral` | 8   |
| `semestral`     | 12  |
| `anual`         | 24  |

**Datos mensuales** — lag en meses (`_LAG_MENSUAL`):

| frecuencia      | lag |
| --------------- | --- |
| `mensual`       | 1   |
| `bimestral`     | 2   |
| `trimestral`    | 3   |
| `cuatrimestral` | 4   |
| `semestral`     | 6   |
| `anual`         | 12  |

Si `frecuencia = "quincenal"` con datos mensuales → `UserWarning("frecuencia 'quincenal' no aplica a datos mensuales. Se usará 'mensual'.")` y continúa con `"mensual"`.

`variacion_periodica(..., "anual")` es equivalente a la inflación interanual en ambos casos.

Se aplica la regla drop/keep. Los primeros `lag` periodos de cada índice quedan sin base → DROPeados.

Raises `InvarianteViolado` si:

- `resultado.df["tipo"]` no es homogéneo
- Ningún periodo tiene base disponible: `"Sin periodos con base para frecuencia '{frecuencia}'. Se requieren ≥{lag} periodos de datos."`

`descripcion` = `frecuencia`. `clase_variacion` = `"periodica"`. `periodos_semiok` poblado desde `resultado.df["estado_calculo"]`.

`indices_parciales` = `{}` (no aplica).

`descripcion` = valor de `frecuencia` (posiblemente corregido a `"mensual"` si hubo warning).

---

**`variacion_desde(resultado, desde, hasta=None, incluir_parciales=False)`**

```python
def variacion_desde(
    resultado: ResultadoCalculo,
    desde: str,
    hasta: str | None = None,
    incluir_parciales: bool = False,
) -> ResultadoVariacion:
```

`desde` y `hasta` son strings detectados automáticamente con `periodo_desde_str()`: `"1Q Mes AAAA"` → `PeriodoQuincenal`; `"Mes AAAA"` → `PeriodoMensual`.

Calcula la variación acumulada desde `desde` hasta `hasta`.

`base_periodo` = periodo inmediato anterior a `desde`: usa `_restar_quincenas(desde_p, 1)` para quincenal o `_restar_meses(desde_p, 1)` para mensual. Es el denominador de todos los cálculos. La variación en el primer periodo del output es `I[desde] / I[base_periodo] - 1`.

Raises `InvarianteViolado` si el tipo de `desde`/`hasta` no coincide con el tipo de periodos del resultado (`"no se pueden mezclar tipos de periodo"`).

`hasta=None` → se usa el último periodo disponible en `resultado`.

**`incluir_parciales=False` (default):**

Solo incluye índices con `indice_replicado` válido (NOT NaN) en `base_periodo`. Para cada `(t, indice)` con `desde <= t <= hasta` calcula `I[t] / I[base_periodo, indice] - 1`. Se aplica regla drop/keep. `indices_parciales` = `{}`.

**`incluir_parciales=True`:**

Incluye también índices sin dato en `base_periodo`. Para cada índice se distinguen dos casos:

- **No-parcial** (tiene dato válido en `base_periodo`): misma lógica que `incluir_parciales=False`; base = `base_periodo`. No aparece en `indices_parciales`.
- **Parcial** (sin dato válido en `base_periodo`): base = `t0`, el primer periodo en `[desde, hasta]` con `indice_replicado` NOT NaN. Variación en `t0` = 0; periodos siguientes acumulan desde `t0`. Aparece en `indices_parciales` con valor `t0`.

Se aplica regla drop/keep. `indices_parciales` contiene solo los índices parciales y su `t0`.

Raises `InvarianteViolado` si:

- `resultado.df["tipo"]` no es homogéneo
- `hasta < desde`: `"'hasta' debe ser posterior a 'desde'"`
- `base_periodo` no existe en el df (ej. `desde` es el primer periodo de datos): `"No hay datos en '{base_periodo}' (base de '{desde_p}'). 'desde' mínimo válido: '{min_desde}'."`
- Ningún índice tiene dato en el rango (output vacío): `"Ningún índice tiene dato en el rango [{desde}, {hasta}]. Usa incluir_parciales=True."` (solo si `incluir_parciales=False`) o `"Sin datos en el rango desde {desde} hasta {hasta}."` (si `incluir_parciales=True`)

`descripcion` = `f"desde {desde} hasta {hasta_efectivo}"`. `clase_variacion` = `"desde"`. `periodos_semiok` poblado desde `resultado.df["estado_calculo"]`.

---

**`variacion_acumulada_anual(resultado)`**

```python
def variacion_acumulada_anual(
    resultado: ResultadoCalculo,
) -> ResultadoVariacion:
```

Para cada `(periodo t, indice)` calcula `I[t] / I[base_anual(t), indice] - 1`, donde:

- Datos quincenales: `base_anual(t) = PeriodoQuincenal(t.año - 1, 12, 2)` — `2Q Dic` del año anterior.
- Datos mensuales: `base_anual(t) = PeriodoMensual(t.año - 1, 12)` — `Dic` mensual del año anterior.

La base cambia por año: periodos de 2024 usan Dic 2023 (en su formato correspondiente).

Se aplica la regla drop/keep. El primer año de datos de cada índice queda sin base → DROPeado.

Raises `InvarianteViolado` si:

- `resultado.df["tipo"]` no es homogéneo
- Ningún periodo tiene base anual disponible: `"Sin periodos con base anual disponible. Se requiere ≥1 año de datos."`

`indices_parciales` = `{}` (no aplica).

`descripcion` = `"acumulada_anual"`. `clase_variacion` = `"acumulada_anual"`. `periodos_semiok` poblado desde `resultado.df["estado_calculo"]`.

---

#### Helpers privados

**`_restar_quincenas(periodo: PeriodoQuincenal, n: int) -> PeriodoQuincenal`**

```python
def _restar_quincenas(periodo: PeriodoQuincenal, n: int) -> PeriodoQuincenal:
    if periodo.es_mensual:
        raise InvarianteViolado("_restar_quincenas no aplica a PeriodoMensual")
    ordinal = periodo.año * 24 + (periodo.mes - 1) * 2 + (periodo.quincena - 1)
    ordinal -= n
    año = ordinal // 24
    mes = (ordinal % 24) // 2 + 1
    quincena = (ordinal % 24) % 2 + 1
    return PeriodoQuincenal(año, mes, quincena)
```

Usado por `variacion_periodica` (quincenal) y `variacion_desde` (quincenal).

**`_restar_meses(periodo: PeriodoMensual, n: int) -> PeriodoMensual`**

```python
def _restar_meses(periodo: PeriodoMensual, n: int) -> PeriodoMensual:
    ordinal = periodo.año * 12 + (periodo.mes - 1)
    ordinal -= n
    año = ordinal // 12
    mes = ordinal % 12 + 1
    return PeriodoMensual(año, mes)
```

Usado por `variacion_periodica` (mensual) y `variacion_desde` (mensual).

---

### 5.13 a_mensual — conversión quincenal → mensual

**Archivo:** `dominio/conversion.py`. Exportada desde `replica_inpc`.

```python
def a_mensual(resultado: ResultadoCalculo) -> ResultadoCalculo:
```

Convierte un `ResultadoCalculo` con periodos quincenales a periodos mensuales mediante promedio simple de las dos quincenas de cada mes.

**Restricción:** `resultado` debe ser quincenal (todos `PeriodoQuincenal`). Si ya es mensual → `InvarianteViolado("a_mensual requiere un ResultadoCalculo quincenal")`.

**Cálculo por `(mes, indice)`:**

Para cada mes `(año, mes)` agrupa las filas `1Q` y `2Q` del mismo índice:

| 1Q | 2Q | `indice_replicado` mensual | `estado_calculo` |
| --- | --- | --- | --- |
| valor | valor | `(1Q + 2Q) / 2` | `'ok'` |
| valor | NaN | valor de 1Q | `'semi_ok'` |
| NaN | valor | valor de 2Q | `'semi_ok'` |
| NaN | NaN | NaN | `'null_por_faltantes'` |
| cualquiera | `'fallida'` | NaN | `'fallida'` |

`motivo_error` = NaN para `'ok'` y `'semi_ok'`; hereda el motivo de la quincena fallida/faltante para los demás casos.

**`version`:** hereda la de la quincena más reciente (`2Q` si existe, `1Q` si no).

**`id_corrida`:** mismo que el resultado fuente.

**Mes frontera (ej. Jul 2024 en resultado combinado 2018+2024):**

El resultado de `combinar([r2018, r2024])` tiene `1Q Jul 2024` con `version=2018` y `2Q Jul 2024` con `version=2024`. `a_mensual` los promedia normalmente → `PeriodoMensual(2024, 7)` con `version=2024` (`'ok'`). Es el comportamiento correcto.

**Workflow recomendado:**

```python
# Correcto — encadenamiento se resuelve en quincenal:
resultado_mensual = a_mensual(combinar([r2018.resultado, r2024.resultado]))

# Incorrecto — UserWarning; mes frontera pierde una quincena:
resultado_mensual = combinar([a_mensual(r2018.resultado), a_mensual(r2024.resultado)])
```

**Verificación empírica:** el INPC mensual de INEGI (indicador 910392) es el promedio simple de los quincenales. `a_mensual(combinar([r2018, r2024]))` difiere del INEGI mensual oficial en máximo 0.0000046 relativo (tolerancia: 0.0009). Ver §8.6.

---

### 5.14 ResumenValidacionVariaciones

> **Dead code — diferido a v2.0.** La clase existe en `dominio/modelos/validacion.py` pero no es retornada por ninguna función pública desde v1.2.4. Se retomará cuando `validar_variaciones_mensual` acepte múltiples variaciones a la vez.

**Representación:** DataFrame-backed. Índice MultiIndex `(tipo_variacion, indice)`.
Agrega el resultado de validar variaciones mensuales contra el INEGI.

```python
class ResumenValidacionVariaciones:
    def __init__(self, df: pd.DataFrame) -> None: ...

    @property
    def df(self) -> pd.DataFrame: ...

    def _repr_html_(self) -> str:
        return self.df._repr_html_()
```

**Esquema del DataFrame (índice MultiIndex: `tipo_variacion`, `indice`):**

| Columna | dtype pandas | Notas |
| --- | --- | --- |
| `n_comparaciones` | `int` | periodos efectivamente comparados |
| `n_excluidos` | `int` | periodos excluidos por base `semi_ok` |
| `n_no_disponibles` | `int` | periodos sin dato INEGI |
| `max_error_pp` | `float` / `NaN` | error absoluto máximo en pp; NaN si `n_comparaciones == 0` |
| `estado_validacion_global` | `object` (str) | `'ok'`, `'diferencia_detectada'` o `'no_disponible'` |

Valores de `tipo_variacion`: `"periodica"`, `"interanual"`, `"acumulada_anual"`.

**Invariantes — validados al construir:**

| Invariante | Regla |
| --- | --- |
| Al menos una fila | el DataFrame no está vacío |
| Índice sin duplicados | el MultiIndex no tiene filas repetidas |
| `estado_validacion_global` válido | valores in `{'ok', 'diferencia_detectada', 'no_disponible'}` |

---

### 5.15 ReporteValidacionVariaciones

**Representación:** DataFrame-backed. Índice MultiIndex `(tipo_variacion, periodo, indice)`.
Detalle fila a fila de la comparación variación replicada vs INEGI.

```python
class ReporteValidacionVariaciones:
    def __init__(self, df: pd.DataFrame) -> None: ...

    @property
    def df(self) -> pd.DataFrame: ...

    def como_tabla(self, ancho: bool = False) -> pd.DataFrame: ...

    def _repr_html_(self) -> str:
        return self.como_tabla()._repr_html_()
```

**`como_tabla(ancho=False)`:** descarta el nivel `tipo_variacion` del índice (siempre es uno solo en v1). `ancho=False` devuelve formato largo con índice `(periodo, indice)`. `ancho=True` pivota con periodos como columnas y filas `{indice}_variacion_replicada`, `{indice}_variacion_inegi_pp`, `{indice}_error_absoluto_pp`, `{indice}_estado_validacion`.

**Esquema del DataFrame (índice MultiIndex: `tipo_variacion`, `periodo`, `indice`):**

| Columna | dtype pandas | Notas |
| --- | --- | --- |
| `variacion_replicada_pp` | `float` / `NaN` | variación calculada en porcentaje (pp); NaN si `excluido_semi_ok` o sin dato |
| `variacion_inegi_pp` | `float` / `NaN` | variación publicada por INEGI en porcentaje (pp); NaN si no disponible |
| `error_absoluto_pp` | `float` / `NaN` | `abs(variacion_replicada_pp − variacion_inegi_pp)`; NaN si no comparable |
| `estado_validacion` | `object` (str) | ver valores abajo |

Valores de `estado_validacion`:

| Valor | Condición |
| --- | --- |
| `'ok'` | `error_absoluto_pp` ≤ 0.009 pp |
| `'diferencia_detectada'` | `error_absoluto_pp` > 0.009 pp |
| `'excluido_semi_ok'` | base del periodo tiene `estado_calculo == 'semi_ok'` (solo mensual) |
| `'no_disponible'` | INEGI publicó el indicador para ese rango pero no hay valor en ese periodo |
| `'fuera_de_rango_inegi'` | el periodo es anterior al primer dato publicado por INEGI para ese indicador |

**Invariantes — validados al construir:**

| Invariante | Regla |
| --- | --- |
| Al menos una fila | el DataFrame no está vacío |
| Índice sin duplicados | el MultiIndex no tiene filas repetidas |
| `estado_validacion` válido | valores in `{'ok', 'diferencia_detectada', 'excluido_semi_ok', 'no_disponible', 'fuera_de_rango_inegi'}` |

---

### 5.16 validar_variaciones.py

Función del dominio que compara una variación mensual o quincenal calculada contra las
series publicadas por el INEGI. No hace requests — recibe los datos INEGI ya obtenidos
por la capa api. Privada: llamada solo desde `api/validacion.py`.

**Archivo:** `dominio/validar_variaciones.py`

```python
def validar_variaciones(
    rv: ResultadoVariacion,
    tipo_variacion: Literal["periodica", "interanual", "acumulada_anual"],
    inegi: dict[str, dict[PeriodoMensual | PeriodoQuincenal, float | None]],
) -> ReporteValidacionVariaciones:
```

**Precondición:** `rv` puede tener periodos `PeriodoMensual` o `PeriodoQuincenal`. `tipo_variacion`
indica qué tipo de base usar para la exclusión semi_ok.

**Algoritmo:**

1. Lee `periodos_semiok` desde `rv.periodos_semiok` (poblado al calcular la variación).
2. Para cada `(periodo, indice)` en `rv.df` determina el `estado_validacion`:
   - Calcula `base` según `tipo_variacion` y tipo de periodo (ver tabla abajo).
   - Si `base` está en `periodos_semiok` → `"excluido_semi_ok"`
   - Si `indice` no está en `inegi` o `periodo` no está en `inegi[indice]` → `"fuera_de_rango_inegi"` (el periodo es anterior al primer dato publicado por INEGI para ese indicador)
   - Si `inegi[indice][periodo]` es `None` → `"no_disponible"`
   - Si `abs(variacion_replicada_pp − variacion_inegi_pp)` ≤ `_TOLERANCIA_VARIACION_PP` → `"ok"`
   - Si no → `"diferencia_detectada"`
3. Construye y retorna `ReporteValidacionVariaciones`.

**Cálculo del periodo base:**

| `tipo_variacion` | `PeriodoMensual` | `PeriodoQuincenal` |
| --- | --- | --- |
| `"periodica"` | `_restar_meses(p, 1)` | `_restar_quincenas(p, 1)` |
| `"interanual"` | `_restar_meses(p, 12)` | `_restar_quincenas(p, 24)` |
| `"acumulada_anual"` | `PeriodoMensual(p.año - 1, 12)` | `PeriodoQuincenal(p.año - 1, 12, 2)` |

`_restar_meses` y `_restar_quincenas` se implementan inline en el archivo.

**Detección `fuera_de_rango_inegi`:** `obtener_variaciones` solo incluye en el dict retornado
los periodos `p >= min(historico)` — la ausencia de la clave en el dict indica que el periodo
está fuera del rango publicado por INEGI. Ver §8.6.

**Tolerancia:** `_TOLERANCIA_VARIACION_PP = 0.009` (pp). Aplica igual para mensual y quincenal. Ver §8.7 y §8.8.

---

## 6. Fachada — api/corrida.py

Punto de entrada principal para notebooks. Composition root: instancia todos los
adaptadores concretos y los inyecta en `EjecutarCorrida`.

```python
class Corrida:
    def __init__(
        self,
        ruta_datos: str | Path = "data/runs",
        ruta_salida: str | Path = "output",
        token_inegi: str | None = None,
    ) -> None: ...

    def ejecutar(
        self,
        canasta: str | Path,
        series: str | Path,
        version: VersionCanasta,
        tipo: str = "inpc",
        persistir: bool = False,
        resultado_referencia: ResultadoCalculo | None = None,
    ) -> ResultadoCorrida: ...
```

**Parámetros de `__init__`:**

| Parámetro | Default | Notas |
| --- | --- | --- |
| `ruta_datos` | `"data/runs"` | Base para `RepositorioCorridasFs` y `AlmacenArtefactosFs`. Relativa al CWD del notebook. |
| `ruta_salida` | `"output"` | Destino de los CSV exportados. Relativa al CWD del notebook. |
| `token_inegi` | `None` | Token para la API del INEGI. Si es `None`, la validación queda `no_disponible`. |

**Parámetros de `ejecutar`:**

| Parámetro | Obligatorio | Default | Notas |
| --- | --- | --- | --- |
| `canasta` | sí | — | Ruta al CSV de canasta |
| `series` | sí | — | Ruta al CSV de series |
| `version` | sí | — | `VersionCanasta`: `2010`, `2013`, `2018`, `2024` |
| `tipo` | no | `"inpc"` | Tipo de índice a calcular. Valores válidos: claves de `INDICE_POR_TIPO` o valores de `COLUMNAS_CLASIFICACION`. Lanza `ErrorConfiguracion` si no es válido. |
| `persistir` | no | `False` | Si `True`, guarda artefactos en `ruta_datos` y exporta CSV a `ruta_salida`. La fachada crea los directorios si no existen. |
| `resultado_referencia` | no | `None` | `ResultadoCalculo` de la corrida anterior (ej. 2018) para obtener `f_h` exacto del INEGI en el periodo de traslape. Solo aplica a canastas encadenadas (2013, 2024). Si la canasta no usa encadenamiento, se emite `UserWarning` y se ignora. Ver §11.20. |

**Uso típico:**

```python
corrida = Corrida(token_inegi="mi_token")
r_2018 = corrida.ejecutar(canasta="data/canasta_2018.csv", series="data/series_2018.csv", version=2018)
r_2024 = corrida.ejecutar(
    canasta="data/canasta_2024.csv",
    series="data/series_2024.csv",
    version=2024,
    resultado_referencia=r_2018.resultado,  # f_h exacto — ver §11.20
)
```

**Selección de fuente de validación:**

`ejecutar()` selecciona la fuente según `token_inegi` y `tipo`:

| Condición | Fuente usada |
| --- | --- |
| `token_inegi=None` | `_FuenteValidacionNula` |
| `token_inegi` presente y `tipo in INDICADORES_INEGI` | `FuenteValidacionApi(token_inegi, tipo)` |
| `token_inegi` presente y `tipo not in INDICADORES_INEGI` | `_FuenteValidacionNula` |

`INDICADORES_INEGI` vive en `infraestructura/inegi/fuente_validacion_api.py`. Ver §8.6.

**`_FuenteValidacionNula`:**

Clase interna. Se usa cuando `token_inegi=None`. Lanza `FuenteNoDisponible` en
`obtener()` — el caso de uso la captura y marca la validación como `no_disponible`.

**Errores que puede lanzar `ejecutar`:**

| Error | Causa |
| --- | --- |
| `ErrorConfiguracion` | `tipo` no válido, o `persistir=True` con configuración incompleta |
| `ErrorImportacion` | Archivo no encontrado, vacío, corrupto o mal formado |
| `ErrorCalculo` | Correspondencia insuficiente o ponderador faltante |

---

## 6.2 Fachada de validación — api/validacion.py

Funciones públicas de validación independientes de `Corrida`. Viven en `api/validacion.py`
y se exportan desde `replica_inpc`. Usan `FuenteValidacionApi` internamente — el usuario
solo pasa el `ResultadoCalculo` y el token.

```python
def validar_mensual(
    resultado: ResultadoCalculo,
    token: str,
) -> tuple[ResumenValidacion, ReporteDetalladoValidacion, DiagnosticoFaltantes]: ...

def validar_quincenal(
    resultado: ResultadoCalculo,
    token: str,
) -> tuple[ResumenValidacion, ReporteDetalladoValidacion, DiagnosticoFaltantes]: ...
```

**`validar_mensual`:**

1. Si `resultado` es quincenal (índice contiene `PeriodoQuincenal`) → llama `a_mensual(resultado)` internamente.
2. Detecta `tipo` desde `resultado.df["tipo"].iloc[0]`.
3. Obtiene periodos del índice del resultado mensual.
4. Construye `FuenteValidacionApi(token, tipo)` y llama `.obtener(periodos)`.
5. Delega a `validar_mensual` del dominio (`dominio/validar_inpc.py`).
6. Retorna la tupla resultante.

**`validar_quincenal`:**

1. Si `resultado` es mensual (índice contiene `PeriodoMensual`) → lanza `ErrorConfiguracion`.
2. Detecta `tipo` desde `resultado.df["tipo"].iloc[0]`.
3. Obtiene periodos del índice quincenal.
4. Construye `FuenteValidacionApi(token, tipo)` y llama `.obtener(periodos)`.
5. Delega a `validar` del dominio (`dominio/validar_inpc.py`), pasando `canasta` y `serie` como `None` — **pendiente:** actualmente `validar` requiere `canasta` y `serie`; ver nota abajo.
6. Retorna la tupla resultante.

> **Nota `validar_quincenal`:** la función de dominio `validar()` actualmente requiere
> `CanastaCanonica` y `SerieNormalizada` para calcular cobertura de genéricos y ponderadores.
> `validar_quincenal` en la capa api no tiene acceso a esos objetos. Dos opciones:
>
> a) Pasar `canasta` y `serie` como parámetros opcionales de `validar_quincenal` (más completo).
> b) Extraer la lógica de validación pura (sin cobertura) a una función separada del dominio, análoga a `validar_mensual` que ya opera sin canasta/serie.
>
> **Decisión adoptada:** opción (b) — `validar_quincenal` en la capa api delega a una nueva
> función `validar_quincenal_resultado` en el dominio que, al igual que `validar_mensual`,
> no requiere canasta ni serie y deja las columnas de cobertura en `NaN`.
> La función existente `validar()` se mantiene intacta para el pipeline interno de `EjecutarCorrida`.

**Uso típico en notebook:**

```python
from replica_inpc import combinar, a_mensual, validar_mensual, validar_quincenal

# mensual — acepta quincenal o mensual directamente
resumen, reporte, _ = validar_mensual(
    combinar([inpc_2018.resultado, inpc_2024.resultado]),
    token=TOKEN,
)

# quincenal
resumen_q, reporte_q, diag_q = validar_quincenal(
    combinar([inpc_2018.resultado, inpc_2024.resultado]),
    token=TOKEN,
)
```

**Errores que pueden lanzar:**

| Error | Causa |
| --- | --- |
| `ErrorConfiguracion` | `tipo` no tiene indicador INEGI disponible, o `validar_quincenal` recibe resultado mensual |
| `ErrorConexion` | Fallo de red al consultar la API del INEGI |

**Exportaciones desde `replica_inpc`:**

```python
from replica_inpc import validar_mensual, validar_quincenal
```

> **v2.0:** estas funciones retornarán `ResultadoValidacion` en lugar de la tupla actual.
> Ver gap §12.14.

---

## 6.3 Validación de variaciones — api/validacion.py

Función pública que valida las tres variaciones mensuales calculadas internamente contra
series publicadas por el INEGI. Vive en `api/validacion.py` y se exporta desde `replica_inpc`.

```python
def validar_variaciones_mensual(
    rv: ResultadoVariacion,
    token: str,
) -> ReporteValidacionVariaciones: ...
```

**Comportamiento:**

1. Valida que `rv.clase_variacion` sea soportada — lanza `ErrorConfiguracion` si:
   - `clase_variacion == "desde"`: INEGI no publica ese tipo de variación.
   - `clase_variacion == "periodica"` con `rv.descripcion` no en `{"mensual", "anual"}`: INEGI solo publica periódica mensual e interanual.
2. Valida que los periodos en `rv.df` sean `PeriodoMensual` — lanza `ErrorConfiguracion` si no.
3. Determina `tipo_variacion_inegi`:
   - `clase="periodica"` + `descripcion="mensual"` → `"periodica"`
   - `clase="periodica"` + `descripcion="anual"` → `"interanual"`
   - `clase="acumulada_anual"` → `"acumulada_anual"`
4. Construye `FuenteValidacionApi(token=token, tipo=rv.tipo)` y llama `.obtener_variaciones(periodos, tipo_variacion_inegi)` una vez.
5. Delega a `validar_variaciones(rv, tipo_variacion_inegi, inegi)` del dominio.
6. Retorna el `ReporteValidacionVariaciones` resultante.

**Exclusión de periodos `semi_ok`:** `rv.periodos_semiok` (poblado automáticamente por las funciones de variación) es usado por `validar_variaciones` para excluir periodos cuya base tiene `estado_calculo == "semi_ok"`. Ver §8.7.

### ReporteValidacionVariaciones

Detalle por periodo e índice. Ver §5.15 para el esquema completo.

`como_tabla(ancho=False)`: descarta nivel `tipo_variacion`; `ancho=True` pivota periodos como columnas.

**Tolerancia:** 0.009 pp. Ver §8.7.

**Exportación desde `replica_inpc`:**

```python
from replica_inpc import validar_variaciones_mensual, validar_variaciones_quincenal
```

> **v2.0:** `ResumenValidacionVariaciones` será retornado nuevamente cuando la función acepte múltiples variaciones a la vez.

### validar_variaciones_quincenal

```python
def validar_variaciones_quincenal(
    rv: ResultadoVariacion,
    token: str,
) -> ReporteValidacionVariaciones: ...
```

Igual que `validar_variaciones_mensual` pero para periodos `PeriodoQuincenal`. Lanza `ErrorConfiguracion` si:

- `clase_variacion == "desde"`: INEGI no publica ese tipo.
- `clase_variacion == "periodica"` con `rv.descripcion` no en `{"quincenal", "anual"}`: INEGI solo publica periódica quincenal e interanual.
- Los periodos en `rv.df` no son `PeriodoQuincenal`.

Mapeo `descripcion` → `tipo_variacion_inegi`:

| `clase_variacion` | `rv.descripcion` | `tipo_variacion_inegi` |
| --- | --- | --- |
| `"periodica"` | `"quincenal"` | `"periodica"` |
| `"periodica"` | `"anual"` | `"interanual"` |
| `"acumulada_anual"` | cualquiera | `"acumulada_anual"` |

**Nota sobre cobertura:** interanual quincenal y acumulada anual quincenal solo tienen datos INEGI desde `1Q Ago 2024`. Periodos anteriores aparecen como `fuera_de_rango_inegi` en el reporte. Ver §8.8.

**periodos_semiok:** siempre vacío para quincenal — `semi_ok` es concepto mensual (mes con solo 1 quincena disponible). La exclusión no aplica a cálculos quincenales.

---

## 7. Capa de aplicación

Contiene los contratos de puertos y los casos de uso. No conoce CSV, filesystem ni APIs
— solo opera con los contratos definidos en esta sección.

---

### 7.1 Puertos

Los puertos son los contratos que el dominio impone a sus dependencias externas.
Cada puerto es un `Protocol` de Python — el dominio depende de la interfaz, no de la
implementación concreta. Un nuevo adaptador (xlsx, SQL, API, etc.) solo necesita
implementar el puerto correspondiente sin tocar el dominio.

`VersionCanasta`, `ManifestCorrida` y `ResultadoCorrida` se definen en `dominio/tipos.py`
— ver §5.9.

---

#### 7.1.1 LectorCanasta

Recibe una fuente de datos y devuelve una `CanastaCanonica` lista para usar.
La versión se pasa explícitamente para que el lector sepa qué columnas esperar
y cómo interpretar el archivo.

```python
class LectorCanasta(Protocol):
    def leer(self, ruta: Path, version: VersionCanasta) -> CanastaCanonica: ...
```

---

#### 7.1.2 LectorSeries

Recibe un archivo de series y devuelve una `SerieNormalizada` lista para usar.
Resuelve internamente la orientación (horizontal/vertical), la presencia de
metadatos y el encoding. No filtra por versión — esa responsabilidad es del
caso de uso.

```python
class LectorSeries(Protocol):
    def leer(self, ruta: Path) -> SerieNormalizada: ...
```

---

#### 7.1.3 FuenteValidacion

Obtiene el INPC publicado por el INEGI para los periodos solicitados.
Devuelve `None` por periodo cuando el INEGI no tiene dato para ese periodo.
Lanza excepción cuando la fuente no está disponible — el caso de uso la captura
y marca la validación como `no_disponible`.

```python
class FuenteValidacion(Protocol):
    def obtener(
        self, periodos: list[PeriodoQuincenal | PeriodoMensual]
    ) -> dict[str, dict[PeriodoQuincenal | PeriodoMensual, float | None]]: ...
```

`obtener()` devuelve un dict keyed por nombre de índice (ej. `{"INPC": {periodo: valor}}` para `"inpc"`,
`{"subyacente": {...}, "no subyacente": {...}}` para `"inflacion componente"`).
Devuelve `None` por periodo cuando el INEGI no tiene dato para ese periodo.
Lanza excepción cuando la fuente no está disponible — el caso de uso la captura y pasa `{}` a `validar()`.

Implementaciones:

- `_FuenteValidacionNula` — usada cuando `token_inegi=None`. Siempre lanza `FuenteNoDisponible`.
- `FuenteValidacionApi` — usada cuando `token_inegi` está presente y `tipo in _INDICADORES_QUINCENALES`. Ver §8.6.

---

#### 7.1.4 EscritorResultados

Exporta los artefactos de resultado al usuario. `ResultadoCalculo` no se exporta
directamente — sus datos están contenidos en `ReporteDetalladoValidacion`.

```python
class EscritorResultados(Protocol):
    def escribir_reporte(self, reporte: ReporteDetalladoValidacion, ruta: Path) -> None: ...
    def escribir_diagnostico(self, diagnostico: DiagnosticoFaltantes, ruta: Path) -> None: ...
```

---

#### 7.1.5 RepositorioCorridas

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

#### 7.1.6 AlmacenArtefactos

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
> de guardar; `obtener` los devuelve como string — ver §12.8.

---

### 7.2 EjecutarCorrida

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
        tipo: str = "inpc",
        persistir: bool = False,
        resultado_referencia: ResultadoCalculo | None = None,
    ) -> ResultadoCorrida: ...
```

**Pasos en orden:**

1. Si `persistir=True` y alguno de `repositorio`, `almacen`, `escritor`, `ruta_salida` es `None` → lanza `ErrorConfiguracion`
2. Generar `id_corrida` (UUID) y crear `ManifestCorrida`
3. `LectorCanasta.leer(ruta_canasta, version)` → `CanastaCanonica`
4. `LectorSeries.leer(ruta_series)` → `SerieNormalizada` (todos los periodos del archivo; no depende del paso 3)
5. Filtrar columnas de `serie` a `RANGOS_VALIDOS[version]` → `SerieNormalizada` con solo los periodos válidos. Si ninguna columna cae en el rango → `PeriodosInsuficientes`
6. `correspondencia.py` — valida y alinea genérico↔genérico
6.5. `_rellenar_faltantes(serie)` → `(SerieNormalizada, imputados)`. Rellena NaN con el valor del periodo disponible más próximo (adelante primero, atrás si no hay). `imputados` es `dict[tuple[str, Periodo], Periodo]` que mapea `(generico, periodo)` al periodo fuente del que se tomó el valor — ver §11.21.
7. Si `resultado_referencia` no es `None` y la canasta usa encadenamiento: `_f_h_desde_referencia(resultado_referencia, traslape)` → `f_h_por_indice`. Si la canasta no usa encadenamiento: emite `UserWarning` e ignora `resultado_referencia`. Cálculo: `para_canasta(canasta, f_h_por_indice).calcular(canasta, serie, id_corrida, tipo)` → `ResultadoCalculo`. El dispatch entre INPC y subíndices es interno al calculador — ver §5.8.1 y §5.8.3.
8. `periodos = resultado.df.index.get_level_values("periodo").unique()`; `FuenteValidacion.obtener(periodos)` — si lanza `ErrorValidacion`: continúa con validación `no_disponible`
9. `validar_inpc.py` recibe también `imputados: dict[tuple[str, Periodo], Periodo]` — construye `ResumenValidacion`, `ReporteDetalladoValidacion`, `DiagnosticoFaltantes` (incluye filas `tipo_faltante = 'indice_imputado'` para cada par en `imputados`; periodos imputados que superan tolerancia reciben `estado_validacion = 'diferencia_detectada_imputado'`)
10. Si `persistir=True`:
    - `RepositorioCorridas.guardar(manifest)` → `data/runs/<id_corrida>/`
    - `AlmacenArtefactos.guardar(...)` para `resultado`, `resumen`, `reporte`, `diagnostico` → `data/runs/<id_corrida>/`
    - `EscritorResultados.escribir_reporte()` + `escribir_diagnostico()` → `output/`
11. Devolver `ResultadoCorrida`

**Extensibilidad:** el caso de uso no necesita cambiar al agregar nuevas versiones —
la selección de estrategia en `para_canasta()` absorbe la extensión.

**Errores:** cualquier `ErrorImportacion`, `ErrorDominio` o `ErrorCalculo` falla la corrida
inmediatamente. `ErrorValidacion` no falla la corrida — ver §9.

---

## 8. Infraestructura

Adaptadores concretos que implementan los puertos de §7.1. El dominio y la capa de
aplicación no conocen estos detalles — solo operan con los contratos.

---

### 8.1 Formato del CSV canasta

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
`encadenamiento` a `str` antes de construir `CanastaCanonica` — ver §11.5.
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

### 8.2 Formato del CSV de series

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
son agregados CCIF y se descartan (ver §12.3).

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

### 8.3 Repositorio de corridas (filesystem)

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

### 8.4 Almacén de artefactos (filesystem)

`AlmacenArtefactos` persiste los DataFrames computados por el pipeline como archivos
Parquet en `data/runs/<id_corrida>/<nombre>.parquet`.

**Artefactos guardados:** `resultado`, `resumen`, `reporte`, `diagnostico`.

**Serialización de `Periodo`:** los objetos `Periodo` en el índice o en columnas
se convierten a string con `str(Periodo)` antes de guardar (produce `"1Q Ene 2024"`).
El MultiIndex de `reporte` (`["periodo", "subindice"]`) se preserva gracias a Parquet.

**`obtener()`:** devuelve el DataFrame con el índice como string — no re-parsea
`Periodo`. Ver gap §12.8.

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

### 8.5 Formato de los CSV de salida (escritor)

Archivos exportados a `output/` para consumo del usuario. Generados por
`EscritorResultados` cuando `persistir=True`.

#### reporte_<id_corrida>.csv

El MultiIndex `(Periodo, indice)` de `ReporteDetalladoValidacion.df` se aplana
como columnas regulares. `Periodo` se serializa a string (`"1Q Ene 2024"`).
Diseñado para concatenarse con reportes de otras versiones y construir un historial
completo del INPC — el par `(periodo, subindice)` identifica unívocamente cada fila.

**Renombrado al serializar:** las columnas del modelo se renombran en el CSV para
mayor legibilidad en v1. El serializador aplica este mapeo:

| Nombre en modelo (`§5.6`)     | Nombre en CSV       |
| ----------------------------- | ------------------- |
| nivel `indice` del MultiIndex | `subindice`         |
| `indice_replicado`            | `inpc_replicado`    |
| `indice_inegi`                | `inpc_inegi`        |

En v2, cuando se agreguen subíndices, este mapeo deberá revisarse.

| Columna                       | Tipo     | Notas                                                                         |
| ----------------------------- | -------- | ----------------------------------------------------------------------------- |
| `periodo`                     | `str`    | Ej. `"1Q Ene 2018"`                                                           |
| `subindice`                   | `str`    | Ej. `"INPC general"`                                                          |
| `version`                     | `int`    |                                                                               |
| `inpc_replicado`              | `float`  | `null` si `estado_calculo != 'ok'`                                            |
| `inpc_inegi`                  | `float`  | `null` si validación no disponible                                            |
| `error_absoluto`              | `float`  | `null` si validación no disponible                                            |
| `error_relativo`              | `float`  | `null` si validación no disponible                                            |
| `estado_calculo`              | `str`    | `ok`, `null_por_faltantes`, `fallida`                                         |
| `motivo_error`                | `str`    | `null` si `estado_calculo = 'ok'`                                             |
| `estado_validacion`           | `str`    | `ok`, `diferencia_detectada`, `diferencia_detectada_imputado`, `no_disponible`|
| `total_genericos_esperados`   | `int`    |                                                                               |
| `total_genericos_con_indice`  | `int`    |                                                                               |
| `total_genericos_sin_indice`  | `int`    |                                                                               |
| `cobertura_genericos_pct`     | `float`  |                                                                               |
| `ponderador_total_esperado`   | `float`  |                                                                               |
| `ponderador_total_cubierto`   | `float`  |                                                                               |

#### diagnostico_<id_corrida>.csv

Índice entero descartado (`index=False`). `Periodo` en columna `periodo` serializado
a string.

| Columna          | Tipo  | Notas                                                |
| ---------------- | ----- | ---------------------------------------------------- |
| `id_corrida`     | `str` |                                                      |
| `version`        | `int` |                                                      |
| `periodo`        | `str` | `null` si `nivel_faltante = 'estructural'`           |
| `generico`       | `str` |                                                      |
| `nivel_faltante` | `str` | `periodo`, `estructural`                             |
| `tipo_faltante`  | `str` | `indice`, `ponderador`, `indice_imputado`            |
| `detalle`        | `str` | para `indice_imputado`: `"imputado desde <Periodo>"` |

**Adaptador:**

```python
class EscritorResultadosCsv:
    def escribir_reporte(self, reporte: ReporteDetalladoValidacion, ruta: Path) -> None: ...
    def escribir_diagnostico(self, diagnostico: DiagnosticoFaltantes, ruta: Path) -> None: ...
```

---

### 8.6 FuenteValidacionApi (API del INEGI)

Implementa `FuenteValidacion` consultando la API de indicadores del INEGI.

**Archivo:** `infraestructura/inegi/fuente_validacion_api.py`

**Constructor:**

```python
class FuenteValidacionApi:
    def __init__(self, token: str, tipo: str) -> None: ...
```

Lanza `ErrorConfiguracion` si `tipo not in _INDICADORES_QUINCENALES`.

**Detección automática mensual/quincenal:**

`obtener(periodos)` detecta el tipo de los periodos recibidos (`isinstance(periodos[0], PeriodoMensual)`).
Si son mensuales, usa `_INDICADORES_MENSUALES`; si quincenales, usa `_INDICADORES_QUINCENALES`.
Lanza `ErrorConfiguracion` si el tipo no tiene indicador mensual definido.

**Mapeo tipo → (índice → indicador) — quincenales:**

```python
_INDICADORES_QUINCENALES: dict[str, dict[str, str]] = {
    "inpc": {
        "INPC": "910420",
    },
    "inflacion componente": {
        "subyacente":    "910421",
        "no subyacente": "910424",
    },
    "inflacion subcomponente": {
        "mercancias":                                        "910422",
        "servicios":                                         "910423",
        "agropecuarios":                                     "910425",
        "energeticos y tarifas autorizadas por el gobierno": "910426",
    },
}
```

**Mapeo tipo → (índice → indicador) — mensuales:**

```python
_INDICADORES_MENSUALES: dict[str, dict[str, str]] = {
    "inpc": {
        "INPC": "910392",
    },
    "inflacion componente": {
        "subyacente":    "910393",
        "no subyacente": "910396",
    },
    "inflacion subcomponente": {
        "mercancias":                                        "910394",
        "servicios":                                         "910395",
        "agropecuarios":                                     "910397",
        "energeticos y tarifas autorizadas por el gobierno": "910398",
    },
}
```

Los dicts son privados. `corrida.py` detecta si hay validación vía `tipo in _INDICADORES_QUINCENALES`.
La clave interior es el nombre exacto de la categoría en la canasta.

`obtener()` itera sobre los indicadores del dict correspondiente, llama a `_fetch()` por cada uno y
devuelve `dict[str, dict[PeriodoQuincenal | PeriodoMensual, float | None]]` keyed por nombre de índice.

**URL de la API:**

``` text
https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR/{indicador}/es/00/false/BIE-BISE/2.0/{token}?type=json
```

Una sola llamada devuelve todo el histórico disponible (~917 observaciones para INPC quincenal).
El token no es validado por la API (cualquier string funciona).

**Formato de respuesta:**

```json
{
  "Series": [{
    "OBSERVATIONS": [
      {"TIME_PERIOD": "2026/03/01", "OBS_VALUE": "145.44600000000000000000", "OBS_STATUS": "3"},
      ...
    ]
  }]
}
```

Las observaciones vienen en orden cronológico descendente. `OBS_STATUS` siempre es `"3"` — no se filtra.

**Mapeo `TIME_PERIOD` → periodo:**

`_fetch()` detecta el formato de `TIME_PERIOD` por conteo de partes (`split("/")`):

| Formato | Partes | Tipo | Construcción |
| ------- | ------ | ---- | ------------ |
| `"YYYY/MM/QQ"` | 3 | quincenal | `PeriodoQuincenal(YYYY, MM, QQ)` |
| `"YYYY/MM"` | 2 | mensual | `PeriodoMensual(YYYY, MM)` |

Verificado: `"2018/07/02"` (quincenal) devuelve `100.0` (base canasta 2018). `"2026/03"` (mensual, 910392) devuelve `145.544`.

**`OBS_VALUE`:** string con decimales (`"145.44600000000000000000"`). Se convierte con `float()`.
Si es `null` (JSON `None`), se devuelve `None` para ese periodo sin interrumpir el parseo.

**Cache de clase:** el resultado de la primera llamada se guarda en `_cache` (variable de clase),
keyed por `indicador_id`. Las llamadas subsecuentes — incluso desde instancias distintas —
no hacen requests adicionales. Para limpiar en tests: `FuenteValidacionApi._cache.clear()`.

**Errores:**

| Situación | Excepción |
| --- | --- |
| `tipo not in INDICADORES_INEGI` | `ErrorConfiguracion` (en `__init__`) |
| Red, timeout (`requests.exceptions.RequestException`) | `FuenteNoDisponible` |
| HTTP 4xx / 5xx (`raise_for_status`) | `FuenteNoDisponible` |
| Respuesta no es JSON válido | `RespuestaInvalida` |
| Sin clave `Series` / `OBSERVATIONS`, o `Series` vacío | `RespuestaInvalida` |
| `TIME_PERIOD` o `OBS_VALUE` con formato inesperado | `RespuestaInvalida` |

`timeout=10` segundos en cada request.

**`obtener_variaciones(periodos, tipo_variacion)`:**

```python
def obtener_variaciones(
    self,
    periodos: list[PeriodoMensual] | list[PeriodoQuincenal],
    tipo_variacion: Literal["periodica", "interanual", "acumulada_anual"],
) -> dict[str, dict[PeriodoMensual | PeriodoQuincenal, float | None]]:
```

Obtiene series de variación mensual o quincenal publicadas por INEGI. Detecta automáticamente
si los periodos son mensuales o quincenales y usa los dicts correspondientes (§8.7 o §8.8).
Reutiliza el mismo cache de clase que `obtener()`.

| `tipo_variacion` | Dict mensual (§8.7) | Dict quincenal (§8.8) |
| --- | --- | --- |
| `"periodica"` | `_VARIACIONES_PERIODICA_MENSUAL` | `_VARIACIONES_PERIODICA_QUINCENAL` |
| `"interanual"` | `_VARIACIONES_INTERANUAL_MENSUAL` | `_VARIACIONES_INTERANUAL_QUINCENAL` |
| `"acumulada_anual"` | `_VARIACIONES_ACUMULADA_ANUAL_MENSUAL` | `_VARIACIONES_ACUMULADA_ANUAL_QUINCENAL` |

**Detección `fuera_de_rango_inegi`:** solo incluye en el dict retornado los periodos
`p >= min(historico)`. Los periodos anteriores al primer dato publicado por INEGI quedan
ausentes del dict — la ausencia de clave es la señal que usa `validar_variaciones` para
asignar `"fuera_de_rango_inegi"`. Si el histórico está vacío, retorna dict vacío.

Lanza `ErrorConfiguracion` si `tipo_variacion` no está en los tres valores válidos.
Mismos errores que `obtener()`.

---

### 8.7 Indicadores de variación mensual (API del INEGI)

Series de variación publicadas por INEGI en la misma API BIE-BISE. Se usan para validar
`variacion_periodica`, `variacion_acumulada_anual` calculadas internamente.

**Unidades:** porcentaje (p.ej. `0.86` = 0.86%). Nuestras variaciones están en decimal → multiplicar por 100 para comparar.

**Tolerancia:** 0.009 pp (porcentaje) en diferencia absoluta — igual para canastas 2018 y 2024.

**Exclusión de periodos:** no comparar cuando el periodo base del cálculo tenga `estado_calculo = "semi_ok"`. Esto excluye automáticamente Ago 2018 (periódica) y Jul 2019 (interanual), cuya base es Jul 2018 (solo 1 quincena disponible). Verificación empírica confirmó que sin esta exclusión el error máximo supera 0.3 pp; con exclusión, max ~0.006 pp.

**Verificación empírica (2026-04-24):** 21 combinaciones (7 índices × 3 tipos), 80–92 periodos cada una. Todos dentro de tolerancia tras exclusión. Errores típicos < 0.006 pp.

**Mapeos — inflación periódica mensual (`variacion_periodica(..., "mensual")`):**

```python
_VARIACIONES_PERIODICA_MENSUAL: dict[str, dict[str, str]] = {
    "inpc": {
        "INPC": "910399",
    },
    "inflacion componente": {
        "subyacente":    "910400",
        "no subyacente": "910403",
    },
    "inflacion subcomponente": {
        "mercancias":                                        "910401",
        "servicios":                                         "910402",
        "agropecuarios":                                     "910404",
        "energeticos y tarifas autorizadas por el gobierno": "910405",
    },
}
```

**Mapeos — inflación interanual (`variacion_periodica(..., "anual")`):**

```python
_VARIACIONES_INTERANUAL_MENSUAL: dict[str, dict[str, str]] = {
    "inpc": {
        "INPC": "910406",
    },
    "inflacion componente": {
        "subyacente":    "910407",
        "no subyacente": "910410",
    },
    "inflacion subcomponente": {
        "mercancias":                                        "910408",
        "servicios":                                         "910409",
        "agropecuarios":                                     "910411",
        "energeticos y tarifas autorizadas por el gobierno": "910412",
    },
}
```

**Mapeos — inflación acumulada anual (`variacion_acumulada_anual(...)`):**

```python
_VARIACIONES_ACUMULADA_ANUAL_MENSUAL: dict[str, dict[str, str]] = {
    "inpc": {
        "INPC": "910413",
    },
    "inflacion componente": {
        "subyacente":    "910414",
        "no subyacente": "910417",
    },
    "inflacion subcomponente": {
        "mercancias":                                        "910415",
        "servicios":                                         "910416",
        "agropecuarios":                                     "910418",
        "energeticos y tarifas autorizadas por el gobierno": "910419",
    },
}
```

### 8.8 Indicadores de variación quincenal (API del INEGI)

Series de variación quincenal publicadas por INEGI en la misma API BIE-BISE. Se usan para validar
`variacion_periodica`, `variacion_acumulada_anual` calculadas sobre datos quincenales.

**Unidades:** porcentaje (igual que §8.7). Misma tolerancia: 0.009 pp.

**Cobertura:**

- Periódica quincenal: datos históricos desde ~1988 (INPC), ~1995 (subyacente), 2011 (subcomponentes).
- Interanual quincenal: solo desde `1Q Ago 2024` — periodos anteriores → `fuera_de_rango_inegi`.
- Acumulada anual quincenal: solo desde `1Q Ago 2024` — periodos anteriores → `fuera_de_rango_inegi`.

**Verificación empírica (2026-04-25):**

| tipo | comparados | fuera_rango | max_error |
| --- | --- | --- | --- |
| periódica | 184 | 0 | 0.00566 pp |
| interanual | 39 | 121 | 0.00512 pp |
| acumulada | 39 | 134 | 0.00512 pp |

Todos dentro de 0.009 pp. `periodos_semiok` vacío en quincenal — no hay exclusiones.

**Mapeos — inflación periódica quincenal (`variacion_periodica(..., "quincenal")`):**

```python
_VARIACIONES_PERIODICA_QUINCENAL: dict[str, dict[str, str]] = {
    "inpc": {
        "INPC": "910427",
    },
    "inflacion componente": {
        "subyacente":    "910428",
        "no subyacente": "910431",
    },
    "inflacion subcomponente": {
        "mercancias":                                        "910429",
        "servicios":                                         "910430",
        "agropecuarios":                                     "910432",
        "energeticos y tarifas autorizadas por el gobierno": "910433",
    },
}
```

**Mapeos — inflación interanual quincenal (`variacion_periodica(..., "anual")`):**

```python
_VARIACIONES_INTERANUAL_QUINCENAL: dict[str, dict[str, str]] = {
    "inpc": {
        "INPC": "910438",
    },
    "inflacion componente": {
        "subyacente":    "910439",
        "no subyacente": "910442",
    },
    "inflacion subcomponente": {
        "mercancias":                                        "910440",
        "servicios":                                         "910441",
        "agropecuarios":                                     "910443",
        "energeticos y tarifas autorizadas por el gobierno": "910444",
    },
}
```

**Mapeos — inflación acumulada anual quincenal (`variacion_acumulada_anual(...)`):**

```python
_VARIACIONES_ACUMULADA_ANUAL_QUINCENAL: dict[str, dict[str, str]] = {
    "inpc": {
        "INPC": "910445",
    },
    "inflacion componente": {
        "subyacente":    "910446",
        "no subyacente": "910449",
    },
    "inflacion subcomponente": {
        "mercancias":                                        "910447",
        "servicios":                                         "910448",
        "agropecuarios":                                     "910450",
        "energeticos y tarifas autorizadas por el gobierno": "910451",
    },
}
```

---

## 9. Estrategia de errores

### 9.1 Jerarquía de excepciones

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

### 9.2 Propagación

Los errores se lanzan lo más cerca posible de donde ocurren y se capturan
en el caso de uso, que decide qué hacer con ellos. Las capas intermedias
no capturan ni envuelven — dejan pasar.

| Error              | Dónde se lanza                     | Quién lo captura | Efecto                     |
| ------------------ | ---------------------------------- | ---------------- | -------------------------- |
| `ErrorImportacion` | adaptador (infraestructura)        | caso de uso      | falla la corrida           |
| `ErrorDominio`     | constructor del contrato (dominio) | caso de uso      | falla la corrida           |
| `ErrorCalculo`     | dominio (cálculo)                  | caso de uso      | falla la corrida           |
| `ErrorValidacion`  | adaptador (infraestructura)        | caso de uso      | validación `no_disponible` |

### 9.3 Traducción en adaptadores

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

## 10. Estrategia de testing

### 10.1 Tipos de test

| Componente            | Tipo        | Nota                                                                            |
| --------------------- | ----------- | ------------------------------------------------------------------------------- |
| Contratos del dominio | Unit        |                                                                                 |
| `Periodo`             | Unit        | Explícito — parseo, orden, hash, `to_timestamp()`                               |
| Lógica de cálculo     | Unit        | `LaspeyresDirecto` y `LaspeyresEncadenado`                                      |
| `correspondencia.py`  | Unit        |                                                                                 |
| Adaptadores CSV       | Integration | Archivos reales                                                                 |
| Casos de uso          | Integration | Archivos reales                                                                 |
| `api/corrida.py`      | Integration | Archivos reales                                                                 |
| API INEGI             | Integration | Mockeada — ver §10.3                                                            |
| `interfaces/cli.py`   | ——————————— | Fuera de v1                                                                     |

---

### 10.2 Fixtures

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

**Test de humo** — usa los archivos reales de `data/inputs/` para verificar
que el sistema procesa un archivo INEGI real sin errores. No verifica el resultado
numérico en detalle.

---

### 10.3 Mock de la API del INEGI

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

### 10.4 Criterio de suficiencia para v1

El suite es suficiente cuando cubre los siguientes comportamientos:

- Corrida completa exitosa (canasta 2018, series completas)
- Corrida con faltantes en series → periodos en `null`
- Corrida con faltante en ponderador → falla inmediata
- Corrida con API no disponible → continúa, validación `no_disponible`
- Corrida con respuesta inválida de API → continúa, validación `no_disponible`
- Corrida encadenada (canasta 2024) con `resultado_referencia` → `f_h` exacto, error_absoluto ≤ 0.0009
- Corrida encadenada sin `resultado_referencia` → fallback media ponderada, error sistemático ~0.72
- Series con NaN → imputación bfill/ffill, trazabilidad en `DiagnosticoFaltantes`
- `combinar` de dos corridas → serie continua sin duplicados, UUID nuevo
- Invariantes de todos los contratos del dominio
- `Periodo`: parseo, orden, hash, `to_timestamp()`
- Las 4 variantes de archivo de series (con/sin metadatos × horizontal/vertical)
- Correspondencia: match exitoso; match fallido por cobertura insuficiente
- Test de humo con datos reales (canasta 2018)

---

## 11. Decisiones y razones

### 11.1 `SerieNormalizada` en formato ancho

**Decisión:** DataFrame con `generico_limpio` como índice y objetos `Periodo` como columnas.

**Alternativa considerada:** formato largo — columnas `generico_limpio`, `periodo`, `indice`.

**Razón:** el cálculo Laspeyres sobre todos los periodos es una multiplicación matricial directa entre el vector de ponderadores y la matriz de índices. El formato ancho lo hace eficiente y legible. El formato largo requeriría un pivot antes de cada cálculo.

---

### 11.2 `generico_original` como diccionario

**Decisión:** `generico_original` vive en `serie.mapeo` como `dict[str, str]` (`generico_limpio → generico_original`), fuera del DataFrame.

**Alternativa considerada:** columna opcional en el DataFrame de `SerieNormalizada`.

**Razón:** `generico_original` es dato de trazabilidad, no de cálculo. Mantenerlo fuera del DataFrame evita que aparezca en operaciones sobre la matriz de índices y deja claro su propósito.

---

### 11.3 Correspondencia genérico↔genérico por normalización exacta

**Decisión:** matching exacto después de normalizar — quitar tildes + lowercase (`unicodedata`). `rapidfuzz` removido del stack.

**Alternativa considerada:** matching fuzzy con `rapidfuzz`.

**Razón:** la divergencia entre nombres de series y canasta es sistemática y determinista — los ponderadores fueron extraídos sin tildes mientras las series las conservan. Después de normalizar ambos lados, los 299 genéricos de la canasta 2018 coinciden exactamente. El fuzzy resolvía un problema que la normalización resuelve de forma predecible y sin riesgo de falsos positivos entre genéricos con nombres parecidos.

---

### 11.4 pandas en el dominio

**Decisión:** los contratos del dominio usan DataFrames de pandas directamente.

**Alternativa considerada:** dominio sin dependencias externas, pandas solo en infraestructura.

**Razón:** el proyecto es notebook-first. Aislar pandas del dominio agregaría una capa de conversión sin beneficio real — el dominio siempre va a operar sobre estructuras tabulares. El hexágono aísla formato y fuente de datos, no librerías de procesamiento.

---

### 11.5 `ponderador` y `encadenamiento` como `str`

**Decisión:** se almacenan como `str` en `CanastaCanonica`. La conversión a `float` ocurre solo en el momento del cálculo.

**Alternativa considerada:** almacenar directamente como `float`.

**Razón:** los archivos fuente tienen precisión decimal que puede perderse en la conversión binaria a `float`. Almacenar como `str` preserva el valor exacto extraído del CSV oficial. La conversión a `float` en el cálculo no acumula error adicional porque se aplica una sola vez por operación.

---

### 11.6 `Periodo` como tipo propio

**Decisión:** value object `Periodo` con atributos `año`, `mes`, `quincena`.

**Alternativa considerada:** `str` con formato `"1Q Ene 2020"` o `pd.Timestamp`.

**Razón:** una quincena no tiene representación natural en Python ni en pandas. `str` no permite sorting natural ni uso como clave hashable confiable. `pd.Timestamp` requiere una convención arbitraria para el día (día 1 o día 16) que no es un dato real. `Periodo` encapsula esa convención en `to_timestamp()` y expone sorting, hash e igualdad de forma explícita.

---

### 11.7 Categorías de clasificación version-específicas

**Decisión:** las columnas de clasificación en `CanastaCanonica` almacenan texto tal como viene del CSV intermedio. No se usan `pd.Categorical`. El mapeo cross-versión de nombres no vive en `CanastaCanonica` sino en `RENOMBRES_INDICES` en `correspondencia_canastas.py` — se aplica al combinar resultados, no al leer la canasta (ver §11.23).

**Columnas con categorías en canasta 2018** (`encadenamiento` y `canasta consumo minimo` están vacías para esta versión):

| Columna | N categorías | Valores |
| ------- | -----------: | ------- |
| `COG` | 8 | `alimentos, bebidas y tabaco` · `educacion y esparcimiento` · `muebles, aparatos y accesorios domesticos` · `otros servicios` · `ropa, calzado y accesorios` · `salud y cuidado personal` · `transporte` · `vivienda` |
| `CCIF division` | 12 | `alimentos y bebidas no alcoholicas` · `bebidas alcoholicas y tabaco` · `bienes y servicios diversos` · `comunicaciones` · `educacion` · `muebles, articulos para el hogar y para su conservacion` · `prendas de vestir y calzado` · `recreacion y cultura` · `restaurantes y hoteles` · `salud` · `transporte` · `vivienda, agua, electricidad, gas y otros combustibles` |
| `CCIF grupo` | 44 | (ver CSV `ponderadores_2018.csv`) |
| `CCIF clase` | 87 | (ver CSV `ponderadores_2018.csv`) |
| `inflacion componente` | 2 | `no subyacente` · `subyacente` |
| `inflacion subcomponente` | 4 | `agropecuarios` · `energeticos y tarifas autorizadas por el gobierno` · `mercancias` · `servicios` |
| `inflacion agrupacion` | 9 | `alimentos, bebidas y tabaco` · `educacion (colegiaturas)` · `energeticos` · `frutas y verduras` · `mercancias no alimenticias` · `otros servicios` · `pecuarios` · `tarifas autorizadas por el gobierno` · `vivienda` |
| `SCIAN sector` | 18 | (ver CSV `ponderadores_2018.csv`) |
| `SCIAN rama` | 91 | (ver CSV `ponderadores_2018.csv`) |
| `durabilidad` | 4 | `duradero` · `no duradero` · `semiduradero` · `servicio` |
| `canasta basica` | 1 | `X` (indica pertenencia; ausente si no aplica) |

**Nota cross-versión:** entre versiones hay cambios de nombre de categorías (ej. `"comunicaciones"` en 2018 → `"informacion y comunicacion"` en 2024). `combinar` normaliza automáticamente los nombres para `CCIF division`, `SCIAN rama` y, de forma preliminar, para renombres 1:1 de `CCIF grupo` y `CCIF clase` al concatenar resultados de distintas canastas. `SCIAN sector` no tiene renombres 1:1 confirmados. Los splits, fusiones, categorías nuevas y categorías eliminadas no se mapean. Un join directo sobre el df sin pasar por `combinar` seguirá produciendo categorías no coincidentes.

---

### 11.8 Tolerancia numérica por versión

**Decisión:** la tolerancia para marcar `estado_validacion = diferencia_detectada` es fija por versión:

| Versión | Tolerancia (`error_absoluto`) | Nota                                      |
| ------- | ----------------------------- | ----------------------------------------- |
| 2010    | `<= 0.0005`                   | provisional — sin validación empírica aún |
| 2013    | `<= 0.0005`                   | provisional — sin validación empírica aún |
| 2018    | `<= 0.0005`                   | basada en experiencia previa              |
| 2024    | `<= 0.005`                    | mayor variación por encadenamiento        |

**Razón:** las diferencias observadas entre el INPC replicado y el publicado por el INEGI varían por versión — la canasta 2024 usa Laspeyres encadenado con normalización, lo que introduce mayor variación numérica acumulada. Una tolerancia única global sería demasiado estricta para 2024 o demasiado laxa para 2018. Las tolerancias de 2010 y 2013 son provisionales y deben revisarse cuando se implemente y pruebe con datos reales.

---

### 11.9 Reglas de `estado_corrida`

**Decisión:** `estado_corrida` en `ResumenValidacion` se determina a partir de `estado_calculo` por periodo:

| Condición                                                    | `estado_corrida` |
| ------------------------------------------------------------ | ---------------- |
| Todos los periodos con `estado_calculo = 'ok'`               | `'ok'`           |
| Algunos periodos con `estado_calculo = 'null_por_faltantes'` | `'ok_parcial'`   |
| Todos los periodos con `estado_calculo != 'ok'`              | `'fallida'`      |

---

### 11.10 Detección de `null_por_faltantes`

**Decisión:** la detección de valores faltantes en la serie por periodo es responsabilidad del calculador (`LaspeyresDirecto`, `LaspeyresEncadenado`), no de `validar_inpc.py`.

**Razón:** el calculador es quien conoce si el cálculo fue íntegro. Si la serie tiene NaN para un genérico en un periodo, ese periodo se marca como `estado_calculo = 'null_por_faltantes'` e `inpc_replicado = NaN`. `validar_inpc.py` solo valida — no recalcula ni inspecciona la serie.

---

### 11.11 Firma de `validar_inpc.py`

**Decisión:** el dominio no recibe el puerto `FuenteValidacion` — recibe el dict ya obtenido por `ejecutar_corrida.py`. Si la fuente no estaba disponible, el caso de uso pasa `{}`. Ver contrato completo en §5.11.

**Estructura de `inegi`:** `dict[str, dict[Periodo, float | None]]` — clave exterior = nombre del índice (ej. `"INPC"` para `inpc`, `"subyacente"` para `inflacion componente`). Esto unifica el acceso para índice único y para subíndices sin condicionales adicionales en `validar()`: siempre `inegi.get(indice, {}).get(periodo)`.

---

### 11.12 `id_corrida` en `ResultadoCalculo`

**Decisión:** `ejecutar_corrida.py` genera el UUID y lo pasa como parámetro `id_corrida: str` a `calcular()`. La firma de `CalculadorBase.calcular()` se actualiza para incluirlo.

**Razón:** el calculador no debe generar IDs — esa responsabilidad pertenece al caso de uso. Pasar el `id_corrida` como parámetro mantiene el calculador como función pura.

---

### 11.13 Loop de subíndices en `EjecutarCorrida`, no en el calculador

> **Decisión revertida en v1.2.0 — ver §11.18.**

**Decisión original (v1.1.0):** el loop que itera sobre categorías de un clasificador, re-normaliza ponderadores y combina resultados vive en `ejecutar_corrida.py`, no en `LaspeyresDirecto`.

**Razón original:** el loop es orquestación, no cálculo. El trigger para extraerlo sería un segundo caso de uso que lo necesite.

**Por qué se revirtió:** el trigger llegó con v1.2.0 — `LaspeyresEncadenado` necesita el mismo patrón. El dispatch se movió al interior de cada `CalculadorBase` y el split se delegó al helper `grupos_por_clasificacion` en `subindices.py`. Ver §11.18.

---

### 11.14 Schema condicional en `ReporteDetalladoValidacion`

**Decisión:** el DataFrame interno de `ReporteDetalladoValidacion` tiene esquemas distintos según si el `tipo` tiene validación INEGI disponible. Con validación incluye `indice_inegi`, `error_absoluto`, `error_relativo` y `estado_validacion`; sin validación esas columnas están ausentes.

**Alternativa considerada:** schema único siempre con todas las columnas, rellenando con `NaN` cuando el tipo no tiene validación INEGI.

**Razón:** un schema único con NaN genera ambigüedad — el usuario no puede distinguir si `indice_inegi = NaN` significa "no hay dato para ese periodo" o "este tipo nunca tendrá dato INEGI". El schema condicional hace explícita la ausencia de columnas como propiedad estructural del tipo, no como dato faltante.

---

### 11.15 `TIPOS_CON_VALIDACION` en el dominio, no en infraestructura

**Decisión:** `TIPOS_CON_VALIDACION` vive en `dominio/tipos.py`, aunque `INDICADORES_INEGI` (que mapea tipo → indicador concreto) vive en `infraestructura/inegi/fuente_validacion_api.py`.

**Alternativa considerada:** derivar `TIPOS_CON_VALIDACION` dinámicamente desde `INDICADORES_INEGI` en infraestructura.

**Razón:** qué tipos admiten comparación contra una fuente oficial es una propiedad del dominio — afecta el esquema de `ReporteDetalladoValidacion` y la lógica de `validar_inpc.py`, ambos en el dominio. Que el indicador concreto sea `910420` es un detalle del adaptador INEGI. Si se agrega un adaptador distinto (ej. CSV con datos oficiales), `TIPOS_CON_VALIDACION` no debería cambiar.

---

### 11.16 Cache de clase en `FuenteValidacionApi`

**Decisión:** `_cache` en `FuenteValidacionApi` es un atributo de clase (`dict[str, dict[Periodo, float | None]]`), no de instancia.

**Alternativa considerada:** cache de instancia — cada objeto `FuenteValidacionApi` mantiene su propio cache.

**Razón:** la API del INEGI devuelve el histórico completo en una sola llamada — no hay paginación por rango de fechas. Un cache de instancia no evitaría llamadas redundantes entre corridas distintas que instancian objetos separados. El cache de clase garantiza que el histórico de un indicador se descarga una sola vez por sesión, sin importar cuántas instancias o corridas se ejecuten. En tests se limpia con `FuenteValidacionApi._cache.clear()`.

---

### 11.17 UTF-8 como primer encoding en `LectorSeriesCsv`

**Decisión:** el orden de encodings a intentar en `LectorSeriesCsv._leer_csv` es `["utf-8", "cp1252", "latin-1"]`.

**Alternativa considerada:** mantener solo `["cp1252", "latin-1"]` — suficiente para archivos reales del INEGI.

**Razón:** los archivos del demo (`demo/series_demo.csv`) se generan en UTF-8. Un archivo UTF-8 con caracteres no-ASCII leído con cp1252 produce texto corrupto sin lanzar `UnicodeDecodeError`, por lo que el fallback nunca se activaría. Agregar UTF-8 primero es seguro: los archivos cp1252 del INEGI contienen bytes no-ASCII que forman secuencias UTF-8 inválidas, lo que sí lanza `UnicodeDecodeError` y activa el fallback a cp1252. El comportamiento con archivos reales no cambia.

---

### 11.18 Dispatch interno en `CalculadorBase` con helper `grupos_por_clasificacion`

**Decisión:** el dispatch entre INPC y subíndices vive dentro de cada implementación de `CalculadorBase` (no en `EjecutarCorrida`). El split por categoría lo hace el helper `grupos_por_clasificacion(canasta, serie, tipo)` en `dominio/calculo/subindices.py` — un generador que hace un solo `groupby` y entrega pares `(categoria, df_canasta, df_serie)` crudos. Cada calculador aplica su propia fórmula sobre esos pares. Los ponderadores no se renormalizan: la fórmula usa $\sum w_j$ como denominador, válido tanto para la canasta completa ($\sum w_j = 100$) como para subgrupos ($\sum w_j < 100$). La firma de `CalculadorBase.calcular()` pierde el parámetro `indice` — se deriva internamente.

**Alternativas consideradas:**

1. Mantener el loop en `EjecutarCorrida` (decisión original, §11.13).
2. Función orquestadora `calcular_por_clasificacion(tipo, canasta, serie, calculador,
   id_corrida)` llamada por `EjecutarCorrida` (decisión intermedia, reemplazada por esta).
3. `groupby` vectorizado completo dentro de cada calculador:

   ```python
   resultado = serie.df.multiply(ponds, axis=0).groupby(cats).sum()
               .divide(ponds.groupby(cats).sum(), axis=0)
   ```

**Razón para rechazar la alternativa 2:** mantiene el dispatch fuera del calculador — `EjecutarCorrida` aún necesita conocer la diferencia entre INPC y subíndices, y `calcular_por_clasificacion` recibe el calculador como argumento externo. El dispatch pertenece al calculador, no al caso de uso.

**Razón para rechazar el groupby completo (alternativa 3):** acopla la lógica de agregación a la fórmula Laspeyres dentro del calculador. `LaspeyresEncadenado` tendría que duplicar el groupby con su propia fórmula de encadenamiento, rompiendo el patrón donde `grupos_por_clasificacion` es el único punto de split.

**Razón para esta decisión:** `EjecutarCorrida` queda con una sola llamada `calculador.calcular(canasta, serie, id_corrida, tipo)` sin conocer el tipo de cálculo. `grupos_por_clasificacion` hace el split una vez en O(n) y es reutilizable por `LaspeyresEncadenado`. La renormalización desaparece — el denominador correcto es siempre $\sum w_j$. El invariante $\sum w_j = 100$ de `CanastaCanonica` se verifica antes del split y no se propaga a los subgrupos (DataFrames crudos).

### 11.19 Vectorización del loop interno de `validar_inpc`

**Decisión:** reemplazar los loops Python escalares de `validar_inpc.validar()` con operaciones vectorizadas de pandas.

**Por qué:** profiling con SCIAN rama (91 categorías, 158 periodos, canasta 2018) mostró que `validar` consume el 96% del tiempo de la corrida (10.1s de 10.5s totales). Tres causas:

1. 3× `.loc[(periodo, indice), col]` por iteración del loop `indices × periodos` → 39 592 llamadas a `__getitem__` con tupla sobre MultiIndex.
2. `serie_col[ponderadores.index]` + 2× `notna()` por iteración → 26 390 llamadas escalares.
3. Loop `for generico × for periodo` en el bloque de diagnóstico → 47 242 accesos escalares `pd.isna()`.

**Tres cambios en la implementación:**

1. `res_lookup = resultado.df[cols].to_dict("index")` pre-computado antes del loop → acceso O(1) por par `(periodo, indice)` en lugar de `.loc[(tupla)]`.
2. `notna_df = ~serie.df.isna()` pre-computado una vez; dentro del loop por índice: `notna_df.loc[idx_grupo].sum()` y `notna_df.loc[idx_grupo].multiply(ponderadores, axis=0).sum()` calculan cobertura y ponderador cubierto para **todos los periodos a la vez** → 91 operaciones matriciales en lugar de 13 195 escalares.
3. Diagnóstico: `serie.df.isna().stack()` seguido de filtro booleano reemplaza el doble loop Python → 1 operación vectorizada en lugar de 47 242 accesos escalares.

**Comportamiento idéntico.** Estimado post-optimización: ~0.75s con datos reales (SCIAN rama, 91 categorías, 158 periodos).

**Alternativa descartada:** mantener los loops Python y compensar con `numba` o `cython`. Descartada porque la causa raíz es el overhead de dispatch de pandas por acceso escalar, no el costo de la operación aritmética — la vectorización lo elimina directamente sin dependencias adicionales.

---

### 11.20 Implementación de `LaspeyresEncadenado` — derivación de `f_h`

#### Primer enfoque (descartado): media ponderada con ponderadores nuevos

El diseño original computaba $f_h$ como media ponderada de los $f_k$ individuales usando los ponderadores de la canasta nueva (2024):

$$f_h^{\text{nuevo}} = \frac{\sum_{k \in h} w_k^{(2024)} \cdot f_k}{\sum_{k \in h} w_k^{(2024)}}$$

**Por qué falló con datos reales:** el INEGI calcula $f_h$ con los 299 ponderadores de la canasta 2018, no con los 292 de la canasta 2024. Las dos estructuras son diferentes tanto en número de genéricos como en los pesos relativos. Al validar contra los valores publicados, el error resultante fue:

- `error_absoluto` ≈ 0.716–0.737 puntos de índice (creciente conforme sube el INPC)
- `error_relativo` ≈ 0.53% sistemático en todos los periodos post-traslape
- Estado de validación: `diferencia_detectada` en todos los periodos — no pasa ninguno

El error es proporcional al nivel del INPC porque $f_h^{\text{nuevo}} \neq f_h^{\text{INEGI}}$ por una diferencia fija de ponderación; a medida que el INPC crece, el error absoluto crece con él. Una tolerancia absoluta (como la declarada en §6.1) no puede cubrir este error indefinidamente.

#### Enfoque final: $f_h$ desde el resultado de la versión anterior

**Decisión:** `f_h` se obtiene del resultado de la corrida 2018 en el periodo de traslape:

$$f_h^{\text{INEGI}} = \frac{I_h^{(2018)}[t_{\text{traslape}}]}{100}$$

donde $I_h^{(2018)}[t_{\text{traslape}}]$ es el índice calculado con LaspeyresDirecto sobre la canasta 2018 (299 genéricos, ponderadores viejos) en el periodo de traslape. Este valor es algebraicamente idéntico al $f_h$ que usa el INEGI.

**Por qué funciona:** en el traslape $I_k^{\text{pub}} = f_k \times 100$, por lo que:

$$I_h^{(2018)}[t_{\text{traslape}}] = \frac{\sum_{k} w_k^{(2018)} \cdot f_k \cdot 100}{\sum_k w_k^{(2018)}} = 100 \cdot f_h^{\text{INEGI}}$$

**Implementación:** `LaspeyresEncadenado` recibe `f_h_por_indice: dict[str, float] | None` en el constructor. `EjecutarCorrida.ejecutar()` recibe `resultado_referencia: ResultadoCalculo | None` y extrae el dict con la función `_f_h_desde_referencia(resultado_ref, traslape)`. `para_canasta(canasta, f_h_por_indice)` pasa el dict al constructor.

**Flujo de uso:**

```python
corrida_2018 = Corrida(...).ejecutar(canasta_2018, series_2018, version=2018)
corrida_2024 = Corrida(...).ejecutar(
    canasta_2024, series_2024, version=2024,
    resultado_referencia=corrida_2018.resultado,
)
```

**Fallback:** si `resultado_referencia` es `None` o el índice no está en el dict (p. ej. subíndices con clasificadores que no existen en la corrida de referencia), se usa la media ponderada con ponderadores nuevos. Este fallback introduce el error sistemático descrito arriba y es aceptable solo cuando no se dispone del resultado 2018.

**No-aditividad:** cada agregado $h$ tiene su propio $f_h$. Los subíndices encadenados no suman al INPC encadenado post-traslape. Propiedad esperada y documentada por el INEGI; el proyecto replica cada índice independientemente.

---

### 11.21 Imputación de faltantes en series

Las series del INEGI ocasionalmente contienen `NaN` para un genérico en un periodo específico, incluso cuando ese genérico tiene datos en periodos adyacentes. En datos reales (canastas 2018 y 2024) se observa exactamente un caso por versión.

**Algoritmo:** para cada `NaN` en `(generico, periodo)`, buscar el periodo disponible más próximo en la serie ya filtrada a `RANGOS_VALIDOS[version]`:

1. Buscar hacia adelante: `t+1, t+2, ...` hasta encontrar valor no NaN.
2. Si no hay ninguno hacia adelante, buscar hacia atrás: `t-1, t-2, ...`

Implementado como `df.bfill(axis=1).ffill(axis=1)` sobre el DataFrame de la serie (columnas = periodos ordenados ascendente). `bfill` sobre `axis=1` rellena con el siguiente periodo disponible; `ffill` cubre los NaN que quedaron al final de la serie.

**Implementación:** función privada `_rellenar_faltantes(serie: SerieNormalizada) -> tuple[SerieNormalizada, dict[tuple[str, Periodo], Periodo]]` en `aplicacion/casos_uso/ejecutar_corrida.py`. Se ejecuta en el paso 6.5 del pipeline, después de `alinear_genericos` y antes del cálculo. El dict `(generico, periodo) → Periodo_fuente` se pasa a `validar_inpc.py` para registrar cada par en `DiagnosticoFaltantes` con `tipo_faltante = 'indice_imputado'` y `detalle = "imputado desde <Periodo_fuente>"`.

**Por qué en la capa de aplicación y no en el dominio:** es una decisión de preparación de insumos antes del cálculo, no lógica del cálculo en sí. El calculador recibe una serie sin NaN y no sabe que hubo imputación.

**Limitación:** el valor fuente (el periodo desde el que se tomó el dato) solo queda en `detalle` del diagnóstico como texto. No es un campo estructurado — consultas programáticas sobre qué valor se usó requieren parsear `detalle`.

---

### 11.22 `combinar` — función de combinación histórica de `ResultadoCalculo`

**Problema:** cada corrida cubre un solo rango de canasta. Para visualizar o analizar la serie histórica continua del INPC (ej. 2010–hoy) el usuario necesita concatenar resultados de múltiples corridas.

**Decisión:** función suelta `combinar(resultados: list[ResultadoCalculo]) -> ResultadoCalculo` en `dominio/modelos/resultado.py`. Exportada desde `replica_inpc/__init__.py`.

**Por qué función suelta y no método de `Corrida`:** no requiere puertos ni infraestructura — es lógica pura sobre modelos de dominio. Vive en el dominio.

**Por qué no `ResultadoCorrida.combinar`:** `ResumenValidacion`, `ReporteDetalladoValidacion` y `DiagnosticoFaltantes` son por corrida individual y no tienen semántica clara al combinarse. Solo `ResultadoCalculo` (la serie de valores) tiene sentido continuo.

**Algoritmo:**

1. Ordenar la lista cronológicamente por `min(index.get_level_values("periodo"))` de cada resultado.
2. Para cada par `(anterior, posterior)`: excluir del `anterior` los periodos que ya están en `posterior` — el traslape queda en el posterior.
3. `pd.concat` de todos los dfs resultantes.
4. `id_corrida` = UUID nuevo (el resultado combinado no pertenece a ninguna corrida individual).

**Invariantes que se preservan:** el df combinado cumple todos los invariantes de `ResultadoCalculo` — versiones válidas por fila, sin índices duplicados, consistencia ok/fallo. Un df con filas de versión 2018 y 2024 es válido porque `version` es columna por fila.

**`version_canonica`:** `combinar` acepta `version_canonica: VersionCanasta | None = None`. Si `None`, usa la versión más reciente de los resultados pasados. Si se especifica, renombra los índices de todas las demás versiones hacia los nombres de esa versión. Ver §11.23 para la tabla de correspondencia y el algoritmo.

---

### 11.23 `RENOMBRES_INDICES` y normalización cross-versión en `combinar`

**Problema:** al combinar `ResultadoCalculo` de canastas distintas, el nivel `indice` del MultiIndex contiene el nombre de la categoría tal como lo generó cada corrida. Para `CCIF division`, los nombres cambiaron entre 2018 y 2024 (ej. `"comunicaciones"` → `"informacion y comunicacion"`). Sin normalización, `combinar` produce dos filas separadas para lo que conceptualmente es la misma serie.

**Decisión:** constante `RENOMBRES_INDICES` en nuevo módulo `dominio/correspondencia_canastas.py`. Función privada `_normalizar_indices` en `resultado.py`. `combinar` la invoca antes de concatenar.

**Estructura de `RENOMBRES_INDICES`:**

```python
RENOMBRES_INDICES: dict[str, dict[int, dict[str, str]]]
# tipo → version_origen → {nombre_viejo: nombre_canonico_2024}
```

**Tabla de correspondencia CCIF division (2018 → 2024):**

| 2018 | 2024 (canónico) |
| ---- | --------------- |
| `bienes y servicios diversos` | `cuidado personal, proteccion social y bienes diversos` |
| `comunicaciones` | `informacion y comunicacion` |
| `educacion` | `servicios educativos` |
| `muebles, articulos para el hogar y para su conservacion` | `mobiliario, equipo domestico y mantenimiento rutinario del hogar` |
| `prendas de vestir y calzado` | `ropa y calzado` |
| `recreacion y cultura` | `recreacion, deporte y cultura` |
| `restaurantes y hoteles` | `restaurantes y servicios de alojamiento` |
| `vivienda, agua, electricidad, gas y otros combustibles` | `vivienda, agua, electricidad y gas` |

Sin cambio (4): `alimentos y bebidas no alcoholicas`, `bebidas alcoholicas y tabaco`, `salud`, `transporte`.

Nueva solo en 2024: `seguros y servicios financieros` — sin equivalente en 2018; aparece a partir del primer periodo de la canasta 2024. `bienes y servicios diversos` se mapea a `cuidado personal...` (categoría más cercana del split); `seguros...` queda sin historia previa.

**Algoritmo de `_normalizar_indices(df, version_canonica)`:**

Para cada `tipo` único en el df:

1. Si `tipo` no está en `RENOMBRES_INDICES`: skip.
2. Obtener `version_origen = df.loc[df["tipo"] == tipo, "version"].iloc[0]`.
3. Si `version_origen == version_canonica`: skip.
4. Si `version_origen < version_canonica` (forward): `mapa = RENOMBRES_INDICES[tipo].get(version_origen, {})`.
5. Si `version_origen > version_canonica` (backward): `mapa = {v: k for k, v in RENOMBRES_INDICES[tipo].get(version_canonica, {}).items()}`.
6. Aplicar al nivel `indice`: `index.get_level_values("indice").map(lambda x: mapa.get(x, x))`.
7. Reconstruir el MultiIndex con `pd.MultiIndex.from_arrays`.

**Decisión — categorías sin mapeo:** se dejan con su nombre original. Aparecen solo en los periodos de la canasta donde existen — comportamiento natural, no es un error.

**Decisión — `version_canonica` en `combinar`:** si `None`, `vc = max(version)` de todos los resultados pasados. Si especificado, se convierte a `int` internamente para evitar dependencia circular con `tipos.py` (`tipos.py` importa `ResultadoCalculo`; usar `TYPE_CHECKING` para la anotación `VersionCanasta | None`).

**CCIF grupo — versión preliminar:** se agregaron 19 renombres 1:1 (2018 → 2024). La selección se hizo cruzando los valores reales de `ponderadores_2018.csv` y `ponderadores_2024.csv`: una categoría 2018 se acepta sólo si sus genéricos comunes caen en una única categoría 2024 y esa categoría 2024 no recibe genéricos comunes de otra categoría 2018. Los splits, fusiones, categorías nuevas y categorías eliminadas se dejan sin mapeo.

**Renombres `CCIF grupo` (2018 → 2024):**

| 2018 | 2024 (canónico) |
| ---- | --------------- |
| `agua y otros servicios referentes a la vivienda` | `suministro de agua y servicios diversos relacionados con la vivienda` |
| `articulos de cristal, vajillas y utensilios para el hogar` | `cristaleria, vajillas y utensilios para el hogar` |
| `articulos para el hogar` | `electrodomesticos` |
| `bienes y servicios para la conservacion ordinaria del hogar` | `bienes y servicios para el mantenimiento rutinario del hogar` |
| `educacion no atribuible a algun nivel` | `educacion no definida por nivel` |
| `educacion terciaria` | `educacion terciaria (universitaria)` |
| `funcionamiento de equipo de transporte personal` | `funcionamiento del equipo de transporte personal` |
| `herramientas y equipo para el hogar y el jardin` | `herramienta y equipo para casa y jardin` |
| `mantenimiento y reparacion de la vivienda` | `mantenimiento, reparacion y seguridad de la vivienda` |
| `muebles y accesorios, alfombras y otros materiales para pisos` | `muebles, mobiliario y alfombras sueltas` |
| `paquetes turisticos` | `paquetes de vacaciones` |
| `prendas de vestir` | `ropa` |
| `productos textiles para el hogar` | `textiles para el hogar` |
| `productos, artefactos y equipos medicos` | `medicamentos y productos sanitarios` |
| `renta de vivienda` | `alquileres reales de vivienda` |
| `servicios de hospital` | `servicios de atencion para pacientes hospitalizados` |
| `servicios de suministro de comidas` | `servicios de alimentos y bebidas` |
| `servicios de transporte` | `servicios de transporte de pasajeros` |
| `vivienda propia` | `alquileres imputados para vivienda` |

**Excluidos explícitamente para `CCIF grupo`:** `equipo audiovisual, fotografico y de procesamiento de informacion`, `equipo telefonico y de facsimile`, `otros articulos y equipo para recreacion, jardineria y animales domesticos`, `otros productos duraderos importantes para recreacion y cultura`, `servicios de recreacion y culturales`, `servicios para pacientes externos`, `servicios postales`, `servicios telefonicos y de facsimile`.

**CCIF clase:** se agregaron 52 renombres 1:1 (2018 → 2024). Con esta normalización, las clases comunes pasan de 25 a 77; quedan 10 clases 2018 sin mapear y 17 clases 2024 sin historia directa. La selección usa el mismo criterio que `CCIF grupo`: reciprocidad estricta sobre genéricos comunes en los CSVs de ponderadores. Los 2 renombres adicionales (`diarios y periodicos` y `instrumentos musicales y equipos duraderos...`) fueron confirmados contra COICOP 2018 (UN Statistics Division): corresponden a los cambios oficiales de código 09.5.2→09.7.2 y 09.2.2→09.5.1 respectivamente.

**Renombres `CCIF clase` (2018 → 2024):**

| 2018 | 2024 (canónico) |
| ---- | --------------- |
| `animales domesticos y productos relacionados` | `mascotas y productos relacionados` |
| `artefactos y equipos terapeuticos` | `productos de apoyo` |
| `articulos de cristal, vajillas y utensilios para el hogar` | `cristaleria, vajillas y utensilios para el hogar` |
| `articulos de papeleria y dibujo` | `material de papeleria y dibujo` |
| `articulos electricos pequeños para el hogar` | `electrodomesticos pequeños` |
| `articulos grandes para el hogar, electricos o no` | `grandes electrodomesticos, electricos o no` |
| `bienes no duraderos para el hogar` | `articulos domesticos no duraderos` |
| `carnes` | `animales vivos, carne y otras partes comestibles de animales terrestres` |
| `diarios y periodicos` | `periodicos y publicaciones periodicas` |
| `educacion no atribuible a algun nivel` | `educacion no definida por nivel` |
| `educacion terciaria` | `educacion terciaria (universitaria)` |
| `equipo de deportes, campamento y recreacion al aire libre` | `equipo para deportes, campismo y recreacion al aire libre` |
| `equipo fotografico y cinematografico e instrumentos opticos` | `equipos e instrumentos opticos fotograficos y cinematograficos` |
| `equipo para el procesamiento de informacion` | `equipo de procesamiento de informacion` |
| `equipo para la recepcion, grabacion y reproduccion de sonidos e imagenes` | `equipo para la recepcion, grabacion y reproduccion de sonido y video` |
| `equipo telefonico y de facsimile` | `equipo de telefonia movil` |
| `frutas` | `frutas y frutos secos` |
| `herramientas pequeñas y accesorios diversos` | `herramientas no motorizadas y accesorios diversos` |
| `instrumentos musicales y equipos duraderos importantes para recreacion en interiores` | `instrumentos musicales` |
| `jardines, plantas y flores` | `productos de jardineria, plantas y flores` |
| `joyeria, relojes de pared y relojes de pulsera` | `joyas y relojes` |
| `juegos, juguetes y aficiones` | `juguetes, juegos y pasatiempos` |
| `leche, quesos y huevos` | `leche, otros productos lacteos y huevos` |
| `legumbres y hortalizas` | `hortalizas, tuberculos, platanos de coccion y legumbres` |
| `licores` | `bebidas destiladas y licores` |
| `limpieza, reparacion y alquiler de prendas de vestir` | `limpieza, reparacion, confeccion y alquiler de ropa` |
| `mantenimiento y reparacion para equipo de transporte personal` | `mantenimiento y reparacion de equipo de transporte personal` |
| `materiales para la conservacion y reparacion de la vivienda` | `materiales para el mantenimiento y reparacion de la vivienda` |
| `muebles y accesorios` | `muebles, mobiliario y alfombras sueltas` |
| `otros productos alimenticios` | `alimentos preparados y otros productos alimenticios` |
| `otros productos medicos` | `productos medicos` |
| `otros servicios relativos al transporte personal` | `otros servicios relacionados con equipos de transporte personal` |
| `pan y cereales` | `cereales y productos a base de cereales` |
| `paquetes turisticos` | `paquetes de vacaciones` |
| `pescados y mariscos` | `pescados y otros mariscos` |
| `piezas de repuesto y accesorios para equipo de transporte personal` | `partes y accesorios para equipo de transporte personal` |
| `productos farmaceuticos` | `medicamentos` |
| `productos textiles para el hogar` | `textiles para el hogar` |
| `renta de vivienda` | `alquileres reales pagados por los inquilinos de la residencia principal` |
| `restaurantes, cafes y establecimientos similares` | `restaurantes, cafes y similares` |
| `salones de peluqueria de cuidado personal` | `salones de peluqueria y establecimientos de aseo personal` |
| `seguros` | `seguros relacionado con el transporte` |
| `servicios de hospital` | `servicios curativos y de rehabilitacion para pacientes hospitalizados` |
| `servicios de recreacion y deportivos` | `servicios recreativos y deportivos` |
| `servicios dentales` | `servicios dentales para pacientes ambulatorios` |
| `servicios medicos` | `servicios de atencion preventiva` |
| `servicios paramedicos` | `servicios de diagnostico por imagenes y servicios de laboratorio medico` |
| `transporte de pasajeros por aire` | `transporte de pasajeros por via aerea` |
| `vehiculos a motor` | `automoviles` |
| `veterinaria y otros servicios para animales domesticos` | `veterinarios y otros servicios para mascotas` |
| `vivienda propia` | `alquileres imputados de propietarios-ocupantes para residencia principal` |
| `zapatos y otros calzados` | `calzado y otros tipos de calzado` |

**Excluidos explícitamente para `CCIF clase`:** `agua mineral, refrescos y jugos`, `alfombras y otros revestimientos para pisos`, `azucar, mermeladas, miel, chocolates y dulces`, `cafe, te y cacao`, `herramientas y equipos principales`, `medios para grabacion`, `reparacion y alquiler de calzado`, `servicios culturales`, `servicios postales`, `servicios telefonicos y de facsimile`.

**SCIAN sector — sin mapeo:** no hay renombres 1:1 entre 2018 y 2024. La única categoría presente solo en 2018 es `49 transportes, correos y almacenamiento`, causada por el genérico `paqueteria`; en 2024 no existe ese genérico ni rama `4921`. Aunque el sector cercano en 2024 es `48 transportes, correos y almacenamiento`, se trata como categoría eliminada, no como renombre 1:1 confirmado.

**SCIAN rama:** se agregaron 4 renombres 1:1 (2018 → 2024). La selección usa el mismo criterio de reciprocidad estricta sobre genéricos comunes en los CSVs de ponderadores. Con esta normalización, las ramas comunes pasan de 82 a 86; quedan 5 ramas 2018 sin mapear y 2 ramas 2024 sin historia directa.

**Renombres `SCIAN rama` (2018 → 2024):**

| 2018 | 2024 (canónico) |
| ---- | --------------- |
| `3111 elaboracion de alimentos para animales` | `3111 elaboracion de alimentos balanceados para animales` |
| `3116 matanza, empacado y procesamiento de carne de ganado, aves y otros animales` | `3116 matanza, empacado y procesamiento de carne de ganado, aves y otros animales comestibles` |
| `3253 fabricacion de fertilizantes, pesticidas y otros agroquimicos` | `3253 fabricacion de fertilizantes, plaguicidas y otros agroquimicos` |
| `5111 edicion de periodicos, revistas, libros y similares, y edicion de estas publicaciones integrada con la impresion` | `5131 edicion de periodicos, revistas, libros, directorios y otros materiales` |

**Excluidos explícitamente para `SCIAN rama`:** `3346 fabricacion y reproduccion de medios magneticos y opticos`, `4921 servicios de mensajeria y paqueteria foranea`, `7111 compañias y grupos de espectaculos artisticos y culturales`, `7224 centros nocturnos, bares, cantinas y similares`, `8114 reparacion y mantenimiento de articulos para el hogar y personales`, `7113 promotores de espectaculos artisticos, culturales, deportivos y similares`, `7121 museos, sitios historicos, zoologicos y similares`.

**Validación COICOP 2018:** todos los renombres de `CCIF grupo` y `CCIF clase` fueron verificados contra los CSVs de ponderadores (reciprocidad estricta de genéricos) y contra COICOP 2018 (UN Statistics Division, publicación pre-copy-edit 2018-12-26). Los cambios de nombre son oficiales de la revisión COICOP 2018, no renombres locales del INEGI.

---

## 12. Gaps conocidos y mejoras futuras

Decisiones de diseño que se tomaron con limitaciones conocidas. Cada entrada registra el comportamiento actual, el problema identificado y la mejora propuesta para cuando el trigger se cumpla.

---

### 12.1 `estado_validacion_global` no distingue cobertura parcial ✓ RESUELTO

**Solución aplicada:** se agregaron `'ok_parcial'` a `estado_validacion_global` y `estado_corrida` en `ResumenValidacion`.

- `estado_corrida = 'ok_parcial'`: al menos un periodo es `null_por_faltantes` pero no todos.
- `estado_corrida = 'fallida'`: todos los periodos son `null_por_faltantes`, o hay faltantes de ponderador.
- `estado_validacion_global = 'ok_parcial'`: se activa en dos casos: (a) entre los periodos con `estado_calculo == 'ok'`, al menos uno pasó la tolerancia y al menos uno no pudo ser comparado (`no_disponible`); (b) todos los periodos son `ok` o `diferencia_detectada_imputado` — la diferencia es atribuible a imputación, no a error de cálculo.
- `estado_validacion_global = 'ok'`: todos los periodos comparables fueron verificados y pasaron.

---

### 12.2 Validación por niveles en `LectorCanastaCsv`

**Comportamiento actual:** `LectorCanastaCsv` valida todas las columnas del esquema canónico o falla. No hay distinción entre "mínimo para calcular INPC" y "completo para calcular subíndices".

**Problema:** en el futuro puede haber CSVs que solo tengan `ponderador` y `encadenamiento` (suficientes para INPC) pero sin clasificaciones (COG, CCIF, etc.). Con el validador actual, ese CSV falla aunque el cálculo sea posible.

**Mejora propuesta:** agregar un parámetro `nivel` al método `leer` y actualizar el Protocol `LectorCanasta`. Tres niveles: `"inpc"` (solo ponderador), `"subindices"` (+ clasificaciones), `"completo"` (todas las columnas).

**Cuándo implementar:** cuando se requiera calcular subíndices en v2.

---

### 12.3 Agregados CCIF en `LectorSeriesCsv`

**Comportamiento actual:** `LectorSeriesCsv` filtra y descarta todas las filas que no tienen código de 3 dígitos en el `Título` — es decir, descarta los agregados CCIF (`01 Alimentos...`, `01.1 Alimentos`, etc.).

**Problema:** en v2 los subíndices requieren las series de los agregados CCIF, no solo los genéricos.

**Mejora propuesta:** agregar un parámetro `incluir_agregados: bool = False` al método `leer`.

**Cuándo implementar:** cuando se implemente el cálculo de subíndices en v2.

---

### 12.4 Detección dinámica del header en `LectorSeriesCsv`

**Comportamiento actual:** `LectorSeriesCsv` usa `skiprows=5` fijo para saltar el encabezado de INEGI, asumiendo que siempre son exactamente 5 líneas.

**Problema:** si INEGI cambia el formato de exportación (más o menos líneas de encabezado), el lector fallaría silenciosamente — leería datos incorrectos sin lanzar error.

**Mejora propuesta:** detectar dinámicamente la fila del header contando la moda de separadores (comas) en las primeras 25 líneas y usando la primera fila que alcanza ese conteo como header. Enfoque usado en el proyecto anterior (`archivos.py: cargar_de_raw`).

**Cuándo implementar:** si se detecta que INEGI cambia su formato de exportación, o al implementar soporte para otras fuentes de series.

---

### 12.5 ñ en canasta intermedia ✓ RESUELTO

**Solución aplicada:** los CSV de canasta intermedia (2010, 2013, 2018, 2024) fueron regenerados con ñ donde corresponde. Los nombres de genéricos ahora son consistentes con la normalización de `LectorSeriesCsv` (ej: `"piña"`, `"pañales"`, `"enseñanza adicional"`).

---

### 12.6 Formato de series BIE en versiones 2010 y 2013

**Comportamiento actual:** `LectorSeriesCsv` extrae genéricos con el patrón `\b\d{3}\b` en el campo `Título`. Verificado solo contra series de la canasta 2018.

**Problema:** las series 2010 y 2013 descargadas del BIE podrían tener un formato de título distinto donde los códigos de genérico no sean de 3 dígitos. Si no hay matches, el lector lanzaría `SerieVacia` sin indicar que el problema es de formato.

**Mejora propuesta:** verificar el formato real de las series 2010/2013 en el BIE y ajustar el patrón si es necesario.

**Cuándo implementar:** antes de implementar corridas 2010 y 2013.

---

### 12.7 Cobertura parcial de periodos no reportada explícitamente ✓ RESUELTO

**Solución aplicada:** se agregaron `periodo_inicio = min(periodos)` y `periodo_fin = max(periodos)` a `ResumenValidacion`. El usuario puede comparar estos valores contra `RANGOS_VALIDOS[version]` para saber si la corrida cubre el rango completo. `estado_corrida = 'parcial'` sigue siendo exclusivo de `null_por_faltantes`.

---

### 12.8 `AlmacenArtefactos.obtener` devuelve índice como string

**Comportamiento actual:** `AlmacenArtefactosFs.obtener` lee el Parquet y devuelve el DataFrame con el índice `Periodo` como string (`"1Q Ene 2024"`). La estructura del MultiIndex (niveles, nombres) se preserva gracias a Parquet, pero los valores siguen siendo strings.

**Problema:** el consumidor que llame a `obtener` y quiera operar sobre el DataFrame con lógica de dominio (ordenar por periodo, filtrar por rango) tendrá que re-parsear el índice manualmente con `Periodo.desde_str()`.

**Mejora propuesta:** agregar métodos tipados por artefacto (`obtener_resultado`, `obtener_reporte`, etc.) que re-parseen el índice y devuelvan el tipo correcto.

**Cuándo implementar:** cuando haya un caso de uso que necesite operar sobre artefactos recuperados del almacén (ej. comparar corridas, generar históricos).

---

### 12.9 Validación INEGI solo disponible para tipos específicos ✓ RESUELTO

**Solución implementada en v1.1.0:**

- `TIPOS_CON_VALIDACION` en `dominio/tipos.py` define explícitamente qué tipos soportan comparación INEGI.
- `ReporteDetalladoValidacion` solo incluye columnas de validación (`indice_inegi`, `error_absoluto`, `error_relativo`, `estado_validacion`) cuando `tipo in TIPOS_CON_VALIDACION`. Para el resto el esquema es más compacto y no genera confusión.
- `INDICADORES_INEGI` en `fuente_validacion_api.py` se reestructuró como `dict[str, dict[str, str]]` (tipo → índice → indicador) para soportar múltiples indicadores por tipo. `FuenteValidacion.obtener()` devuelve `dict[str, dict[Periodo, float | None]]`.
- La firma de `validar()` cambió a `inegi: dict[str, dict[Periodo, float | None]]` — unifica el acceso para `"inpc"` y subíndices sin condicionales adicionales.

---

### 12.10 Incompatibilidad de nombres de categorías entre canastas al combinar resultados ✓ RESUELTO

**Solución implementada:**

- Nuevo `dominio/correspondencia_canastas.py` con `RENOMBRES_INDICES` — 8 renombres para `CCIF division`, 19 renombres para `CCIF grupo`, 52 renombres para `CCIF clase` y 4 renombres para `SCIAN rama` (2018 → 2024). Todos validados contra COICOP 2018.
- `SCIAN sector` no requiere mapeo: `49 transportes, correos y almacenamiento` aparece solo en 2018 por `paqueteria`, genérico eliminado en 2024.
- `combinar` aplica normalización automática vía `_normalizar_indices` antes de concatenar.
- `version_canonica: VersionCanasta | None = None` en `combinar` — `None` usa la versión más reciente.
- Ver §11.23 para algoritmo completo y tabla de correspondencia.

**Medición original del problema (2026-04-19):**

| Clasificación         | Solo en 2018 | Solo en 2024 | Comunes |
| --------------------- | -----------: | -----------: | ------: |
| `CCIF division`       | 8            | 1            | 4       |
| `CCIF grupo`          | 27           | 29           | 17      |
| `CCIF clase`          | 62           | 69           | 25      |
| `SCIAN sector`        | 1            | 0            | 17      |
| `SCIAN rama`          | 9            | 6            | 82      |

**Clasificaciones sin fricción** (sin cambios entre 2018 y 2024): `inpc`, `inflacion componente`, `inflacion subcomponente`, `inflacion agrupacion`, `COG`, `durabilidad`, `canasta basica`.

**Resultado tras normalización SCIAN:** `SCIAN sector` queda sin renombres aplicables; `SCIAN rama` pasa de 82 a 86 ramas comunes. Quedan sin mapear ramas eliminadas/nuevas o cambios que no cumplen reciprocidad 1:1.

**Pendiente:** `CCIF grupo` y `CCIF clase` deben considerarse preliminares: sólo incluyen renombres 1:1 observados en la canasta INPC; no incluyen splits, fusiones, categorías nuevas ni categorías eliminadas.

---

### 12.11 Salida mensual directa desde `ejecutar_corrida` (v1.x)

**Situación actual:** para obtener resultados mensuales el usuario debe llamar explícitamente `a_mensual(resultado)` después de `ejecutar_corrida`. No existe un parámetro `formato_salida="mensual"` en `Corrida.ejecutar()`.

**Mejora propuesta:** parámetro opcional en `ejecutar()` que devuelva directamente el resultado mensual:

```python
corrida.ejecutar(..., formato_salida="mensual")  # devuelve ResultadoCalculo mensual
```

**Por qué no se implementa ahora:** requeriría encadenamiento mensual independiente (calcular `f_k` y `f_h` con datos mensuales), lo que produce resultados que divergen ~0.147 pp en variación mensual respecto al INPC mensual oficial del INEGI. El único camino correcto verificado empíricamente es `a_mensual(resultado_quincenal)` (diferencia máxima relativa: 0.0000046 — ver §5.13).

**Cuándo implementar:** si se obtienen series de precios mensuales independientes del INEGI (no derivadas de quincenales) que permitan un Laspeyres mensual directo con error dentro de tolerancia (< 0.0009).

---

### 12.12 `ejecutar` multi-canasta (v2.0)

**Comportamiento actual:** `Corrida.ejecutar()` opera sobre una sola canasta y una sola serie. Para obtener una serie histórica continua, el usuario debe llamar `ejecutar` múltiples veces y combinar los `ResultadoCalculo` manualmente.

**Mejora propuesta:** soporte nativo para múltiples canastas en una sola llamada:

```python
corrida.ejecutar(
    canastas=["canasta_2018.csv", "canasta_2024.csv"],
    series=["series_2018.csv", "series_2024.csv"],
    versions=[2018, 2024],
    tipo="inpc",
) -> list[ResultadoCorrida]
```

Internamente encadena `resultado_referencia` automáticamente entre corridas consecutivas.

**Por qué es v2.0:** cambia la firma pública de `ejecutar`, `ManifestCorrida` (que referencia una sola canasta/series), y la lógica de persistencia. Rompe compatibilidad con código existente.

**Cuándo implementar:** cuando la combinación manual con `ResultadoCalculo.combinar()` resulte insuficiente para los casos de uso del proyecto.

---

### 12.13 Validación de variaciones contra series INEGI (v1.2.4) ✓ RESUELTO

**Implementado:** `validar_variaciones_mensual` y `validar_variaciones_quincenal` en `api/validacion.py`. Ver §6.3.

**Mensual:** 21 indicadores (7 × 3 tipos). Ver §8.7. Verificación empírica 2026-04-24.

**Quincenal:** 21 indicadores (7 × 3 tipos). Ver §8.8. Verificación empírica 2026-04-25.

**Tolerancia:** 0.009 pp para mensual y quincenal.

**Estado `fuera_de_rango_inegi`:** periodos anteriores al primer dato publicado por INEGI para ese indicador. Para interanual y acumulada quincenal, afecta todo el rango 2018–2024 (INEGI solo publica desde `1Q Ago 2024`).

**Mapeos completos:** §8.7 (mensual) y §8.8 (quincenal).

---

### 12.14 Rediseño de API de validación: `ResultadoCalculo`, `ResultadoValidacion` y wrappers con token (v2.0)

**Situación actual:** `ResultadoCorrida` mezcla información de cálculo (siempre disponible, sin red) con información de validación (requiere API INEGI, opcional). Las funciones de dominio `validar` y `validar_mensual` requieren que el usuario construya manualmente `FuenteValidacionApi` y llame a `.obtener()` antes de poder validar.

**Problema:** hay tipos de índice que INEGI no publica (subíndices CCIF de mayor granularidad), por lo que la validación no siempre es posible. Además, mezclar calculo y validación en un solo objeto dificulta los casos de uso donde solo se quiere calcular sin validar.

**Mejora propuesta — dos clases:**

``` text
ResultadoCalculo:
  manifiesto      # ManifestCorrida — metadatos de la corrida
  resultado (df)  # índices calculados, estado_calculo, motivo_error
  reporte         # cobertura de genéricos y ponderadores (sin columnas INEGI)
  diagnostico     # DiagnosticoFaltantes — genéricos ausentes en series CSV
  resumen         # estado_corrida, total_nulls, periodo_inicio/fin, version

ResultadoValidacion:
  calculo         # referencia al ResultadoCalculo validado
  reporte         # extiende el reporte de calculo con: indice_inegi,
                  #   error_absoluto, error_relativo, estado_validacion
  diagnostico     # DiagnosticoValidacion — periodos que no pudieron verificarse
                  #   porque INEGI no publicó datos para esas fechas
                  #   (ej: inflación quincenal interanual disponible solo desde 1Q Ago 2024)
  resumen         # estado_validacion_global, total_diferencias_detectadas,
                  #   total_no_disponibles
```

**`DiagnosticoValidacion`** es distinto a `DiagnosticoFaltantes`: no captura genéricos ausentes en series, sino **cobertura temporal de la API INEGI** — qué periodos del resultado calculado no pudieron verificarse y por qué (fuera del rango histórico publicado, indicador no disponible para ese tipo, etc.).

**Mejora propuesta — wrappers públicos con token (implementar antes de v2.0):**

```python
# Valida índices mensuales (INPC, subyacente, no subyacente, etc.)
# Si resultado es quincenal, llama a_mensual() internamente.
validar_mensual(resultado: ResultadoCalculo, token: str) -> ResultadoValidacion

# Valida índices quincenales. Lanza error si resultado es mensual.
validar_quincenal(resultado: ResultadoCalculo, token: str) -> ResultadoValidacion
```

Ambas funciones:

- Detectan `tipo` desde `resultado.df["tipo"]`
- Construyen `FuenteValidacionApi(token, tipo)` internamente
- Obtienen periodos del resultado y llaman `.obtener()`
- Delegan a la función de dominio correspondiente
- Retornan `ResultadoValidacion` (v2.0) o la tupla actual (antes de v2.0)

**Flujo objetivo en notebook:**

```python
calculo = combinar([inpc_2018.resultado, inpc_2024.resultado])
validacion = validar_mensual(calculo, TOKEN)

validacion.resumen.df
validacion.reporte.df
validacion.diagnostico.df   # periodos no verificados por ausencia en API
```

**Por qué parte es v2.0:** `ResultadoCalculo` y `ResultadoValidacion` como clases nuevas rompen la API pública actual (`ResultadoCorrida`). Los wrappers `validar_mensual` y `validar_quincenal` con token se implementan antes en la capa `api/` retornando la tupla actual, y se migran a `ResultadoValidacion` en v2.0.

**Cuándo implementar wrappers:** v1.2.3 / v1.2.4. **Cuándo implementar clases nuevas:** v2.0, junto con gap 12.12 (multi-canasta).
