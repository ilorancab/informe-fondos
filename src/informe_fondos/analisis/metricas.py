"""Métricas de rentabilidad, riesgo y comportamiento de una serie de precios."""

from __future__ import annotations

import math

import pandas as pd

from ..datos import inflacion

# (etiqueta visible, código interno)
PERIODOS = [
    ("1 día", "1d"),
    ("1 semana", "1w"),
    ("5 días", "5d"),
    ("1 mes", "1m"),
    ("3 meses", "3m"),
    ("6 meses", "6m"),
    ("Año en curso", "ytd"),
    ("1 año", "1a"),
    ("3 años", "3a"),
    ("5 años", "5a"),
    ("10 años", "10a"),
    ("Desde el inicio de la serie", "max"),
]


# --------------------------------------------------------------------------
# Utilidades básicas
# --------------------------------------------------------------------------

def _desplazamiento(codigo: str) -> pd.DateOffset | pd.Timedelta | None:
    if codigo == "max":
        return None
    if codigo == "ytd":
        return "ytd"
    numero, unidad = int(codigo[:-1]), codigo[-1]
    if unidad == "d":
        return pd.Timedelta(days=numero)
    if unidad == "w":
        return pd.Timedelta(weeks=numero)
    if unidad == "m":
        return pd.DateOffset(months=numero)
    if unidad == "a":
        return pd.DateOffset(years=numero)
    raise ValueError(f"Periodo no reconocido: {codigo}")


def recortar(serie: pd.Series, periodo: str) -> pd.Series:
    """Devuelve la parte de la serie que cubre el periodo pedido."""
    if serie.empty or periodo in ("max", "todo", None):
        return serie

    fin = serie.index[-1]
    desplazamiento = _desplazamiento(periodo)
    if desplazamiento == "ytd":
        inicio = pd.Timestamp(year=fin.year, month=1, day=1)
    else:
        inicio = fin - desplazamiento

    recorte = serie[serie.index >= inicio]
    return recorte if len(recorte) >= 2 else serie


def _punto_en(serie: pd.Series, fecha: pd.Timestamp):
    """Último (fecha, valor) anterior o igual a ``fecha``."""
    anteriores = serie[serie.index <= fecha]
    if anteriores.empty:
        return None
    return anteriores.index[-1], float(anteriores.iloc[-1])


# --------------------------------------------------------------------------
# Rentabilidades
# --------------------------------------------------------------------------

def rentabilidad(serie: pd.Series, codigo: str) -> dict | None:
    """Rentabilidad de un periodo y, si procede, su equivalente anualizado."""
    if len(serie) < 2:
        return None

    fin_fecha = serie.index[-1]
    fin_valor = float(serie.iloc[-1])

    if codigo == "1d":
        base_fecha, base_valor = serie.index[-2], float(serie.iloc[-2])
    elif codigo == "max":
        base_fecha, base_valor = serie.index[0], float(serie.iloc[0])
    else:
        desplazamiento = _desplazamiento(codigo)
        if desplazamiento == "ytd":
            objetivo = pd.Timestamp(year=fin_fecha.year - 1, month=12, day=31)
        else:
            objetivo = fin_fecha - desplazamiento
        punto = _punto_en(serie, objetivo)
        if punto is None:
            # Tolerancia: si el histórico empieza justo después del objetivo
            # (por ejemplo, faltan tres días para los cinco años), se usa el
            # primer dato disponible en lugar de dejar la celda vacía.
            if objetivo < serie.index[0] and (serie.index[0] - objetivo).days <= 31:
                base_fecha, base_valor = serie.index[0], float(serie.iloc[0])
            else:
                return None
        else:
            base_fecha, base_valor = punto

    dias = (fin_fecha - base_fecha).days
    if base_valor <= 0 or dias <= 0:
        return None

    bruta = fin_valor / base_valor - 1
    anualizada = None
    if dias >= 360 and codigo not in ("ytd",):
        anualizada = (1 + bruta) ** (365.25 / dias) - 1

    return {
        "codigo": codigo,
        "rentabilidad": bruta,
        "anualizada": anualizada,
        "dias": dias,
        "desde": base_fecha,
    }


