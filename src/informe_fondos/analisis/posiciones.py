"""Rentabilidad de las mayores posiciones de un fondo o ETF."""

from __future__ import annotations

from ..datos import fuentes


def analizar_posiciones(
    simbolo: str,
    desde,
    hasta,
    limite: int = 10,
    minimo: int = 5,
) -> dict | None:
    """Compara la evolución de las mayores posiciones del fondo.

    Devuelve las posiciones ordenadas de mejor a peor rentabilidad en el
    periodo, o ``None`` si Yahoo no publica composición o no hay suficientes
    posiciones con datos.
    """
    composicion = fuentes.obtener_composicion(simbolo)
    if not composicion:
        return None

    filas = []
    for posicion in composicion[:limite]:
        try:
            serie = fuentes.descargar_ventana(
                posicion["simbolo"], desde, hasta
            )
        except fuentes.ErrorFuente:
            # Una posición sin datos no invalida el resto del gráfico.
            continue

        if len(serie) < 2:
            continue

        primero = float(serie.iloc[0])
        ultimo = float(serie.iloc[-1])
        if primero <= 0:
            continue

        filas.append(
            {
                **posicion,
                "rentabilidad": ultimo / primero - 1,
            }
        )

    if len(filas) < minimo:
        return None

    filas.sort(key=lambda fila: fila["rentabilidad"], reverse=True)
    return {
        "filas": filas,
        "desde": desde,
        "hasta": hasta,
        "total": len(filas),
        "mejor": filas[0],
        "peor": filas[-1],
    }
