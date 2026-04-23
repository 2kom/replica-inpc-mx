from __future__ import annotations

import calendar
import functools

import pandas as pd

from replica_inpc.dominio.errores import PeriodoNoInterpretable

_MESES: dict[str, int] = {
    "Ene": 1,
    "Feb": 2,
    "Mar": 3,
    "Abr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Ago": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dic": 12,
}

_MESES_INV: dict[int, str] = {v: k for k, v in _MESES.items()}


def _ultimo_dia(año: int, mes: int) -> int:
    return calendar.monthrange(año, mes)[1]


def _validar_año_mes(año: int, mes: int) -> None:
    if mes not in _MESES_INV:
        raise ValueError(f"mes debe estar entre 1 y 12, se recibio {mes}")
    if año <= 0:
        raise ValueError(f"año debe ser un entero positivo, se recibio {año}")


@functools.total_ordering
class PeriodoQuincenal:
    """Representa un periodo quincenal del dominio.

    Un periodo se modela como el triplete `(año, mes, quincena)`. Su orden
    natural es cronológico, se puede usar como clave hashable y su
    serialización canónica es `"1Q Ene 2024"`.

    Args:
        año: Año calendario del periodo. Debe ser un entero positivo.
        mes: Mes calendario del periodo. Debe estar entre 1 y 12.
        quincena: Quincena del mes. Solo se permiten los valores 1 y 2.

    Raises:
        ValueError: Si `año` no es positivo, `mes` no está entre 1 y 12
            o `quincena` no es 1 ni 2.

    Ver: docs/diseño.md §5.3, §11.6
    """

    def __init__(self, año: int, mes: int, quincena: int) -> None:
        if quincena not in (1, 2):
            raise ValueError(f"quincena debe ser 1 o 2, se recibio {quincena}")
        _validar_año_mes(año, mes)
        self.año = año
        self.mes = mes
        self.quincena = quincena

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PeriodoQuincenal):
            return NotImplemented
        return (self.año, self.mes, self.quincena) == (
            other.año,
            other.mes,
            other.quincena,
        )

    def __lt__(self, other: PeriodoQuincenal) -> bool:
        if not isinstance(other, PeriodoQuincenal):
            return NotImplemented
        return (self.año, self.mes, self.quincena) < (
            other.año,
            other.mes,
            other.quincena,
        )

    def __hash__(self) -> int:
        return hash((self.año, self.mes, self.quincena))

    def __str__(self) -> str:
        return f"{self.quincena}Q {_MESES_INV[self.mes]} {self.año}"

    def __repr__(self) -> str:
        return f"PeriodoQuincenal({self.año}, {self.mes}, {self.quincena})"

    @classmethod
    def desde_str(cls, periodo_str: str) -> PeriodoQuincenal:
        """Construye un `PeriodoQuincenal` desde su representación textual canónica.

        Args:
            periodo_str: Texto en formato `"1Q Mes AAAA"`, por ejemplo
                `"2Q Jul 2024"`.

        Returns:
            El periodo interpretado desde `periodo_str`.

        Raises:
            PeriodoNoInterpretable: Si el texto no corresponde a un periodo
                válido o usa un mes fuera del catálogo esperado.

        Ver: docs/diseño.md §5.3
        """
        try:
            quincena_str, mes_str, año_str = periodo_str.split(" ")
            quincena = int(quincena_str[0])
            mes = _MESES[mes_str]
            año = int(año_str)
            return cls(año, mes, quincena)
        except Exception as e:
            raise PeriodoNoInterpretable(
                f"Formato de periodo inválido: '{periodo_str}'. Se esperaba formato '1Q Mes AAAA' o '2Q Mes AAAA'"
            ) from e

    def to_timestamp(self) -> pd.Timestamp:
        """Convierte el periodo a `pd.Timestamp` usando la convención "último día del periodo".

        Returns:
            Día 15 para `1Q`; último día del mes para `2Q`.

        Ver: docs/diseño.md §5.3, §11.6
        """
        dia = 15 if self.quincena == 1 else _ultimo_dia(self.año, self.mes)
        return pd.Timestamp(year=self.año, month=self.mes, day=dia)


@functools.total_ordering
class PeriodoMensual:
    """Representa un periodo mensual del dominio.

    Args:
        año: Año calendario. Debe ser entero positivo.
        mes: Mes calendario. Debe estar entre 1 y 12.

    Raises:
        ValueError: Si `año` no es positivo o `mes` no está entre 1 y 12.

    Ver: docs/diseño.md §5.3
    """

    def __init__(self, año: int, mes: int) -> None:
        _validar_año_mes(año, mes)
        self.año = año
        self.mes = mes

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PeriodoMensual):
            return NotImplemented
        return (self.año, self.mes) == (other.año, other.mes)

    def __lt__(self, other: PeriodoMensual) -> bool:
        if not isinstance(other, PeriodoMensual):
            return NotImplemented
        return (self.año, self.mes) < (other.año, other.mes)

    def __hash__(self) -> int:
        return hash((self.año, self.mes))

    def __str__(self) -> str:
        return f"{_MESES_INV[self.mes]} {self.año}"

    def __repr__(self) -> str:
        return f"PeriodoMensual({self.año}, {self.mes})"

    @classmethod
    def desde_str(cls, periodo_str: str) -> PeriodoMensual:
        """Construye un `PeriodoMensual` desde su representación textual canónica.

        Args:
            periodo_str: Texto en formato `"Mes AAAA"`, por ejemplo `"Jul 2024"`.

        Raises:
            PeriodoNoInterpretable: Si el texto no corresponde a un periodo válido.
        """
        try:
            mes_str, año_str = periodo_str.split(" ")
            mes = _MESES[mes_str]
            año = int(año_str)
            return cls(año, mes)
        except Exception as e:
            raise PeriodoNoInterpretable(
                f"Formato de periodo mensual inválido: '{periodo_str}'. Se esperaba formato 'Mes AAAA'"
            ) from e

    def to_timestamp(self) -> pd.Timestamp:
        """Convierte el periodo a `pd.Timestamp` usando el último día del mes.

        Ver: docs/diseño.md §5.3
        """
        return pd.Timestamp(year=self.año, month=self.mes, day=_ultimo_dia(self.año, self.mes))


def periodo_desde_str(texto: str) -> PeriodoQuincenal | PeriodoMensual:
    """Detecta el tipo de periodo a partir del texto y lo construye.

    - ``"1Q Ene 2024"`` -> `PeriodoQuincenal`
    - ``"Ene 2024"`` -> `PeriodoMensual`

    Raises:
        PeriodoNoInterpretable: Si el texto no corresponde a ningún formato reconocido.

    Ver: docs/diseño.md §5.3
    """
    partes = texto.split(" ")
    if len(partes) == 3:
        return PeriodoQuincenal.desde_str(texto)
    if len(partes) == 2:
        return PeriodoMensual.desde_str(texto)
    raise PeriodoNoInterpretable(
        f"Formato de periodo no reconocido: '{texto}'. "
        "Se esperaba '1Q Mes AAAA' (quincenal) o 'Mes AAAA' (mensual)."
    )
