from __future__ import annotations

import pandas as pd
import pytest
from canasta_inpc.esquema import COLUMNAS_BASE
from canasta_inpc.match import (
    _coinciden_por_redondeo,
    _decimales,
    _mas_preciso,
    _preguntar,
    _resolver,
    _resolver_categoria,
    _resolver_fila,
    match_dfs,
)

# -- helpers ------------------------------------------------------------


def _sin_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: object, **kwargs: object) -> str:
        raise AssertionError("no deberia preguntar en consola")

    monkeypatch.setattr("builtins.input", _boom)


def _respuestas(monkeypatch: pytest.MonkeyPatch, respuestas: list[str]) -> list[str]:
    llamadas: list[str] = []
    it = iter(respuestas)

    def _input(prompt: str = "") -> str:
        llamadas.append(prompt)
        return next(it)

    monkeypatch.setattr("builtins.input", _input)
    return llamadas


def _xlsx_2013() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "generico": ["pan", "aceite"],
            "ponderador": ["2.5", "1.23456"],
            "encadenamiento": ["0.87654", "0.9"],
            "COG": ["panaderia", "aceites y grasas"],
            "CCIF division": ["alimentos", "alimentos"],
            "inflacion componente": ["subyacente", "subyacente"],
            "inflacion subcomponente": ["mercancias", "mercancias"],
            "inflacion agrupacion": ["alimentos bebidas y tabaco"] * 2,
            "canasta basica": ["-", "X"],
        }
    )


def _pdf_2013() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "generico": ["aceite", "pan"],
            "ponderador": ["1.2346", "2.5"],
            "encadenamiento": ["0.900", "0.8765"],
            "CCIF division": ["01 alimentos", "01 alimentos"],
            "CCIF grupo": ["01.1 aceites y grasas", "01.2 pan y cereales"],
            "CCIF clase": ["01.1.1 aceites comestibles", "01.2.1 pan de trigo"],
            "SCIAN sector": ["11 agricultura", "31 industrias manufactureras"],
            "SCIAN rama": ["1111 cultivo", "3118 panificacion"],
        }
    )


# -- _decimales -----------------------------------------------------------


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("1.23", 2),
        ("1", 0),
        ("1.230000", 6),
        ("-1.5", 1),
        ("0.9", 1),
    ],
)
def test_decimales(valor: str, esperado: int) -> None:
    assert _decimales(valor) == esperado


# -- _coinciden_por_redondeo -----------------------------------------------


@pytest.mark.parametrize(
    ("valor_xlsx", "valor_pdf", "esperado"),
    [
        ("1.23456", "1.2346", True),
        ("1.0", "2.0", False),
        ("1.20", "1.2", True),
        ("1.25", "1.24", False),
    ],
)
def test_coinciden_por_redondeo(valor_xlsx: str, valor_pdf: str, esperado: bool) -> None:
    assert _coinciden_por_redondeo(valor_xlsx, valor_pdf) == esperado


# -- _mas_preciso -----------------------------------------------------------


def test_mas_preciso_devuelve_el_de_mas_decimales() -> None:
    assert _mas_preciso("1.23456", "1.2346") == "1.23456"
    assert _mas_preciso("1.2", "1.234") == "1.234"


def test_mas_preciso_empate_prefiere_xlsx() -> None:
    assert _mas_preciso("1.20", "1.30") == "1.20"


# -- _preguntar ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("respuesta", "esperado"),
    [
        ("", "pdf"),
        ("pdf", "pdf"),
        ("xlsx", "xlsx"),
        ("x", "xlsx"),
        ("X", "xlsx"),
        ("algo random", "pdf"),
    ],
)
def test_preguntar_enter_o_no_reconocido_es_pdf(
    monkeypatch: pytest.MonkeyPatch, respuesta: str, esperado: str
) -> None:
    monkeypatch.setattr("builtins.input", lambda _="": respuesta)
    assert _preguntar("xlsx", "pdf") == esperado


