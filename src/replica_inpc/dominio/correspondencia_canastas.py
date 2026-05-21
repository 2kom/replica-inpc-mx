from __future__ import annotations

# version_origen -> {nombre_viejo: nombre_destino}
RENOMBRES_GENERICOS: dict[int, dict[str, str]] = {
    2013: {
        "calcetines": "calcetines y calcetas para niños",
        "camisas": "camisas y playeras para hombre",
        "carnes secas y otros embutidos": "carnes secas, procesadas y otros embutidos",
        "crema de leche": "crema y otros productos a base de leche",
        "frutas y legumbres preparadas para bebes": "alimentos para bebe",
        "helados": "helados, nieves y paletas de hielo",
        "instrumentos musicales y otros": "instrumentos musicales",
        "juguetes": "juguetes y juegos de mesa",
        "medias y pantimedias": "calcetas, medias y pantimedias",
        "otras diversiones y espectaculos deportivos": "otros servicios culturales, diversiones y espectaculos deportivos",
        "otras prendas para hombre": "otras prendas de vestir para hombre",
        "otras prendas para mujer": "otras prendas de vestir para mujer",
        "otras refacciones": "partes, accesorios y otras refacciones para vehiculos",
        "otros gastos del calzado": "servicios y articulos para el calzado",
        "papas fritas y similares": "papas fritas",
        "pasta dental": "crema y productos para higiene dental",
        "queso manchego o chihuahua": "queso manchego y chihuahua",
        "queso oaxaca o asadero": "queso oaxaca y asadero",
        "trajes": "traje para hombre",
    },
    2018: {
        "leche de soya": "leches de origen vegetal",
        "ropa interior para infantes": "ropa interior para niños, niñas y adolescentes",
        "zapatos de material sintetico": "sandalias y huaraches",
    },
}

# version_origen -> {generico_viejo: (genericos_destino, ...)}
DESAGREGACIONES_GENERICOS: dict[int, dict[str, tuple[str, ...]]] = {
    2013: {
        "bicicletas y motocicletas": ("motocicletas", "bicicletas"),
        "chiles envasados, moles y salsas": ("chiles envasados", "moles y salsas"),
        "chocolate": (
            "chocolate y productos de confiteria",
            "chocolate liquido y para preparar bebida",
        ),
        "dulces, cajetas y miel": (
            "chocolate y productos de confiteria",
            "gelatina, miel y mermeladas",
        ),
        "estudios medicos de gabinete": (
            "analisis clinicos",
            "atencion medica durante el parto",
        ),
        "otros aparatos electricos": (
            "aspiradoras y otros aparatos para el hogar",
            "cafeteras, tostadoras, ventiladores y otros electrodomesticos pequeños",
            "aparatos electricos para el cuidado personal",
        ),
        "otros textiles para el hogar": (
            "blancos y otros textiles para el hogar",
            "articulos desechables y no duraderos",
        ),
        "otros utensilios de cocina": (
            "articulos y utensilios para el hogar",
            "articulos desechables y no duraderos",
        ),
        "peliculas, musica y videojuegos": (
            "peliculas y musica",
            "juegos electronicos; consola, cartuchos y discos para videojuegos",
        ),
    },
    2018: {
        "alimentos para bebe": ("leche maternizada y alimentos para bebe",),
        "articulos desechables y no duraderos": ("articulos desechables y no duraderos",),
        "aspiradoras y otros aparatos para el hogar": (
            "aspiradoras y otros aparatos para el hogar",
        ),
        "blancos y otros textiles para el hogar": (
            "complementos de vestir",
            "toallas, cortinas y otros blancos",
        ),
        "bolsas, maletas y cinturones": (
            "complementos de vestir",
            "bolsas y mochilas",
        ),
        "cafeteras, tostadoras, ventiladores y otros electrodomesticos pequeños": (
            "aspiradoras y otros aparatos para el hogar",
            "cafeteras, tostadoras, ventiladores y otros electrodomesticos pequeños",
        ),
        "cine": ("cine", "servicios recreativos y centros nocturnos"),
        "instrumentos musicales": ("instrumentos musicales y descargas de audio y video",),
        "juegos electronicos; consola, cartuchos y discos para videojuegos": (
            "consolas, discos y descargas de videojuegos",
            "servicios recreativos y centros nocturnos",
        ),
        "otras prendas de vestir para hombre": (
            "otras prendas de vestir para hombre",
            "complementos de vestir",
        ),
        "otras prendas de vestir para mujer": (
            "otras prendas de vestir para mujer",
            "complementos de vestir",
        ),
        "otros servicios culturales, diversiones y espectaculos deportivos": (
            "cine",
            "museos y sitios culturales",
            "paquetes para fiesta",
        ),
        "otros servicios para el hogar": (
            "servicios para el mantenimiento, reparacion y seguridad de la vivienda",
            "otros servicios relacionados con la vivienda",
            "servicio domestico",
        ),
        "leche evaporada, condensada y maternizada": (
            "leche evaporada y condensada",
            "leche maternizada y alimentos para bebe",
        ),
        "peliculas y musica": (
            "streaming de peliculas y musica",
            "instrumentos musicales y descargas de audio y video",
        ),
        "platanos": ("platanos", "otras verduras y legumbres"),
        "refrescos envasados": ("refrescos envasados", "bebidas energeticas"),
        "otras verduras y legumbres": (
            "otras verduras y legumbres",
            "cilantro, epazote y perejil",
        ),
        "ropa de abrigo": ("ropa de abrigo", "complementos de vestir"),
        "servicio domestico": ("servicio domestico",),
        "servicios y articulos para el calzado": ("articulos desechables y no duraderos",),
    },
}

