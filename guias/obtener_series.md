# Obtener series de genéricos — INPC 2018

> Las capturas de pantalla de esta guía corresponden al sitio del INEGI
> (inegi.org.mx) y se incluyen únicamente con fines ilustrativos.

Las series de genéricos son los índices publicados por el INEGI para cada
genérico de la canasta, quincena por quincena. Son uno de los dos insumos
que necesita el sistema para calcular el INPC.

## Pasos

### 1. Ir al programa INPC 2018

Abrir la siguiente URL:

```text
https://www.inegi.org.mx/programas/inpc/2018/
```

Ruta equivalente en el sitio del INEGI:

> Inicio -> Programas de Información -> Históricas -> Índices de Precios ->
> Índice Nacional de Precios al Consumidor (INPC) -> Base 2ª Quincena Julio 2018

![Página del programa INPC 2018 en el sitio del INEGI](img/series_01_programa.png)

### 2. Ir a la pestaña Tabulados

Hacer clic en la pestaña **Tabulados**.

![Pestaña Tabulados en la página del programa INPC 2018](img/series_02_tabulados.png)

### 3. Seleccionar el tabulado CCIF quincenal

Dentro de **Tabulados predefinidos**, desplegar:

> Índice Nacional de Precios al Consumidor →
> Estructura de Información (Índices) →
> **Clasificación del consumo individual por finalidades(CCIF) (quincenal)**

![Menú de tabulados CCIF quincenal](img/series_03_menu.png)

### 4. Desplegar la tabla y exportar

1. Hacer clic en **Desplegar** y esperar a que cargue la tabla completa.
2. Hacer clic en el botón verde **CSV**.

![Botón Desplegar y botón CSV](img/series_04_desplegar_csv.png)

### 5. Configurar la exportación

![Diálogo de exportación con Tipo de información en Índices](img/series_05_dialogo.png)

| Campo               | Valor               |
| ------------------- | ------------------- |
| Período             | `2018` — `2024`     |
| Orientación         | cualquiera          |
| Metadatos           | cualquiera          |
| Tipo de información | **Índices** o Vacio |

> El campo **Tipo de información** debe quedar en **Índices** o dejarse en
> blanco (valor por defecto). Las opciones de inflación (quincenal, acumulada
> anual, interanual) no son las que usa el sistema.

Hacer clic en **Exportar**.

## Dónde colocar el archivo

Mover el CSV descargado a:

```text
data/inputs/series/
```

## Notas

- El encoding del archivo es `cp1252`. El sistema lo maneja automáticamente.
- La orientación y los metadatos no importan; el sistema los maneja automaticamente.
- El sistema solo usa periodos entre `2Q Jul 2018` y `2Q Jul 2024`. El rango
  de descarga debe incluir al menos un año dentro de ese intervalo, de lo
  contrario el sistema no encontrará periodos calculables y fallará.
