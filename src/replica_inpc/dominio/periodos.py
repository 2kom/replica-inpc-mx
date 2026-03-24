from __future__ import annotations

import functools

import pandas as pd

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
class Periodo:
    def __init__(self, año: int, mes: int, quincena: int) -> None:
        # Validaciones basicas
        if quincena not in (1, 2):
            raise ValueError(f"quincena debe ser 1 o 2, se recibió {quincena}")
        if mes not in _MESES_INV:
            raise ValueError(f"mes debe estar entre 1 y 12, se recibió {mes}")
        if año <= 0:
            raise ValueError(f"año debe ser un entero positivo, se recibió {año}")

        # Asignación de atributos
        self.año = año
        self.mes = mes
        self.quincena = quincena

    def __eq__(self, other: object) -> bool:  # define ==
        if not isinstance(other, Periodo):
            return NotImplemented
        return (self.año, self.mes, self.quincena) == (
            other.año,
            other.mes,
            other.quincena,
        )

    def __lt__(self, other: Periodo) -> bool:  # define <
        if not isinstance(other, Periodo):
            return NotImplemented
        return (self.año, self.mes, self.quincena) < (
            other.año,
            other.mes,
            other.quincena,
        )

    def __hash__(self) -> int:
        # define hash(), permite usar Periodo como clave en diccionarios y columna de DataFrame
        return hash((self.año, self.mes, self.quincena))

    def __str__(self) -> str:
        # define str(), devuelve en formato "1Q Ene 2024" o "2Q Ene 2024"
        return f"{self.quincena}Q {_MESES_INV[self.mes]} {self.año}"

    def __repr__(self) -> str:
        # define repr(), devuelve en formato Periodo(2024, 1, 1)
        return f"Periodo({self.año}, {self.mes}, {self.quincena})"

    @classmethod
    def desde_str(cls, periodo_str: str) -> Periodo:
        # parsea un string en formato "1Q Mes AAAA" y devuelve un objeto Periodo
        try:
            quincena_str, mes_str, año_str = periodo_str.split(" ")
            quincena = int(quincena_str[0])
            mes = _MESES[mes_str]
            año = int(año_str)
            return cls(año, mes, quincena)
        except Exception as e:
            raise ValueError(
                f"Formato de periodo inválido: '{periodo_str}'. Se esperaba formato '1Q Mes AAAA' o '2Q Mes AAAA'"
            ) from e

    def to_timestamp(self) -> pd.Timestamp:
        # 1Q -> dia 1, 2Q -> dia 16
        dia = 1 if self.quincena == 1 else 16
        return pd.Timestamp(year=self.año, month=self.mes, day=dia)
