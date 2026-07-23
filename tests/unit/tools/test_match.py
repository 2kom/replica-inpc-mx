from __future__ import annotations

import pandas as pd
import pytest
from canasta_inpc.esquema import COLUMNAS_BASE
from canasta_inpc.match import (
    Resolucion,
    _coinciden_por_redondeo,
    _decimales,
    _mas_preciso,
    _preguntar,
    _reconstruir_hibrido_ccif,
    _resolver,
    _resolver_categoria,
    _resolver_directo,
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
        ("1E-5", 5),
        ("1.5e-3", 4),
    ],
)
def test_decimales(valor: str, esperado: int) -> None:
    assert _decimales(valor) == esperado


def test_decimales_notacion_cientifica_no_se_confunde_con_menos_precision() -> None:
    # antes de usar Decimal, "1E-5" (5 decimales reales) contaba 0 por no
    # tener "." -- _mas_preciso hubiera preferido "0.0000" (4 decimales) y
    # convertido 0.00001 en 0.0000, perdiendo el dato real
    assert _mas_preciso("1E-5", "0.0000") == ("1E-5", "xlsx")


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
    assert _mas_preciso("1.23456", "1.2346") == ("1.23456", "xlsx")
    assert _mas_preciso("1.2", "1.234") == ("1.234", "pdf")


def test_mas_preciso_empate_prefiere_xlsx() -> None:
    assert _mas_preciso("1.20", "1.30") == ("1.20", "xlsx")


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
    assert _resolver("valor_xlsx", "valor_pdf", "pdf") == "pdf"


def test_resolver_preferir_xlsx_no_pregunta(monkeypatch: pytest.MonkeyPatch) -> None:
    _sin_prompt(monkeypatch)
    assert _resolver("valor_xlsx", "valor_pdf", "xlsx") == "xlsx"


def test_resolver_sin_preferir_delega_a_preguntar(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _="": "xlsx")
    assert _resolver("valor_xlsx", "valor_pdf", None) == "xlsx"


# -- _reconstruir_hibrido_ccif --------------------------------------------------------


def test_hibrido_ccif_repone_codigo_de_pdf_sobre_nombre_de_xlsx() -> None:
    # sin esto, "03 prendas de vestir y calzado" perderia el "03" al ganar
    # el nombre del xlsx ("ropa y calzado", que nunca trae codigo)
    assert _reconstruir_hibrido_ccif("ropa y calzado", "03 prendas de vestir y calzado") == (
        "03 ropa y calzado",
        "mixto",
    )


def test_hibrido_ccif_codigo_jerarquico_con_puntos() -> None:
    assert _reconstruir_hibrido_ccif("aceites y grasas", "01.1 aceites comestibles") == (
        "01.1 aceites y grasas",
        "mixto",
    )


def test_hibrido_ccif_sin_codigo_en_pdf_se_queda_con_xlsx_tal_cual() -> None:
    # no deberia pasar dado el contrato de extraccion, pero si el pdf no
    # trae codigo no hay nada que reponer -- no se fabrica un origen mixto
    assert _reconstruir_hibrido_ccif("ropa y calzado", "prendas de vestir y calzado") == (
        "ropa y calzado",
        "xlsx",
    )


def test_hibrido_ccif_xlsx_vacio_no_fabrica_codigo_suelto() -> None:
    # xlsx no clasifico este generico -- "01 " (codigo sin nombre) seria
    # basura; debe quedar vacio tal cual, para caer en sin_clasificar
    assert _reconstruir_hibrido_ccif("", "01 alimentos") == ("", "xlsx")


# -- _resolver_fila -----------------------------------------------------


def test_resolver_fila_valores_iguales_no_pregunta(monkeypatch: pytest.MonkeyPatch) -> None:
    _sin_prompt(monkeypatch)
    col_xlsx = pd.Series(["arroz", "frijol"])
    col_pdf = pd.Series(["arroz", "frijol"])
    genericos = pd.Series(["arroz", "frijol"])
    valores, resoluciones = _resolver_fila(
        col_xlsx, col_pdf, genericos, "generico", numerica=False, preferir=None
    )
    assert list(valores) == ["arroz", "frijol"]
    assert [r.metodo for r in resoluciones] == ["igual", "igual"]
    assert [r.origen for r in resoluciones] == ["ambas", "ambas"]
    assert [r.genericos for r in resoluciones] == [("arroz",), ("frijol",)]