def test_preguntar_muestra_ambos_valores_antes_de_preguntar(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # si se borra alguno de los 2 print() por accidente, quien responde
    # elegiria a ciegas -- esto blinda que ambos valores se muestren
    monkeypatch.setattr("builtins.input", lambda _="": "")
    _preguntar("valor de xlsx", "valor de pdf")
    salida = capsys.readouterr().out
    # linea completa con etiqueta -- no solo el valor suelto, para que un swap
    # de etiquetas (xlsx <-> pdf) no pase desapercibido
    assert "xlsx: valor de xlsx" in salida
    assert "pdf:  valor de pdf" in salida


def test_preguntar_imprime_la_eleccion_final_con_enter(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Enter (default = pdf) tambien debe confirmar que se eligio, no solo
    # cuando la respuesta es explicita -- sin esto, quien corre la tool no
    # sabe que quedo en el csv sin volver a mirar el archivo
    monkeypatch.setattr("builtins.input", lambda _="": "")
    _preguntar("valor de xlsx", "valor de pdf")
    assert "elegido: pdf" in capsys.readouterr().out


def test_preguntar_imprime_la_eleccion_final_explicita(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("builtins.input", lambda _="": "xlsx")
    _preguntar("valor de xlsx", "valor de pdf")
    assert "elegido: xlsx" in capsys.readouterr().out


# -- _resolver ----------------------------------------------------------------


def test_resolver_preferir_pdf_no_pregunta(monkeypatch: pytest.MonkeyPatch) -> None:
    _sin_prompt(monkeypatch)
    assert _resolver("valor_xlsx", "valor_pdf", "pdf") == "valor_pdf"


def test_resolver_preferir_csv_no_pregunta(monkeypatch: pytest.MonkeyPatch) -> None:
    _sin_prompt(monkeypatch)
    assert _resolver("valor_xlsx", "valor_pdf", "csv") == "valor_xlsx"


def test_resolver_sin_preferir_delega_a_preguntar(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _="": "xlsx")
    assert _resolver("valor_xlsx", "valor_pdf", None) == "valor_xlsx"


# -- _resolver_fila -----------------------------------------------------


def test_resolver_fila_valores_iguales_no_pregunta(monkeypatch: pytest.MonkeyPatch) -> None:
    _sin_prompt(monkeypatch)
    col_xlsx = pd.Series(["arroz", "frijol"])
    col_pdf = pd.Series(["arroz", "frijol"])
    resultado = _resolver_fila(col_xlsx, col_pdf, numerica=False, preferir=None)
    assert list(resultado) == ["arroz", "frijol"]


def test_resolver_fila_numerica_dentro_de_tolerancia_no_pregunta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _sin_prompt(monkeypatch)
    col_xlsx = pd.Series(["1.23456"])
    col_pdf = pd.Series(["1.2346"])
    resultado = _resolver_fila(col_xlsx, col_pdf, numerica=True, preferir=None)
    assert list(resultado) == ["1.23456"]  # se queda con el mas preciso, sin preguntar


def test_resolver_fila_numerica_fuera_de_tolerancia_pregunta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llamadas = _respuestas(monkeypatch, ["pdf"])
    col_xlsx = pd.Series(["1.0"])
    col_pdf = pd.Series(["2.0"])
    resultado = _resolver_fila(col_xlsx, col_pdf, numerica=True, preferir=None)
    assert list(resultado) == ["2.0"]
    assert len(llamadas) == 1


def test_resolver_fila_no_numerica_ignora_tolerancia(monkeypatch: pytest.MonkeyPatch) -> None:
    # generico no pasa por _coinciden_por_redondeo aunque los valores fueran numericos
    llamadas = _respuestas(monkeypatch, ["xlsx"])
    col_xlsx = pd.Series(["aceite"])
    col_pdf = pd.Series(["aceite comestible"])
    resultado = _resolver_fila(col_xlsx, col_pdf, numerica=False, preferir=None)
    assert list(resultado) == ["aceite"]
    assert len(llamadas) == 1


def test_resolver_fila_preferir_aplica_incluso_a_numerica_fuera_de_tolerancia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # --preferir no tiene excepcion para ponderador/encadenamiento (la doc vieja decia
    # que si, quedo confirmado obsoleto -- ver uso_generar_canasta.md)
    _sin_prompt(monkeypatch)
    col_xlsx = pd.Series(["1.0"])
    col_pdf = pd.Series(["2.0"])
    resultado = _resolver_fila(col_xlsx, col_pdf, numerica=True, preferir="csv")
    assert list(resultado) == ["1.0"]


def test_resolver_fila_preserva_indice_original() -> None:
    col_xlsx = pd.Series(["a", "b"], index=[5, 9])
    col_pdf = pd.Series(["a", "b"], index=[5, 9])
    resultado = _resolver_fila(col_xlsx, col_pdf, numerica=False, preferir=None)
    assert list(resultado.index) == [5, 9]


# -- _resolver_categoria -------------------------------------------------


def test_resolver_categoria_filas_iguales_no_preguntan(monkeypatch: pytest.MonkeyPatch) -> None:
    _sin_prompt(monkeypatch)
    col_xlsx = pd.Series(["alimentos", "alimentos"])
    col_pdf = pd.Series(["alimentos", "alimentos"])
    resultado = _resolver_categoria(col_xlsx, col_pdf, preferir=None, columna="COG")
    assert list(resultado) == ["alimentos", "alimentos"]


def test_resolver_categoria_pregunta_una_vez_por_par_no_por_fila(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llamadas = _respuestas(monkeypatch, ["", ""])
    col_xlsx = pd.Series(["ropa y calzado"] * 3 + ["otro"])
    col_pdf = pd.Series(["prendas de vestir y calzado"] * 3 + ["otro pdf"])
    resultado = _resolver_categoria(col_xlsx, col_pdf, preferir=None, columna="COG")
    assert len(llamadas) == 2  # 2 pares unicos, no 4 filas
    assert list(resultado) == ["prendas de vestir y calzado"] * 3 + ["otro pdf"]


def test_resolver_categoria_aplica_eleccion_distinta_por_par(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # pares ordenados alfabeticamente: ("a","b") antes que ("c","d")
    _respuestas(monkeypatch, ["xlsx", ""])
    col_xlsx = pd.Series(["a", "c"])
    col_pdf = pd.Series(["b", "d"])
    resultado = _resolver_categoria(col_xlsx, col_pdf, preferir=None, columna="COG")
    assert list(resultado) == ["a", "d"]


def test_resolver_categoria_preferir_csv_no_pregunta(monkeypatch: pytest.MonkeyPatch) -> None:
    _sin_prompt(monkeypatch)
    col_xlsx = pd.Series(["ropa y calzado"])
    col_pdf = pd.Series(["prendas de vestir y calzado"])
    resultado = _resolver_categoria(col_xlsx, col_pdf, preferir="csv", columna="COG")
    assert list(resultado) == ["ropa y calzado"]


def test_resolver_categoria_ccif_ignora_prefijo_numerico_al_comparar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # xlsx nunca trae el prefijo (extraccion_xlsx.py lo quita siempre), pdf
    # siempre si (extraccion_pdf.py lo conserva) -- esa diferencia sola NO es
    # una discrepancia real, no debe preguntar (bug real encontrado corriendo
    # la tool contra 2018: decenas de prompts espurios solo por el prefijo)
    _sin_prompt(monkeypatch)
    col_xlsx = pd.Series(["alimentos y bebidas no alcoholicas"] * 2)
    col_pdf = pd.Series(["01 alimentos y bebidas no alcoholicas"] * 2)
    resultado = _resolver_categoria(col_xlsx, col_pdf, preferir=None, columna="CCIF division")
    assert list(resultado) == ["01 alimentos y bebidas no alcoholicas"] * 2


def test_resolver_categoria_ccif_detecta_divergencia_real_de_nombre(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # caso real 2018: "ropa y calzado" (xlsx) vs "prendas de vestir y calzado"
    # (pdf, nombre CCIF oficial) -- divergen en el nombre, no solo el
    # prefijo, si debe preguntar
    llamadas = _respuestas(monkeypatch, [""])
    col_xlsx = pd.Series(["ropa y calzado"])
    col_pdf = pd.Series(["03 prendas de vestir y calzado"])
    resultado = _resolver_categoria(col_xlsx, col_pdf, preferir=None, columna="CCIF division")
    assert len(llamadas) == 1
    assert list(resultado) == ["03 prendas de vestir y calzado"]


def test_resolver_categoria_ccif_ignora_codigo_jerarquico_con_puntos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # CCIF grupo/clase traen codigo con puntos ("01.1", "01.1.1"), no solo
    # simple ("01") -- el stripper de comparacion debe pelar ambos niveles
    _sin_prompt(monkeypatch)
    col_xlsx = pd.Series(["aceites y grasas"])
    col_pdf = pd.Series(["01.1 aceites y grasas"])
    resultado = _resolver_categoria(col_xlsx, col_pdf, preferir=None, columna="CCIF grupo")
    assert list(resultado) == ["01.1 aceites y grasas"]


def test_resolver_categoria_imprime_genericos_afectados(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _respuestas(monkeypatch, [""])
    col_xlsx = pd.Series(["ropa y calzado"] * 3)
    col_pdf = pd.Series(["03 prendas de vestir y calzado"] * 3)
    _resolver_categoria(col_xlsx, col_pdf, preferir=None, columna="CCIF division")
    assert "afecta a 3 generico(s)" in capsys.readouterr().out


# -- match_dfs --------------------------------------------------------------


def test_match_dfs_columna_de_una_sola_fuente_se_copia_directo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # COG en 2013 solo viene de xlsx (FUENTES_POSIBLES) -- no debe comparar; valores
    # distintos por generico confirman que el mapeo sobrevive al ordenamiento interno
    # de match_dfs, no solo que la columna "se llena" con un valor cualquiera
    _sin_prompt(monkeypatch)
    resultado = match_dfs(_xlsx_2013(), _pdf_2013(), 2013, preferir="csv").set_index("generico")
    assert resultado.loc["pan", "COG"] == "panaderia"
    assert resultado.loc["aceite", "COG"] == "aceites y grasas"


def test_match_dfs_columna_solo_pdf_mantiene_mapeo_por_generico_tras_ordenar() -> None:
    # CCIF grupo/SCIAN rama en 2013 solo vienen de pdf; valores distintos por generico
    # confirman que match_dfs no desalinea el copiado tras su propio sort interno --
    # el contenido real extraido del pdf ya tiene sus tests en test_extraccion_pdf.py,
    # esto es sobre el mecanismo de copia de match_dfs, no sobre la extraccion
    resultado = match_dfs(_xlsx_2013(), _pdf_2013(), 2013, preferir="pdf").set_index("generico")
    assert resultado.loc["aceite", "CCIF grupo"] == "01.1 aceites y grasas"
    assert resultado.loc["pan", "CCIF grupo"] == "01.2 pan y cereales"
    assert resultado.loc["aceite", "SCIAN rama"] == "1111 cultivo"
    assert resultado.loc["pan", "SCIAN rama"] == "3118 panificacion"


def test_match_dfs_columna_sin_ninguna_fuente_queda_vacia() -> None:
    # canasta consumo minimo: frozenset() en 2013
    resultado = match_dfs(_xlsx_2013(), _pdf_2013(), 2013, preferir="pdf")
    assert (resultado["canasta consumo minimo"] == "").all()


def test_match_dfs_columna_solo_sync_no_participa_del_cruce_xlsx_pdf() -> None:
    # SCIAN sector en 2010 es frozenset({"sync"}) -- no xlsx ni pdf, match_dfs la deja vacia
    df_xlsx = pd.DataFrame(
        {
            "generico": ["arroz"],
            "ponderador": ["1.0"],
            "COG": ["alimentos"],
            "inflacion componente": ["subyacente"],
            "inflacion subcomponente": ["mercancias"],
            "inflacion agrupacion": ["alimentos bebidas y tabaco"],
            "canasta basica": ["X"],
        }
    )
    df_pdf = pd.DataFrame(
        {
            "generico": ["arroz"],
            "ponderador": ["1.0"],
            "COG": ["alimentos"],
            "CCIF division": ["01 alimentos"],
            "CCIF grupo": ["01.1 x"],
            "CCIF clase": ["01.1.1 x"],
        }
    )
    resultado = match_dfs(df_xlsx, df_pdf, 2010, preferir="pdf")
    assert (resultado["SCIAN sector"] == "").all()


def test_match_dfs_columnas_en_orden_de_columnas_base() -> None:
    resultado = match_dfs(_xlsx_2013(), _pdf_2013(), 2013, preferir="pdf")
    assert list(resultado.columns) == list(COLUMNAS_BASE)


def test_match_dfs_alinea_por_generico_sin_importar_orden_de_entrada() -> None:
    # df_xlsx entra con "pan" primero, df_pdf con "aceite" primero
    resultado = match_dfs(_xlsx_2013(), _pdf_2013(), 2013, preferir="pdf")
    assert list(resultado["generico"]) == ["aceite", "pan"]


def test_match_dfs_preferir_pdf_repone_prefijo_de_ccif_division() -> None:
    resultado = match_dfs(_xlsx_2013(), _pdf_2013(), 2013, preferir="pdf")
    fila_aceite = resultado.loc[resultado["generico"] == "aceite"]
    assert fila_aceite["CCIF division"].iloc[0] == "01 alimentos"


def test_match_dfs_sin_preferir_no_pregunta_si_ccif_solo_difiere_en_prefijo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # CCIF division de las fixtures difiere solo en el prefijo numerico
    # ("alimentos" xlsx vs "01 alimentos" pdf) -- eso no es una discrepancia
    # real (ver _resolver_categoria), cero preguntas; el resto de columnas
    # cruzadas coincide exacto o dentro de tolerancia de redondeo
    _sin_prompt(monkeypatch)
    resultado = match_dfs(_xlsx_2013(), _pdf_2013(), 2013, preferir=None)
    assert list(resultado["CCIF division"]) == ["01 alimentos", "01 alimentos"]


def test_match_dfs_sin_preferir_pregunta_divergencia_real_de_nombre_ccif(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # a diferencia del test de arriba, acá el nombre real difiere (no solo el
    # prefijo) -- caso real 2018 "ropa y calzado" vs "prendas de vestir y calzado"
    llamadas = _respuestas(monkeypatch, [""])
    df_xlsx = _xlsx_2013()
    df_xlsx["CCIF division"] = ["ropa y calzado", "ropa y calzado"]
    df_pdf = _pdf_2013()
    df_pdf["CCIF division"] = ["03 prendas de vestir y calzado"] * 2

    resultado = match_dfs(df_xlsx, df_pdf, 2013, preferir=None)
    assert len(llamadas) == 1
    assert list(resultado["CCIF division"]) == ["03 prendas de vestir y calzado"] * 2
