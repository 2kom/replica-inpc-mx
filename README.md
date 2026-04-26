# replica-inpc-mx

[![CI](https://github.com/2kom/replica-inpc-mx/actions/workflows/ci.yml/badge.svg)](https://github.com/2kom/replica-inpc-mx/actions/workflows/ci.yml)

Replicacion independiente del INPC general de Mexico a partir de insumos publicos del INEGI.

## Aviso importante

Este proyecto es una implementacion independiente y **no es un producto oficial del INEGI**.
No esta avalado, patrocinado ni apoyado por el INEGI.
Para efectos oficiales, fiscales, legales o contractuales, deben consultarse siempre las publicaciones oficiales del INEGI.

## Objetivo

El objetivo del proyecto es replicar el **INPC general** usando:

- indices superiores nacionales de genericos publicados por el INEGI;
- canastas y ponderadores publicados por el INEGI.

## Contexto

El INPC es el índice oficial de inflación de México, elaborado por el INEGI con base en los precios de una canasta representativa del consumo de los hogares. Se publica quincenalmente y tiene usos que van desde la política monetaria hasta la actualización de contratos privados.

Este proyecto replica el INPC a partir de los índices de genéricos y los ponderadores que el INEGI publica, sin acceso a los datos de campo. El objetivo es verificar de forma independiente y reproducible el índice publicado.

Para profundizar:

- [docs/contexto_inpc.md](docs/contexto_inpc.md) — qué es el INPC, usos y conceptos clave.
- [docs/metodologia_inegi.md](docs/metodologia_inegi.md) — metodología oficial de cálculo según el INEGI.
- [docs/metodologia_replica.md](docs/metodologia_replica.md) — cómo este proyecto replica el INPC.

## Alcance actual (v1.2.5)

La v1.2.5 del proyecto permite:

- importar canastas y series de genericos en formato CSV;
- calcular el INPC general mediante Laspeyres directo (canasta 2018) o encadenado (canasta 2024);
- calcular subindices por clasificador (COG, CCIF, inflacion componente, inflacion subcomponente, durabilidad, entre otros);
- imputar periodos faltantes en series via bfill/ffill con trazabilidad completa;
- combinar resultados de distintas corridas en un unico `ResultadoCalculo` cronologico;
- convertir resultados quincenales a mensuales via `a_mensual()`;
- validar indices quincenales o mensuales contra lo publicado por el INEGI via su API;
- calcular variaciones periodicas, acumuladas anuales y desde un periodo base (quincenales y mensuales);
- validar variaciones quincenales o mensuales contra lo publicado por el INEGI via su API;
- calcular incidencias periodicas, acumuladas anuales y desde un periodo base por subindice clasificador (mensuales o quincenales), incluyendo flujos multi-canasta (2018 + 2024);
- validar incidencias mensuales periodicas contra lo publicado por el INEGI via su API;
- exportar resultados de calculo y validacion;
- ejecutar un demo completo con datos sinteticos (ver `demo/`).

El proyecto **no** incluye todavia:

- soporte operativo para canastas 2010 y 2013; el calculo encadenado de 2013 esta diseñado, pero aun no probado;
- mapeo de splits, fusiones, categorias nuevas o eliminadas entre canastas: las categorias que
  desaparecen, aparecen o se parten entre versiones aparecen solo en los periodos donde existen,
  sin continuidad historica.

## Politica de insumos

Este repositorio **no distribuye**:

- archivos oficiales del INEGI;
- datos publicados por el INEGI;
- transformaciones o derivados de esos datos como parte del repositorio.

El usuario debe obtener los insumos directamente desde las fuentes oficiales del INEGI.

## Fuentes oficiales

- INEGI - INPC: <https://www.inegi.org.mx/programas/inpc/>
- INEGI - API de indicadores: <https://www.inegi.org.mx/servicios/api_indicadores.html>

## Uso esperado

### 1. Obtener insumos

- Series de genéricos: ver [guias/obtener_series.md](guias/obtener_series.md).
- Ponderadores (xlsx y PDF) y generar canasta: ver [guias/obtener_ponderadores.md](guias/obtener_ponderadores.md).

### 2.1 Instalar dependencias

```bash
pip install -e '.[dependencies]'
```

### 2.2 Ejecutar desde el notebook

Abrir `notebook.ipynb` y ajustar las variables de configuración:

```python
# Token del INEGI — opcional.
# Sin token el cálculo corre igual, pero la validación queda como no_disponible.
# Registro en: https://www.inegi.org.mx/app/api/denue/v1/tokenVerify.aspx
TOKEN_INEGI = None
# TOKEN_INEGI = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

**Canasta 2018 (Laspeyres directo):**

```python
from replica_inpc.api.corrida import Corrida

corrida = Corrida(token_inegi=TOKEN_INEGI)

resultado_2018 = corrida.ejecutar(
    canasta="data/inputs/canastas/ponderadores_2018.csv",
    series="data/inputs/series/series_2018.csv",
    version=2018,
    tipo="inpc",
    persistir=False,
)
```

**Canasta 2024 (Laspeyres encadenado):**

```python
# resultado_referencia es la corrida 2018; provee f_h exacto del INEGI para el periodo de traslape.
resultado_2024 = corrida.ejecutar(
    canasta="data/inputs/canastas/ponderadores_2024.csv",
    series="data/inputs/series/series_2024.csv",
    version=2024,
    tipo="inpc",
    resultado_referencia=resultado_2018.resultado,
    persistir=False,
)
```

**Combinar corridas en serie temporal continua:**

```python
from replica_inpc import combinar

# Por defecto usa los nombres de la canasta mas reciente (2024 en este caso).
resultado_completo = combinar([resultado_2018.resultado, resultado_2024.resultado])

# version_canonica=2018 normaliza todos los nombres hacia los de la canasta 2018.
resultado_completo = combinar(
    [resultado_2018.resultado, resultado_2024.resultado],
    version_canonica=2018,
)
```

> **Nota:** `combinar` normaliza automáticamente los renombres 1:1 de `RENOMBRES_INDICES`
> para clasificadores con cambios de nombre entre canastas (`CCIF division`, `CCIF grupo`,
> `CCIF clase`, `SCIAN rama`). Los renombres están validados contra los CSVs de ponderadores;
> `CCIF clase` adicionalmente contra COICOP 2018 (UN Statistics Division). Las categorías
> nuevas, eliminadas, splits o fusiones aparecen solo en los periodos donde existen
> (ver §12.10 en `docs/diseño.md`).

**Obtener resultado mensual:**

```python
from replica_inpc import a_mensual

# Convierte ResultadoCalculo quincenal a mensual (promedio simple de 1Q y 2Q).
# Las series de entrada siempre deben ser quincenales; los datos mensuales
# se derivan del cálculo quincenal, no se cargan directamente.
resultado_mensual = a_mensual(resultado_completo)
```

**Calcular variaciones:**

```python
from replica_inpc import variacion_periodica, variacion_desde, variacion_acumulada_anual

# Variacion mensual sobre resultado quincenal (quincena t vs quincena t-2)
rv_mensual = variacion_periodica(resultado_completo, "mensual")

# Variacion mensual sobre resultado mensual (mes t vs mes t-1)
rv_mensual_m = variacion_periodica(resultado_mensual, "mensual")

# Variacion acumulada desde un periodo base
rv_desde = variacion_desde(resultado_completo, "1Q Ene 2024")

# Con indice hasta explicito
rv_desde = variacion_desde(resultado_completo, "1Q Ene 2024", hasta="2Q Jun 2024")

# Variacion acumulada anual (quincena t vs 2Q Dic del año anterior)
rv_anual = variacion_acumulada_anual(resultado_completo)
```

El resultado `rv.df` tiene MultiIndex `(Periodo, indice)` y columna `variacion` (fraccion, no porcentaje).

**Validar contra el INEGI:**

```python
from replica_inpc import validar_mensual, validar_quincenal

# Valida indices mensuales — acepta resultado quincenal o mensual.
# Si es quincenal, aplica a_mensual() internamente.
resumen, reporte, _ = validar_mensual(resultado_completo, token=TOKEN_INEGI)

# Valida indices quincenales directamente.
resumen_q, reporte_q, diag_q = validar_quincenal(resultado_completo, token=TOKEN_INEGI)
```

**Validar variaciones contra el INEGI:**

```python
from replica_inpc import variacion_periodica, variacion_acumulada_anual
from replica_inpc import validar_variaciones_mensual, validar_variaciones_quincenal

# Validar variacion quincenal (periodica quincenal)
rv_q = variacion_periodica(resultado_completo, "quincenal")
reporte_var_q = validar_variaciones_quincenal(rv_q, token=TOKEN_INEGI)

# Validar variacion mensual (periodica mensual)
rv_m = variacion_periodica(resultado_mensual, "mensual")
reporte_var_m = validar_variaciones_mensual(rv_m, token=TOKEN_INEGI)

# Validar variacion acumulada anual (quincenal o mensual)
rv_anual = variacion_acumulada_anual(resultado_completo)
reporte_var_anual = validar_variaciones_quincenal(rv_anual, token=TOKEN_INEGI)
```

El reporte `reporte_var.df` tiene MultiIndex `(tipo_variacion, periodo, indice)` y columnas
`variacion_replicada_pp`, `variacion_inegi_pp`, `error_absoluto_pp`, `estado_validacion`.
Los estados posibles son `ok`, `diferencia_detectada`, `no_disponible`,
`fuera_de_rango_inegi` (periodo aun no publicado por INEGI) y `excluido_semi_ok`.

**Subindices por clasificador:**

```python
resultado = corrida.ejecutar(
    canasta="data/inputs/canastas/ponderadores_2018.csv",
    series="data/inputs/series/series_2018.csv",
    version=2018,
    tipo="inflacion componente",
    persistir=False,
)
```

El resultado incluye:

- `resultado.resumen` — estado general de la corrida
- `resultado.reporte.como_tabla()` — INPC replicado vs INEGI por periodo
- `resultado.resultado.como_tabla()` — índices calculados
- `resultado.diagnostico` — faltantes detectados e imputados

**Calcular incidencias:**

```python
from replica_inpc import incidencia_periodica, incidencia_acumulada_anual, incidencia_desde

# Incidencia periodica mensual (contribucion de cada subindice a la variacion mensual del INPC)
# Soporta multi-canasta: acepta una lista de (ruta_canasta, version)
ri_mensual = incidencia_periodica(
    inpc=resultado_mensual,
    clasificacion=clasificacion_mensual,
    canastas=[
        ("data/inputs/canastas/ponderadores_2018.csv", 2018),
        ("data/inputs/canastas/ponderadores_2024.csv", 2024),
    ],
    frecuencia="mensual",
)

# Incidencia acumulada anual
ri_anual = incidencia_acumulada_anual(
    inpc=resultado_mensual,
    clasificacion=clasificacion_mensual,
    canastas=[("data/inputs/canastas/ponderadores_2018.csv", 2018)],
)

# Incidencia desde un periodo base especifico
ri_desde = incidencia_desde(
    inpc=resultado_mensual,
    clasificacion=clasificacion_mensual,
    canastas=[("data/inputs/canastas/ponderadores_2018.csv", 2018)],
    desde=periodo_desde_str("Ene 2024"),
    hasta=periodo_desde_str("Jun 2024"),
)
```

El resultado `ri.df` tiene MultiIndex `(periodo, indice)` y columnas
`incidencia_pp`, `tipo`, `frecuencia`, `clase_incidencia`, `estado_calculo`.
La suma de `incidencia_pp` sobre todos los subindices para un periodo dado
es igual a la variacion del INPC en puntos porcentuales.

**Validar incidencias contra el INEGI:**

```python
from replica_inpc import validar_incidencias_mensual

# Solo soporta incidencia 'periodica' con frecuencia='mensual'.
reporte_inc = validar_incidencias_mensual(ri_mensual, token=TOKEN_INEGI)
```

El reporte `reporte_inc.df` tiene MultiIndex `(tipo_incidencia, periodo, indice)` y columnas
`incidencia_replicada_pp`, `incidencia_inegi_pp`, `error_absoluto_pp`, `estado_validacion`.

Para detalles de arquitectura y contratos, ver `docs/diseño.md`.

## Herramienta de canastas

El repositorio incluye `tools/generar_canasta.py`, una herramienta para generar los archivos CSV intermedios de canasta a partir de los insumos oficiales del INEGI (xlsx y PDF).

Para obtener el xlsx y el PDF necesarios, ver [guias/obtener_ponderadores.md](guias/obtener_ponderadores.md).

Ver [tools/uso_generar_canasta.md](tools/uso_generar_canasta.md) para instrucciones de uso del script.

## Licencia

El codigo de este repositorio se distribuye bajo la licencia MIT. Ver [LICENSE](LICENSE).
