"""Pruebas básicas de los cálculos del informe."""

from __future__ import annotations

import pandas as pd
import pytest

from informe_fondos import analisis
from informe_fondos.datos import inflacion


def _serie(valores, inicio="2020-01-01"):
    return pd.Series(
        valores,
        index=pd.date_range(inicio, periods=len(valores), freq="D"),
        dtype="float64",
    )


def test_rentabilidad_y_anualizada():
    serie = _serie([100, 110])
    datos = analisis.rentabilidad(serie, "max")
    assert datos is not None
    assert datos["rentabilidad"] == pytest.approx(0.10)
    assert datos["dias"] == 1
    assert datos["anualizada"] is None


def test_caida_maxima():
    serie = _serie([100, 120, 60, 90])
    caidas = analisis.serie_caidas(serie)
    assert caidas.min() == pytest.approx(-0.5)
    assert caidas.idxmin() == serie.index[2]


def test_tabla_incluye_inflacion_y_real():
    serie = pd.Series(
        [100, 110],
        index=pd.to_datetime(["2020-01-01", "2020-02-01"]),
    )
    ipc = pd.Series(
        [100.0, 102.0],
        index=pd.to_datetime(["2020-01-01", "2020-02-01"]),
    )
    filas = analisis.tabla_rentabilidades(serie, ipc)
    inicio = next(fila for fila in filas if fila["codigo"] == "max")
    assert inicio["rentabilidad"] == pytest.approx(0.10)
    assert inicio["inflacion"] == pytest.approx(0.02)
    assert inicio["real"] == pytest.approx(1.10 / 1.02 - 1)


def test_simulacion_dca():
    serie = _serie([100] * 40 + [110] * 10)
    resultado = analisis.simular_dca(serie, 100, frecuencia="mensual")
    assert resultado is not None
    assert resultado["num_aportaciones"] >= 1
    assert resultado["invertido"] == pytest.approx(
        resultado["num_aportaciones"] * 100
    )
    assert resultado["valor_final"] > 0


def test_comparacion_identica():
    serie = _serie([100, 101, 99, 102, 105] * 30)
    datos = analisis.comparar(serie, serie, "max")
    assert datos is not None
    assert datos["correlacion"] == pytest.approx(1.0)
    assert datos["beta"] == pytest.approx(1.0)


def test_rentabilidad_real():
    assert inflacion.real(0.10, 0.04) == pytest.approx(1.10 / 1.04 - 1)
    assert inflacion.real(None, 0.04) is None
    assert inflacion.real(0.10, None) is None