def tabla_rentabilidades(
    serie: pd.Series, ipc: pd.Series | None = None
) -> list[dict]:
    """Lista de rentabilidades para todos los periodos predefinidos.

    Si se pasa el IPC, añade la inflación acumulada y la rentabilidad real de
    cada periodo.

    En series semanales o mensuales, los periodos de «1 día» y «1 semana»
    coincidirían con la observación anterior; se ajustan las etiquetas y se
    omiten las filas duplicadas.
    """
    dias = dias_entre_datos(serie)
    etiquetas = {codigo: etiqueta for etiqueta, codigo in PERIODOS}
    omitir: set[str] = set()

    if dias and dias > 3:
        if dias <= 9:
            etiquetas["1d"] = "1 semana"
            omitir.add("1w")
        elif dias <= 20:
            etiquetas["1d"] = "2 semanas"
            omitir.add("1w")
        else:
            omitir.update({"1d", "1w"})

    filas = []
    for etiqueta, codigo in PERIODOS:
        if codigo in omitir:
            continue
        datos = rentabilidad(serie, codigo)
        inflacion_periodo = None
        rentabilidad_real = None
        real_anualizada = None
        if datos and ipc is not None:
            inflacion_periodo = inflacion.acumulada(
                ipc, datos["desde"], serie.index[-1]
            )
            rentabilidad_real = inflacion.real(
                datos["rentabilidad"], inflacion_periodo
            )
            if datos["anualizada"] is not None:
                real_anualizada = inflacion.anualizar(
                    rentabilidad_real, datos["dias"]
                )
        filas.append(
            {
                "etiqueta": etiquetas[codigo],
                "codigo": codigo,
                "rentabilidad": datos["rentabilidad"] if datos else None,
                "anualizada": datos["anualizada"] if datos else None,
                "dias": datos["dias"] if datos else None,
                "inflacion": inflacion_periodo,
                "real": rentabilidad_real,
                "real_anualizada": real_anualizada,
            }
        )
    return filas


def resumen_inflacion(serie: pd.Series, ipc: pd.Series | None) -> dict | None:
    """Inflación acumulada y rentabilidad real del periodo seleccionado."""
    if ipc is None or len(serie) < 2:
        return None

    inicio = serie.index[0]
    fin = serie.index[-1]
    dias = (fin - inicio).days
    nominal = float(serie.iloc[-1] / serie.iloc[0] - 1)
    inflacion_periodo = inflacion.acumulada(ipc, inicio, fin)
    rentabilidad_real = inflacion.real(nominal, inflacion_periodo)

    hasta = ipc.index[ipc.index <= pd.Timestamp(fin).replace(day=1)]
    ipc_hasta = hasta[-1] if len(hasta) else None

    return {
        "inicio": inicio,
        "fin": fin,
        "dias": dias,
        "nominal": nominal,
        "inflacion": inflacion_periodo,
        "real": rentabilidad_real,
        "nominal_anual": inflacion.anualizar(nominal, dias) if dias >= 360 else None,
        "inflacion_anual": (
            inflacion.anualizar(inflacion_periodo, dias) if dias >= 360 else None
        ),
        "real_anual": (
            inflacion.anualizar(rentabilidad_real, dias) if dias >= 360 else None
        ),
        "ipc_hasta": ipc_hasta,
    }


# --------------------------------------------------------------------------
# Riesgo
# --------------------------------------------------------------------------

def serie_caidas(serie: pd.Series) -> pd.Series:
    """Caída porcentual respecto al máximo anterior (drawdown)."""
    return serie / serie.cummax() - 1


def dias_entre_datos(serie: pd.Series, max_muestras: int = 500) -> float | None:
    """Separación típica (en días) entre dos observaciones consecutivas.

    Muchos fondos europeos solo publican valor liquidativo semanal o mensual.
    Anualizar su volatilidad con 252 sesiones multiplicaría el riesgo por más
    de dos, así que la frecuencia se deduce de la propia serie.
    """
    if len(serie) < 3:
        return None
    muestra = serie.tail(max_muestras)
    dias = pd.Series(muestra.index).diff().dt.total_seconds().div(86400).dropna()
    dias = dias[dias > 0]
    if dias.empty:
        return None
    return float(dias.median())


def _factor_anualizacion(dias: float | None) -> float:
    """Número de observaciones al año para anualizar una volatilidad."""
    if not dias or dias < 1:
        return 252.0
    # Para datos diarios se usa el convencional de 252 sesiones; para el resto,
    # la frecuencia real (semanal ≈ 52, mensual ≈ 12, trimestral ≈ 4).
    return min(252.0, 365.25 / dias)


def _frecuencia(dias: float | None) -> str:
    if not dias:
        return "—"
    if dias <= 3:
        return "diaria"
    if dias <= 9:
        return "semanal"
    if dias <= 20:
        return "quincenal"
    if dias <= 45:
        return "mensual"
    if dias <= 100:
        return "trimestral"
    return "anual"


_FRECUENCIAS_PLURAL = {
    "diaria": "diarios",
    "semanal": "semanales",
    "quincenal": "quincenales",
    "mensual": "mensuales",
    "trimestral": "trimestrales",
    "anual": "anuales",
}


def _volatilidad(serie: pd.Series, anios: float) -> float | None:
    corte = serie.index[-1] - pd.DateOffset(years=anios)
    # Si el histórico empieza después del corte, no hay ventana suficiente.
    if serie.index[0] > corte + pd.Timedelta(days=30):
        return None
    recorte = serie[serie.index >= corte]
    rentabilidades = recorte.pct_change().dropna()
    if len(rentabilidades) < 20:
        return None
    factor = _factor_anualizacion(dias_entre_datos(recorte))
    return float(rentabilidades.std(ddof=1) * math.sqrt(factor))


