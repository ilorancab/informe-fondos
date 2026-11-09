"""Gráficos del informe, construidos con Plotly.

Cada función devuelve un fragmento HTML (un ``<div>``) que se inserta en la
plantilla. El JavaScript de Plotly se incluye una sola vez en el informe.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from ..config import COLORES
from .formato import numero, porcentaje

FUENTE = (
    "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
    "Helvetica, Arial, sans-serif"
)

_CONFIG = {
    "displayModeBar": False,
    "responsive": True,
    "scrollZoom": False,
}


def _html(fig: go.Figure) -> str:
    return pio.to_html(
        fig,
        include_plotlyjs=False,
        full_html=False,
        config=_CONFIG,
        default_width="100%",
    )


def _base(alto: int = 340, superior: int = 28) -> dict:
    return dict(
        height=alto,
        template=None,
        margin=dict(l=56, r=18, t=superior, b=36),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FUENTE, size=12, color="#475569"),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#e2e8f0",
            font=dict(family=FUENTE, size=12, color="#0f172a"),
        ),
        showlegend=False,
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            linecolor="#e2e8f0",
            tickcolor="#e2e8f0",
            ticks="outside",
            ticklen=4,
            tickfont=dict(color="#64748b"),
        ),
        yaxis=dict(
            gridcolor="#eef2f7",
            zeroline=False,
            linecolor="#e2e8f0",
            ticks="",
            ticklen=0,
            tickfont=dict(color="#64748b"),
        ),
    )


def evolucion(serie: pd.Series, divisa: str) -> str:
    """Valor liquidativo a lo largo del tiempo."""
    figura = go.Figure()
    figura.add_trace(
        go.Scatter(
            x=serie.index,
            y=serie.to_numpy(),
            mode="lines",
            line=dict(color=COLORES["principal"], width=2),
            customdata=[numero(valor, 2) for valor in serie.to_numpy()],
            hovertemplate=(
                "%{x|%d/%m/%Y}<br><b>%{customdata} " + divisa + "</b><extra></extra>"
            ),
        )
    )

    figura.update_layout(**_base(380, superior=58))
    figura.update_xaxes(
        rangeselector=dict(
            buttons=[
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="1a", step="year", stepmode="backward"),
                dict(count=3, label="3a", step="year", stepmode="backward"),
                dict(count=5, label="5a", step="year", stepmode="backward"),
                dict(step="all", label="Todo"),
            ],
            bgcolor="white",
            bordercolor="#e2e8f0",
            borderwidth=1,
            font=dict(color="#475569", size=11),
            activecolor="#ccfbf1",
            x=0,
            y=1.12,
        )
    )
    return _html(figura)


def comparativa(datos: dict, nombre_referencia: str) -> str:
    """Fondo frente al índice de referencia, ambos normalizados a 100."""
    figura = go.Figure()
    figura.add_trace(
        go.Scatter(
            x=datos["fechas"],
            y=datos["fondo"],
            mode="lines",
            name="Fondo",
            line=dict(color=COLORES["principal"], width=2),
            hovertemplate="Fondo: <b>%{y:.1f}</b><extra></extra>",
        )
    )
    figura.add_trace(
        go.Scatter(
            x=datos["fechas"],
            y=datos["referencia"],
            mode="lines",
            name=nombre_referencia,
            line=dict(color=COLORES["secundario"], width=1.6, dash="dot"),
            hovertemplate=f"{nombre_referencia}: <b>%{{y:.1f}}</b><extra></extra>",
        )
    )

    figura.update_layout(**_base(340, superior=42))
    figura.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0,
            font=dict(size=11, color="#475569"),
        ),
    )
    figura.update_yaxes(title=None, ticksuffix="")
    return _html(figura)


def caidas(serie: pd.Series) -> str:
    """Drawdown: distancia porcentual al máximo histórico anterior."""
    caidas = serie / serie.cummax() - 1

    figura = go.Figure()
    figura.add_trace(
        go.Scatter(
            x=caidas.index,
            y=caidas.to_numpy() * 100,
            mode="lines",
            line=dict(color=COLORES["negativo"], width=1.4),
            fill="tozeroy",
            fillcolor="rgba(220,38,38,0.10)",
            customdata=[porcentaje(valor) for valor in caidas.to_numpy()],
            hovertemplate="%{x|%d/%m/%Y}<br><b>%{customdata}</b><extra></extra>",
        )
    )

    figura.update_layout(**_base(300))
    figura.update_yaxes(ticksuffix=" %", tickformat=".0f")
    return _html(figura)


def rentabilidades_anuales(filas: list[dict]) -> str:
    """Barras verdes y rojas con la rentabilidad de cada año natural."""
    anios = [
        f"{fila['anio']}*" if fila["parcial"] else fila["anio"] for fila in filas
    ]
    valores = [(fila["rentabilidad"] or 0) * 100 for fila in filas]
    colores = [
        COLORES["positivo"] if valor >= 0 else COLORES["negativo"] for valor in valores
    ]
    etiquetas = [
        porcentaje(fila["rentabilidad"]) if fila["rentabilidad"] is not None else ""
        for fila in filas
    ]

    figura = go.Figure()
    figura.add_trace(
        go.Bar(
            x=anios,
            y=valores,
            marker_color=colores,
            marker_line_width=0,
            text=etiquetas,
            textposition="outside",
            textfont=dict(size=11, color="#475569"),
            customdata=etiquetas,
            hovertemplate="%{x}<br><b>%{customdata}</b><extra></extra>",
        )
    )

    figura.update_layout(**_base(320))
    figura.update_layout(bargap=0.35)
    figura.update_xaxes(type="category", tickangle=0)
    figura.update_yaxes(ticksuffix=" %", tickformat=".0f", zeroline=True, zerolinecolor="#cbd5e1")
    return _html(figura)


def matriz_mensual(datos: dict) -> str:
    """Mapa de calor con la rentabilidad de cada mes."""
    meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
             "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    z = []
    texto = []
    for fila in datos["filas"]:
        z.append([None if v is None else v * 100 for v in fila["valores"]])
        texto.append(["" if v is None else porcentaje(v, 1, signo=False) for v in fila["valores"]])

    figura = go.Figure(
        data=go.Heatmap(
            z=z,
            x=meses,
            y=[fila["anio"] for fila in datos["filas"]],
            text=texto,
            texttemplate="%{text}",
            textfont=dict(size=10, color="#334155"),
            colorscale=[
                [0.0, "#fca5a5"],
                [0.5, "#f8fafc"],
                [1.0, "#86efac"],
            ],
            zmid=0,
            showscale=False,
            xgap=2,
            ygap=2,
            hovertemplate="%{y} %{x}<br><b>%{text}</b><extra></extra>",
        )
    )

    figura.update_layout(**_base(max(170, 70 + 36 * len(datos["filas"]))))
    figura.update_layout(margin=dict(l=56, r=18, t=34, b=36))
    figura.update_yaxes(
        autorange="reversed",
        type="category",
        showgrid=False,
        range=[len(datos["filas"]) - 0.5, -0.5],
    )
    figura.update_xaxes(side="top", showgrid=False, ticks="")
    return _html(figura)


def simulacion_dca(datos: dict, divisa: str) -> str:
    """Valor de la cartera frente al dinero aportado."""
    figura = go.Figure()
    figura.add_trace(
        go.Scatter(
            x=datos["fechas"],
            y=datos["aportado"],
            mode="lines",
            name="Aportado",
            line=dict(color="#94a3b8", width=1.6, dash="dot"),
            hovertemplate="Aportado: <b>%{y:,.0f}</b><extra></extra>",
        )
    )
    figura.add_trace(
        go.Scatter(
            x=datos["fechas"],
            y=datos["valor"],
            mode="lines",
            name="Valor",
            line=dict(color=COLORES["principal"], width=2),
            fill="tonexty",
            fillcolor="rgba(13,148,136,0.10)",
            hovertemplate="Valor: <b>%{y:,.0f}</b><extra></extra>",
        )
    )

    figura.update_layout(**_base(320, superior=42))
    figura.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0,
            font=dict(size=11, color="#475569"),
        ),
    )
    figura.update_yaxes(ticksuffix=f" {divisa}")
    return _html(figura)


def inflacion(serie: pd.Series, ipc: pd.Series) -> str:
    """Fondo, IPC y poder de compra real, normalizados a 100."""
    ipc_en_fechas = ipc.reindex(serie.index, method="ffill")
    unidas = pd.concat(
        [serie.rename("fondo"), ipc_en_fechas.rename("ipc")],
        axis=1,
        join="inner",
    ).dropna()
    if len(unidas) < 2:
        return ""

    normalizadas = unidas / unidas.iloc[0] * 100
    real = normalizadas["fondo"] / normalizadas["ipc"] * 100

    figura = go.Figure()
    figura.add_trace(
        go.Scatter(
            x=normalizadas.index,
            y=normalizadas["fondo"],
            mode="lines",
            name="Fondo (nominal)",
            line=dict(color=COLORES["principal"], width=2),
            hovertemplate="Fondo: <b>%{y:.1f}</b><extra></extra>",
        )
    )
    figura.add_trace(
        go.Scatter(
            x=normalizadas.index,
            y=normalizadas["ipc"],
            mode="lines",
            name="IPC España",
            line=dict(color=COLORES["secundario"], width=1.6, dash="dot"),
            hovertemplate="IPC: <b>%{y:.1f}</b><extra></extra>",
        )
    )
    figura.add_trace(
        go.Scatter(
            x=real.index,
            y=real,
            mode="lines",
            name="Fondo en euros de hoy",
            line=dict(color="#94a3b8", width=1.6, dash="dash"),
            hovertemplate="Poder de compra: <b>%{y:.1f}</b><extra></extra>",
        )
    )

    figura.update_layout(**_base(340, superior=42))
    figura.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0,
            font=dict(size=11, color="#475569"),
        ),
    )
    return _html(figura)


def cartera_comparativa(fechas, series: list[tuple[str, list[float]]]) -> str:
    """Compara varios fondos normalizados a 100 desde una fecha común."""
    figura = go.Figure()
    for indice, (nombre, valores) in enumerate(series):
        color = COLORES["serie"][indice % len(COLORES["serie"])]
        figura.add_trace(
            go.Scatter(
                x=fechas,
                y=valores,
                mode="lines",
                name=nombre,
                line=dict(color=color, width=2),
                hovertemplate=nombre + ": <b>%{y:.1f}</b><extra></extra>",
            )
        )

    figura.update_layout(**_base(360, superior=42))
    figura.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0,
            font=dict(size=11, color="#475569"),
        ),
    )
    return _html(figura)
