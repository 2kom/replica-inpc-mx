# replica-inpc-mx

Replicacion independiente del INPC general de Mexico a partir de insumos publicos del INEGI.

## Aviso importante

Este proyecto es una implementacion independiente y **no es un producto oficial del INEGI**.
No esta avalado, patrocinado ni apoyado por el INEGI.
Para efectos oficiales, fiscales, legales o contractuales, deben consultarse siempre las publicaciones oficiales del INEGI.

## Objetivo

El objetivo del proyecto es replicar el **INPC general** usando:

- indices superiores nacionales de genericos publicados por el INEGI;
- canastas y ponderadores publicados por el INEGI.

## Alcance actual (v1)

La v1 del proyecto permite:

- importar canastas y series de genericos en formato CSV;
- calcular el INPC general mediante Laspeyres directo (canasta 2018);
- validar el resultado contra lo publicado por el INEGI via su API de indicadores;
- exportar resultados de calculo y validacion.

El proyecto **no** incluye todavia:

- subindices;
- incidencias ni variaciones;
- calculo encadenado (canastas 2013 y 2024);
- soporte operativo para canastas 2010 y 2013.

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

El flujo general de uso del proyecto es:

1. descargar los insumos oficiales desde el INEGI;
2. colocarlos en las rutas esperadas por el proyecto;
3. ejecutar la corrida desde un notebook o script.

Para detalles de arquitectura y contratos, ver `docs/diseño.md`.

## Herramienta de canastas

El repositorio incluye `tools/generar_canasta.py`, una herramienta para generar los archivos CSV intermedios de canasta a partir de los insumos oficiales del INEGI (xlsx y PDF).

Ver [tools/uso_generar_canasta.md](tools/uso_generar_canasta.md) para instrucciones de uso.

## Licencia

El codigo de este repositorio se distribuye bajo la licencia MIT. Ver [LICENSE](LICENSE).
