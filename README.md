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

## Alcance actual

La primera etapa del proyecto contempla:

- soporte inicial para la `canasta y ponderadores actualizados a 2018`
- extension posterior a la `canasta y ponderadores actualizados a 2024`.

Por ahora, el proyecto **no** incluye:

- comparacion de resultados con datos oficiales;
- subindices;
- incidencias;
- variaciones;
- soporte operativo para `canasta y ponderadores actualizados a 2010` y `actualizacion de ponderadores a 2013`.

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
3. ejecutar los scripts o comandos del proyecto para procesarlos y calcular el INPC.

La documentacion de instalacion y uso se ira agregando conforme avance la implementacion.

## Estado

Proyecto en construccion.

## Licencia

El codigo de este repositorio se distribuye bajo la licencia MIT. Ver [LICENSE](LICENSE).
