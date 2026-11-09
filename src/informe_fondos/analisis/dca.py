"""Simulación de aportaciones periódicas (DCA)."""

from __future__ import annotations

import pandas as pd


def _tir(flujos: list[tuple[pd.Timestamp, float]]) -> float | None:
    """Tasa interna de retorno anualizada por bisección."""
    if len(flujos) < 2:
        return None

    inicio = flujos[0][0]

    def van(tasa: float) -> float:
        return sum(
            importe / (1 + tasa) ** ((fecha - inicio).days / 365.25)
            for fecha, importe in flujos
        )

    bajo, alto = -0.9999, 10.0
    try:
        if van(bajo) * van(alto) > 0:
            return None
        for _ in range(200):
            medio = (bajo + alto) / 2
            if van(bajo) * van(medio) <= 0:
                alto = medio
            else:
                bajo = medio
    except (OverflowError, ZeroDivisionError):
        return None

    return (bajo + alto) / 2


def simular_dca(
    serie: pd.Series, aportacion: float, frecuencia: str = "mensual"
) -> dict | None:
    """Simula invertir ``aportacion`` al inicio de cada mes, semana o quincena."""
    if len(serie) < 30 or aportacion <= 0:
        return None

    reglas = {"mensual": "MS", "semanal": "W-MON", "quincenal": "2W-MON"}
    regla = reglas.get(frecuencia, "MS")
    compras = serie.resample(regla, label="left", closed="left").first().dropna()
    if compras.empty:
        return None

    participaciones = aportacion / compras
    acumuladas = participaciones.cumsum()

    en_cada_dia = acumuladas.reindex(serie.index, method="ffill").fillna(0.0)
    valor = en_cada_dia * serie

    aportado = pd.Series(aportacion, index=compras.index).cumsum()
    aportado = aportado.reindex(serie.index, method="ffill").fillna(0.0)

    invertido_total = float(len(compras) * aportacion)
    valor_final = float(valor.iloc[-1])
    beneficio = valor_final - invertido_total

    flujos = [(fecha, -aportacion) for fecha in compras.index]
    flujos.append((serie.index[-1], valor_final))

    participaciones_unicas = invertido_total / float(serie.iloc[0])
    valor_si_unica = participaciones_unicas * float(serie.iloc[-1])

    return {
        "aportacion": aportacion,
        "frecuencia": frecuencia,
        "num_aportaciones": int(len(compras)),
        "invertido": invertido_total,
        "valor_final": valor_final,
        "beneficio": beneficio,
        "rentabilidad": valor_final / invertido_total - 1,
        "tir": _tir(flujos),
        "valor_si_unica": valor_si_unica,
        "rentabilidad_si_unica": valor_si_unica / invertido_total - 1,
        "fechas": list(valor.index),
        "valor": list(valor.to_numpy()),
        "aportado": list(aportado.to_numpy()),
        "primera_compra": compras.index[0],
        "ultima_compra": compras.index[-1],
    }
