"""Formato de números, porcentajes y fechas al estilo español."""

from __future__ import annotations

import pandas as pd

_SIMBOLOS = {"EUR": "€", "USD": "USD", "GBP": "£", "CHF": "CHF", "JPY": "JPY"}


def _cambiar_separadores(texto: str) -> str:
    """Convierte 1,234.56 en 1.234,56."""
    return texto.replace(",", "\u0000").replace(".", ",").replace("\u0000", ".")


def numero(valor, decimales: int = 2, signo: bool = False) -> str:
    if valor is None or (isinstance(valor, float) and valor != valor):
        return "—"
    if abs(valor) < 10 ** (-(decimales + 2)):
        valor = 0.0
    formato = f"{{:{'+' if signo else ''},.{decimales}f}}"
    return _cambiar_separadores(formato.format(valor))


def porcentaje(valor, decimales: int = 1, signo: bool = True) -> str:
    if valor is None or (isinstance(valor, float) and valor != valor):
        return "—"
    if abs(valor) < 10 ** (-(decimales + 2)):
        valor = 0.0
    return numero(valor * 100, decimales, signo=signo) + " %"


def dinero(valor, divisa: str = "EUR", decimales: int = 2) -> str:
    if valor is None:
        return "—"
    simbolo = _SIMBOLOS.get((divisa or "").upper())
    texto = numero(valor, decimales)
    if simbolo == "€":
        return f"{texto} €"
    if simbolo in ("£", "$"):
        return f"{texto} {simbolo}"
    return f"{texto} {divisa}" if divisa else texto


def fecha(valor, formato: str = "%d/%m/%Y") -> str:
    if valor is None:
        return "—"
    if isinstance(valor, str):
        return valor
    return pd.Timestamp(valor).strftime(formato)


def fecha_larga(valor) -> str:
    return fecha(valor, "%d de %B de %Y")


def clase(valor) -> str:
    """Clase CSS según el signo de un número."""
    if valor is None:
        return "neu"
    if valor > 0:
        return "pos"
    if valor < 0:
        return "neg"
    return "neu"
