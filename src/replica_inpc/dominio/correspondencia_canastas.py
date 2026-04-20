from __future__ import annotations

# tipo → version_origen → {nombre_viejo: nombre_canonico_2024}
RENOMBRES_INDICES: dict[str, dict[int, dict[str, str]]] = {
    "CCIF division": {
        2018: {
            "bienes y servicios diversos": "cuidado personal, proteccion social y bienes diversos",
            "comunicaciones": "informacion y comunicacion",
            "educacion": "servicios educativos",
            "muebles, articulos para el hogar y para su conservacion": "mobiliario, equipo domestico y mantenimiento rutinario del hogar",
            "prendas de vestir y calzado": "ropa y calzado",
            "recreacion y cultura": "recreacion, deporte y cultura",
            "restaurantes y hoteles": "restaurantes y servicios de alojamiento",
            "vivienda, agua, electricidad, gas y otros combustibles": "vivienda, agua, electricidad y gas",
        }
    }
}
