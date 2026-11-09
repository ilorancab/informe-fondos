"""Cálculos del informe: rentabilidades, riesgo, comparación y DCA."""

from .comparacion import comparar
from .dca import simular_dca
from .metricas import (
    PERIODOS,
    dias_entre_datos,
    matriz_mensual,
    metricas,
    recortar,
    rentabilidad,
    rentabilidades_anuales,
    resumen_inflacion,
    serie_caidas,
    tabla_rentabilidades,
)
from .posiciones import analizar_posiciones

__all__ = [
    "PERIODOS",
    "analizar_posiciones",
    "comparar",
    "dias_entre_datos",
    "matriz_mensual",
    "metricas",
    "recortar",
    "rentabilidad",
    "rentabilidades_anuales",
    "resumen_inflacion",
    "serie_caidas",
    "simular_dca",
    "tabla_rentabilidades",
]
