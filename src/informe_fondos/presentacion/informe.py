"""Construcción del informe HTML a partir de las series de precios."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.offline as plotly_offline
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .. import analisis
from ..config import PLANTILLAS, SALIDA
from . import formato, graficos


# --------------------------------------------------------------------------
# Jinja
# --------------------------------------------------------------------------

def _entorno() -> Environment:
    entorno = Environment(
        loader=FileSystemLoader(PLANTILLAS),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    entorno.filters.update(
        numero=formato.numero,
        porcentaje=formato.porcentaje,
        dinero=formato.dinero,
        fecha=formato.fecha,
        clase=formato.clase,
    )
    return entorno


def _nombre_archivo(texto: str) -> str:
    limpio = re.sub(r"[^A-Za-z0-9._-]+", "-", texto).strip("-")
    return limpio.lower() or "fondo"


# --------------------------------------------------------------------------
# Ficha de cada fondo
# --------------------------------------------------------------------------

def _kpi(etiqueta: str, valor: str, pie: str = "", clase: str = "neu") -> dict:
    return {"etiqueta": etiqueta, "valor": valor, "pie": pie, "clase": clase}


def construir_ficha(
    instrumento,
    serie: pd.Series,
    periodo: str,
    benchmark_serie: pd.Series | None = None,
    benchmark_nombre: str | None = None,
    aportacion: float = 200.0,
    frecuencia_aportacion: str = "mensual",
    tasa_libre_riesgo: float = 2.0,
    ipc: pd.Series | None = None,
) -> dict:
    """Reúne métricas, tablas y gráficos de un fondo."""
    serie_periodo = analisis.recortar(serie, periodo)
    metricas = analisis.metricas(serie, tasa_libre_riesgo)
    max_caida = float(metricas.get("max_caida") or 0.0)
    fecha_max_caida = metricas.get("fecha_max_caida")
    tabla = analisis.tabla_rentabilidades(serie, ipc)
    anuales = analisis.rentabilidades_anuales(serie)
    mensual = analisis.matriz_mensual(serie)
    dca = analisis.simular_dca(serie_periodo, aportacion, frecuencia_aportacion)
    inflacion_resumen = analisis.resumen_inflacion(serie_periodo, ipc)
    grafico_inflacion = (
        graficos.inflacion(serie_periodo, ipc) if inflacion_resumen else None
    )
    comparacion = (
        analisis.comparar(serie, benchmark_serie, periodo)
        if benchmark_serie is not None
        else None
    )

    por_codigo = {fila["codigo"]: fila for fila in tabla}
    ytd = por_codigo["ytd"]["rentabilidad"]
    un_anio = por_codigo["1a"]["rentabilidad"]
    tres_anios = por_codigo["3a"]

    kpis = [
        _kpi(
            "Último valor",
            formato.dinero(float(serie.iloc[-1]), instrumento.divisa),
            formato.fecha(serie.index[-1]),
            "neu",
        ),
        _kpi(
            "Año en curso",
            formato.porcentaje(ytd),
            "desde el 31/12",
            formato.clase(ytd),
        ),
        _kpi(
            "Últimos 12 meses",
            formato.porcentaje(un_anio),
            "rentabilidad simple" if un_anio is not None else "histórico insuficiente",
            formato.clase(un_anio),
        ),
        _kpi(
            "3 años (anualizada)",
            formato.porcentaje(tres_anios["anualizada"]),
            "media geométrica anual"
            if tres_anios["anualizada"] is not None
            else "histórico insuficiente",
            formato.clase(tres_anios["anualizada"]),
        ),
        _kpi(
            "Volatilidad 3 años",
            formato.porcentaje(metricas.get("vol_3a"), signo=False),
            "riesgo anualizado" if metricas.get("vol_3a") is not None else "histórico insuficiente",
            "neu",
        ),
        _kpi(
            "Máxima caída histórica",
            formato.porcentaje(max_caida),
            f"peor momento: {formato.fecha(fecha_max_caida)}",
            "neg" if max_caida else "neu",
        ),
    ]

    mejores = [fila for fila in anuales if fila["rentabilidad"] is not None]
    mejor_anio = max(mejores, key=lambda fila: fila["rentabilidad"]) if mejores else None
    peor_anio = min(mejores, key=lambda fila: fila["rentabilidad"]) if mejores else None

    lecturas = []
    cinco_anios = por_codigo["5a"]
    if cinco_anios["anualizada"] is not None:
        lecturas.append(
            f"En los últimos cinco años ha rentado un "
            f"{formato.porcentaje(cinco_anios['anualizada'])} anual compuesto "
            f"({formato.porcentaje(cinco_anios['rentabilidad'])} acumulado)."
        )
    elif un_anio is not None:
        lecturas.append(
            f"En el último año ha rentado un {formato.porcentaje(un_anio)}."
        )

    if comparacion and benchmark_nombre and comparacion.get("correlacion") is not None:
        diferencia = (
            comparacion["rentabilidad_fondo"]
            - comparacion["rentabilidad_referencia"]
        )
        posicion = "por encima" if diferencia >= 0 else "por debajo"
        lecturas.append(
            f"Frente a {benchmark_nombre}, ha quedado {posicion} en "
            f"{formato.porcentaje(abs(diferencia), signo=False)} durante el periodo "
            f"(correlación {comparacion.get('frecuencia_correlacion', 'diaria')} "
            f"{formato.numero(comparacion['correlacion'], 2)})."
        )

    if max_caida < 0:
        recuperacion = 1 / (1 + max_caida) - 1
        lecturas.append(
            f"Su peor caída desde un máximo fue del "
            f"{formato.porcentaje(max_caida)}; volver a ese nivel exigía una "
            f"subida del {formato.porcentaje(recuperacion, signo=False)}."
        )

    if metricas.get("vol_3a") is not None:
        lecturas.append(
            f"La volatilidad anualizada a tres años es del "
            f"{formato.porcentaje(metricas['vol_3a'], signo=False)}: mide "
            "cuánto oscila el valor, no cuánto gana."
        )

    ficha = {
        "nombre": instrumento.nombre,
        "isin": instrumento.isin,
        "simbolo": instrumento.simbolo,
        "divisa": instrumento.divisa,
        "mercado": instrumento.mercado,
        "tipo": instrumento.tipo,
        "frecuencia": metricas.get("frecuencia"),
        "frecuencia_plural": metricas.get("frecuencia_plural"),
        "fecha_datos": serie.index[-1],
        "fecha_inicio": serie.index[0],
        "num_datos": int(len(serie)),
        "anios_historial": metricas.get("anios_historial"),
        "kpis": kpis,
        "lecturas": lecturas,
        "rentabilidades": tabla,
        "anuales": anuales,
        "mejor_anio": mejor_anio,
        "peor_anio": peor_anio,
        "mensual": mensual,
        "dca": dca,
        "ipc_activo": ipc is not None,
        "inflacion": inflacion_resumen,
        "comparacion": comparacion,
        "benchmark_nombre": benchmark_nombre,
        "graficos": {
            "evolucion": graficos.evolucion(serie_periodo, instrumento.divisa),
            "caidas": graficos.caidas(serie),
            "anuales": graficos.rentabilidades_anuales(anuales),
            "mensual": graficos.matriz_mensual(mensual),
            "dca": graficos.simulacion_dca(dca, instrumento.divisa) if dca else None,
            "inflacion": grafico_inflacion or None,
            "comparativa": (
                graficos.comparativa(comparacion, benchmark_nombre)
                if comparacion
                else None
            ),
        },
        "metricas": metricas,
        "max_caida": max_caida,
        "fecha_max_caida": fecha_max_caida,
        "periodo": periodo,
        "aportacion": aportacion,
        "frecuencia_aportacion": frecuencia_aportacion,
        "aporta_etiqueta": {
            "mensual": "al mes",
            "semanal": "a la semana",
            "quincenal": "cada dos semanas",
        }.get(frecuencia_aportacion, "al mes"),
        "aporta_periodo": {
            "mensual": "mes",
            "semanal": "semana",
            "quincenal": "quincena",
        }.get(frecuencia_aportacion, "mes"),
        "tasa_libre_riesgo": tasa_libre_riesgo,
    }
    return ficha


def _corto(texto: str, maximo: int = 34) -> str:
    texto = (texto or "").strip()
    return texto if len(texto) <= maximo else texto[: maximo - 1].rstrip() + "…"


def comparativa_cartera(fichas: list[dict], series: list[pd.Series], periodo: str):
    """Serie normalizada a 100 de varios fondos para compararlos entre sí."""
    if len(series) < 2:
        return None

    recortes = [analisis.recortar(serie, periodo) for serie in series]
    unidas = pd.concat(recortes, axis=1, join="inner").dropna()
    if len(unidas) < 2:
        return None

    normalizadas = unidas / unidas.iloc[0] * 100
    etiquetas = [_corto(ficha["nombre"]) for ficha in fichas]
    identificadores = [ficha["isin"] or ficha["simbolo"] for ficha in fichas]
    return {
        "fechas": list(normalizadas.index),
        "series": [
            (etiqueta, list(normalizadas.iloc[:, indice].to_numpy()))
            for indice, etiqueta in enumerate(etiquetas)
        ],
        "grafico": graficos.cartera_comparativa(
            list(normalizadas.index),
            [
                (etiqueta, list(normalizadas.iloc[:, indice].to_numpy()))
                for indice, etiqueta in enumerate(etiquetas)
            ],
        ),
        "filas": [
            {
                "nombre": ficha["nombre"],
                "etiqueta": identificadores[indice],
                "rentabilidad": float(
                    normalizadas.iloc[-1, indice] / 100 - 1
                ),
            }
            for indice, (ficha, etiqueta) in enumerate(zip(fichas, etiquetas, strict=True))
        ],
        "desde": unidas.index[0],
    }


# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------

def generar(
    fichas: list[dict],
    comparativa: dict | None,
    benchmark_nombre: str | None,
    periodo: str,
    ruta: Path | None = None,
    cdn: bool = False,
    benchmark_divisa: str | None = None,
    tema: str = "auto",
) -> Path:
    """Renderiza la plantilla y escribe el informe HTML."""
    ahora = datetime.now()
    if ruta is None:
        if len(fichas) == 1:
            base = fichas[0]["isin"] or fichas[0]["simbolo"]
        else:
            base = "cartera"
        ruta = SALIDA / f"informe-{_nombre_archivo(base)}-{ahora:%Y%m%d}.html"
    ruta = Path(ruta).expanduser()
    ruta.parent.mkdir(parents=True, exist_ok=True)

    if cdn:
        version = plotly_offline.get_plotlyjs_version()
        plotly_js = f'<script src="https://cdn.plot.ly/plotly-{version}.min.js"></script>'
    else:
        plotly_js = f"<script>{plotly_offline.get_plotlyjs()}</script>"

    titulo = (
        fichas[0]["nombre"] if len(fichas) == 1 else f"Cartera de {len(fichas)} fondos"
    )

    contexto = {
        "titulo": titulo,
        "fondos": fichas,
        "comparativa": comparativa,
        "benchmark_nombre": benchmark_nombre,
        "benchmark_divisa": benchmark_divisa,
        "periodo": periodo,
        "fecha_generacion": ahora,
        "plotly_js": plotly_js,
        "cdn": cdn,
        "tema": tema,
    }

    html = _entorno().get_template("informe.html.j2").render(**contexto)
    ruta.write_text(html, encoding="utf-8")
    return ruta