def metricas(serie: pd.Series, tasa_libre_riesgo: float = 2.0) -> dict:
    """Métricas de riesgo y comportamiento de toda la serie disponible."""
    if len(serie) < 2:
        return {}

    caidas = serie_caidas(serie)
    fecha_peor = caidas.idxmin()

    retornos_diarios = serie.pct_change().dropna()
    retornos_mensuales = serie.resample("ME").last().dropna().pct_change().dropna()

    rent_1a = rentabilidad(serie, "1a")
    rent_3a = rentabilidad(serie, "3a")
    vol_1a = _volatilidad(serie, 1)
    vol_3a = _volatilidad(serie, 3)

    def sharpe(rent, vol):
        if rent is None or vol in (None, 0):
            return None
        anual = rent["anualizada"] if rent["anualizada"] is not None else rent["rentabilidad"]
        return (anual - tasa_libre_riesgo / 100) / vol

    anios = (serie.index[-1] - serie.index[0]).days / 365.25
    periodicidad = dias_entre_datos(serie)

    return {
        "max_caida": float(caidas.min()),
        "fecha_max_caida": fecha_peor,
        "caida_actual": float(caidas.iloc[-1]),
        "periodicidad": periodicidad,
        "frecuencia": _frecuencia(periodicidad),
        "frecuencia_plural": _FRECUENCIAS_PLURAL.get(
            _frecuencia(periodicidad), _frecuencia(periodicidad)
        ),
        "vol_1a": vol_1a,
        "vol_3a": vol_3a,
        "sharpe_1a": sharpe(rent_1a, vol_1a),
        "sharpe_3a": sharpe(rent_3a, vol_3a),
        "dias_positivos": float((retornos_diarios > 0).mean()) if len(retornos_diarios) else None,
        "mejor_dia": float(retornos_diarios.max()) if len(retornos_diarios) else None,
        "peor_dia": float(retornos_diarios.min()) if len(retornos_diarios) else None,
        "mejor_mes": float(retornos_mensuales.max()) if len(retornos_mensuales) else None,
        "peor_mes": float(retornos_mensuales.min()) if len(retornos_mensuales) else None,
        "anios_historial": anios,
        "num_datos": int(len(serie)),
    }


# --------------------------------------------------------------------------
# Rentabilidades por año y por mes
# --------------------------------------------------------------------------

def rentabilidades_anuales(serie: pd.Series) -> list[dict]:
    """Rentabilidad de cada año natural. El primer año puede ser parcial."""
    if serie.empty:
        return []

    filas = []
    anterior = None
    ultimo_anio = int(serie.index[-1].year)
    ultimo_dia = serie.index[-1]

    for anio, grupo in serie.groupby(serie.index.year):
        fin = float(grupo.iloc[-1])
        if anterior is None:
            base = float(grupo.iloc[0])
            parcial = grupo.index[0].dayofyear > 7
        else:
            base = anterior
            parcial = False

        if int(anio) == ultimo_anio and ultimo_dia.month < 12:
            parcial = True

        filas.append(
            {
                "anio": int(anio),
                "rentabilidad": (fin / base - 1) if base else None,
                "parcial": bool(parcial),
            }
        )
        anterior = fin

    return filas


def matriz_mensual(serie: pd.Series, max_anios: int = 12) -> dict:
    """Tabla año x mes con la rentabilidad de cada mes."""
    if len(serie) < 40:
        return {"anios": [], "filas": [], "mejor": None, "peor": None}

    mensual = serie.resample("ME").last().dropna()
    retornos = mensual.pct_change().dropna()

    datos = pd.DataFrame(
        {
            "anio": retornos.index.year,
            "mes": retornos.index.month,
            "retorno": retornos.to_numpy(),
        }
    )
    tabla = datos.pivot(index="anio", columns="mes", values="retorno")
    tabla = tabla.tail(max_anios)

    filas = []
    for anio, fila in tabla.iterrows():
        valores = [
            None if pd.isna(fila.get(mes)) else float(fila.get(mes))
            for mes in range(1, 13)
        ]
        filas.append({"anio": int(anio), "valores": valores})

    mejor = datos.loc[datos["retorno"].idxmax()]
    peor = datos.loc[datos["retorno"].idxmin()]

    return {
        "anios": [fila["anio"] for fila in filas],
        "filas": filas,
        "mejor": {
            "anio": int(mejor["anio"]),
            "mes": int(mejor["mes"]),
            "retorno": float(mejor["retorno"]),
        },
        "peor": {
            "anio": int(peor["anio"]),
            "mes": int(peor["mes"]),
            "retorno": float(peor["retorno"]),
        },
    }

