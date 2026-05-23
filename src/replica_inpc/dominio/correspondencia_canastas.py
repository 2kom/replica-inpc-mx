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
            # Renombres 2013 -> 2018 incluidos cuando hay continuidad clara de
            # rama: mismo codigo SCIAN, o cambio oficial de codigo, y genericos
            # compatibles despues de aplicar RENOMBRES_GENERICOS[2013].
            #
            # Incluidos:
            # - 2211 y 2221/2213: cambio oficial SCIAN de nombre/codigo; los
            #   genericos INPC son exactamente electricidad y derechos por agua.
            # - 3114 y 3151: mismo codigo y cambio de titulo; conservan la
            #   mayoria de genericos y el resto se explica por cambios de
            #   genericos documentados entre canastas.
            # - 3116: mismo codigo y cambio de titulo; los 9 genericos de 2013
            #   estan contenidos en 2018, que solo agrega "manteca de cerdo".
            # - 3272/3271: cambio de codigo/nombre; el unico generico INPC
            #   ("loza, cristaleria y cubiertos") se conserva exacto.
            # - 5412/5411: continuidad operativa por generico INPC exacto, no
            #   renombre SCIAN semantico limpio.
            # - 7221/7225: continuidad operativa por genericos INPC completos,
            #   aunque cambia el titulo SCIAN de restaurantes a preparacion de alimentos.
            # - 8121: continuidad operativa por mismo codigo y fusion documentada
            #   de "sala de belleza" en "sala de belleza y masajes".
            # - 5241 y 6112: cambio oficial de titulo; cada rama contiene un
            #   unico generico, igual entre canastas.
            # - 8122, 8123, 8124 y 9312: solo normalizan punto final en la
            #   canasta 2013; el contenido de genericos es identico.
            #
            # No se incluyen casos con traslape parcial de genericos. Por ejemplo:
            # 3118, 3119 y 3399 mezclan genericos comunes con genericos nuevos,
            # eliminados o reasignados; no son renombres 1:1 de rama.
            # 5171/5172 se reestructura hacia 5173; 7222 se reestructura
            # parcialmente hacia 7223.
            "2211 generacion, transmision y distribucion de energia electrica.": "2211 generacion, transmision, distribucion y comercializacion de energia electrica",
            "2221 captacion, tratamiento y suministro de agua.": "2213 captacion, tratamiento y suministro de agua",
            "3114 conservacion de frutas, verduras y alimentos preparados": "3114 conservacion de frutas, verduras, guisos y otros alimentos preparados",  # no es 1:1 en contenido de genericos
            "3116 matanza, empacado y procesamiento de carne de ganado, aves y otros animales comestibles": "3116 matanza, empacado y procesamiento de carne de ganado, aves y otros animales",  # no es 1:1 en contenido de genericos
            "3151 fabricacion de prendas de vestir de punto": "3151 fabricacion de prendas de vestir de tejido de punto",  # no es 1:1 en contenido de genericos
            "3272 fabricacion de vidrio y productos de vidrio": "3271 fabricacion de productos a base de arcillas y minerales refractarios",
            "5241 instituciones de seguros y fianzas": "5241 compañias de seguros y fianzas",
            "5412 servicios de contabilidad, auditoria y servicios relacionados": "5411 servicios legales",  # continuidad por generico INPC exacto: "servicios profesionales"; no es renombre SCIAN semantico limpio
            "6112 escuelas de educacion post bachillerato": "6112 escuelas de educacion tecnica superior",
            "7221 restaurantes con servicio completo": "7225 servicios de preparacion de alimentos y bebidas alcoholicas y no alcoholicas",  # continuidad completa por genericos INPC; no es renombre SCIAN literal
            "8121 salones y clinicas de belleza, baños publicos y bolerias.": "8121 salones y clinicas de belleza, baños publicos y bolerias",  # continuidad por fusion documentada: "sala de belleza" -> "sala de belleza y masajes"
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


