from __future__ import annotations

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
            raise ValueError(f"quincena debe ser 1 o 2, se recibió {quincena}")
        if mes not in _MESES_INV:
            raise ValueError(f"mes debe estar entre 1 y 12, se recibió {mes}")
        if año <= 0:
            raise ValueError(f"año debe ser un entero positivo, se recibió {año}")

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
        """Convierte el periodo a `pd.Timestamp` usando la convención quincenal.

        Returns:
            Un timestamp con día 1 para `1Q` y día 16 para `2Q`.

        Ver: docs/diseño.md §5.3, §11.6
        """
        dia = 1 if self.quincena == 1 else 16
        return pd.Timestamp(year=self.año, month=self.mes, day=dia)
