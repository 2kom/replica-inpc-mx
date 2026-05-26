# replica-inpc-mx

[![CI](https://github.com/2kom/replica-inpc-mx/actions/workflows/ci.yml/badge.svg)](https://github.com/2kom/replica-inpc-mx/actions/workflows/ci.yml)

Réplica independiente del INPC general de México a partir de insumos públicos del INEGI.

## Aviso importante

Este proyecto es una implementación independiente y **no es un producto oficial del INEGI**.
No está avalado, patrocinado ni apoyado por el INEGI.
Para efectos oficiales, fiscales, legales o contractuales, deben consultarse siempre las publicaciones oficiales del INEGI.

## Objetivo

Replicar el INPC general y sus subíndices usando índices de genéricos y ponderadores publicados por el INEGI, sin acceso a los datos de campo. El objetivo es verificar de forma independiente y reproducible el índice publicado.

Para profundizar:

- [docs/contexto_inpc.md](docs/contexto_inpc.md) — qué es el INPC, usos y conceptos clave
- [docs/metodologia_inegi.md](docs/metodologia_inegi.md) — metodología oficial de cálculo según el INEGI
- [docs/metodologia_replica.md](docs/metodologia_replica.md) — cómo este proyecto replica el INPC

## Alcance (v2.0.0)

La v2.0.0 del proyecto permite:

- cargar canastas y series de genéricos desde CSV (`cargar_canasta`, `cargar_serie`);
- calcular el INPC general mediante Laspeyres directo (canastas 2010 y 2018) o encadenado (canastas 2013 y 2024);
- calcular la serie histórica 2010–2024 con una sola llamada (`calcular_historia`);
- calcular subíndices por clasificador (COG, CCIF, inflación componente/subcomponente, durabilidad, entre otros);
- empalmar tramos de distintas versiones de canasta con normalización automática de nombres cross-versión;
- rebasar a cualquier periodo de referencia;
- imputar periodos faltantes en series vía bfill/ffill con trazabilidad completa (`estado_calculo`);
- convertir resultados quincenales a mensuales vía `a_mensual`;
- calcular variaciones periódicas, acumuladas anuales y desde un periodo base (quincenales y mensuales);
- calcular incidencias periódicas, acumuladas anuales y desde un periodo base por subíndice clasificador (mensuales o quincenales), incluyendo flujos multi-canasta;
- validar índices, variaciones e incidencias contra lo publicado por el INEGI vía su API.

El proyecto **no** incluye todavía:

- mapeo de splits, fusiones, categorías nuevas o eliminadas entre canastas: las categorías que desaparecen, aparecen o se parten entre versiones aparecen solo en los periodos donde existen, sin continuidad histórica.

## Instalación

```bash
# Crear el entorno conda (solo la primera vez)
conda create -n replica-inpc python=3.10

# Activar el entorno
conda activate replica-inpc

# Instalar el paquete en modo editable
pip install -e '.[dev]'
```

## Insumos necesarios

El cálculo requiere dos archivos por versión de canasta: series de genéricos y ponderadores.

- **Series de genéricos:** descargar directamente desde el BIE del INEGI — ver [guias/obtener_series.md](guias/obtener_series.md)
- **Ponderadores:** descargar xlsx y PDF del INEGI y luego generar el CSV canónico con la herramienta incluida — ver [guias/obtener_ponderadores.md](guias/obtener_ponderadores.md) y [tools/uso_generar_canasta.md](tools/uso_generar_canasta.md)

## Quickstart

En un archivo notebook.ipynb en la raiz del proyecto escribes lo siguiente:

```python
import replica_inpc as rep

# Token INEGI — opcional; sin él, la validación no está disponible.
# Registro: https://www.inegi.org.mx/app/api/denue/v1/tokenVerify.aspx
rep.set_token("xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
# Alternativa: variable de entorno INEGI_TOKEN

# Serie histórica 2018 + 2024, mensual, base 2Q Jul 2018 = 100
resultado = rep.calcular_historia(
    insumos=[
        (2018, "data/inputs/ponderadores_2018.csv", "data/inputs/series_2018.CSV"),
        (2024, "data/inputs/ponderadores_2024.csv", "data/inputs/series_2024.CSV"),
    ],
    tipo="inpc",
    referencia="2Q Jul 2018",
    periodicidad="mensual", # te da el resultado en formato mensual
)

# Variaciones mensuales
rv = rep.variacion_periodica(resultado, "mensual")
rep.inflacion_en(rv, "Jun 2024")   # DataFrame con variación de cada índice en Jun 2024

# Validar contra INEGI
validacion = rep.validar_indice(resultado)
validacion.resumen
```

Para uso detallado (modo manual, subíndices, incidencias, validaciones), ver [docs/uso.md](docs/uso.md).

## Política de insumos

Este repositorio **no distribuye**:

- archivos oficiales del INEGI;
- datos publicados por el INEGI;
- transformaciones o derivados de esos datos como parte del repositorio.

El usuario debe obtener los insumos directamente desde las fuentes oficiales del INEGI.

## Fuentes oficiales

- INEGI - INPC: <https://www.inegi.org.mx/programas/inpc/>
- INEGI - API de indicadores: <https://www.inegi.org.mx/servicios/api_indicadores.html>

## Documentación

- [docs/uso.md](docs/uso.md) — uso detallado: modo manual, subíndices, incidencias, validaciones
- [docs/diseño.md](docs/diseño.md) — arquitectura, contratos del dominio, decisiones de diseño

## Licencia

El código de este repositorio se distribuye bajo la licencia MIT. Ver [LICENSE](LICENSE).