def test_resolver_fila_numerica_dentro_de_tolerancia_no_pregunta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _sin_prompt(monkeypatch)
    col_xlsx = pd.Series(["1.23456"])
    col_pdf = pd.Series(["1.2346"])
    genericos = pd.Series(["aceite"])
    valores, resoluciones = _resolver_fila(
        col_xlsx, col_pdf, genericos, "ponderador", numerica=True, preferir=None
    )
    assert list(valores) == ["1.23456"]  # se queda con el mas preciso, sin preguntar
    assert resoluciones[0].metodo == "redondeo"
    assert resoluciones[0].origen == "xlsx"


def test_resolver_fila_numerica_fuera_de_tolerancia_pregunta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llamadas = _respuestas(monkeypatch, ["pdf"])
    col_xlsx = pd.Series(["1.0"])
    col_pdf = pd.Series(["2.0"])
    genericos = pd.Series(["aceite"])
    valores, resoluciones = _resolver_fila(
        col_xlsx, col_pdf, genericos, "ponderador", numerica=True, preferir=None
    )
    assert list(valores) == ["2.0"]
    assert len(llamadas) == 1
    assert resoluciones[0].metodo == "interactiva"
    assert resoluciones[0].origen == "pdf"


def test_resolver_fila_no_numerica_ignora_tolerancia(monkeypatch: pytest.MonkeyPatch) -> None:
    # generico no pasa por _coinciden_por_redondeo aunque los valores fueran numericos
    llamadas = _respuestas(monkeypatch, ["xlsx"])
    col_xlsx = pd.Series(["aceite"])
    col_pdf = pd.Series(["aceite comestible"])
    genericos = pd.Series(["aceite"])
    valores, resoluciones = _resolver_fila(
        col_xlsx, col_pdf, genericos, "generico", numerica=False, preferir=None
    )
    assert list(valores) == ["aceite"]
    assert len(llamadas) == 1
    assert resoluciones[0].origen == "xlsx"


def test_resolver_fila_preferir_aplica_incluso_a_numerica_fuera_de_tolerancia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # --preferir no tiene excepcion para ponderador/encadenamiento (la doc vieja decia
    # que si, quedo confirmado obsoleto -- ver uso_generar_canasta.md)
    _sin_prompt(monkeypatch)
    col_xlsx = pd.Series(["1.0"])
    col_pdf = pd.Series(["2.0"])
    genericos = pd.Series(["aceite"])
    valores, resoluciones = _resolver_fila(
        col_xlsx, col_pdf, genericos, "ponderador", numerica=True, preferir="xlsx"
    )
    assert list(valores) == ["1.0"]
    assert resoluciones[0].metodo == "preferido"
    assert resoluciones[0].origen == "xlsx"


def test_resolver_fila_preserva_indice_original() -> None:
    col_xlsx = pd.Series(["a", "b"], index=[5, 9])
    col_pdf = pd.Series(["a", "b"], index=[5, 9])
    genericos = pd.Series(["a", "b"], index=[5, 9])
    valores, _ = _resolver_fila(
        col_xlsx, col_pdf, genericos, "generico", numerica=False, preferir=None
    )
    assert list(valores.index) == [5, 9]


# -- _resolver_categoria -------------------------------------------------


def test_resolver_categoria_filas_iguales_no_preguntan(monkeypatch: pytest.MonkeyPatch) -> None:
    _sin_prompt(monkeypatch)
    col_xlsx = pd.Series(["alimentos", "alimentos"])
    col_pdf = pd.Series(["alimentos", "alimentos"])
    genericos = pd.Series(["arroz", "frijol"])
    valores, resoluciones = _resolver_categoria(
        col_xlsx, col_pdf, genericos, preferir=None, columna="COG"
    )
    assert list(valores) == ["alimentos", "alimentos"]
    assert len(resoluciones) == 1  # un solo par unico, agrupa los 2 genericos
    assert resoluciones[0].metodo == "igual"
    assert resoluciones[0].origen == "ambas"
    assert resoluciones[0].genericos == ("arroz", "frijol")