# version_origen -> {generico_destino: (genericos_viejos, ...)}
FUSIONES_GENERICOS: dict[int, dict[str, tuple[str, ...]]] = {
    2013: {
        "cafeteras, tostadoras, ventiladores y otros electrodomesticos pequeños": ("ventiladores",),
        "equipo terminal de comunicacion": ("aparatos de telefonia fija",),
        "otras verduras y legumbres": ("otras legumbres", "chicharo"),
        "sala de belleza y masajes": ("sala de belleza",),
        "servicios de telefonia fija": (
            "servicio telefonico local fijo",
            "larga distancia internacional",
        ),
    },
    2018: {
        "autobus foraneo": ("autobus foraneo", "paqueteria"),
        "camaron": ("camaron", "otros mariscos"),
        "herramientas y equipo para el hogar": (
            "herramientas y equipo grande para el hogar",
            "herramientas pequeñas y accesorios diversos",
        ),
        "muebles diversos para el hogar": (
            "lamparas",
            "muebles diversos para el hogar",
            "alfombras y otros materiales para pisos",
            "objetos ornamentales y decorativos",
        ),
        "periodicos y revistas": ("periodicos", "revistas"),
        "reproductores de audio y video, y sus accesorios": (
            "equipos y reproductores de audio",
            "reproductores de video",
        ),
        "ropa para bebes": ("camisetas para bebes", "ropa para bebes"),
        "servicios recreativos y centros nocturnos": (
            "centro nocturno",
            "otros servicios culturales, diversiones y espectaculos deportivos",
        ),
        "toallas, cortinas y otros blancos": ("cortinas", "toallas"),
    },
}

# version_origen -> {version_destino: (genericos_nuevos, ...)}
NUEVOS_GENERICOS: dict[int, dict[int, tuple[str, ...]]] = {
    2013: {
        2018: (
            "alfombras y otros materiales para pisos",
            "herramientas pequeñas y accesorios diversos",
            "herramientas y equipo grande para el hogar",
            "lamparas",
            "leche de soya",
            "paqueteria",
            "productos para reparacion menor de la vivienda",
            "servicios para mascotas",
            "te",
            "transporte escolar",
        ),
    },
}

