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
    },
    # Renombres 1:1 validados contra CSVs de ponderadores (reciprocidad de genericos).
    # Splits, fusiones, categorias nuevas y eliminadas quedan fuera.
    "CCIF grupo": {
        2018: {
            "agua y otros servicios referentes a la vivienda": "suministro de agua y servicios diversos relacionados con la vivienda",
            "articulos de cristal, vajillas y utensilios para el hogar": "cristaleria, vajillas y utensilios para el hogar",
            "articulos para el hogar": "electrodomesticos",
            "bienes y servicios para la conservacion ordinaria del hogar": "bienes y servicios para el mantenimiento rutinario del hogar",
            "educacion no atribuible a algun nivel": "educacion no definida por nivel",
            "educacion terciaria": "educacion terciaria (universitaria)",
            "funcionamiento de equipo de transporte personal": "funcionamiento del equipo de transporte personal",
            "herramientas y equipo para el hogar y el jardin": "herramienta y equipo para casa y jardin",
            "mantenimiento y reparacion de la vivienda": "mantenimiento, reparacion y seguridad de la vivienda",
            "muebles y accesorios, alfombras y otros materiales para pisos": "muebles, mobiliario y alfombras sueltas",
            "paquetes turisticos": "paquetes de vacaciones",
            "prendas de vestir": "ropa",
            "productos textiles para el hogar": "textiles para el hogar",
            "productos, artefactos y equipos medicos": "medicamentos y productos sanitarios",
            "renta de vivienda": "alquileres reales de vivienda",
            "servicios de hospital": "servicios de atencion para pacientes hospitalizados",
            "servicios de suministro de comidas": "servicios de alimentos y bebidas",
            "servicios de transporte": "servicios de transporte de pasajeros",
            "vivienda propia": "alquileres imputados para vivienda",
        }
    },
    # Renombres 1:1 validados contra CSVs de ponderadores (reciprocidad de genericos)
    # y contra COICOP 2018 (UN Statistics Division) para confirmar cambios oficiales.
    # Splits, fusiones, categorias nuevas y eliminadas quedan fuera.
    "CCIF clase": {
        2018: {
            "animales domesticos y productos relacionados": "mascotas y productos relacionados",
            "artefactos y equipos terapeuticos": "productos de apoyo",
            "articulos de cristal, vajillas y utensilios para el hogar": "cristaleria, vajillas y utensilios para el hogar",
            "articulos de papeleria y dibujo": "material de papeleria y dibujo",
            "articulos electricos pequeños para el hogar": "electrodomesticos pequeños",
            "articulos grandes para el hogar, electricos o no": "grandes electrodomesticos, electricos o no",
            "bienes no duraderos para el hogar": "articulos domesticos no duraderos",
            "carnes": "animales vivos, carne y otras partes comestibles de animales terrestres",
            "diarios y periodicos": "periodicos y publicaciones periodicas",
            "educacion no atribuible a algun nivel": "educacion no definida por nivel",
            "educacion terciaria": "educacion terciaria (universitaria)",
            "equipo de deportes, campamento y recreacion al aire libre": "equipo para deportes, campismo y recreacion al aire libre",
            "equipo fotografico y cinematografico e instrumentos opticos": "equipos e instrumentos opticos fotograficos y cinematograficos",
            "equipo para el procesamiento de informacion": "equipo de procesamiento de informacion",
            "equipo para la recepcion, grabacion y reproduccion de sonidos e imagenes": "equipo para la recepcion, grabacion y reproduccion de sonido y video",
            "equipo telefonico y de facsimile": "equipo de telefonia movil",
            "frutas": "frutas y frutos secos",
            "herramientas pequeñas y accesorios diversos": "herramientas no motorizadas y accesorios diversos",
            "instrumentos musicales y equipos duraderos importantes para recreacion en interiores": "instrumentos musicales",
            "jardines, plantas y flores": "productos de jardineria, plantas y flores",
            "joyeria, relojes de pared y relojes de pulsera": "joyas y relojes",
            "juegos, juguetes y aficiones": "juguetes, juegos y pasatiempos",
            "leche, quesos y huevos": "leche, otros productos lacteos y huevos",
            "legumbres y hortalizas": "hortalizas, tuberculos, platanos de coccion y legumbres",
            "licores": "bebidas destiladas y licores",
            "limpieza, reparacion y alquiler de prendas de vestir": "limpieza, reparacion, confeccion y alquiler de ropa",
            "mantenimiento y reparacion para equipo de transporte personal": "mantenimiento y reparacion de equipo de transporte personal",
            "materiales para la conservacion y reparacion de la vivienda": "materiales para el mantenimiento y reparacion de la vivienda",
            "muebles y accesorios": "muebles, mobiliario y alfombras sueltas",
            "otros productos alimenticios": "alimentos preparados y otros productos alimenticios",
            "otros productos medicos": "productos medicos",
            "otros servicios relativos al transporte personal": "otros servicios relacionados con equipos de transporte personal",
            "pan y cereales": "cereales y productos a base de cereales",
            "paquetes turisticos": "paquetes de vacaciones",
            "pescados y mariscos": "pescados y otros mariscos",
            "piezas de repuesto y accesorios para equipo de transporte personal": "partes y accesorios para equipo de transporte personal",
            "productos farmaceuticos": "medicamentos",
            "productos textiles para el hogar": "textiles para el hogar",
            "renta de vivienda": "alquileres reales pagados por los inquilinos de la residencia principal",
            "restaurantes, cafes y establecimientos similares": "restaurantes, cafes y similares",
            "salones de peluqueria de cuidado personal": "salones de peluqueria y establecimientos de aseo personal",
            "seguros": "seguros relacionado con el transporte",
            "servicios de hospital": "servicios curativos y de rehabilitacion para pacientes hospitalizados",
            "servicios de recreacion y deportivos": "servicios recreativos y deportivos",
            "servicios dentales": "servicios dentales para pacientes ambulatorios",
            "servicios medicos": "servicios de atencion preventiva",
            "servicios paramedicos": "servicios de diagnostico por imagenes y servicios de laboratorio medico",
            "transporte de pasajeros por aire": "transporte de pasajeros por via aerea",
            "vehiculos a motor": "automoviles",
            "veterinaria y otros servicios para animales domesticos": "veterinarios y otros servicios para mascotas",
            "vivienda propia": "alquileres imputados de propietarios-ocupantes para residencia principal",
            "zapatos y otros calzados": "calzado y otros tipos de calzado",
        }
    },
    # SCIAN sector: no se agrega mapeo 2018 -> 2024.
    # En 2018 existe "49 transportes, correos y almacenamiento" solo por el
    # generico "paqueteria"; en 2024 no existe ese generico ni rama 4921.
    # Aunque el sector cercano en 2024 es "48 transportes, correos y almacenamiento",
    # esto se trata como categoria eliminada, no como renombre 1:1 confirmado.
    "SCIAN rama": {
        2018: {
            "3111 elaboracion de alimentos para animales": "3111 elaboracion de alimentos balanceados para animales",
            "3116 matanza, empacado y procesamiento de carne de ganado, aves y otros animales": "3116 matanza, empacado y procesamiento de carne de ganado, aves y otros animales comestibles",
            "3253 fabricacion de fertilizantes, pesticidas y otros agroquimicos": "3253 fabricacion de fertilizantes, plaguicidas y otros agroquimicos",
            "5111 edicion de periodicos, revistas, libros y similares, y edicion de estas publicaciones integrada con la impresion": "5131 edicion de periodicos, revistas, libros, directorios y otros materiales",
        }
    },
}