def test_resolver_categoria_pregunta_una_vez_por_par_no_por_fila(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llamadas = _respuestas(monkeypatch, ["", ""])
    col_xlsx = pd.Series(["ropa y calzado"] * 3 + ["otro"])
    col_pdf = pd.Series(["prendas de vestir y calzado"] * 3 + ["otro pdf"])
    genericos = pd.Series(["g0", "g1", "g2", "g3"])
    valores, resoluciones = _resolver_categoria(
        col_xlsx, col_pdf, genericos, preferir=None, columna="COG"
    )
    assert len(llamadas) == 2  # 2 pares unicos, no 4 filas
    assert list(valores) == ["prendas de vestir y calzado"] * 3 + ["otro pdf"]
    assert len(resoluciones) == 2


def test_resolver_categoria_aplica_eleccion_distinta_por_par(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # pares ordenados alfabeticamente: ("a","b") antes que ("c","d")
    _respuestas(monkeypatch, ["xlsx", ""])
    col_xlsx = pd.Series(["a", "c"])
    col_pdf = pd.Series(["b", "d"])
    genericos = pd.Series(["g0", "g1"])
    valores, _ = _resolver_categoria(col_xlsx, col_pdf, genericos, preferir=None, columna="COG")
    assert list(valores) == ["a", "d"]


def test_resolver_categoria_preferir_xlsx_no_pregunta(monkeypatch: pytest.MonkeyPatch) -> None:
    _sin_prompt(monkeypatch)
    col_xlsx = pd.Series(["ropa y calzado"])
    col_pdf = pd.Series(["prendas de vestir y calzado"])
    genericos = pd.Series(["abrigo"])
    valores, resoluciones = _resolver_categoria(
        col_xlsx, col_pdf, genericos, preferir="xlsx", columna="COG"
    )
    assert list(valores) == ["ropa y calzado"]
    assert resoluciones[0].metodo == "preferido"
    assert resoluciones[0].origen == "xlsx"


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
    genericos = pd.Series(["g0", "g1"])
    valores, resoluciones = _resolver_categoria(
        col_xlsx, col_pdf, genericos, preferir=None, columna="CCIF division"
    )
    assert list(valores) == ["01 alimentos y bebidas no alcoholicas"] * 2
    # coincide solo por clave normalizada (sin prefijo), no literal -- el
    # codigo solo vino de pdf, origen no es "ambas"
    assert resoluciones[0].metodo == "igual"
    assert resoluciones[0].origen == "pdf"


def test_resolver_categoria_ccif_detecta_divergencia_real_de_nombre(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # caso real 2018: "ropa y calzado" (xlsx) vs "prendas de vestir y calzado"
    # (pdf, nombre CCIF oficial) -- divergen en el nombre, no solo el
    # prefijo, si debe preguntar
    llamadas = _respuestas(monkeypatch, [""])
    col_xlsx = pd.Series(["ropa y calzado"])
    col_pdf = pd.Series(["03 prendas de vestir y calzado"])
    genericos = pd.Series(["abrigo"])
    valores, resoluciones = _resolver_categoria(
        col_xlsx, col_pdf, genericos, preferir=None, columna="CCIF division"
    )
    assert len(llamadas) == 1
    assert list(valores) == ["03 prendas de vestir y calzado"]
    assert resoluciones[0].origen == "pdf"  # gano pdf, ya trae su propio codigo coherente


def test_resolver_categoria_ccif_discrepancia_real_hacia_xlsx_repone_codigo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # gana el nombre del xlsx -- sin el hibrido, "03" se perderia
    _respuestas(monkeypatch, ["xlsx"])
    col_xlsx = pd.Series(["ropa y calzado"])
    col_pdf = pd.Series(["03 prendas de vestir y calzado"])
    genericos = pd.Series(["abrigo"])
    valores, resoluciones = _resolver_categoria(
        col_xlsx, col_pdf, genericos, preferir=None, columna="CCIF division"
    )
    assert list(valores) == ["03 ropa y calzado"]
    assert resoluciones[0].origen == "mixto"
    assert resoluciones[0].metodo == "interactiva"


def test_resolver_categoria_ccif_xlsx_vacio_no_genera_codigo_suelto() -> None:
    # xlsx no clasifico este generico ("") y gana via --preferir xlsx -- sin
    # el guard en _reconstruir_hibrido_ccif esto daba "01 " (codigo sin
    # nombre); debe quedar vacio y conservar la decision (fix conserva
    # eventos reales aunque resuelvan a vacio)
    col_xlsx = pd.Series([""])
    col_pdf = pd.Series(["01 alimentos"])
    genericos = pd.Series(["arroz"])
    valores, resoluciones = _resolver_categoria(
        col_xlsx, col_pdf, genericos, preferir="xlsx", columna="CCIF division"
    )
    assert list(valores) == [""]
    assert len(resoluciones) == 1
    assert resoluciones[0].valor_final == ""
    assert resoluciones[0].origen == "xlsx"


def test_resolver_categoria_ccif_ignora_codigo_jerarquico_con_puntos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # CCIF grupo/clase traen codigo con puntos ("01.1", "01.1.1"), no solo
    # simple ("01") -- el stripper de comparacion debe pelar ambos niveles
    _sin_prompt(monkeypatch)
    col_xlsx = pd.Series(["aceites y grasas"])
    col_pdf = pd.Series(["01.1 aceites y grasas"])
    genericos = pd.Series(["aceite"])
    valores, _ = _resolver_categoria(
        col_xlsx, col_pdf, genericos, preferir=None, columna="CCIF grupo"
    )
    assert list(valores) == ["01.1 aceites y grasas"]


def test_resolver_categoria_imprime_genericos_afectados(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _respuestas(monkeypatch, [""])
    col_xlsx = pd.Series(["ropa y calzado"] * 3)
    col_pdf = pd.Series(["03 prendas de vestir y calzado"] * 3)
    genericos = pd.Series(["g0", "g1", "g2"])
    _resolver_categoria(col_xlsx, col_pdf, genericos, preferir=None, columna="CCIF division")
    assert "afecta a 3 generico(s)" in capsys.readouterr().out


def test_resolver_categoria_omite_resolucion_si_valor_final_vacio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ambas fuentes sin clasificar ese generico -- no es una resolucion real
    _sin_prompt(monkeypatch)
    col_xlsx = pd.Series([""])
    col_pdf = pd.Series([""])
    genericos = pd.Series(["arroz"])
    valores, resoluciones = _resolver_categoria(
        col_xlsx, col_pdf, genericos, preferir=None, columna="COG"
    )
    assert list(valores) == [""]
    assert resoluciones == ()


def test_resolver_categoria_conserva_decision_real_que_resulta_en_vacio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # xlsx sin clasificar, pdf si -- SI es una decision real (clave difiere:
    # "" != "alimentos"), aunque --preferir xlsx la resuelva hacia vacio; a
    # diferencia del caso arriba (ambas vacias, sin decision), esta si debe
    # quedar en el registro
    col_xlsx = pd.Series([""])
    col_pdf = pd.Series(["alimentos"])
    genericos = pd.Series(["arroz"])
    valores, resoluciones = _resolver_categoria(
        col_xlsx, col_pdf, genericos, preferir="xlsx", columna="COG"
    )
    assert list(valores) == [""]
    assert len(resoluciones) == 1
    assert resoluciones[0].valor_final == ""
    assert resoluciones[0].metodo == "preferido"
    assert resoluciones[0].origen == "xlsx"


# -- match_dfs --------------------------------------------------------------


def test_match_dfs_columna_de_una_sola_fuente_se_copia_directo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # COG en 2013 solo viene de xlsx (FUENTES_POSIBLES) -- no debe comparar; valores
    # distintos por generico confirman que el mapeo sobrevive al ordenamiento interno
    # de match_dfs, no solo que la columna "se llena" con un valor cualquiera
    _sin_prompt(monkeypatch)
    resultado = match_dfs(_xlsx_2013(), _pdf_2013(), 2013, preferir="xlsx")
    df = resultado.df.set_index("generico")
    assert df.loc["pan", "COG"] == "panaderia"
    assert df.loc["aceite", "COG"] == "aceites y grasas"


def test_match_dfs_columna_de_una_sola_fuente_produce_resolucion_directo() -> None:
    resultado = match_dfs(_xlsx_2013(), _pdf_2013(), 2013, preferir="pdf")
    eventos_cog = [r for r in resultado.resoluciones if r.columna == "COG"]
    assert eventos_cog
    assert all(r.metodo == "directo" and r.origen == "xlsx" for r in eventos_cog)
    assert set(g for r in eventos_cog for g in r.genericos) == {"pan", "aceite"}


def test_resolver_directo_fila_no_omite_valores_vacios() -> None:
    # regresion: un vacio omitido aqui deja sin metadata a ese generico en
    # _construir_detalle_genericos_pdf -- mismo patron de bug que tiene_enc
    # via FUENTES_POSIBLES vs columna vacia, pero a nivel de una fila puntual
    col = pd.Series(["1.01", ""])
    genericos = pd.Series(["arroz", "frijol"])
    resoluciones = _resolver_directo(col, genericos, "encadenamiento", "xlsx")
    assert len(resoluciones) == 2
    assert {r.genericos[0] for r in resoluciones} == {"arroz", "frijol"}
    vacio = next(r for r in resoluciones if r.genericos == ("frijol",))
    assert vacio.valor_final == ""
    assert vacio.metodo == "directo"


def test_resolver_directo_categoria_omite_valores_vacios() -> None:
    col = pd.Series(["alimentos", ""])
    genericos = pd.Series(["arroz", "frijol"])
    resoluciones = _resolver_directo(col, genericos, "COG", "xlsx")
    assert len(resoluciones) == 1
    assert resoluciones[0].valor_final == "alimentos"


def test_match_dfs_columna_solo_pdf_mantiene_mapeo_por_generico_tras_ordenar() -> None:
    # CCIF grupo/SCIAN rama en 2013 solo vienen de pdf; valores distintos por generico
    # confirman que match_dfs no desalinea el copiado tras su propio sort interno --
    # el contenido real extraido del pdf ya tiene sus tests en test_extraccion_pdf.py,
    # esto es sobre el mecanismo de copia de match_dfs, no sobre la extraccion
    df = match_dfs(_xlsx_2013(), _pdf_2013(), 2013, preferir="pdf").df.set_index("generico")
    assert df.loc["aceite", "CCIF grupo"] == "01.1 aceites y grasas"
    assert df.loc["pan", "CCIF grupo"] == "01.2 pan y cereales"
    assert df.loc["aceite", "SCIAN rama"] == "1111 cultivo"
    assert df.loc["pan", "SCIAN rama"] == "3118 panificacion"


def test_match_dfs_columna_sin_ninguna_fuente_queda_vacia() -> None:
    # canasta consumo minimo: frozenset() en 2013
    resultado = match_dfs(_xlsx_2013(), _pdf_2013(), 2013, preferir="pdf")
    assert (resultado.df["canasta consumo minimo"] == "").all()
    assert not any(r.columna == "canasta consumo minimo" for r in resultado.resoluciones)


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
    assert (resultado.df["SCIAN sector"] == "").all()


def test_match_dfs_columnas_en_orden_de_columnas_base() -> None:
    resultado = match_dfs(_xlsx_2013(), _pdf_2013(), 2013, preferir="pdf")
    assert list(resultado.df.columns) == list(COLUMNAS_BASE)


def test_match_dfs_alinea_por_generico_sin_importar_orden_de_entrada() -> None:
    # df_xlsx entra con "pan" primero, df_pdf con "aceite" primero
    resultado = match_dfs(_xlsx_2013(), _pdf_2013(), 2013, preferir="pdf")
    assert list(resultado.df["generico"]) == ["aceite", "pan"]


def test_match_dfs_preferir_pdf_repone_prefijo_de_ccif_division() -> None:
    df = match_dfs(_xlsx_2013(), _pdf_2013(), 2013, preferir="pdf").df
    fila_aceite = df.loc[df["generico"] == "aceite"]
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
    assert list(resultado.df["CCIF division"]) == ["01 alimentos", "01 alimentos"]


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
    assert list(resultado.df["CCIF division"]) == ["03 prendas de vestir y calzado"] * 2


def test_match_dfs_resoluciones_ponderador_una_por_generico() -> None:
    resultado = match_dfs(_xlsx_2013(), _pdf_2013(), 2013, preferir="pdf")
    eventos = [r for r in resultado.resoluciones if r.columna == "ponderador"]
    assert {r.genericos for r in eventos} == {("pan",), ("aceite",)}


def test_match_dfs_resoluciones_es_instancia_de_resolucion() -> None:
    resultado = match_dfs(_xlsx_2013(), _pdf_2013(), 2013, preferir="pdf")
    assert all(isinstance(r, Resolucion) for r in resultado.resoluciones)