# version_origen -> {version_destino: (genericos_eliminados, ...)}
ELIMINADOS_GENERICOS: dict[int, dict[int, tuple[str, ...]]] = {
    2013: {
        2018: ("calentadores para agua", "larga distancia nacional"),
    },
}

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
        },
    },
    # Renombres 1:1 validados contra CSVs de ponderadores (reciprocidad de genericos)
    # y contra COICOP 2018 (UN Statistics Division) para confirmar cambios oficiales.
    # Splits, fusiones, categorias nuevas y eliminadas quedan fuera.
    "CCIF clase": {
        2013: {
            "seguro relacionado con el transporte": "seguros",
        },
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
        },
    },
    # SCIAN sector: no se agrega mapeo 2018 -> 2024.
    # En 2018 existe "49 transportes, correos y almacenamiento" solo por el
    # generico "paqueteria"; en 2024 no existe ese generico ni rama 4921.
    # Aunque el sector cercano en 2024 es "48 transportes, correos y almacenamiento",
    # esto se trata como categoria eliminada, no como renombre 1:1 confirmado.
    "SCIAN sector": {
        2013: {
            "22 generacion, transmision y distribucion de energia electrica, suministro de agua y de gas por ductos al consumidor final": "22 generacion, transmision, distribucion y comercializacion de energia electrica, suministro de agua y de gas natural por ductos al consumidor final",
            "56 servicios de apoyo a los negocios y manejo de desechos y servicios de remediacion": "56 servicios de apoyo a los negocios y manejo de residuos, y servicios de remediacion",
            "93 actividades legislativas, gubernamentales, de imparticion de justicia y de organismos internacionales y extraterritorial": "93 actividades legislativas, gubernamentales, de imparticion de justicia y de organismos internacionales y extraterritoriales",
        }
    },
    "SCIAN rama": {
        2010: {
            # El CSV de la canasta 2010 exporta estos 6 índices sin punto final.
            # El CSV de la canasta 2013 tiene punto final en los mismos índices
            # (artefacto de exportación; el contenido de genéricos es idéntico).
            # Sin este mapa, empalmar([r_2010, r_2013]) trata ambas variantes como
            # índices distintos → duplicado al aplicar el mapa 2013→2018.
            "2211 generacion, transmision y distribucion de energia electrica": "2211 generacion, transmision y distribucion de energia electrica.",
            "2221 captacion, tratamiento y suministro de agua": "2221 captacion, tratamiento y suministro de agua.",
            "8122 lavanderias y tintorerias": "8122 lavanderias y tintorerias.",
            "8123 servicios funerarios y administracion de cementerios": "8123 servicios funerarios y administracion de cementerios.",
            "8124 estacionamientos y pensiones para vehiculos automotores": "8124 estacionamientos y pensiones para vehiculos automotores.",
            "9312 administracion publica en general": "9312 administracion publica en general.",
        },
        2013: {
            # Renombres 2013 -> 2018 incluidos solo cuando pasan tres filtros:
            # 1) nombre/codigo compatible entre versiones SCIAN oficiales,
            # 2) genericos identicos despues de aplicar RENOMBRES_GENERICOS[2013],
            # 3) sin depender de fusiones, desagregaciones, nuevos o eliminados.
            #
            # Incluidos:
            # - 2211 y 2221/2213: cambio oficial SCIAN de nombre/codigo; los
            #   genericos INPC son exactamente electricidad y derechos por agua.
            # - 5241 y 6112: cambio oficial de titulo; cada rama contiene un
            #   unico generico, igual entre canastas.
            # - 8122, 8123, 8124 y 9312: solo normalizan punto final en la
            #   canasta 2013; el contenido de genericos es identico.
            #
            # No se incluyen casos con traslape parcial de genericos. Por ejemplo:
            # 3118, 3119 y 3399 mezclan genericos comunes con genericos nuevos,
            # eliminados o reasignados; no son renombres 1:1 de rama.
            # 3114 separa "chiles envasados, moles y salsas" y agrega genericos;
            # 3116 agrega "manteca de cerdo"; 8121 requiere la fusion de
            # "sala de belleza" en "sala de belleza y masajes"; 5171/5172 se
            # reestructura hacia 5173; 7221/7222 se reestructura hacia 7223/7225.
            # Tampoco se incluyen falsos positivos por genericidad del INPC:
            # 3272 -> 3271 y 5412 -> 5411 comparten un generico, pero no son
            # renombres SCIAN oficiales 1:1.
            "2211 generacion, transmision y distribucion de energia electrica.": "2211 generacion, transmision, distribucion y comercializacion de energia electrica",
            "2221 captacion, tratamiento y suministro de agua.": "2213 captacion, tratamiento y suministro de agua",
            "5241 instituciones de seguros y fianzas": "5241 compañias de seguros y fianzas",
            "6112 escuelas de educacion post bachillerato": "6112 escuelas de educacion tecnica superior",
            "8122 lavanderias y tintorerias.": "8122 lavanderias y tintorerias",
            "8123 servicios funerarios y administracion de cementerios.": "8123 servicios funerarios y administracion de cementerios",
            "8124 estacionamientos y pensiones para vehiculos automotores.": "8124 estacionamientos y pensiones para vehiculos automotores",
            "9312 administracion publica en general.": "9312 administracion publica en general",
        },
        2018: {
            "3111 elaboracion de alimentos para animales": "3111 elaboracion de alimentos balanceados para animales",
            "3116 matanza, empacado y procesamiento de carne de ganado, aves y otros animales": "3116 matanza, empacado y procesamiento de carne de ganado, aves y otros animales comestibles",
            "3253 fabricacion de fertilizantes, pesticidas y otros agroquimicos": "3253 fabricacion de fertilizantes, plaguicidas y otros agroquimicos",
            "5111 edicion de periodicos, revistas, libros y similares, y edicion de estas publicaciones integrada con la impresion": "5131 edicion de periodicos, revistas, libros, directorios y otros materiales",
        },
    },
}
