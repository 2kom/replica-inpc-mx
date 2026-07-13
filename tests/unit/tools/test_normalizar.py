# Valida normalizar_genericos (canasta_inpc.normalizar) — función pura de texto, sin archivo.

import pandas as pd
import pytest
from canasta_inpc.normalizar import (
    normalizar_celda,
    normalizar_genericos,
    normalizar_texto,
    quitar_prefijo_numerico,
    quitar_prefijos,
    quitar_puntuacion,
    quitar_tildes,
)

# -- quitar_tildes --------------------------------------------------------


def test_quitar_tildes_vocales() -> None:
    assert quitar_tildes("áéíóú") == "aeiou"


def test_quitar_tildes_conserva_enie_minuscula() -> None:
    assert quitar_tildes("año") == "año"


def test_quitar_tildes_conserva_enie_mayuscula() -> None:
    assert quitar_tildes("Ñoño") == "Ñoño"


def test_quitar_tildes_dieresis() -> None:
    assert quitar_tildes("bilingüe") == "bilingue"


# -- normalizar_texto ------------------------------------------------------


def test_normalizar_texto_minusculas() -> None:
    assert normalizar_texto("ARROZ") == "arroz"


def test_normalizar_texto_colapsa_espacios_repetidos() -> None:
    assert normalizar_texto("frijol   negro") == "frijol negro"


def test_normalizar_texto_quita_nbsp() -> None:
    assert normalizar_texto("café\xa0soluble") == "cafe soluble"


def test_normalizar_texto_no_quita_puntuacion() -> None:
    # normalizar_texto por si sola conserva comas; quitarlas es responsabilidad
    # de quitar_puntuacion, un paso separado en normalizar_celda.
    assert normalizar_texto("Carnes secas, procesadas") == "carnes secas, procesadas"


# -- quitar_prefijo_numerico ------------------------------------------------


@pytest.mark.parametrize(
    ("crudo", "esperado"),
    [
        ("1. Alimentos", "Alimentos"),
        ("01- Alimentos", "Alimentos"),
        ("2) Alimentos", "Alimentos"),
        ("3 Alimentos", "Alimentos"),
    ],
)
def test_quitar_prefijo_numerico_formatos(crudo: str, esperado: str) -> None:
    assert quitar_prefijo_numerico(crudo) == esperado


def test_quitar_prefijo_numerico_sin_prefijo_no_cambia() -> None:
    assert quitar_prefijo_numerico("Alimentos") == "Alimentos"


def test_quitar_prefijo_numerico_no_toca_codigo_interno() -> None:
    # el prefijo debe estar al inicio; un digito interno (ej. SCIAN) no se toca
    assert quitar_prefijo_numerico("Alimentos 1") == "Alimentos 1"


# -- quitar_puntuacion -------------------------------------------------------


def test_quitar_puntuacion_coma() -> None:
    assert quitar_puntuacion("carnes secas, procesadas") == "carnes secas procesadas"


def test_quitar_puntuacion_punto_y_coma() -> None:
    assert quitar_puntuacion("consola; cartuchos") == "consola cartuchos"


def test_quitar_puntuacion_parentesis() -> None:
    assert quitar_puntuacion("educacion (colegiaturas)") == "educacion colegiaturas"


def test_quitar_puntuacion_conserva_digitos() -> None:
    assert quitar_puntuacion("3116 matanza") == "3116 matanza"


def test_quitar_puntuacion_recolapsa_espacio_tras_quitar_signo() -> None:
    assert quitar_puntuacion("a  ,  b") == "a b"


# -- normalizar_celda (estandar de comparacion, sin prefijo) ----------------


def test_normalizar_celda_combina_minusculas_tildes_puntuacion() -> None:
    assert normalizar_celda("Carnes Secas, Procesadas") == "carnes secas procesadas"


def test_normalizar_celda_conserva_enie() -> None:
    assert normalizar_celda("Año, nuevo") == "año nuevo"


def test_normalizar_celda_no_quita_prefijo() -> None:
    # el prefijo numerico no es parte del estandar de comparacion/matching —
    # normalizar_celda se usa para eso (ver quitar_prefijos para el otro caso).
    assert normalizar_celda("1. Alimentos") == "1 alimentos"


# -- normalizar_genericos (DataFrame, estandar de comparacion) --------------


def _df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "generico": ["Arroz, integral"],
            "ponderador": ["0.5"],
            "encadenamiento": ["1.0"],
            "COG": ["1. Alimentos, bebidas"],
            "SCIAN sector": ["31 Industrias, manufactureras"],
            "canasta basica": ["X"],
            "canasta consumo minimo": [""],
        }
    )


def test_normalizar_genericos_normaliza_generico() -> None:
    resultado = normalizar_genericos(_df())
    assert resultado["generico"].iloc[0] == "arroz integral"


def test_normalizar_genericos_no_toca_ponderador() -> None:
    resultado = normalizar_genericos(_df())
    assert resultado["ponderador"].iloc[0] == "0.5"


def test_normalizar_genericos_no_toca_encadenamiento() -> None:
    resultado = normalizar_genericos(_df())
    assert resultado["encadenamiento"].iloc[0] == "1.0"


def test_normalizar_genericos_no_toca_canasta_basica() -> None:
    resultado = normalizar_genericos(_df())
    assert resultado["canasta basica"].iloc[0] == "X"


def test_normalizar_genericos_normaliza_clasificacion_sin_quitar_prefijo() -> None:
    resultado = normalizar_genericos(_df())
    assert resultado["COG"].iloc[0] == "1 alimentos bebidas"


def test_normalizar_genericos_scian_tambien_se_normaliza_para_matchear() -> None:
    # normalizar_genericos no distingue SCIAN — la excepcion de prefijo vive
    # en quitar_prefijos, no aca, porque el prefijo no participa en el match.
    resultado = normalizar_genericos(_df())
    assert resultado["SCIAN sector"].iloc[0] == "31 industrias manufactureras"


# -- quitar_prefijos (DataFrame, paso final antes de escribir) --------------


def test_quitar_prefijos_quita_de_clasificacion() -> None:
    resultado = quitar_prefijos(normalizar_genericos(_df()))
    assert resultado["COG"].iloc[0] == "alimentos bebidas"


def test_quitar_prefijos_scian_conserva_codigo() -> None:
    resultado = quitar_prefijos(normalizar_genericos(_df()))
    assert resultado["SCIAN sector"].iloc[0] == "31 industrias manufactureras"


def test_quitar_prefijos_no_toca_ponderador() -> None:
    resultado = quitar_prefijos(normalizar_genericos(_df()))
    assert resultado["ponderador"].iloc[0] == "0.5"


def test_quitar_prefijos_formato_con_puntuacion_propia() -> None:
    # en el pipeline real quitar_prefijos siempre corre DESPUES de
    # normalizar_genericos (la puntuacion ya esta fuera para entonces), pero
    # como funcion publica standalone debe seguir aceptando los formatos
    # documentados ("1.", "01-", "2)") sin depender de ese orden.
    df = pd.DataFrame({"COG": ["1)Alimentos"], "ponderador": ["0.5"]})
    assert quitar_prefijos(df)["COG"].iloc[0] == "Alimentos"
