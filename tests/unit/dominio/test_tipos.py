from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from replica_inpc.dominio.errores import InvarianteViolado
from replica_inpc.dominio.periodos import PeriodoQuincenal
from replica_inpc.dominio.tipos import (
    COLUMNAS_CLASIFICACION,
    INDICES_VALIDABLES,
    RANGOS_CANASTAS,
    TIPO_INPC,
    ManifestCalculo,
    ManifestDerivado,
)

# -- TIPO_INPC --


def test_tipo_inpc_es_inpc_mayuscula() -> None:
    assert TIPO_INPC == "INPC"


# -- COLUMNAS_CLASIFICACION --


def test_columnas_clasificacion_contenido_exacto() -> None:
    assert COLUMNAS_CLASIFICACION == {
        "COG",
        "CCIF DIVISION",
        "CCIF GRUPO",
        "CCIF CLASE",
        "INFLACION COMPONENTE",
        "INFLACION SUBCOMPONENTE",
        "INFLACION AGRUPACION",
        "SCIAN SECTOR",
        "SCIAN RAMA",
        "DURABILIDAD",
        "CANASTA BASICA",
        "CANASTA CONSUMO MINIMO",
    }


# -- INDICES_VALIDABLES --


def test_indices_validables_contenido_exacto() -> None:
    assert INDICES_VALIDABLES == {TIPO_INPC, "INFLACION COMPONENTE", "INFLACION SUBCOMPONENTE"}


def test_indices_validables_es_subconjunto_de_tipos_reconocidos() -> None:
    tipos_reconocidos = {TIPO_INPC} | COLUMNAS_CLASIFICACION
    assert INDICES_VALIDABLES <= tipos_reconocidos


# -- RANGOS_CANASTAS --


def test_rangos_canastas_cubre_las_4_versiones() -> None:
    assert set(RANGOS_CANASTAS) == {2010, 2013, 2018, 2024}


def test_rangos_canastas_limites_exactos() -> None:
    assert RANGOS_CANASTAS[2010] == (
        PeriodoQuincenal(2010, 12, 2),
        PeriodoQuincenal(2013, 3, 2),
    )
    assert RANGOS_CANASTAS[2013] == (
        PeriodoQuincenal(2013, 3, 2),
        PeriodoQuincenal(2018, 7, 2),
    )
    assert RANGOS_CANASTAS[2018] == (
        PeriodoQuincenal(2018, 7, 2),
        PeriodoQuincenal(2024, 7, 2),
    )
    assert RANGOS_CANASTAS[2024] == (PeriodoQuincenal(2024, 7, 2), None)


def test_rangos_canastas_juntas_son_continuas() -> None:
    assert RANGOS_CANASTAS[2010][1] == RANGOS_CANASTAS[2013][0]
    assert RANGOS_CANASTAS[2013][1] == RANGOS_CANASTAS[2018][0]
    assert RANGOS_CANASTAS[2018][1] == RANGOS_CANASTAS[2024][0]


def test_rangos_canastas_ultima_version_sin_fin() -> None:
    assert RANGOS_CANASTAS[2024][1] is None


# -- ManifestCalculo --


def test_manifest_calculo_construccion_valida() -> None:
    m = ManifestCalculo(
        version=2018,
        tipo="INPC",
        calculador="LaspeyresDirecto",
        ruta_canasta=Path("/tmp/c.csv"),
        ruta_series=Path("/tmp/s.csv"),
        fecha=datetime(2024, 1, 1),
    )
    assert m.version == 2018


def test_manifest_calculo_rutas_y_fecha_por_defecto() -> None:
    antes = datetime.now()
    m = ManifestCalculo(version=2018, tipo="INPC", calculador="LaspeyresDirecto")
    despues = datetime.now()
    assert m.ruta_canasta is None
    assert m.ruta_series is None
    assert antes <= m.fecha <= despues


# -- ManifestDerivado --


def test_manifest_derivado_clase_vacia_falla() -> None:
    with pytest.raises(InvarianteViolado):
        ManifestDerivado(
            versiones=[2018],
            tipo="INPC",
            clase="",
            descripcion="",
            fecha=datetime(2024, 1, 1),
        )


def test_manifest_derivado_fecha_por_defecto() -> None:
    antes = datetime.now()
    m = ManifestDerivado(versiones=[2018], tipo="INPC", clase="periodica_mensual", descripcion="")
    despues = datetime.now()
    assert antes <= m.fecha <= despues