# Notas de analisis SCIAN rama 2013/2018/2024:
#
# 1114 cultivo en invernaderos y otras estructuras agricolas protegidas, y floricultura
# - Generico 2024: "plantas y flores".
# - 2018: existe igual en 1114, con el mismo sector SCIAN 11.
# - 2013 y 2010: no existe el generico, ni aparece candidato real por nombres
#   similares ("planta", "flor", "jardin" o "jardineria"). Los parecidos por
#   distancia textual son falsos positivos, como "velas y veladoras".
# - Conclusion: 1114 es categoria nueva desde 2018 y se mantiene igual en 2024;
#   no viene de renombre, fusion o desagregacion visible desde 2013/2010.
#
# 3159 confeccion de accesorios de vestir y otras prendas de vestir no clasificados en otra parte
# - Genericos 2024: "complementos de vestir", "otras prendas de vestir para
#   hombre" y "otras prendas de vestir para mujer".
# - "otras prendas de vestir para hombre": en 2010/2013 existe como "otras
#   prendas para hombre" en 3152; en 2018/2024 cae en 3159.
# - "otras prendas de vestir para mujer": en 2010/2013 existe como "otras
#   prendas para mujer" en 3152; en 2018/2024 cae en 3159.
# - "complementos de vestir": no existe exacto ni por renombre en 2010/2013/2018;
#   los similares apuntan a ropa/prendas, pero no hay equivalente directo.
# - Conclusion: 3159 no es renombre puro de 3152; es reclasificacion o
#   desagregacion parcial desde 3152 para "otras prendas...", y en 2024 agrega
#   "complementos de vestir".
#
# 3255 fabricacion de pinturas, recubrimientos y adhesivos
# - Generico 2024: "productos para reparacion menor de la vivienda".
# - 2018: existe igual en 3255, con sector SCIAN 32.
# - 2013 y 2010: no existe exacto ni por renombre de genericos. Los similares
#   por texto apuntan a falsos positivos como "pasta dental", "productos para
#   el cabello", "reparacion de automovil" o "renta de vivienda".
# - Conclusion: 3255 es categoria nueva desde 2018 y se mantiene igual en 2024;
#   no viene de renombre, fusion o desagregacion visible desde 2013/2010.
#
# 4854 transporte escolar y de personal
# - Generico 2024: "transporte escolar".
# - 2018: existe igual en 4854, con sector SCIAN 48.
# - 2013 y 2010: no existe exacto ni por renombre de genericos. Los similares
#   por texto son falsos positivos por "transporte" o "escolar", como
#   "transporte aereo", "metro o transporte electrico", "uniformes escolares",
#   "material escolar" o "preescolar".
# - Conclusion: 4854 es categoria nueva desde 2018 y se mantiene igual en 2024;
#   no viene de renombre, fusion o desagregacion visible desde 2013/2010.
#
# 4921 servicios de mensajeria y paqueteria foranea
# - Generico 2018: "paqueteria".
# - 2018: existe en 4921, con sector SCIAN 49 y CCIF "servicios postales".
# - 2013 y 2010: no existe exacto ni por renombre de genericos. Los similares
#   por texto son falsos positivos como "pera", "primaria", "preparatoria" o
#   "planchas electricas".
# - 2024: no existe "paqueteria"; "paquetes para fiesta" es falso positivo
#   porque cae en servicios culturales/alquiler, no en postal o paqueteria.
# - Conclusion: 4921 aparece como categoria nueva en 2018 y desaparece en 2024;
#   no hay traduccion 2018 -> 2024 ni origen visible en 2013/2010.
#
# 5173 operadores de servicios de telecomunicaciones alambricas e inalambricas
# - Genericos 2024: "servicio de telefonia movil", "servicios de telefonia
#   fija", "paquetes de internet, telefonia y television de paga", "servicio de
#   internet", "servicio de television de paga" y "streaming de peliculas y musica".
# - "servicio de telefonia movil": en 2010/2013 cae en 5172; en 2018/2024 cae
#   en 5173.
# - "servicio de internet" y "servicio de television de paga": en 2010/2013 caen
#   en 5171; en 2018/2024 caen en 5173.
# - "servicios de telefonia fija": aparece en 2018/2024; en 2010/2013 no existe
#   exacto por renombre, aunque se relaciona con fusiones de telefonia fija.
# - "paquetes de internet, telefonia y television de paga": aparece en
#   2018/2024; en 2010/2013 solo hay componentes parciales.
# - "streaming de peliculas y musica": aparece en 2024; los similares previos,
#   como "peliculas, musica y videojuegos", no son equivalentes directos.
# - Conclusion: 5173 es consolidacion de 5171 + 5172 desde 2013 hacia 2018 y
#   expansion en 2024; no es renombre 1:1 de rama.
#
# 5419 otros servicios profesionales, cientificos y tecnicos
# - Generico 2024: "servicios para mascotas".
# - 2018: existe igual en 5419, con sector SCIAN 54.
# - 2013 y 2010: no existe exacto ni por renombre de genericos. El similar real
#   mas cercano es "alimento para mascotas", pero no es equivalente porque es
#   producto/alimento, no servicio. Otros similares por "servicios" son falsos
#   positivos.
# - Conclusion: 5419 es categoria nueva desde 2018 y se mantiene igual en 2024;
#   no viene de renombre, fusion o desagregacion visible desde 2013/2010.
#
# 7111 compañias y grupos de espectaculos artisticos y culturales
# - Generico 2018: "otros servicios culturales, diversiones y espectaculos deportivos".
# - 2010/2013: existe como "otras diversiones y espectaculos deportivos" en 7139.
# - 2018: cae en 7111.
# - 2024: no existe el generico; los similares relevantes son "museos y sitios
#   culturales" en 7121 y "servicios recreativos y centros nocturnos" en 7113,
#   pero no son equivalentes exactos.
# - Conclusion: 7111 es continuidad parcial desde 7139 hacia 2018 para ese
#   generico; en 2024 desaparece y se reparte o reformula en categorias
#   culturales/recreativas.
#
# 7113 promotores de espectaculos artisticos, culturales, deportivos y similares
# - Generico 2024: "servicios recreativos y centros nocturnos".
# - 2018, 2013 y 2010: no existe exacto ni por renombre de genericos.
# - Similares relevantes: "centro nocturno" cae en 7224 hasta 2018; "otros
#   servicios culturales, diversiones y espectaculos deportivos" cae en 7111 en
#   2018 y en 7139 en 2010/2013.
# - Conclusion: 7113 es categoria nueva en 2024 formada por reacomodo o fusion
#   parcial de servicios recreativos/culturales y centros nocturnos; no es
#   renombre 1:1 desde 2018 o 2013.
#
# 7121 museos, sitios historicos, zoologicos y similares
# - Generico 2024: "museos y sitios culturales".
# - 2018, 2013 y 2010: no existe exacto ni por renombre de genericos.
# - Similar relevante: el bloque amplio "otros servicios culturales, diversiones
#   y espectaculos deportivos", que cae en 7111 en 2018 y en 7139 en 2010/2013,
#   pero no es equivalente exacto.
# - Conclusion: 7121 es categoria nueva en 2024, probablemente por desagregacion
#   o reacomodo desde el bloque cultural amplio; no es renombre 1:1 desde 2018
#   o 2013.
#
# 7223 servicios de preparacion de alimentos por encargo
# - Genericos 2024: "barbacoa o birria", "carnitas", "otros alimentos
#   cocinados", "pizzas" y "pollos rostizados".
# - "barbacoa o birria", "carnitas" y "pizzas": en 2010/2013 caen en 3119; en
#   2018/2024 caen en 7223.
# - "otros alimentos cocinados" y "pollos rostizados": en 2010/2013 caen en
#   7222; en 2018/2024 caen en 7223.
# - Conclusion: 7223 no es renombre 1:1 desde 2013; es reagrupacion o fusion
#   parcial desde 3119 y 7222. Desde 2018 a 2024 se mantiene estable con los
#   mismos cinco genericos.
