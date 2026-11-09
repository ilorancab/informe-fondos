"""Comparación con un índice de referencia."""

from __future__ import annotations

import pandas as pd

from .metricas import dias_entre_datos, recortar


def comparar(serie: pd.Series, referencia: pd.Series, periodo: str = "max") -> dict | None:
    """Compara dos series normalizadas a 100 en su primer día común."""
    a = recortar(serie, periodo)
    b = recortar(referencia, periodo)

    unidas = pd.concat([a, b], axis=1, join="inner").dropna()
    if len(unidas) < 2:
        return None

    unidas.columns = ["fondo", "referencia"]
    normalizadas = unidas / unidas.iloc[0] * 100
    retornos = unidas.pct_change().dropna()

    correlacion = None
    beta = None
    frecuencia_correlacion = "diaria"
    if len(retornos) >= 20:
        # El valor liquidativo del fondo y el precio del ETF no se fijan a la
        # misma hora; en diario eso infravalora la correlación. Se compara en
        # semanal (lo habitual) o mensual si el fondo solo publica ese ritmo.
        dias_fondo = dias_entre_datos(unidas["fondo"])
        dias_ref = dias_entre_datos(unidas["referencia"])
        dias = max(d for d in (dias_fondo, dias_ref, 1) if d)
        if dias > 9:
            base = unidas.resample("ME").last().pct_change().dropna()
            frecuencia_correlacion = "mensual"
        else:
            base = unidas.resample("W-FRI").last().pct_change().dropna()
            frecuencia_correlacion = "semanal"
        if len(base) < 12:
            base = retornos
            frecuencia_correlacion = "diaria"
        correlacion = float(base["fondo"].corr(base["referencia"]))
        varianza = float(base["referencia"].var())
        if varianza:
            beta = float(base["fondo"].cov(base["referencia"]) / varianza)

    return {
        "fechas": list(normalizadas.index),
        "fondo": list(normalizadas["fondo"].to_numpy()),
        "referencia": list(normalizadas["referencia"].to_numpy()),
        "rentabilidad_fondo": float(unidas["fondo"].iloc[-1] / unidas["fondo"].iloc[0] - 1),
        "rentabilidad_referencia": float(
            unidas["referencia"].iloc[-1] / unidas["referencia"].iloc[0] - 1
        ),
        "correlacion": correlacion,
        "beta": beta,
        "frecuencia_correlacion": frecuencia_correlacion,
        "desde": unidas.index[0],
    }
